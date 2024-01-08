from flask import session, redirect, url_for, render_template
from functools import wraps
from pymongo import MongoClient
import bcrypt
import os

client = MongoClient(os.environ.get("DATABASE_URL"))
db = client["UserLogin"]

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'username' not in session:
            return redirect(url_for('login_page', message='Please log in to access the dashboard.'))
        return f(*args, **kwargs)
    return decorated_function

def check_password_hash(pwhash, password):
    return bcrypt.checkpw(password.encode('utf-8'), pwhash)

def generate_password_hash(password):
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode('utf-8'), salt)
