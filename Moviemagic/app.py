from flask import Flask, render_template, request, redirect, url_for, flash, session, send_file
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
from reportlab.pdfgen import canvas
from io import BytesIO
import qrcode
import time
import os
import boto3
import uuid

app = Flask(__name__)
app.secret_key = 'your_secret_key'

# AWS setup
REGION = 'us-east-1'
dynamodb = boto3.resource('dynamodb', region_name=REGION)
users_table = dynamodb.Table('MovieMagic_Users')
bookings_table = dynamodb.Table('MovieMagic_Bookings')

sns = boto3.client('sns', region_name=REGION)
sns_topic_arn = 'arn:aws:sns:us-east-1:195275652542:BookingRequestNotifications'

# Movies data
movies = [
    {"id": 1, "title": "RRR", "genre": "Action,thriller,drama", "language": "Telugu", "duration": "3h 2m", "price": 150, "poster": "rrr.jpg", "location": "Prasads Multiplex, Hyderabad", "booked_seats": {}},
    {"id": 2, "title": "Pushpa", "genre": "Action,violence", "language": "Telugu", "duration": "3h 2m", "price": 150, "poster": "pushpa.jpeg", "location": "Prasads Multiplex, Hyderabad", "booked_seats": {"2025-07-02_11:30 AM": ["1-4", "1-5"]}},
    {"id": 3, "title": "Mission Impossible", "genre": "Action,adventures,drama,thriller", "language": "Telugu", "duration": "3h 2m", "price": 150, "poster": "mi.jpeg", "location": "Prasads Multiplex, Hyderabad", "booked_seats": {}},
    {"id": 4, "title": "Kubera", "genre": "Action,drama", "language": "Telugu", "duration": "3h 2m", "price": 150, "poster": "kbr.jpeg", "location": "AMB, Hyderabad", "booked_seats": {}},
    {"id": 5, "title": "Hit3", "genre": "Action,thriller", "language": "Telugu", "duration": "3h 2m", "price": 150, "poster": "hit.jpeg", "location": "AMB, Hyderabad", "booked_seats": {}},
    {"id": 6, "title": "Jailer", "genre": "Thriller", "language": "Telugu", "duration": "3h 2m", "price": 150, "poster": "jailer.jpeg", "location": "Sandhya 70mm, Hyderabad", "booked_seats": {}},
    {"id": 7, "title": "Jawan", "genre": "Action", "language": "Telugu", "duration": "2h 45m", "price": 150, "poster": "jawan.jpeg", "location": "AMB, Hyderabad", "booked_seats": {}},
    {"id": 8, "title": "Kaithi", "genre": "Action,thriller", "language": "Telugu", "duration": "3h 2m", "price": 150, "poster": "kaithi.jpeg", "location": "Sudharshan 35mm, Hyderabad", "booked_seats": {}},
    {"id": 9, "title": "Kantara", "genre": "ancient", "language": "Telugu", "duration": "2h 45m", "price": 150, "poster": "kantara.jpeg", "location": "AMB, Hyderabad", "booked_seats": {}},
    {"id": 10, "title": "Leo", "genre": "Action", "language": "Telugu", "duration": "3h 20m", "price": 150, "poster": "leo.jpeg", "location": "Inox, Hyderabad", "booked_seats": {}},
     {"id": 11, "title": "kgf", "genre": "Action", "language": "Telugu", "duration": "3h 2m", "price": 150, "poster": "kgf.jpeg", "location": "Inox, Hyderabad", "booked_seats": {}},
      {"id": 12, "title": "Sita ramam", "genre": "romantic,drama", "language": "Telugu", "duration": "3h 20m", "price": 150, "poster": "sitaramam.jpeg", "location": "jaysyam, Hyderabad", "booked_seats": {}},
       {"id": 13, "title": "karthikeya", "genre": "Action,adventures", "language": "Telugu", "duration": "2h 45m", "price": 150, "poster": "karthikeya.jpeg", "location": "AA Multiplex, Hyderabad", "booked_seats": {}}, 
       {"id": 14, "title": "temper", "genre": "Action", "language": "Telugu", "duration": "2h 45m", "price": 150, "poster": "temper.jpeg", "location": "AA Multiplex, Hyderabad", "booked_seats": {}},
       {"id": 15, "title": "Vakeel saab", "genre": "action", "language": "Telugu", "duration": "2h 50m", "price": 150, "poster": "vakeel.jpeg", "location": "AA Multiplex, Hyderabad", "booked_seats": {}},
       {"id": 13, "title": "vikram", "genre": "Action,thriller", "language": "Telugu", "duration": "2h 45m", "price": 150, "poster": "vikram.jpeg", "location": "AA Multiplex, Hyderabad", "booked_seats": {}},
]

def get_movie_by_id(movie_id):
    return next((m for m in movies if m['id'] == movie_id), None)

def generate_qr_code(data, filename):
    qr = qrcode.QRCode(version=1, box_size=10, border=4)
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    os.makedirs(os.path.dirname(filename), exist_ok=True)
    img.save(filename)

@app.route('/')
def landing():
    return render_template('landing.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        email = request.form['email'].lower()
        existing_user = users_table.get_item(Key={'email': email})
        if 'Item' in existing_user:
            flash("Account already exists.")
            return redirect(url_for('login'))
        user = {
            'email': email,
            'id': str(uuid.uuid4()),
            'name': request.form['name'],
            'password': generate_password_hash(request.form['password'])
        }
        users_table.put_item(Item=user)
        flash("Registered successfully. Please login.")
        return redirect(url_for('login'))
    return render_template('signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email'].lower()
        password = request.form['password']
        user_response = users_table.get_item(Key={'email': email})
        user = user_response.get('Item')
        if not user or not check_password_hash(user['password'], password):
            flash("Invalid credentials.")
            return redirect(url_for('login'))
        session['user'] = {
            'id': user['id'],
            'email': user['email'],
            'name': user['name']
        }
        return redirect(url_for('home1'))
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('user', None)
    flash("Logged out.")
    return redirect(url_for('login'))

@app.route('/home1')
def home1():
    if 'user' not in session:
        return redirect(url_for('login'))
    return render_template('home1.html', movies=movies)

@app.route('/select_datetime/<int:movie_id>')
def select_datetime(movie_id):
    movie = get_movie_by_id(movie_id)
    now = datetime.now()
    return render_template('select_datetime.html', movie=movie, now=now, timedelta=timedelta)

@app.route('/show_times/<int:movie_id>', methods=['POST'])
def show_times(movie_id):
    selected_date = request.form.get('date')
    movie = get_movie_by_id(movie_id)
    current_time = datetime.now()
    return render_template('show_times.html', movie=movie, selected_date=selected_date, datetime=datetime, current_time=current_time)

@app.route('/b1/<int:movie_id>')
def b1(movie_id):
    movie = get_movie_by_id(movie_id)
    selected_date = request.args.get('selected_date')
    selected_time = request.args.get('selected_time')
    if not selected_date or not selected_time:
        flash("Select date and time.")
        return redirect(url_for('home1'))
    key = f"{selected_date}_{selected_time}"
    booked_seats = movie['booked_seats'].get(key, [])
    return render_template('b1.html', movie=movie, selected_date=selected_date, selected_time=selected_time, booked_seats=booked_seats)

@app.route('/tickets', methods=['POST'])
def tickets():
    if 'user' not in session:
        return redirect(url_for('login'))
    form = request.form
    selected_seats = form.get('seats')
    if not selected_seats:
        flash("Please select at least one seat.")
        return redirect(request.referrer)
    seat_list = selected_seats.split(',')
    for field, message in [('payment_method', 'payment method'), ('full_name', 'name'), ('email', 'email'), ('phone', 'phone number')]:
        if not form.get(field):
            flash(f"Please enter your {message}.")
            return redirect(request.referrer)
    movie_id = int(form.get('movie_id'))
    selected_date = form.get('selected_date')
    selected_time = form.get('selected_time')
    movie = get_movie_by_id(movie_id)
    if not movie:
        return "Movie not found", 404
    key = f"{selected_date}_{selected_time}"
    if key not in movie['booked_seats']:
        movie['booked_seats'][key] = []
    for seat in seat_list:
        if seat in movie['booked_seats'][key]:
            flash(f"Seat {seat} is already booked.")
            return redirect(url_for('b1', movie_id=movie_id, selected_date=selected_date, selected_time=selected_time))
    movie['booked_seats'][key].extend(seat_list)
    seat_prices = []
    for seat in seat_list:
        row = int(seat.split('-')[0])
        price = movie['price'] + (50 if 4 <= row <= 6 else 100 if row >= 7 else 0)
        seat_prices.append(price)
    total_price = sum(seat_prices)
    booking_id = f"B{int(time.time())}"
    booking = {
        'booking_id': booking_id,
        'user_id': session['user']['id'],
        'movie': movie['title'],
        'theater': movie['location'],
        'seats': seat_list,
        'seat_prices': seat_prices,
        'total_price': total_price,
        'date': selected_date,
        'time': selected_time,
        'name': form.get('full_name'),
        'email': form.get('email'),
        'phone': form.get('phone'),
        'payment_method': form.get('payment_method'),
        'booking_time': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    bookings_table.put_item(Item=booking)
    sns.publish(
        TopicArn=sns_topic_arn,
        Message=f"New booking for {movie['title']} on {selected_date} at {selected_time}. Seats: {', '.join(seat_list)}. Name: {form.get('full_name')}, Phone: {form.get('phone')}",
        Subject="New Booking Confirmation"
    )
    qr_text = f"""🎟 Movie Magic Ticket 🎟
Name: {form.get('full_name')}
Movie: {movie['title']}
Date: {selected_date}
Time: {selected_time}
Theater: {movie['location']}
Seats: {', '.join(seat_list)}
Booking ID: {booking_id}"""
    qr_filename = f"static/qr/booking_{booking_id}.png"
    generate_qr_code(qr_text, qr_filename)
    return render_template('ticket.html', booking=booking, movie=movie, qr_image=qr_filename)

@app.route('/user_bookings')
def user_bookings():
    if 'user' not in session:
        flash("Please login to see your bookings.")
        return redirect(url_for('login'))
    user_id = session['user']['id']
    # Fetch all bookings for this user
    response = bookings_table.scan(
        FilterExpression="user_id = :uid",
        ExpressionAttributeValues={":uid": user_id}
    )
    user_bookings = response.get('Items', [])
    return render_template('user_bookings.html', bookings=user_bookings)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
