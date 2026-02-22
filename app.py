from flask import Flask, jsonify, redirect, request, render_template, url_for, session
from db import get_mongo_collection, get_mysql_connection
import mysql.connector
import json
import time

app = Flask(__name__)
db = get_mongo_collection()
app.secret_key = 'your_secret_key'

@app.route('/')
def index():
    if 'username' in session:
        return redirect(url_for('profile', username=session['username']))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':

        username = request.form.get('username')
        password = request.form.get('password')

        conn = None
        cursor = None
        try:
            conn = get_mysql_connection()
            if not conn:
                return "Could not connect to the database. Please try again later.", 500
            cursor = conn.cursor(dictionary=True)
            
            cursor.execute("SELECT * FROM users WHERE username = %s AND password = %s", (username, password))
            user = cursor.fetchone()

            if user:
                session['username'] = username
                return redirect(url_for('index'))
            else:
                return "Invalid username or password. Please try again."
        except mysql.connector.Error as err:
            return str(err), 500
        finally:
            if cursor: cursor.close()
            if conn: conn.close()

    return render_template('login.html')
def init_databases():
    # --- Initialize MySQL ---
    conn = get_mysql_connection()
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    username VARCHAR(100) NOT NULL UNIQUE,
                    password VARCHAR(255) NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.commit()
            print("MySQL 'users' table initialized successfully.")
        except mysql.connector.Error as err:
            print(f"Error initializing MySQL table: {err}")
        finally:
            if 'cursor' in locals() and cursor: cursor.close()
            if conn: conn.close()
    else:
        print("Warning: Could not connect to MySQL during initialization.")

    # --- Initialize MongoDB ---
    try:
        # Create a unique index on the 'username' field in the 'users' collection
        # This guarantees database-level enforcement of unique usernames
        db.users.create_index("username", unique=True)
        print("MongoDB unique index on 'username' initialized successfully.")
    except Exception as e:
        print(f"Warning: MongoDB init failed: {e}")


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        conn = None
        cursor = None
        try:
            conn = get_mysql_connection()
            if not conn:
                return "Could not connect to the database. Please try again later.", 500
            cursor = conn.cursor(dictionary=True)
            
            cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
            if cursor.fetchone():
                return "Username already exists. Please choose a different one."
            
            cursor.execute("INSERT INTO users (username, password) VALUES (%s, %s)", (username, password))
            conn.commit()

            db.users.insert_one({'username': username})

            session['username'] = username
            return redirect(url_for('index'))
            
        except mysql.connector.Error as err:
            return str(err), 500
        finally:
            if cursor: cursor.close()
            if conn: conn.close()

    return render_template('register.html')

@app.route('/profile/<username>')
def profile(username):

    user = db.users.find_one({'username': username})
    
    if not user:
        return "User not found", 404

    return render_template('profile.html', user=user, current_user=session.get('username'))

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == '__main__':
    try:
        init_databases()
    except Exception as e:
        print(f"Warning: DB init failed: {e}")

    app.run(host='0.0.0.0', port=5001, debug=True)