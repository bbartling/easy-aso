from flask import Flask, render_template, request, redirect, url_for, flash
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
import requests, json

# Flask app setup
app = Flask(__name__)
app.secret_key = 'your_secret_key'

# Configure Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)

# Dummy user data - replace with a real database in production
users = {'admin': {'password': 'admin'}}

# Define days of the week and time slots
time_slots = [f"{hour:02d}:00" for hour in range(24)]

# Define days of the week
days_of_week = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']

# Load the default schedule with 7 AM to 5 PM for Monday to Friday
default_schedule = {day: {"start": "07:00", "end": "17:00"} if day in ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday'] else {"start": None, "end": None} for day in days_of_week}


# User class for Flask-Login
class User(UserMixin):
    pass

# User loader callback for Flask-Login
@login_manager.user_loader
def user_loader(username):
    if username not in users:
        return None

    user = User()
    user.id = username
    return user

# Routes
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if username in users and users[username]['password'] == password:
            user = User()
            user.id = username
            login_user(user)
            return redirect(url_for('manage_schedule'))  # Redirect to manage_schedule

    return render_template('login.html')

@app.route('/dashboard')
@login_required
def dashboard():
    # Additional logic can be added here if needed
    return render_template('dashboard.html')

@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/schedule')
@login_required
def schedule():
    try:
        response = requests.get("http://localhost:8080/get_schedule")
        response.raise_for_status()
        schedule = response.json()
    except (requests.HTTPError, json.JSONDecodeError, Exception) as e:
        flash(f"Error loading schedule: {e}")
        schedule = {}

    # Pass the schedule data to the template
    return render_template('schedule.html', schedule=schedule)


@app.route('/manage-schedule', methods=['GET', 'POST'])
@login_required
def manage_schedule():

    if request.method == 'POST':
        # Extract and process form data
        schedule = {}
        for day in days_of_week:
            start_time = request.form.get(f'{day}-start-time')
            end_time = request.form.get(f'{day}-end-time')
            schedule[day] = {'start': start_time, 'end': end_time}
        
        # Logic to update the schedule
        # Save the schedule to a file or database, as required
        # ...

        flash('Schedule updated!', 'success')  # Display a success message
        return redirect(url_for('schedule'))

    # If GET request, load the default schedule or the last saved schedule
    return render_template('manage_schedule.html', 
                           days_of_week=days_of_week, 
                           time_slots=time_slots, 
                           schedule=default_schedule)


if __name__ == '__main__':
    app.run(debug=True, host="0.0.0.0")
