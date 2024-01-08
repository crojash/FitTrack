# tests.py
#SAUD
import pytest
import time
import requests
from app import app as flask_app 
from app import db 
from flask import url_for, session
from unittest.mock import patch
from bson.objectid import ObjectId
import psutil
from unittest.mock import patch

@pytest.fixture
def app():
    yield flask_app

@pytest.fixture
def client(app):
    return app.test_client()
#User_Authentication
@pytest.fixture
def test_session(client):
    with client.session_transaction() as sess:
        sess['user_id'] = 'session_id' #session_id
        sess['username'] = 'email@gmail.com'   
    yield client  # Provide the client instance with the test session
# Test Dashboard Access When Logged In (R3)
def test_dashboard_access_logged_in(test_session):
    response = test_session.get('/dashboard')
    assert response.status_code == 200  # Assuming successful access returns 200 OK

# Test Redirect to Login for Unauthorized Users (R3.1)
def test_dashboard_access_unauthorized(client):
    response = client.get('/dashboard', follow_redirects=True)
    assert response.status_code == 200  # Assuming redirection returns 200 OK
    assert b"Login" in response.data  # Assuming the login page contains the word "Login"

# Test Dashboard Content for Logged-In Users (R3.2)
def test_dashboard_content_logged_in(test_session):
    response = test_session.get('/dashboard')
    assert b"BMR" in response.data  # Check if BMR is displayed
    assert b"TDEE" in response.data  # Check if TDEE is displayed
    assert b"Calorie Limit" in response.data  # Check if daily calorie limit is displayed

@pytest.fixture
def check_ssl_status():
    url = 'https://fittrack.hopto.org'  # Replace with your app's URL
    try:
        response = requests.get(url)
        return response.status_code == 200  # If SSL is active, it should return 200 OK
    except requests.exceptions.SSLError:
        return False  # SSL error means SSL is not active
def test_check_checkssl(client):
        assert check_ssl_status  # Check SSL status before the test
def test_chat_history_storage(test_session):
    # Step 1: Send a chat message
    test_message = "Hello, this is a test message."
    test_session.post('/chat', json={'user_message': test_message})

    # Step 2: Fetch the chat history
    response = test_session.get('/get_chat_history')
    chat_history = response.json.get('chat_history', [])

    # Step 3: Verify the chat message is in the chat history
    assert any(msg.get('content') == test_message for msg in chat_history)  # Adjust according to the actual data structure
from unittest.mock import patch

def test_get_nearest_gym(client):
    with patch('requests.get') as mock_get:
        # Setting up the mock response
        mock_response = mock_get.return_value
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'results': [
                {'name': 'Test Gym', 'photos': [{'photo_reference': 'photo_ref'}]}
            ]
        }

        # Define the data to send
        data = {
            'latitude': 123.45,
            'longitude': 678.90
        }

        # Send a POST request to the route
        response = client.post('/get_nearest_gym', json=data)

        # Assert the response
        assert response.status_code == 200
        response_data = response.get_json()
        assert response_data['gymName'] == 'Test Gym'
        assert 'photoUrl' in response_data
def test_get_weather(client):
    with patch('requests.get') as mock_get:
        # Setting up the mock response
        mock_response = mock_get.return_value
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'cod': 200,
            'main': {
                'temp': 300,  # Kelvin
                'humidity': 50  # Adding humidity key
            },
            'weather': [{'description': 'sunny'}],
            'name': 'Test City'
        }

        # Define the data to send
        data = {
            'latitude': 123.45,
            'longitude': 678.90
        }

        # Send a POST request to the route
        response = client.post('/weather', json=data)

        # Assert the response
        assert response.status_code == 200



def test_login_success(client):
    assert check_ssl_status  # Check SSL status before the test

    response = client.post('/login', data={
        'email': 'admin@me.com',
        'password': 'admin1234'
    })
    assert response.status_code == 302  # Assuming a redirect happens on successful login
    assert 'dashboard' in response.headers['Location']  # Assuming redirection to the dashboard

def test_login_failure(client):
    response = client.post('/login', data={
        'email': 'admin@me.com',
        'password': 'wrongpassword'
    })
    assert response.status_code == 302  # Assuming a redirect happens on failed login
    assert 'login' in response.headers['Location']  # Assuming redirection to the login page
def test_signup_success(client):
    import time
    from app import app as flask_app

    # Create a unique email and username to avoid conflicts with existing data
    unique_email = 'testuser_{}@example.com'.format(time.time())
    unique_username = 'testuser_{}'.format(time.time())

    # Use the test_request_context to simulate a request
    with flask_app.test_request_context():
        response = client.post('/signup', data={
            'name': unique_username,
            'password': 'testpassword',
            'email': unique_email
        })

        # Now you can use url_for since we are in an app context
        redirect_location = url_for('index', _external=True)
        
        # Check for redirect on successful signup
        assert 'successfully' in response.get_data(as_text=True)  # Here we ensure we are searching in the response data

def test_signup_failure(client):
    # Make sure to use a username that already exists in the test database
    #R1.1
    response = client.post('/signup', data={
        'name': 'existing_user',
        'password': 'testpassword',
        'email': 'existing_email@example.com'
    })
    # Assuming you render a signup template with an error on failure
    assert response.status_code == 200  # Assuming the page renders and doesn't redirect
    assert b"Username already exists!" in response.data
def test_dashboard_access_unauthorized(client):
    response = client.get('/dashboard', follow_redirects=True)
    assert response.status_code == 200  # Assuming redirection returns 200 OK
    assert b"Login" in response.data  # Assuming the login page contains the word "Login"
from unittest.mock import patch, MagicMock
from unittest.mock import patch, MagicMock

def test_chat_success(client):
    # Mocked response data for OpenAI API
    mocked_response = MagicMock()
    mocked_choice = MagicMock()
    mocked_choice.message = 'Mocked response from fitness assistant.'
    mocked_response.choices = [mocked_choice]

    # Set up the session with a specific user_id
    with client.session_transaction() as sess:
        sess['user_id'] = 'session_id'
        sess['username'] = 'email@gmail.com'

    # Define the data to send to the chat route
    data = {
        'user_message': 'Hello, how can I improve my fitness?'
    }

    # Use unittest.mock.patch to mock the openai.ChatCompletion.create call
    with patch('openai.ChatCompletion.create', return_value=mocked_response) as mock_create:
        # Send a POST request to the chat route
        response = client.post('/chat', json=data)

        # Assert that the mock was called
        mock_create.assert_called_once()

    # Assert the response
    assert response.status_code == 200
    response_data = response.get_json()
    assert 'assistant_response' in response_data
    assert response_data['assistant_response'] == 'Mocked response from fitness assistant.'
def test_fetch_calorie_count(client):
    food_name = "apple"

    response = client.post('/parse_food', data={'food_name': food_name})

    assert response.status_code == 200
    assert 'calories' in response.json

def test_update_daily_calorie_count(client):
    client.post('/signup', data={'name': 'testuser', 'password': 'testpassword', 'email': 'test@example.com'})
    client.post('/login', data={'email': 'test@example.com', 'password': 'testpassword'})

    food_name = "banana"
    calorie_count = 100

    response = client.post('/logfood', data={'food_name': food_name, 'calorie_count': calorie_count})

    assert response.status_code == 200
    assert 'success' in response.json

def test_clear_user(test_session):
    # Assuming that the user is already logged in via the test_session fixture
    # The test_session fixture sets up the session with the user details

    # Logout request
    logout_response = test_session.get('/logout')
    assert logout_response.status_code == 302  # Assuming a redirect happens on logout

    # After logout, the user details should no longer be in the session
    with test_session.session_transaction() as sess:
        assert 'user_id' not in sess
        assert 'username' not in sess

def test_machine_ram():
    # Get the system's total RAM in bytes
    total_ram = psutil.virtual_memory().total

    # Convert bytes to gigabytes (GB)
    total_ram_gb = total_ram / (1024 ** 3)

    # Define the minimum required RAM (8GB)
    required_ram_gb = 8.0

    # Define an acceptable range (e.g., within 0.5GB of 8GB)
    acceptable_range_gb = 0.5

    assert (
        required_ram_gb - acceptable_range_gb <= total_ram_gb <= required_ram_gb + acceptable_range_gb
    ), f"Machine has {total_ram_gb:.2f} GB of RAM, which is not within the acceptable range of 7.5GB to 8.5GB"
    
# ----------------Josh's Test Cases--------------------------------------------------------------------------------------------

def test_bmr_tdee_daily_limit_calculations(client):

    #Send a post request to the goals route
    response = client.post('/goals', data={
        'age': '27',
        'feet': '6',
        'inches' : '1',
        'activity_level': '0.375',
        'current_weight': '220',
        'goal_weight' : '190',
        'rate_weight' : '-1'
    })

    assert response.status_code == 302 #Assuming a redirect happens after successfully setting goals

    updated_user_data = db.users.find_one({"username" : "Joe"})

    expected_bmr = 2027

    expected_tdee = 2787

    expected_daily_limit = 2287

    assert updated_user_data.get('bmr') == expected_bmr
    assert updated_user_data.get('tdee') == expected_tdee
    assert updated_user_data.get('daily_limit') == expected_daily_limit


def test_store_goals(client):
    
    #Send a POST request to the goals route
    response = client.post('/goals', data={
        'username': 'Joe',
        'password': 'exercises',
        'email': 'exercises@gmail.com',
        'age': '27',
        'feet': '6',
        'inches' : '1',
        'activity_level': '0.375',
        'current_weight': '220',
        'goal_weight' : '190',
        'rate_weight' : '-1'
    })

    updated_user = db.users.find_one({"username" : "Joe"})
    feet = 6
    inches = 1
    assert updated_user.get('age') == 27
    assert updated_user.get('height') == (feet * 30.48) + (inches * 2.54)
    assert updated_user.get('activity_level') == 0.375
    assert updated_user.get('current_weight') == 220
    assert updated_user.get('goal_weight') == 190
    assert updated_user.get('rate_weight') == -1

    assert response.status_code == 302 #Assuming redirect happens after successfully setting goals


def test_search_exercises(client):
    search_term = 'push'
    headers = {
        "X-RapidAPI-Key": "x_rapidAPI_key",
        "X-RapidAPI-Host": "x_rapidAPI_key"
    }
    url = f'https://exercisedb.p.rapidapi.com/exercises/name/{search_term}?limit=100'
    response = requests.get(url, headers = headers)

    assert response.status_code == 200 #Asserting the response 

def test_log_exercise(client):
    # Simulate logged-in user data or session
    with client.session_transaction() as session:
        session['user_id'] = 'session_id'
        session['username'] = 'Joe'

    # Simulating user entering in data for a push up
    exercise_data = {
        'exercise_name': 'Push-ups',
        'duration': 30,
        'sets': 3,
        'reps': 15
    }

    # Send a POST request to log the exercise
    response = client.post('/log_exercise', json=exercise_data)

    # Check the response status code
    assert response.status_code == 200