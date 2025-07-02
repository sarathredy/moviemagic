# === app.py ===
from flask import Flask, render_template, request, redirect, url_for, flash, session, send_file
from flask_mail import Mail, Message
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
from io import BytesIO
from reportlab.pdfgen import canvas
import qrcode
import json
import os

app = Flask(__name__)
app.secret_key = 'your_secret_key'

app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'sarathreddy9377@gmail.com'
app.config['MAIL_PASSWORD'] = 'rhiz play qybj vsda'
app.config['MAIL_DEFAULT_SENDER'] = 'your_email@gmail.com'

mail = Mail(app)

MOVIES_FILE = 'movies.json'
USERS_FILE = 'users.json'
bookings = []

# === Load & Save Helpers ===
def load_users():
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, 'r') as f:
            return json.load(f)
    return []

def save_users(users):
    with open(USERS_FILE, 'w') as f:
        json.dump(users, f, indent=4)

def load_movies():
    if os.path.exists(MOVIES_FILE):
        with open(MOVIES_FILE, 'r') as f:
            return json.load(f)
    return []

def save_movies(movies):
    with open(MOVIES_FILE, 'w') as f:
        json.dump(movies, f, indent=4)

def get_movie_by_id(movie_id):
    return next((m for m in load_movies() if m['id'] == movie_id), None)

# === QR Code ===
def generate_qr_code(data, filename):
    qr = qrcode.QRCode(version=1, box_size=10, border=4)
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    os.makedirs(os.path.dirname(filename), exist_ok=True)
    img.save(filename)

# === Routes ===
'''@app.route('/')
def index():
    return redirect(url_for('login'))'''
@app.route('/')
def landing():
    return render_template('landing.html')


@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        users = load_users()
        email = request.form['email'].lower()
        if any(u['email'] == email for u in users):
            flash("Account already exists. Please login.")
            return redirect(url_for('login'))
        user = {
            'id': len(users)+1,
            'name': request.form['name'],
            'email': email,
            'password': generate_password_hash(request.form['password'])
        }
        users.append(user)
        save_users(users)
        flash("Registered. Please login.")
        return redirect(url_for('login'))
    return render_template('signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        users = load_users()
        email = request.form['email'].lower()
        password = request.form['password']
        user = next((u for u in users if u['email'] == email), None)
        if not user:
            flash("You don't have an account. Please sign up.")
            return redirect(url_for('signup'))
        if check_password_hash(user['password'], password):
            session['user'] = user
            return redirect(url_for('home1'))
        flash("Incorrect password")
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
    return render_template('home1.html', movies=load_movies())
@app.route('/profile')
def profile():
    return render_template('profile.html')
@app.route('/user_bookings')
def user_bookings():
    if 'user' not in session:
        flash("Please log in to view your bookings.")
        return redirect(url_for('login'))

    user_id = session['user']['id']
    user_bookings = [b for b in bookings if b['user_id'] == user_id]

    if not user_bookings:
        flash("No bookings found.")
    return render_template('user_bookings.html', bookings=user_bookings)
@app.route('/contact_us')
def contact_us():
    return render_template('contact_us.html')


from datetime import datetime, timedelta

@app.route('/select_datetime/<int:movie_id>', methods=['GET'])
def select_datetime(movie_id):
    movie = get_movie_by_id(movie_id)
    now = datetime.now()
    return render_template('select_datetime.html', movie=movie, now=now, timedelta=timedelta)

from datetime import datetime

@app.route('/show_times/<int:movie_id>', methods=['POST'])
def show_times(movie_id):
    selected_date = request.form.get('date')
    current_time = datetime.now()
    movie = get_movie_by_id(movie_id)
    return render_template('show_times.html', movie=movie, selected_date=selected_date, current_time=current_time, datetime=datetime)


@app.route('/b1/<int:movie_id>', methods=['GET'])
def b1(movie_id):
    movie = get_movie_by_id(movie_id)
    selected_date = request.args.get('selected_date')
    selected_time = request.args.get('selected_time')

    if not selected_date or not selected_time:
        flash("Please select both date and time.")
        return redirect(url_for('select_datetime', movie_id=movie_id))

    with open('bookings.json', 'r') as f:
        all_bookings = json.load(f)

    # Only load seats booked for this specific movie + date + time
    booked_seats = []
    for b in all_bookings:
        if b['movie_id'] == movie_id and b['selected_date'] == selected_date and b['selected_time'] == selected_time:
            booked_seats.extend(b['seats'])

    return render_template('b1.html', movie=movie, selected_date=selected_date,
                           selected_time=selected_time, booked_seats=booked_seats)

from flask import request, redirect, url_for, render_template, session, flash
from flask_mail import Message
from datetime import datetime
import time
import os

@app.route('/tickets', methods=['POST'])
def tickets():
    if 'user' not in session:
        return redirect(url_for('login'))

    selected_seats = request.form.get('seats')
    if not selected_seats:
        flash("Please select at least one seat to book.")
        return redirect(url_for('home1'))

    seat_list = selected_seats.split(',')
    movie_id = int(request.form['movie_id'])
    selected_date = request.form.get('selected_date')
    selected_time = request.form.get('selected_time')

    # Dummy payment info
    user_name = request.form.get('full_name')
    user_email = request.form.get('email')
    user_phone = request.form.get('phone')

    movies = load_movies()
    movie = next((m for m in movies if m['id'] == movie_id), None)
    if not movie:
        return "Movie not found", 404

    # Key for the specific show
    key = f"{selected_date}_{selected_time}"

    # Ensure booked_seats structure exists
    if 'booked_seats' not in movie or not isinstance(movie['booked_seats'], dict):
        movie['booked_seats'] = {}
    if key not in movie['booked_seats']:
        movie['booked_seats'][key] = []

    # Prevent double booking
    for seat in seat_list:
        if seat in movie['booked_seats'][key]:
            flash(f"Seat {seat} is already booked.")
            return redirect(url_for('b1', movie_id=movie_id, selected_date=selected_date, selected_time=selected_time))

    movie['booked_seats'][key].extend(seat_list)
    save_movies(movies)

    # Price logic based on rows
    total_price = 0
    seat_prices = []
    for seat in seat_list:
        row = int(seat.split('-')[0])
        if row <= 3:
            seat_prices.append(movie['price'])
        elif row <= 6:
            seat_prices.append(movie['price'] + 50)
        else:
            seat_prices.append(movie['price'] + 100)
    total_price = sum(seat_prices)

    # Generate a unique booking ID using timestamp
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
        'name': user_name,
        'email': user_email,
        'phone': user_phone,
        'booking_time': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }

    bookings.append(booking)

    # Generate QR code
    qr_text = f"""🎟 Movie Magic Ticket 🎟
Name: {user_name}
Movie: {movie['title']}
Date: {selected_date}
Time: {selected_time}
Theater: {movie['location']}
Seats: {', '.join(seat_list)}
Booking ID: {booking_id}"""

    qr_filename = f"static/qr/booking_{booking_id}.png"
    generate_qr_code(qr_text, qr_filename)

    # Send confirmation email
    msg = Message(
        subject='🎟 Your Movie Magic Ticket Confirmation',
        recipients=[user_email],
        body=f"""Hello {user_name},

Your booking is confirmed!

Movie: {movie['title']}
Date: {selected_date}
Time: {selected_time}
Seats: {', '.join(seat_list)}
Total Price: ₹{total_price}
Booking ID: {booking_id}

Enjoy your show!
- Movie Magic Team"""
    )
    with open(qr_filename, 'rb') as qr_file:
        msg.attach(f"booking_{booking_id}.png", "image/png", qr_file.read())
    mail.send(msg)

    return render_template('ticket.html', booking=booking, movie=movie, qr_image=qr_filename)

@app.route('/download_pdf/<booking_id>')
def download_pdf(booking_id):
    booking = next((b for b in bookings if b['booking_id'] == booking_id), None)
    if not booking:
        return "Booking not found", 404

    buffer = BytesIO()
    p = canvas.Canvas(buffer)
    p.setFont("Helvetica", 14)
    p.drawString(100, 800, "🎟 Movie Magic Ticket 🎟")
    p.drawString(100, 770, f"Name: {session['user']['name']}")
    p.drawString(100, 750, f"Movie: {booking['movie']}")
    p.drawString(100, 730, f"Date & Time: {booking['date']} @ {booking['time']}")
    p.drawString(100, 710, f"Theater: {booking['theater']}")
    p.drawString(100, 690, f"Seats: {', '.join(booking['seats'])}")
    p.drawString(100, 670, f"Total Price: ₹{booking['total_price']}")
    p.drawString(100, 650, f"Payment Method: {booking['payment_method']}")
    p.drawString(100, 630, f"Booking ID: {booking['booking_id']}")
    p.showPage()
    p.save()
    buffer.seek(0)

    return send_file(buffer, as_attachment=True, download_name=f"Ticket_{booking_id}.pdf", mimetype='application/pdf')



if __name__ == '__main__':
    if not os.path.exists(MOVIES_FILE): save_movies([])
    app.run(debug=True)


"""from flask import Flask, render_template, request, redirect, url_for, flash, session, send_file
from flask_mail import Mail, Message
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
from io import BytesIO
from reportlab.pdfgen import canvas
import qrcode
import json
import os
import qrcode




app = Flask(__name__)
app.secret_key = 'your_secret_key'
from flask_mail import Mail, Message
import qrcode

app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'your_email@gmail.com'         # ⬅️ change this
app.config['MAIL_PASSWORD'] = 'your_app_password'            # ⬅️ use Gmail App Password
app.config['MAIL_DEFAULT_SENDER'] = 'your_email@gmail.com'   # ⬅️ same as above

mail = Mail(app)

users = []
bookings = []


MOVIES_FILE = 'movies.json'
def send_booking_email(email, movie, date, time, seat, booking_id):
    print(f
    Booking Confirmed!

    Email: {email} 
    Movie: {movie}
    Date: {date}
    Time: {time}
    Seat: {seat}
    Booking ID: {booking_id}
    )

import qrcode
from PIL import Image

def generate_qr_code(data, filename):
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(data)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")
    img.save(filename)

def load_movies():
    with open(MOVIES_FILE, 'r') as f:
        return json.load(f)
def get_movie_by_id(movie_id):
    with open('movies.json', 'r') as f:
        movies = json.load(f)
    for movie in movies:
        if movie['id'] == movie_id:
            return movie
    return None



def save_movies(movies):
    with open(MOVIES_FILE, 'w') as f:
        json.dump(movies, f, indent=4)


@app.route('/')
def index():
    return redirect(url_for('login'))


user_counter = 1  # Declare this at the top if not present

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    global user_counter  # Important!
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = generate_password_hash(request.form['password'])

        existing_user = next((u for u in users if u['email'] == email), None)
        if existing_user:
            flash("Account already exists. Please login.")
            return redirect(url_for('login'))

        user = {'id': user_counter, 'name': name, 'email': email, 'password': password}
        users.append(user)
        user_counter += 1
        flash("Registration successful. Please login.")
        return redirect(url_for('login'))
    return render_template('signup.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user = next((u for u in users if u['email'] == email), None)

        if not user:
            flash("You don't have an account. Please sign up.")
            return redirect(url_for('login'))

        if check_password_hash(user['password'], password):
            session['user'] = user
            flash("Login successful!")
            return redirect(url_for('home1'))
        else:
            flash("Incorrect password.")
    return render_template('login.html')


@app.route('/logout')
def logout():
    name = session['user']['name'] if 'user' in session else 'Guest'
    session.pop('user', None)
    return render_template('logout.html', name=name)





@app.route('/home1')
def home1():
    with open('movies.json') as f:
        movies = json.load(f)
    return render_template('home1.html', movies=movies)




@app.route('/seats', methods=['POST'])
def seats():
    movie = request.form.to_dict()
    return render_template('seats.html', movie=movie)



@app.route('/movie/<int:movie_id>')
def movie_details(movie_id):
    with open('movies.json') as f:
        movies = json.load(f)
    movie = next((m for m in movies if m['id'] == movie_id), None)
    if not movie:
        flash("Movie not found.")
        return redirect(url_for('home1'))
    return render_template('movie_details.html', movie=movie)






@app.route('/b1/<int:movie_id>', methods=['GET', 'POST'])
def b1(movie_id):
    movie = get_movie_by_id(movie_id)
    
    selected_date = request.args.get('selected_date')
    selected_time = request.args.get('selected_time')

    if not selected_date or not selected_time:
        flash("Please select both date and time.")
        return redirect(url_for('select_datetime', movie_id=movie_id))

    # Add logic to fetch or prepare seat layout and booking info
    return render_template('b1.html', movie=movie, selected_date=selected_date, selected_time=selected_time)



@app.route('/tickets', methods=['POST'])
def tickets():
    

    if 'user' not in session:
        return redirect(url_for('login'))

    selected_seats = request.form.get('seats')
    if not selected_seats:
        flash("Please select at least one seat to book.")
        return redirect(url_for('home1'))

    seat_list = selected_seats.split(',')
    movie_id = int(request.form['movie_id'])

    movies = load_movies()
    movie = next((m for m in movies if m['id'] == movie_id), None)

    if not movie:
        return "Movie not found", 404

    # Initialize booked_seats if not already present
    if 'booked_seats' not in movie:
        movie['booked_seats'] = []

    # Check for duplicate booking
    for seat in seat_list:
        if seat in movie['booked_seats']:
            flash(f"Seat {seat} is already booked.")
            return redirect(url_for('b1', movie_id=movie_id))

    movie['booked_seats'].extend(seat_list)
    movie['available_seats'] -= len(seat_list)
    save_movies(movies)

    booking = {
    'booking_id': len(bookings) + 1,
    'user_id': session['user']['id'],  # ✅ This line is correct
    'movie': movie['title'],
    'theater': movie['location'],
    'seats': seat_list,
    'price': movie['price'],
    'total_price': len(seat_list) * movie['price'],
    'booking_time': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
  
}


    bookings.append(booking)

    # ✅ Generate QR with text (not URL)
    qr_text = f🎟 Movie Magic Ticket 🎟
Name: {session['user']['name']}
Movie: {movie['title']}
Theater: {movie['location']}
Seats: {', '.join(seat_list)}

Booking ID: {booking['booking_id']}
Date: {datetime.now().strftime('%Y-%m-%d')}


    qr_filename = f"static/qr/booking_{booking['booking_id']}.png"
    generate_qr_code(qr_text, qr_filename)

    return render_template('ticket.html', booking=booking, movie=movie, qr_image=qr_filename)
def send_booking_email(email, movie, date, time, seat, booking_id):
    print(f
    Booking Confirmed!

    Email: {email} 
    Movie: {movie}
    Date: {date}
    Time: {time}
    Seat: {seat}
    Booking ID: {booking_id}
    )

# Example call with correct dictionary keys
    send_booking_email(
        booking['email'], 
        booking['movie'], 
        booking['date'], 
        booking['time'], 
        booking['seats'], 
        booking['booking_id']
)

    return render_template('tickets.html', booking=booking)


import os
from io import BytesIO
from reportlab.pdfgen import canvas
from flask import send_file

@app.route('/download_ticket/<int:booking_id>')
def download_ticket(booking_id):
    booking = next((b for b in bookings if b['booking_id'] == booking_id), None)
    if not booking:
        return "Booking not found", 404

    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=(600, 800))

    c.setFont("Helvetica", 16)
    c.drawString(50, 750, "🎫 Movie Magic Ticket")
    c.setFont("Helvetica", 12)
    c.drawString(50, 720, f"Movie: {booking['movie']}")
    c.drawString(50, 700, f"Theater: {booking['theater']}")
    c.drawString(50, 680, f"Seats: {', '.join(booking['seats'])}")
    c.drawString(50, 660, f"Total Price: ₹{booking['total_price']}")
    c.drawString(50, 640, f"Booking Time: {booking['booking_time']}")

    # Safe absolute path for QR
    qr_path = os.path.join('static', 'qr', f"booking_{booking_id}.png")
    if os.path.exists(qr_path):
        c.drawImage(qr_path, 400, 600, width=100, height=100)
    else:
        c.drawString(400, 600, "QR not found")

    c.showPage()
    c.save()
    buffer.seek(0)

    return send_file(buffer, as_attachment=True, download_name='ticket.pdf', mimetype='application/pdf')
@app.route('/profile')
def profile():
    return render_template('profile.html')

@app.route('/user_bookings')
def user_bookings():
    if 'user' not in session:
        flash("Please log in to view your bookings.")
        return redirect(url_for('login'))

    user_id = session['user']['id']
    user_bookings = [b for b in bookings if b['user_id'] == user_id]

    if not user_bookings:
        flash("No bookings found.")
    return render_template('user_bookings.html', bookings=user_bookings)


from datetime import datetime, timedelta


@app.route('/select_datetime/<int:movie_id>', methods=['GET'])
def select_datetime(movie_id):
    movie = get_movie_by_id(movie_id)
    now = datetime.now()
    return render_template('select_datetime.html', movie=movie, now=now, timedelta=timedelta)


@app.route('/show_times/<int:movie_id>', methods=['GET', 'POST'])
def show_times(movie_id):
    if request.method == 'POST':
        selected_date = request.form.get('date')
        current_time = datetime.now()

        movie = get_movie_by_id(movie_id)
        return render_template('show_times.html', movie=movie, selected_date=selected_date, current_time=current_time)







@app.route('/contact_us')
def contact():
    return render_template('contact_us.html')




@app.route('/about')
def about():
    return render_template('about.html')


@app.route('/contact_us')
def contact_us():
    return render_template('contact_us.html')


@app.route('/admin')
def admin():
    return render_template('admin.html', bookings=bookings, movies=load_movies())


if __name__ == '__main__':
    if not os.path.exists(MOVIES_FILE):
        save_movies([])  # create empty file if missing
    app.run(debug=True, host='0.0.0.0')
    #app.run(debug=True)
  












    









"""