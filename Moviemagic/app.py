from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import boto3
import uuid
import os
from botocore.exceptions import ClientError

app = Flask(__name__)
app.secret_key = 'your_static_secret_key_here'  # Replace with your own secret string

# AWS Configuration
AWS_REGION = os.environ.get('AWS_REGION', 'us-east-1')
SNS_TOPIC_ARN = 'arn:aws:sns:us-east-1:794038220422:movies'

dynamodb = boto3.resource('dynamodb', region_name=AWS_REGION)
sns = boto3.client('sns', region_name=AWS_REGION)

USERS_TABLE_NAME = os.environ.get('USERS_TABLE_NAME', 'MovieMagic_Users')
BOOKINGS_TABLE_NAME = os.environ.get('BOOKINGS_TABLE_NAME', 'MovieMagic_Bookings')

users_table = dynamodb.Table(USERS_TABLE_NAME)
bookings_table = dynamodb.Table(BOOKINGS_TABLE_NAME)

# ✅ Hardcoded movie list
movies = [
    {
        "id": 1,
        "title": "RRR",
        "genre": "Action",
        "language": "Telugu",
        "duration": "3h 2m",
        "price": 150,
        "poster": "rrr.jpg"  # Place in static/posters/
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

# === Routes ===
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/home1')
def home1():
    if 'user' not in session:
        flash('Please login to continue.', 'warning')
        return redirect(url_for('login'))
    return render_template('home1.html', movies=movies)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        try:
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
            response = users_table.get_item(Key={'email': email})
            if 'Item' in response:
                flash('Email already registered!', 'danger')
                return redirect(url_for('signup'))

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

@app.route('/select_datetime/<int:movie_id>')
def select_datetime(movie_id):
    movie = next((m for m in movies if m['id'] == movie_id), None)
    if not movie:
        flash('Movie not found!', 'danger')
        return redirect(url_for('home1'))
    return render_template('select_datetime.html', movie=movie, now=datetime.now(), timedelta=timedelta)
@app.route('/show_times', methods=['POST'])
def show_times():
    movie_id = int(request.form.get('movie_id'))
    movie = next((m for m in movies if m['id'] == movie_id), None)
    selected_date = request.form.get('date')
    return render_template('show_times.html', movie=movie, selected_date=selected_date)


@app.route('/profile')
def profile():
    if 'user' not in session:
        flash('Please login to view your profile.', 'warning')
        return redirect(url_for('login'))
    return render_template('profile.html', user=session['user'])

# === Booking & Confirmation ===
@app.route('/tickets', methods=['POST'])
def tickets():
    if 'user' not in session:
        return redirect(url_for('login'))
    try:
        booking_id = f"MVM-{datetime.now().strftime('%Y%m%d')}-{str(uuid.uuid4())[:8]}"
        booking_item = {
            'booking_id': booking_id,
            'movie_name': request.form.get('movie'),
            'date': request.form.get('date'),
            'time': request.form.get('time'),
            'theater': request.form.get('theater'),
            'address': request.form.get('address'),
            'booked_by': session['user']['email'],
            'user_name': session['user']['name'],
            'seats': request.form.get('seats'),
            'amount_paid': request.form.get('amount'),
            'booking_time': datetime.now().isoformat()
        }
        bookings_table.put_item(Item=booking_item)
        send_booking_confirmation(booking_item)
        flash('Booking confirmation sent to your email!', 'success')
        return render_template('tickets.html', booking=booking_item)
    except Exception as e:
        print(f"Error: {e}")
        flash('Error processing booking.', 'danger')
        return redirect(url_for('home1'))

def send_booking_confirmation(booking):
    try:
        response = sns.publish(
            TopicArn=SNS_TOPIC_ARN,
            Subject=f"MovieMagic Booking Confirmation - {booking['booking_id']}",
            Message=f"Hello {booking['user_name']},\n\nYour booking for {booking['movie_name']} is confirmed!"
        )
        print(f"SNS response: {response}")
        return True
    except Exception as e:
        print(f"Error sending SNS notification: {e}")
        return False

# === Run App ===
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
