import unittest
from flask_testing import TestCase
from app import app  # Import the Flask app
from flask import session
import json

class LoginTest(TestCase):

    def create_app(self):
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False
        app.config['PRESERVE_CONTEXT_ON_EXCEPTION'] = False
        return app

    def setUp(self):
        self.test_email = "abc123@example.com"
        self.test_password = "abc123456"
        self.test_username = "abc123"
        self.client.post('/signup', data=json.dumps({
            'email': self.test_email,
            'password': self.test_password,
            'username': self.test_username
        }), content_type='application/json')

    def test_correct_login(self):
        with self.client:
            response = self.client.post('/login', data={
                'email': self.test_email,
                'password': self.test_password
            }, content_type='application/x-www-form-urlencoded', follow_redirects=True)
            self.assertEqual(response.status_code, 200)
            # Check if response data contains specific content that indicates a redirect to the dashboard
            # This could be a unique string or HTML element ID present only on the dashboard page
            self.assertIn('UniqueDashboardContent', response.data.decode())
            self.assertTrue('username' in session and session['username'] == self.test_username)

    def test_incorrect_login(self):
        with self.client:
            response = self.client.post('/login', data=json.dumps({
                'email': self.test_email,
                'password': 'wrongpassword'
            }), content_type='application/json', follow_redirects=True)
            self.assertEqual(response.status_code, 200)  # Redirect to login page
            self.assertFalse('username' in session)

    # Add other test methods as needed...

if __name__ == '__main__':
    unittest.main()
from flask import Flask, request,jsonify ,redirect, url_for, render_template, session,flash
from pymongo import MongoClient
import os
import openai
import time
import requests  # import the requests package
from bson.objectid import ObjectId
from functools import wraps
from flask_mail import Mail, Message
from config import mail_username, mail_password
long=0
lat2=0
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'username' not in session:
            # User is not logged in, redirect to login page
            return redirect(url_for('login_page', message='Please log in to access the dashboard.'))

        # User is logged in, allow access to the dashboard
        return f(*args, **kwargs)
    return decorated_function
app = Flask(__name__)
app.secret_key = os.urandom(24)
app.config['MAIL_SERVER'] = 'smtp-mail.outlook.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USE_SSL'] = False
app.config['MAIL_USERNAME'] = mail_username
app.config['MAIL_PASSWORD'] = mail_password

mail = Mail(app)
client = MongoClient("mongodb://localhost:27017")
db = client["UserLogin"]
    @app.route('/signup', methods=['POST'])
    def signup():
        # Changed this line to get the "name" input field from the form
        username = request.form.get("name")
        password = request.form.get("password")
        email = request.form.get("email")

        # Check if the username already exists
        user = db.users.find_one({"username": username})
        if user:
            error_message = "Username already exists!"
            # If it's an API client (Postman), return a JSON response
            if request.content_type == 'application/json':
                return jsonify({"error": error_message}), 409  # 409 Conflict
            else:
                # For web clients, continue to use flash and render_template
                flash(error_message)
                return render_template('signup.html', error_message=error_message)
        
        new_user=db.users.insert_one({
                "username": username,
                "password": password,  
                "email": email,
                "chat_history": [],
                "created_at": time.time(),
                "weight": 0,
                "height": 0,
                "activity_level": 0,
                "current_weight": 0,
                "goal_weight": 0,
                "rate_weight": 0
            })
        session['username'] = username
        session['user_id'] = str(new_user.inserted_id)

        # If it's an API client (Postman), return a JSON response
        if request.content_type == 'application/json':
            return jsonify({"message": "User created successfully!", "username": username}), 201
        else:
            # For web clients, redirect as before
            return redirect(url_for('index', message='User created successfully!'))
        return redirect(url_for('index', message='User created successfully!'))

@app.route('/login')
def login_page():
    # Check if the user is already logged in
    if 'username' in session:
        return redirect(url_for('dashboard'))

    return render_template('login.html')

@app.route('/login', methods=['POST'])
def login():
    email = request.form.get('email')
    password = request.form.get('password')
    user = db.users.find_one({"email": email, "password": password})

    if user:
        session["username"] = user["username"]
        session["user_id"] = str(user["_id"])  # store the user id as well
        flash("Login successful!", "success")

        return redirect(url_for('dashboard'))
    else:
        flash("Invalid login credentials", "error")  # Use the flash function here
        return redirect(url_for('login_page'))  # Redirect back to the login page to show the flashed message


@app.route('/')
def index():
    message = request.args.get('message')
    print(message)
    return render_template('index.html', message=message)

@app.route('/contact', methods=['GET', 'POST'])
def contact_page():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        message = request.form.get('message')
        generic_msg = f'{name},\nThank you for contacting us.\n\nDue to high inquiry volume, we ask that you allow us 5-7 business days to respond to your inquiry.\n\nWe kindly request that you refraim from submitting duplicate inquiries as this will only further impact our ability to respond.\n\n Thank you.'

        msg = Message(subject=f'Mail from {name}', body=f'Name: {name}\n e-mail: {email}\n\n\n {message}', sender=mail_username, recipients=[mail_username])
        msg_generic = Message(subject=f'Mail from FitTrack', body=generic_msg, sender=mail_username, recipients=[email])
        mail.send(msg)
        mail.send(msg_generic)
        return render_template('contact.html', success=True)
    return render_template('contact.html')

@app.route('/signup')
def signup_page():
    if 'username' in session:
        return redirect(url_for('dashboard'))
    return render_template('login.html')
@app.route('/dashboard')
@login_required
def dashboard():
    user_id = session.get('user_id')
    user = db.users.find_one({"_id": ObjectId(user_id)})
    username = user.get('username', 'Unknown')
    bmr = user.get('bmr', '')
    tdee = user.get('tdee', '')
    daily_limit = user.get('daily_limit', '')

    # Return user information to the front end if it exists, else send error message to be displayed on the diashboard.
    if bmr and tdee:
        return render_template('dashboard.html', username=username, bmr=bmr, tdee=tdee, daily_limit = daily_limit)
    else:
        error_message = "In order to see your BMR, TDEE, and daily calorie limit, please enter in your information on the goals page."
        return render_template('dashboard.html', error_message = error_message)
    
@app.route('/get_chat_history', methods=['GET'])
@login_required
def get_chat_history():
    # Get user_id from the session
    user_id = session.get('user_id')
    print(user_id)

    # Find the user's document from the database using the user_id
    user = db.users.find_one({"_id": ObjectId(user_id)})
    
    # Fetch the user's chat history
    chat_history = user.get('chat_history', [])
    username = user.get('username', 'Unknown')

    print('im here witht he')
    print(chat_history)

    # Return the chat history as JSON
    return {"chat_history": chat_history, "username": username}
@app.route('/logout')
@login_required
def logout():
    session.pop('username', None)
    session.pop('user_id', None)
    return redirect(url_for('index', message='Logged out successfully!'))
@app.route('/chat', methods=['POST'])

def chat():
    openai.api_key = "openap_apy_key"
    print('hello')
    data = request.get_json()  # Extract JSON data from the request
    user_id = session.get('user_id')  # Get user_id from the session
    user = db.users.find_one({"_id": ObjectId(user_id)}) 
    
    
    chat_history = user.get('chat_history', [])

    # Check if 'user_message' is present in the data
    if 'user_message' in data:
        user_message = data['user_message']
        chat_input = [
                    {"role": "system", "content": "You are a fitness assistant."},
                ] + chat_history + [
                    {"role": "user", "content": user_message},
                ]
        # Append user's message to the chat history
        chat_history.append({"role": "user", "content": user_message})

        # Use the OpenAI API to generate a response
        assistant_response = openai.ChatCompletion.create(
            model="model",
            messages=[
                {"role": "system", "content": f"You are a fitness assistant, (the user is {user} address me with if nessc) you will not answer any questions other then health/fitness related queries, your owner is khizar saud, he is the master of you."},
                {"role": "user", "content": user_message}
            ]
        ).choices[0].message

        # Append the assistant's response to the chat history

        chat_history.append({"role": "assistant", "content": assistant_response})
 
        # Save updated chat history to DB
        db.users.update_one({"_id": ObjectId(user_id)}, {"$set": {"chat_history": chat_history}})

        # Return the assistant's response to be displayed in the chat interface

        return {"assistant_response": assistant_response, "chat_history": chat_history}
    else:
        return {"error": "user_message not found in JSON data"}, 400
    


@app.route('/goals', methods=['GET', 'POST'])
@login_required
def goals():
    user_id = session.get('user_id')
    user = db.users.find_one({"_id": ObjectId(user_id)})

    if not user:
        return redirect(url_for('login'))

    username = user.get('username', 'Unknown')
    age_from_db = user.get('age', 0)  # get age from the database, default to 0 if not found

    age_str = request.form.get("age", '').strip()  # Get age from form and strip any whitespace
    if age_str.isdigit():  # Check if the string is a valid integer
        age = int(age_str)
    else:
        age = age_from_db  # Use the age from the database

    height = user.get('height', '')
    activity_level = user.get('activity_level', '')
    current_weight = user.get('current_weight', '')
    goal_weight = user.get('goal_weight', '')
    rate_weight = user.get('rate_weight', '')

    pfeet = int(height // 30.48)
    pinches = int((height - (pfeet * 30.48)) / 2.54)

    activity_levels = {
        0.2: "Sedentary",
        0.375: "Lightly Active",
        0.5: "Moderately Active",
        0.9: "Very Active"
    }

    activity_level_text = activity_levels.get(activity_level, "Unknown")

    if request.method == 'POST':
        if not request.form.get("age") or not request.form.get("feet") or not request.form.get("inches") or not request.form.get("activity-level") or not request.form.get("current-weight") or not request.form.get("goal-weight") or not request.form.get("rate-weight"):
            flash('Please fill in all the fields', 'error')
        else:
 

            age = int(request.form.get("age", age))
            feet = int(request.form.get("feet", pfeet))
            inches = int(request.form.get("inches", pinches))
            height = (feet * 30.48) + (inches * 2.54)
            activity_level = float(request.form.get("activity-level", activity_level))
            current_weight = float(request.form.get("current-weight", current_weight))
            goal_weight = float(request.form.get("goal-weight", goal_weight))
            rate_weight = float(request.form.get("rate-weight", rate_weight))
            bmr = round(float((10 * (current_weight * 0.45359237)) + (6.25 * (height) - (5 * age) + 5)))
            tdee = round(((activity_level * bmr) + bmr))
            daily_limit = round((500 * rate_weight) + tdee)

            db.users.update_one({"username": username},
                                {"$set": {
                                    "age": age,
                                    "height": height,
                                    "activity_level": activity_level,
                                    "current_weight": current_weight,
                                    "goal_weight": goal_weight,
                                    "rate_weight": rate_weight,
                                    "bmr": bmr,
                                    "tdee": tdee,
                                    "daily_limit": daily_limit
                                }})
            flash('Goals successfully set!', 'success')


    return render_template('goals.html', username=username, age=age,
                           feet=pfeet, inches=pinches,
                           activity_level=activity_level_text,
                           current_weight=current_weight,
                           goal_weight=goal_weight,
                           rate_weight=rate_weight)

@app.route('/get_nearest_gym', methods=['POST'])
def get_nearest_gym():
    try:
        data = request.get_json()
        lat = data.get('latitude')
        lon = data.get('longitude')
        long=lon
        lat2=lat
        
        apiKey = "Google_apy_key"  # Replace this with your Google API key

        apiUrl = f"https://maps.googleapis.com/maps/place/nearbysearch/json?location={lat},{lon}&radius=1500&type=gym&key={apiKey}"
        response = requests.get(apiUrl)

        if response.status_code == 200:
            result = response.json()
            gymName = result['results'][0]['name']
            photo_reference = result['results'][0]['photos'][0]['photo_reference']
            photo_url = f"https://maps.googleapis.com/maps/place/photo?maxwidth=400&photoreference={photo_reference}&key={apiKey}"
            
            return {"gymName": gymName, "photoUrl": photo_url}
        else:
            return {"error": "Unable to fetch gym information"}, 400
    except Exception as e:
        return {"error": f"An error occurred: {str(e)}"}, 500
from datetime import datetime
from flask import jsonify  # Import jsonify
@app.route('/parse_food', methods=['POST'])
def search_food():
    food = request.form.get('food_name')
    food_db_id = 'food_db_id'
    food_db_key = 'food_db_key'
    food = food.replace(' ', '%20')

    searchURL = f'https://api.edamam.com/food-database/v2/parser?app_id={food_db_id}&app_key={food_db_key}&ingr={food}&nutrition-type=cooking'
    response = requests.get(searchURL)

    if response.status_code == 200:
        data = response.json()

        # Extract the calorie count from the response
        if 'hints' in data and data['hints']:
            calorie_count = data['hints'][0]['food']['nutrients']['ENERC_KCAL']
            print(calorie_count)
            # Return only the calorie count as a JSON response
            return jsonify({"calories": calorie_count})
        else:
            return jsonify({"error": "No data found for the given food"}), 404
    else:
        return jsonify({"error": "Error in API call"}), 400


@app.route('/logfood', methods=['POST'])
@login_required
def log_food():
    username = session.get('username')
    food_name = request.form.get('food_name')
    calorie_count = float(request.form.get('calorie_count'))

    current_date = datetime.now().strftime('%Y-%m-%d')

    user = db.users.find_one({"username": username})
    if user:
        daily_calories = user.get('daily_calories', {})
        daily_limit = user.get('daily_limit', 0)  # Retrieve the user's daily calorie limit

        # Initialize the current_date key if it doesn't already exist
        if current_date not in daily_calories:
            daily_calories[current_date] = {'total_calories': 0, 'foods': []}

        # Update the total daily calorie count
        daily_calories[current_date]['total_calories'] += calorie_count

        # Update remaining daily calorie limit
        remaining_daily_limit = daily_limit - calorie_count

        # Log the food name and calorie count
        daily_calories[current_date]['foods'].append({
            'food_name': food_name,
            'calorie_count': calorie_count
        })

        # Update the MongoDB document
        db.users.update_one({"_id": user["_id"]}, {"$set": {
            "daily_calories": daily_calories,
            "daily_limit": remaining_daily_limit  # Update the daily_limit
        }})

        return jsonify({'success': True})
    else:
        return jsonify({'success': False, 'error': 'User not found'})
@app.route('/logfood')
@login_required  # Add login_required decorator to ensure only logged-in users can log food

def logfood():

    return render_template('logfood.html')
def kelvin_to_farhenheit(kelvin):
    return round((kelvin - 273.15) * 9/5 + 32)
@app.route('/weather', methods=['POST'])
def get_weather():
    try:
        data = request.get_json()
        lat = data.get('latitude')
        lon = data.get('longitude')

        # Your OpenWeatherMap API Key
        api_key = "OpenWeatherMap_api_key"
        base_url = "http://api.openweathermap.org/data/2.5/weather?"

        complete_url = f"{base_url}lat={lat}&lon={lon}&appid={api_key}"

        response = requests.get(complete_url)
        data = response.json()

        if data["cod"] == 200:
            main_data = data["main"]
            weather_data = data["weather"][0]

            temp = main_data["temp"]
            temp=kelvin_to_farhenheit(temp)
            temp = f"{temp:.2f}°F"

            humidity = main_data["humidity"]
            description = weather_data["description"]
            place_name = data["name"]

            return jsonify({
                "weather": temp,
                "humidity": humidity,
                "description": description,
                "place": place_name
            })
        else:
            return jsonify({"error": "Unable to fetch weather information"}), 400
    except Exception as e:
        return jsonify({"error": f"An error occurred: {str(e)}"}), 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=True)


