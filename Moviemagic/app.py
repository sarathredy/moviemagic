from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import boto3
import uuid
import json
import os
from botocore.exceptions import ClientError

app = Flask(__name__)  # ✅ Fixed __name__
# Use a static secret key
app.secret_key = 'your_static_secret_key_here'  # Replace with your own secret string

# AWS Configuration - read from environment variables for security
AWS_REGION = os.environ.get('AWS_REGION', 'us-east-1')

# SNS Topic ARN - make sure this is correct and has an email subscriber
SNS_TOPIC_ARN = 'arn:aws:sns:us-east-1:794038220422:movies'

# Initialize AWS services
dynamodb = boto3.resource('dynamodb', region_name=AWS_REGION)
sns = boto3.client('sns', region_name=AWS_REGION)

# DynamoDB tables
USERS_TABLE_NAME = os.environ.get('USERS_TABLE_NAME', 'MovieMagic_Users')
BOOKINGS_TABLE_NAME = os.environ.get('BOOKINGS_TABLE_NAME', 'MovieMagic_Bookings')

users_table = dynamodb.Table(USERS_TABLE_NAME)
bookings_table = dynamodb.Table(BOOKINGS_TABLE_NAME)

# === Authentication Routes ===
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        try:
            # Get user from DynamoDB
            response = users_table.get_item(Key={'email': email})
            if 'Item' in response:
                user = response['Item']
                if check_password_hash(user['password'], password):
                    session['user'] = {
                        'id': user['id'],
                        'name': user['name'],
                        'email': user['email']
                    }
                    return redirect(url_for('home1'))
            flash('Invalid email or password', 'danger')
        except ClientError as e:
            print(f"Error accessing DynamoDB: {e.response['Error']['Message']}")
            flash('An error occurred. Please try again later.', 'danger')
    return render_template('login.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = generate_password_hash(request.form['password'])
        try:
            # Check if user already exists
            response = users_table.get_item(Key={'email': email})
            if 'Item' in response:
                flash('Email already registered!', 'danger')
                return redirect(url_for('signup'))

            # Create new user in DynamoDB
            user_id = str(uuid.uuid4())
            users_table.put_item(
                Item={
                    'id': user_id,
                    'name': name,
                    'email': email,
                    'password': password,
                    'created_at': datetime.now().isoformat()
                }
            )
            flash('Registration successful! Please login.', 'success')
            return redirect(url_for('login'))
        except ClientError as e:
            print(f"Error accessing DynamoDB: {e.response['Error']['Message']}")
            flash('An error occurred during registration. Please try again.', 'danger')
    return render_template('signup.html')

@app.route('/logout')
def logout():
    session.pop('user', None)
    flash('You have been logged out!', 'info')
    return redirect(url_for('index'))



movies = [
    {
        "id": 1,
        "title": "RRR",
        "genre": "Action",
        "language": "Telugu",
        "duration": "3h 2m",
        "price": 150,
        "poster": "rrr.jpg"  # Make sure this image is in static/posters/
    },
    {
        "id": 2,
        "title": "Pushpa",
        "genre": "Action",
        "language": "Telugu",
        "duration": "3h 2m",
        "price": 150,
        "poster": "pushpa.jpeg"
    },
    {
        "id": 3,
        "title": "Guntur Kaaram",
        "genre": "Drama",
        "language": "Telugu",
        "duration": "2h 45m",
        "price": 180,
        "poster": "gunturkaram.jpeg"
    }
]
    # Simulate logged-in user
    session['user'] = {'name': 'Sarath'}

    return render_template('home1.html', movies=movies)



@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/contact_us')
def contact_us():
    return render_template('contact_us.html')

@app.route('/select_datetime/<int:movie_id>')
def select_datetime(movie_id):
    movie = get_movie_by_id(movie_id)
    return render_template('select_datetime.html', movie=movie, now=datetime.now(), timedelta=timedelta)

@app.route('/show_times/<int:movie_id>', methods=['POST'])
def show_times(movie_id):
    selected_date = request.form.get('date')
    movie = get_movie_by_id(movie_id)
    return render_template('show_times.html', movie=movie, selected_date=selected_date, current_time=datetime.now(), datetime=datetime)


@app.route('/profile')
def profile():
    if 'user' not in session:
        flash('Please login to view your profile.', 'warning')
        return redirect(url_for('login'))
    return render_template('profile.html', user=session['user'])


# Booking page
@app.route('/b1', methods=['GET'])
def booking_page():
    if 'user' not in session:
        return redirect(url_for('login'))
    return render_template('b1.html',
        movie=request.args.get('movie'),
        theater=request.args.get('theater'),
        address=request.args.get('address'),
        price=request.args.get('price')
    )

@app.route('/tickets', methods=['POST'])
def tickets():
    if 'user' not in session:
        return redirect(url_for('login'))
    try:
        # Extract booking details
        movie_name = request.form.get('movie')
        booking_date = request.form.get('date')
        show_time = request.form.get('time')
        theater_name = request.form.get('theater')
        theater_address = request.form.get('address')
        selected_seats = request.form.get('seats')
        amount_paid = request.form.get('amount')
        # Generate a unique booking ID
        booking_id = f"MVM-{datetime.now().strftime('%Y%m%d')}-{str(uuid.uuid4())[:8]}"
        # Store booking in DynamoDB
        booking_item = {
            'booking_id': booking_id,
            'movie_name': movie_name,
            'date': booking_date,
            'time': show_time,
            'theater': theater_name,
            'address': theater_address,
            'booked_by': session['user']['email'],
            'user_name': session['user']['name'],
            'seats': selected_seats,
            'amount_paid': amount_paid,
            'booking_time': datetime.now().isoformat()
        }
        bookings_table.put_item(Item=booking_item)
        # Send booking confirmation
        notification_sent = send_booking_confirmation(booking_item)
        if notification_sent:
            flash('Booking confirmation has been sent to your email!', 'success')
        return render_template('tickets.html', booking=booking_item)
    except Exception as e:
        print(f"Error processing booking: {str(e)}")
        flash('Error processing booking', 'danger')
        return redirect(url_for('home1'))
@app.route('/user_bookings')
def user_bookings():
    if 'user' not in session:
        flash('Please login to view your bookings.', 'warning')
        return redirect(url_for('login'))

    try:
        # Fetch all bookings for the logged-in user
        response = bookings_table.scan(
            FilterExpression=boto3.dynamodb.conditions.Attr('booked_by').eq(session['user']['email'])
        )
        user_bookings = response.get('Items', [])
    except ClientError as e:
        print(f"Error fetching bookings: {e.response['Error']['Message']}")
        flash('Could not fetch your bookings at this time.', 'danger')
        user_bookings = []

    return render_template('user_bookings.html', bookings=user_bookings)


def send_booking_confirmation(booking):
    """Send booking confirmation email using SNS"""
    try:
        email_subject = f"MovieMagic Booking Confirmation - {booking['booking_id']}"
        email_message = f"""
        Hello {booking['user_name']},
        
        Your movie ticket booking is confirmed!
        
        Booking Details:
        ----------------
        Booking ID: {booking['booking_id']}
        Movie: {booking['movie_name']}
        Date: {booking['date']}
        Time: {booking['time']}
        Theater: {booking['theater']}
        Location: {booking['address']}
        Seats: {booking['seats']}
        Amount Paid: ₹{booking['amount_paid']}
        
        Please show this confirmation at the theater to collect your tickets.
        
        Thank you for choosing MovieMagic!
        """
        user_email = booking['booked_by']
        print(f"Sending notification to {user_email} via SNS topic {SNS_TOPIC_ARN}")
        response = sns.publish(
            TopicArn=SNS_TOPIC_ARN,
            Subject=email_subject,
            Message=email_message
        )
        print(f"SNS response: {response}")
        return True
    except Exception as e:
        print(f"Error sending booking confirmation: {str(e)}")
        return False

# === Run Server ===
if __name__ == '__main__':  # ✅ Fixed __name__ and __main__
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
