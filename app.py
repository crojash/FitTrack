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
from datetime import datetime
from flask import jsonify  # Import jsonify\
from itsdangerous import URLSafeTimedSerializer
import base64
import os
import re
from flask_socketio import SocketIO, send

import requests
import json

import hashlib
s = URLSafeTimedSerializer('your-secret-key')
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
CLIENT_ID = 'fitbit_client_key' # fitbit client key
CLIENT_SECRET = 'fitbit_key'  # client secret for fitbit
REDIRECT_URI = 'http://fittrack.hopto.org/fitbit_callback'  # redirect URI for fitbit
mail = Mail(app)
client = MongoClient("mongodb://localhost:27017")
db = client["UserLogin"]
db2 = client['forum_db']

# Create collections for 'users' and 'posts'
users_collection = db2['users']
posts_collection = db2['posts']
socketio = SocketIO(app)

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
@app.route('/connect_fitbit', methods=['GET', 'POST'])
@login_required
def authfitbit():
    if request.method == 'GET':
        # Generate the code verifier and challenge
        code_verifier = base64.urlsafe_b64encode(os.urandom(40)).decode('utf-8')
        code_verifier = re.sub('[^a-zA-Z0-9]+', '', code_verifier)
        session['code_verifier'] = code_verifier

        code_challenge = hashlib.sha256(code_verifier.encode('utf-8')).digest()
        code_challenge = base64.urlsafe_b64encode(code_challenge).decode('utf-8')
        code_challenge = code_challenge.replace('=', '')

        # Construct the authorization URL
        authorization_url = (
            f'https://www.fitbit.com/oauth2/authorize?client_id={CLIENT_ID}'
            f'&response_type=code&code_challenge={code_challenge}'
            f'&code_challenge_method=S256'
            f'&scope=activity%20heartrate%20location%20nutrition%20oxygen_saturation%20profile%20respiratory_rate%20settings%20sleep%20social%20temperature%20weight'
            f'&expires_in=604800'
        )
        return redirect(authorization_url)
    else:
        return redirect(url_for('dashboard'))

@app.route('/fitbit_callback', methods=['GET'])
@login_required
def fitbit_callback():
    code = request.args.get('code')
    code_verifier = session.get('code_verifier')

    user_id = session.get('user_id')
    user = db.users.find_one({"_id": ObjectId(user_id)})
    username = user.get('username', 'Unknown')


    if code and code_verifier:
        # Exchange the code for a token
        token_url = 'https://api.fitbit.com/oauth2/token'
        headers = {
            'Authorization': f'Basic {base64.b64encode(f"{CLIENT_ID}:{CLIENT_SECRET}".encode()).decode()}',
            'Content-Type': 'application/x-www-form-urlencoded'
        }
        data = {
            'client_id': CLIENT_ID,
            'grant_type': 'authorization_code',
            'code': code,
            'code_verifier': code_verifier,
            'redirect_uri': REDIRECT_URI
        }

        response = requests.post(token_url, headers=headers, data=data)
        if response.status_code == 200:
            token_data = response.json()
            session['fitbit_access_token'] = token_data['access_token']
            session['fitbit_refresh_token'] = token_data['refresh_token']
            session['fitbit_user_id'] = token_data['user_id']
            db.users.update_one({"username": username},
                                {"$set": {
                                    "fitbit_code": code,
                                    "fitbit_access_token": session['fitbit_access_token'],
                                    "fitbit_refresh_token": session['fitbit_refresh_token'],
                                    "fitbit_user_id": session['fitbit_user_id']
                                        }})
            return redirect(url_for('dashboard'))
        else:
            return 'Error authenticating with Fitbit.'

    return 'Missing code or code verifier.'


@app.route('/get_fitbit_data')
def get_fitbit_data():
    user_id = session.get('user_id')
    user = db.users.find_one({"_id": ObjectId(user_id)})
    fitbit_token = user.get("fitbit_access_token")
    fitbit_user_id = user.get("fitbit_user_id")

    # Initialize default values
    calories_burned = 0
    steps_taken = 0
    heart_times = []
    beats = []
    calories_eaten = 0
    daily_calories = user.get('daily_calories')

    if fitbit_token and fitbit_user_id:
        response = requests.get(f'https://api.fitbit.com/1/user/{fitbit_user_id}/activities/date/today.json', headers={'Authorization': 'Bearer ' + fitbit_token})
        if response.status_code == 200:
            data = response.json()
            calories_burned = data['summary']['caloriesOut']
            steps_taken = data['summary']['steps']

        heart_response = requests.get(f'https://api.fitbit.com/1/user/{fitbit_user_id}/activities/heart/date/today/today/15min.json', headers={'Authorization': 'Bearer ' + fitbit_token})
        if heart_response.status_code == 200:
            data = heart_response.json()
            heart_rates = data['activities-heart-intraday']['dataset']
            for tick in heart_rates:
                heart_times.append(tick['time'])
                beats.append(tick['value'])

    if daily_calories:
        for date, entries in daily_calories.items():
            for entry in entries['foods']:
                calories_eaten += entry['calorie_count']

    return jsonify({
        "calories_burned": calories_burned,
        "calories_eaten": calories_eaten,
        "steps_taken": steps_taken,
        "heart_times": heart_times,
        "beats": beats
    })

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
        return render_template('signup.html', error_message=error_message)
    
    db.users.insert_one({
            "username": username,
            "password": password, 
            "role":'reg', 
            "email": email,
            "chat_history": [],
            "created_at": time.time(),
            "weight": 0,
            "height": 0,
            "activity_level": 0,
            "current_weight": 0,
            "goal_weight": 0,
            "rate_weight": 0,
            "fitbit_code": "",
            "fitbit_access_token": "",
            "fitbit_refresh_token": "",
            "fitbit_user_id": "",
            "logged_exercises": [],
            "macro_protein": 0,
            "macro_carb": 0,
            "macro_fat": 0,
            "daily_calories": {}  # Daily calorie intake will be stored as a dictionary

        })

    return redirect(url_for('index', message='User created successfully!'))
@app.route('/reset_request', methods=['GET', 'POST'])
def reset_request():
    if request.method == 'GET':
        return render_template('reset_request.html')
    username = request.form.get('email')
    user = db.users.find_one({"email": username})

    if user:
        token = s.dumps(username, salt='reset-password')
        msg = Message('Reset Password', sender=mail_username, recipients=[username])
        link = url_for('reset_password', token=token, _external=True)
        msg.body = 'Your link is {}'.format(link)
        mail.send(msg)
        return render_template('login.html', success=True)

@app.route('/reset_password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    try:
        if request.method == 'GET':
            return render_template('reset_password.html', token=token)
        
        email = s.loads(token, salt='reset-password',max_age=1000)
        password = request.form.get('password')
        db.users.update_one({"email": email}, {"$set": {"password": password}})
        return render_template('login.html')
    except SignatureExpired:
        return '<h1>Token expired</h1>'
        
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
@app.route('/get_daily_calorie_limit', methods=['GET'])
@login_required  # Add login_required decorator to ensure only logged-in users can access this endpoint
def get_daily_calorie_limit():
    try:
        user_id = session.get('user_id')  # Get the user's ID from the session
        user = db.users.find_one({"_id": ObjectId(user_id)})  # Find the user in the database using the user_id

        if user:
            daily_limit = round(user.get('daily_limit', 0))  # Retrieve the user's daily calorie limit and round it
            return jsonify({"daily_limit": daily_limit})
        else:
            return jsonify({"error": "User not found"}), 404

    except Exception as e:
        return jsonify({"error": f"An error occurred: {str(e)}"}), 500
@app.route('/forums')
@login_required
def forums():
   posts = posts_collection.find()
   is_admin = False
   user_id = session.get('user_id')
  
   if user_id:
       user = db.user.find_one({'_id': ObjectId(user_id)})
       if user:
           is_admin = user.get('role') == 'admin'

   return render_template('forums.html', posts=posts, is_admin=is_admin)
from bson.objectid import ObjectId

@app.route('/forum/<post_id>')
def forum(post_id):
   posts_collection = db2['posts']
   users_collection = db2['users']
   post = posts_collection.find_one({'_id': ObjectId(post_id)})
   if not post:
       # Handle post not found
       return render_template('error.html', message='Post not found'), 404

   username = None
   if post.get('created_by') and isinstance(post['created_by'], dict) and '_id' in post['created_by']:
       user_id = ObjectId(post['created_by']['_id'])
       user = users_collection.find_one({"_id": user_id})
       if user:
           username = user.get('username')

   return render_template('forum.html', forum=post, username=username)

@app.route('/create_post', methods=['POST'])
@login_required
def create_post():
   title = request.form.get('title')
   content = request.form.get('content')
   user_id = session.get('user_id')

   # Fetch the user document from the database using the user_id
   user = db.users.find_one({"_id": ObjectId(user_id)})

   if title and content and user_id:
       print('in')
       post = {'title': title, 'content': content, 'created_by': user_id}
       posts_collection.insert_one(post)

   return redirect(url_for('forums'))
@app.route('/chat')
def groupchj():
    return render_template('chat.html')

@socketio.on('message')
def handleMessage(msg):
    print('Message: ' + msg)
    send(msg, broadcast=True)
@app.route('/delete_post/<post_id>', methods=['GET', 'POST'])
@login_required
def delete_post(post_id):
   user_id = session.get('user_id')
   user = db.user.find_one({'_id': ObjectId(user_id)})


   if user and user.get('role') == 'admin':
       if request.method == 'POST':
           # Delete the post
           result = posts_collection.delete_one({'_id': ObjectId(post_id)})
           if result.deleted_count > 0:
               return jsonify({'success': True})
           else:
               return jsonify({'success': False, 'error': 'Post not found'}), 404


   return jsonify({'success': False, 'error': 'Not authorized'}), 403
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
    last_modified_date = user.get('last_modified_date', None)

    try:
        bmr = float(bmr)
    except ValueError:
        bmr = 0.0

    current_date = datetime.now().strftime('%Y-%m-%d')

    if last_modified_date != current_date:
        calculated_daily_limit = bmr * 1.2  
        
        db.users.update_one(
            {"_id": ObjectId(user_id)},
            {
                "$set": {
                    "daily_limit": calculated_daily_limit,
                    "last_modified_date": current_date
                }
            }
        )
        
        daily_limit = calculated_daily_limit

    # Round the daily_limit to a whole number
    try:
        daily_limit = round(float(daily_limit))
    except ValueError:
        daily_limit = 0  # Or handle it in a way that makes sense for your application

    if bmr and tdee:
        return render_template('dashboard.html', username=username, bmr=bmr, tdee=tdee, daily_limit=daily_limit)
    else:
        error_message = "In order to see your BMR, TDEE, and daily calorie limit, please enter in your information on the goals page."
        return render_template('dashboard.html', error_message=error_message)
    
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
    openai.api_key = "openap_api_key"
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
    macro_protein = user.get("macro_protein", '')
    macro_carb = user.get("macro_carb",'')
    macro_fat = user.get("macro_fat", '')

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
        if not request.form.get("age") or not request.form.get("feet") or not request.form.get("inches") or not request.form.get("activity-level") or not request.form.get("current-weight") or not request.form.get("goal-weight") or not request.form.get("rate-weight") or not request.form.get("macro-protein") or not request.form.get("macro-carb") or not request.form.get("macro-fat"):
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
            macro_protein = int(request.form.get("macro-protein", macro_protein))
            macro_carb = int(request.form.get("macro-carb", macro_carb))
            macro_fat = int(request.form.get("macro-fat", macro_fat))
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
                                    "daily_limit": daily_limit,
                                    "macro_protein": macro_protein,
                                    "macro_carb": macro_carb,
                                    "macro_fat": macro_fat,
                                }})
            flash('Goals successfully set!', 'success')


    return render_template('goals.html', username=username, age=age,
                           feet=pfeet, inches=pinches,
                           activity_level=activity_level_text,
                           current_weight=current_weight,
                           goal_weight=goal_weight,
                           rate_weight=rate_weight,
                           macro_protein=macro_protein,
                           macro_carb=macro_carb,
                           macro_fat=macro_fat)

# Takes user to log food page and a user attempting a search and adding items to the log

@app.route('/exercises', methods=['GET'])
@login_required
def exercises():
    
    return render_template('exercises.html')


@app.route('/exercisedetails', methods=['GET', 'POST'])
@login_required
def exercise_details():

    user_id = session.get('user_id')
    user = db.users.find_one({"_id": ObjectId(user_id)})

    if not user:
        return redirect(url_for('login'))

    username = user.get('username', 'Unknown')
    exercise_name = user.get('exercise_name', '')
    duration = user.get('duration', '')
    sets = user.get('sets', '')
    reps = user.get('reps', '')
    logged_exercises = user.get('logged_exercises', [])

    if request.method == 'POST':

        if not request.form.get('duration') or not request.form.get('sets') or not request.form.get('reps'):
            flash('Please fill in all the fields', 'error')
    
        else:

            exercise_name = request.form.get('exercise_name')
            duration = request.form.get('duration')
            sets = request.form.get('sets')
            reps = request.form.get('reps')

            exercise = {
                'exercise_name' : exercise_name,
                'duration': duration,
                'sets': sets,
                'reps': reps
            }

            logged_exercises.append(exercise)


            db.users.update_one({"username": username},
                                {"$set": {
                                    "logged_exercises": logged_exercises
                                }})
            flash('Exercise registered!', 'success')

    return render_template('exercisedetails.html', username = username, logged_exercises = logged_exercises)


@app.route('/search_exercises', methods=['POST'])
@login_required
def search_exercises():
    data = request.get_json()
    search_term = data.get('search_term')

    headers = {
	    "X-RapidAPI-Key": "rapidAPI_Key",
        "X-RapidAPI-Host": "rapidAPI_Host"
    }

    search_term = search_term.replace(' ', '%20')
    url = f'https://exercisedb.p.rapidapi.com/exercises/name/{search_term}?limit=100'

    response = requests.get(url, headers=headers)
    print(response)
    if response.status_code == 200:
        # Convert the response to a valid Flask response using jsonify
        return jsonify(response.json())
    else:
        # Return an error as a JSON response with the appropriate status code
        return jsonify({"error": "Failed to retrieve exercise data from the API"}), 500



@app.route('/log_exercise', methods=['GET', 'POST'])
@login_required
def log_exercises():

    user_id = session.get('user_id')
    user = db.users.find_one({"_id": ObjectId(user_id)})

    #db.users.insertone

    if not user:
        return redirect(url_for('login'))

    username = user.get('username', 'Unknown')
    logged_exercises = user.get('logged_exercises', [])

    #db.users.update_one({"username": username}, {"$set": {"logged_exercises": []}})

    return render_template('logexercises.html', username = username, logged_exercises = logged_exercises)
    


@app.route('/delete_exercise', methods=['DELETE'])
@login_required
def delete_exercises():

    user_id = session.get('user_id')
    user = db.users.find_one({"_id": ObjectId(user_id)})

    if not user:
        return redirect(url_for('login'))
    
    username = user.get('username', 'Unknown')
    
    index = int(request.args.get('index', -1))
    logged_exercises = user.get('logged_exercises', [])

    if 0 <= index < len(logged_exercises):
        del logged_exercises[index]

        db.users.update_one({"username": username},
                                {"$set": {
                                    "logged_exercises": logged_exercises
                            }})
        flash('Exercise deleted!', 'success')
    else:
        flash("Error, exercise doesn't exist.", 'error')

    return render_template('logexercises.html', username = username, logged_exercises = logged_exercises)



@app.route('/edit_exercise', methods=['PUT'])
@login_required
def edit_exercises():
    user_id = session.get('user_id')
    user = db.users.find_one({"_id": ObjectId(user_id)})

    if not user:
        return redirect(url_for('login'))
    
    username = user.get('username', 'Unknown')
    
    index = int(request.args.get('index', -1))
    updated_duration = request.form.get('duration', '')
    updated_sets = request.form.get('sets', '')
    updated_reps = request.form.get('reps', '')
    logged_exercises = user.get('logged_exercises', [])

    if 0 <= index < len(logged_exercises):
        logged_exercises[index].update({'duration': updated_duration, 'sets': updated_sets, 'reps': updated_reps})

        db.users.update_one({"username": username},
                                {"$set": {
                                    "logged_exercises": logged_exercises
                            }})
        flash('Exercise edited!', 'success')
    else:
        flash("Error, exercise doesn't exist.", 'error')
    
    return render_template('logexercises.html', username = username, logged_exercises = logged_exercises)








@app.route('/get_nearest_gym', methods=['POST'])
def get_nearest_gym():
    try:
        data = request.get_json()
        lat = data.get('latitude')
        lon = data.get('longitude')
        long=lon
        lat2=lat
        
        apiKey = "Google_API_Key"  # Replace this with your Google API key

        apiUrl = f"https://maps.googleapis.com/maps/api/place/nearbysearch/json?location={lat},{lon}&radius=1500&type=gym&key={apiKey}"
        response = requests.get(apiUrl)

        if response.status_code == 200:
            result = response.json()
            gymName = result['results'][0]['name']
            photo_reference = result['results'][0]['photos'][0]['photo_reference']
            photo_url = f"https://maps.googleapis.com/maps/api/place/photo?maxwidth=400&photoreference={photo_reference}&key={apiKey}"
            
            return {"gymName": gymName, "photoUrl": photo_url}
        else:
            return {"error": "Unable to fetch gym information"}, 400
    except Exception as e:
        return {"error": f"An error occurred: {str(e)}"}, 500
def kelvin_to_farhenheit(kelvin):
    return round((kelvin - 273.15) * 9/5 + 32)
@app.route('/weather', methods=['POST'])
def get_weather():
    try:
        data = request.get_json()
        lat = data.get('latitude')
        lon = data.get('longitude')

        print(f"Latitude: {lat}, Longitude: {lon}")  # Debug print

        # Your OpenWeatherMap API Key
        api_key = "OpenWeatherMap_API_Key"
        base_url = "http://api.openweathermap.org/data/2.5/weather?"

        complete_url = f"{base_url}lat={lat}&lon={lon}&appid={api_key}"

        response = requests.get(complete_url)
        data = response.json()

        print(f"API response: {data}")  # Debug print

        if data["cod"] == 200:
            main_data = data["main"]
            weather_data = data["weather"][0]

            temp = main_data["temp"]
            temp = kelvin_to_farhenheit(temp)
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
        print(f"Error: {e}")  # Debug print
        return jsonify({"error": f"An error occurred: {str(e)}"}), 500
#yvonnys code:
@app.route('/meals', methods=['GET', 'POST'])
@login_required
def meals():
    user_id = session.get('user_id')
    user = db.users.find_one({"_id": ObjectId(user_id)})

    if not user:
        return redirect(url_for('login'))

    username = user.get('username', 'Unknown')
    my_dict_list = []
    breakfast = get_random_meal(user, "breakfast")
    snacks = get_random_meal(user, "snack")
    dinner = get_random_meal(user, "lunch")
    lunchs = get_random_meal(user, "dinner")

    my_dict_list = [breakfast, snacks, dinner, lunchs]

    # Check for error responses before rendering the template
    for item in my_dict_list:
        if "error" in item:
            return render_template('meals.html', username=username, error=item["error"])

    # If there are no errors, proceed to render the template
    return render_template('meals.html', username=username, my_dict_list=my_dict_list)

@app.route('/get_random_snack', methods=['GET', "POST"])
@login_required
def get_random_snack():
    user_id = session.get('user_id')
    user = db.users.find_one({"_id": ObjectId(user_id)})
    if not user:
        return redirect(url_for('login'))
    # Return the response as JSON
    return get_random_meal(user, "snack")


@app.route('/get_random_breakfast', methods=['GET', "POST"])
@login_required
def get_random_breakfast():
    user_id = session.get('user_id')
    user = db.users.find_one({"_id": ObjectId(user_id)})
    if not user:
        return redirect(url_for('login'))
    # Return the response as JSON
    return get_random_meal(user, "breakfast")



@app.route('/get_random_lunch', methods=['GET', "POST"])
def get_random_lunch():

    user_id = session.get('user_id')
    user = db.users.find_one({"_id": ObjectId(user_id)})
    if not user:
        return redirect(url_for('login'))
    # Return the response as JSON
    return get_random_meal(user, "lunch")

@app.route('/get_random_dinner', methods=['GET', "POST"])
@login_required
def get_random_dinner():
    user_id = session.get('user_id')
    user = db.users.find_one({"_id": ObjectId(user_id)})
    if not user:
        return redirect(url_for('login'))   
    return get_random_meal(user, "dinner")

@app.route("/fetchBreakfast", methods=["POST"])
@login_required
def fetchBreakfast(): 
    if request.method == 'POST':
        data = request.get_json()
        user_id = session.get('user_id')
        user = db.users.find_one({"_id": ObjectId(user_id)})

        breakfast_plan = {
            "breakfast_name": data.get('foodname'),
            "breakfast_ingredients": data.get('ingredients'), 
            "breakfast_carbs": extract_numeric_value(data.get('carbs')),
            "breakfast_protein": extract_numeric_value(data.get('protein')),
            "breakfast_fat": extract_numeric_value(data.get('fat')),
            "breakfast_calories": extract_numeric_value(data.get('calories')),
        }

        # Use $push to append the new breakfast plan to the existing array
        db.users.update_one({"_id": ObjectId(user_id)},
                            {"$push": {"breakfasts": breakfast_plan}})

        flash('Goals successfully set!', 'success')

        # Return a response (you can customize this based on your needs)
        return jsonify({"status": "success"})
    

@app.route("/fetchDinner", methods=["POST"])
@login_required
def fetchDinner(): 
    if request.method == 'POST':
        data = request.get_json()
        user_id = session.get('user_id')
        user = db.users.find_one({"_id": ObjectId(user_id)})

        dinner_plan = {
            "breakfast_name": data.get('foodname'),  # Update this line
            "breakfast_ingredients": data.get('ingredients'),  # Update this line
            "breakfast_carbs": extract_numeric_value(data.get('carbs')),
            "breakfast_protein": extract_numeric_value(data.get('protein')),
            "breakfast_fat": extract_numeric_value(data.get('fat')),
            "breakfast_calories": extract_numeric_value(data.get('calories')),
        }

        db.users.update_one({"_id": ObjectId(user_id)},
                            {"$push": {"dinners": dinner_plan}})

        flash('Goals successfully set!', 'success')

        return jsonify({"status": "success"})
    
@app.route("/fetchSnack", methods=["GET","POST"])
@login_required
def fetchSnack(): 
    if request.method == 'POST':
        data = request.get_json() ## data received from planning.html
        user_id = session.get('user_id')
        user = db.users.find_one({"_id": ObjectId(user_id)})

        snack_plan = {
            "snack_name": data.get('foodname'),
            "snack_ingredients": data.get('ingredients'), 
            "snack_carbs": extract_numeric_value(data.get('carbs')),
            "snack_protein": extract_numeric_value(data.get('protein')),
            "snack_fat": extract_numeric_value(data.get('fat')),
            "snack_calories": extract_numeric_value(data.get('calories')),
        }

        # Use $push to append the new breakfast plan to the existing array
        db.users.update_one({"_id": ObjectId(user_id)},
                            {"$push": {"snacks": snack_plan}})

        flash('Goals successfully set!', 'success')

        # Return a response (you can customize this based on your needs)
        return jsonify({"status": "success"})

@app.route("/fetchLunch", methods=["POST"])
@login_required
def fetchLunch(): 
    if request.method == 'POST':
        data = request.get_json()
        user_id = session.get('user_id')
        user = db.users.find_one({"_id": ObjectId(user_id)})

        lunch_plan = {
            "lunch_name": data.get('foodname'),
            "lunch_ingredients": data.get('ingredients'), 
            "lunch_carbs": extract_numeric_value(data.get('carbs')),
            "lunch_protein": extract_numeric_value(data.get('protein')),
            "lunch_fat": extract_numeric_value(data.get('fat')),
            "lunch_calories": extract_numeric_value(data.get('calories')),
        }

        # Use $push to append the new breakfast plan to the existing array
        db.users.update_one({"_id": ObjectId(user_id)},
                            {"$push": {"lunchs": lunch_plan}})

        flash('Goals successfully set!', 'success')

        # Return a response (you can customize this based on your needs)
        return jsonify({"status": "success"})
    


def get_random_meal(user, foodname):
    openai.api_key = "openai_api_key"
    bmr = user.get("bmr", 'Unknown')
    tdee = user.get("tdee", 'Unknown')
    goal_weight = user.get("goal_weight", 'Unknown')
    weekly_rate_weight = user.get("rate_weight", 'Unknown')
    activity_level = user.get("activity_level", 'Unknown')
    try:
        assistant_response = openai.ChatCompletion.create(
            model="model",
            messages=[
                {"role": "system", "content": "You are a helpful assistant designed to output JSON."},
                {"role": "user", "content": f"Can you generate me a random {foodname} based on bmr= {bmr}, tdee= {tdee}, goal_weight= {goal_weight}, weekly_rate_loose= {float(weekly_rate_weight)*0.453}, and activity_level={activity_level}. The response should be in a json object with foodname: food_name,ingredients: ingredients (quantity),protein: protein,carbs: carbs, fat: fat, calories: calories."}
            ]
        ).choices[0].message
        # Check if 'content' key exists in assistant_response
        if 'content' in assistant_response:
            # Extract the 'content' from the assistant response
            assistant_content = assistant_response['content']

            # Load the JSON string into a Python dictionary
            random_dict = json.loads(assistant_content)

            # Print the final dictionary (for debugging purposes)
            print(random_dict)

            # Return the response as a dictionary
            return random_dict
        else:
            # Return an error message as a dictionary
            return {"error": "Unexpected response format from OpenAI API."}
    except Exception as e:
        print(f"Exception during OpenAI API call: {e}")
        # Return an error message as a dictionary
        return {"error": "An error occurred during the OpenAI API call."}
    

### Helper method
def extract_numeric_value(value):
    if isinstance(value, (float, int)):
        return round(float(value), 2)
    elif isinstance(value, list):
        if len(value) == 1:
            return round(float(value[0]), 2)
        else:
            return [round(float(item), 2) for item in value]
    else:
        matches = re.findall(r"[-+]?\d*\.\d+|\d+", str(value))
        return [round(float(match), 2) for match in matches]


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=True)


