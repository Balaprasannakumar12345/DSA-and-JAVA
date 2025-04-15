from flask import Flask, render_template, request, redirect, flash, url_for, session, abort
import mysql.connector


class Database:
    def __init__(self, host, user, password, database):
        self.connection = mysql.connector.connect(
            host=host,
            user=user,
            password="Bala@123",
            database=database
        )
        self.cursor = self.connection.cursor()

    def execute_query(self, query, params=None, commit=False):
        try:
            self.cursor.execute(query, params or ())
            if commit:
                self.connection.commit()
            return True
        except mysql.connector.Error as err:
            if commit:
                self.connection.rollback()
            raise err

    def fetch_one(self):
        return self.cursor.fetchone()

    def fetch_all(self):
        return self.cursor.fetchall()

    def close(self):
        self.cursor.close()
        self.connection.close()


class User:
    def __init__(self, db):
        self.db = db

    def create_user(self, fullname, email, password):
        query = "INSERT INTO users (fullname, email, password) VALUES (%s, %s, %s)"
        return self.db.execute_query(query, (fullname, email, password), commit=True)

    def authenticate(self, email, password):
        query = "SELECT * FROM users WHERE email=%s AND password=%s"
        self.db.execute_query(query, (email, password))
        return self.db.fetch_one()

    def get_user_by_id(self, user_id):
        query = "SELECT fullname FROM users WHERE id = %s"
        self.db.execute_query(query, (user_id,))
        return self.db.fetch_one()


class Movie:
    def __init__(self, db):
        self.db = db

    def get_all_movies(self):
        query = "SELECT movie_name, hero_name, heroine_name, rating, poster_url, language FROM movies"
        self.db.execute_query(query)
        movies = self.db.fetch_all()

        movie_list = []  # Arrays are used to store the data
        for m in movies:
            movie_list.append({
                "title": m[0],
                "hero": m[1],
                "heroine": m[2],
                "rating": float(m[3]),
                "poster": m[4],
                "language": m[5]
            })

        def merge_sort_by_language(arr):
            if len(arr) <= 1:
                return arr
            mid = len(arr) // 2
            left = merge_sort_by_language(arr[:mid])
            right = merge_sort_by_language(arr[mid:])
            return merge_by_language(left, right)

        def merge_by_language(left, right):
            sorted_arr = []
            i = j = 0
            while i < len(left) and j < len(right):
                if left[i]['language'].lower() < right[j]['language'].lower():
                    sorted_arr.append(left[i])
                    i += 1
                else:
                    sorted_arr.append(right[j])
                    j += 1
            sorted_arr.extend(left[i:])
            sorted_arr.extend(right[j:])
            return sorted_arr

        sorted_movies = merge_sort_by_language(movie_list)

        for movie in sorted_movies:
            movie['rating'] = f"{movie['rating']}/5"

        return sorted_movies


class Booking:
    def __init__(self, db):
        self.db = db

    def get_booked_seats(self, movie_name, date, time):
        query = """
            SELECT seats_selected FROM seat_booked
            WHERE movie_name=%s AND date=%s AND time=%s
        """
        self.db.execute_query(query, (movie_name, date, time))
        rows = self.db.fetch_all()

        booked_seats = []
        for row in rows:
            if row[0]:
                booked_seats += row[0].split(',')
        return booked_seats

    def create_booking(self, movie_name, date, time, seats, email):
        query = """
            INSERT INTO seat_booked (movie_name, date, time, seats_selected, email)
            VALUES (%s, %s, %s, %s, %s)
        """
        return self.db.execute_query(query, (movie_name, date, time, seats, email), commit=True)

    def get_user_bookings(self, email):
        query = """
            SELECT id, movie_name, date, time, seats_selected
            FROM seat_booked
            WHERE email = %s
        """
        self.db.execute_query(query, (email,))
        rows = self.db.fetch_all()

        bookings = []
        for row in rows:
            bookings.append({
                'id': row[0],
                'movie_name': row[1],
                'date': row[2],
                'time': row[3],
                'seats_selected': row[4]
            })
        return bookings

    def cancel_booking(self, booking_id):
        query = "DELETE FROM seat_booked WHERE id = %s"
        return self.db.execute_query(query, (booking_id,), commit=True)


class MovieBookingApp:
    def __init__(self):
        self.app = Flask(__name__)
        self.app.secret_key = 'my_secret_key'

        self.db = Database(
            host="localhost",
            user="root",
            password="Bala@123",
            database="movie_booking"
        )

        self.user_model = User(self.db)
        self.movie_model = Movie(self.db)
        self.booking_model = Booking(self.db)

        self.register_routes()

    def register_routes(self):
        self.app.route('/')(self.show_signup)
        self.app.route('/signup', methods=['POST'])(self.signup)
        self.app.route('/login', methods=['GET', 'POST'])(self.login)
        self.app.route('/logout')(self.logout)
        self.app.route('/main1')(self.main1)
        self.app.route('/movie')(self.movie_page)
        self.app.route('/movie-details')(self.movie_details)
        self.app.route('/seat-booking')(self.seat_booking)
        self.app.route('/payment', methods=['POST'])(self.payment)
        self.app.route('/confirm-payment', methods=['POST'])(self.confirm_payment)
        self.app.route('/cancel')(self.cancel_booking)
        self.app.route('/cancel-ticket', methods=['POST'])(self.cancel_ticket)
        self.app.errorhandler(404)(self.page_not_found)

    def run(self):
        self.app.run(debug=True)

    def show_signup(self):
        return render_template("signup.html")

    def signup(self):
        fullname = request.form['fullname']
        email = request.form['email']
        password = request.form['password']
        confirm = request.form['confirmPassword']

        if password != confirm:
            flash("Passwords do not match.")
            return redirect(url_for('show_signup'))

        try:
            self.user_model.create_user(fullname, email, password)
            flash("Account created successfully! Please log in.")
            return redirect(url_for('login'))
        except mysql.connector.Error as err:
            flash(f"Error: {err}")
            return redirect(url_for('show_signup'))

    def login(self):
        if request.method == 'POST':
            email = request.form['email']
            password = request.form['password']

            user = self.user_model.authenticate(email, password)

            if user:
                session['user_id'] = user[0]
                session['user_email'] = user[2]
                flash("Login successful!")
                return redirect(url_for('main1'))
            else:
                flash("Invalid email or password.")
                return redirect(url_for('login'))
        return render_template("login1.html")

    def logout(self):
        session.clear()
        flash("You have been logged out successfully.")
        return redirect(url_for('login'))

    def main1(self):
        if 'user_id' not in session:
            abort(404)

        user = self.user_model.get_user_by_id(session['user_id'])
        return render_template("main1.html", username=user[0])

    def movie_page(self):
        if 'user_id' not in session:
            return redirect(url_for('login'))

        movies = self.movie_model.get_all_movies()
        user = self.user_model.get_user_by_id(session['user_id'])
        username = user[0] if user else ""

        return render_template("Movie page.html", movies=movies, username=username)

    def movie_details(self):
        if 'user_id' not in session:
            return redirect(url_for('login'))

        return render_template("movie details.html",
            title=request.args.get("title"),
            poster=request.args.get("poster"),
            hero=request.args.get("hero"),
            heroine=request.args.get("heroine"),
            rating=request.args.get("rating")
        )

    def seat_booking(self):
        if 'user_id' not in session:
            abort(404)

        title = request.args.get('title')
        poster = request.args.get('poster')
        date = request.args.get('date')
        time = request.args.get('time')

        booked_seats = self.booking_model.get_booked_seats(title, date, time)

        return render_template("seat-booking4.html",
            title=title,
            poster=poster,
            date=date,
            time=time,
            booked_seats=booked_seats
        )

    def payment(self):
        if 'user_id' not in session:
            abort(404)

        return render_template("payment.html",
            title=request.form['title'],
            poster=request.form['poster'],
            date=request.form['date'],
            time=request.form['time'],
            seats=request.form['seats'],
            total=request.form['total']
        )

    def confirm_payment(self):
        if 'user_id' not in session:
            return redirect(url_for('login'))

        title = request.form['title']
        date = request.form['date']
        time = request.form['time']
        seats = request.form['seats']
        email = session.get('user_email')

        try:
            self.booking_model.create_booking(title, date, time, seats, email)
            flash("Your ticket has been booked successfully!")
            return redirect(url_for('main1'))
        except mysql.connector.Error as err:
            flash(f"Booking failed: {err}")
            return redirect(url_for('main1'))

    def cancel_booking(self):
        if 'user_id' not in session:
            flash("Please log in to view your bookings.")
            return redirect(url_for('login'))

        email = session.get('user_email')
        bookings = self.booking_model.get_user_bookings(email)

        return render_template("cancel.html", bookings=bookings)

    def cancel_ticket(self):
        if 'user_id' not in session:
            flash("Please log in.")
            return redirect(url_for('login'))

        booking_id = request.form.get('booking_id')

        try:
            self.booking_model.cancel_booking(booking_id)
            flash("Booking cancelled successfully.")
        except mysql.connector.Error as err:
            flash(f"Error cancelling booking: {err}")

        return redirect(url_for('cancel_booking'))

    def page_not_found(self, error):
        return render_template("404.html"), 404

if __name__ == '__main__':
    movie_app = MovieBookingApp()
    movie_app.run()
