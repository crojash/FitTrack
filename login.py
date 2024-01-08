from flask import Blueprint, session, redirect, url_for, render_template, request
from pymongo import MongoClient
import os
import openai
import time
from bson.objectid import ObjectId
from flask_mail import Mail, Message
from config import *
from auth import login_required, check_password_hash, generate_password_hash

# Initialize the blueprint for login-related routes
login_bp = Blueprint('login_bp', __name__)

# MongoDB client setup (I'm assuming you also need this for the login routes)
client = MongoClient("mongodb://localhost:27017")
db = client["UserLogin"]

@login_bp.route('/signup', methods=['POST'])
def signup():
    username = request.form.get("username")
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

    return redirect(url_for('index', message='User created successfully!'))

@login_bp.route('/login', methods=['POST'])
def login_page():
    # Check if the user is already logged in
    if 'username' in session:
        return redirect(url_for('dashboard'))
    return render_template('login.html')
@login_bp.route('/signup')
def signup_page():
    if 'username' in session:
        return redirect(url_for('dashboard'))
    return render_template('signup.html')
@login_bp.route('/logout')
@login_required
def logout():
    session.pop('username', None)
    session.pop('user_id', None)
    return redirect(url_for('index', message='Logged out successfully!'))