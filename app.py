from flask import Flask, jsonify, redirect, request, render_template, url_for, session
from db import get_mongo_collection, get_mysql_connection
import mysql.connector
import json
import time
import random

app = Flask(__name__)
db = get_mongo_collection()
app.secret_key = 'your_secret_key'

@app.route('/')
@app.route('/index')
def index():
    if 'username' in session:
        return render_template('index.html', username=session['username'])
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
                    email varchar(100),
                    score int,
                    `rank` varchar(25),
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
        email = request.form.get('email')
        
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
            
            cursor.execute("INSERT INTO users (username, password, email, score, `rank`) VALUES (%s, %s, %s, %s, %s)", (username, password, email, 0, 'Bronze'))
            conn.commit()

            #db.users.insert_one({'username': username})

            session['username'] = username
            return redirect(url_for('login'))
            
        except mysql.connector.Error as err:
            return str(err), 500
        finally:
            if cursor: cursor.close()
            if conn: conn.close()

    return render_template('register.html')

@app.route('/profile/<username>')
def profile(username):
    # เช็คว่าคนที่กดเข้ามาดู คือคนเดียวกับที่ล็อกอินอยู่
    if 'username' in session and session['username'] == username:
        
       # db = get_mongo_collection()
        #user_data = None
        #if db is not None:
            #user_data = db.users.find_one({'username': username})
        
        # ป้องกันกรณีหาใน Mongo ไม่เจอ
        #if not user_data:
        user_data = {'username': username, 'info': 'ยังไม่มีข้อมูลเพิ่มเติมในฐานข้อมูล'}

        return render_template('profile.html', user=user_data, current_user=session['username'])
    else:
        return redirect(url_for('login'))
# 1. เปลี่ยนชื่อ Route นี้ เพื่อใช้ส่ง "ข้อมูล" อย่างเดียว
@app.route("/get_word")
def get_word():
    collection = db["words"]
    docs = list(collection.aggregate([{"$sample": {"size": 1}}]))
    
    if not docs:
        return jsonify({"error": "No data"}), 500

    question = docs[0]
    correct_thai = question["thai"]
    wrong_choices = list(collection.aggregate([
        {"$match": {"eng": {"$ne": question["eng"]}}},
        {"$sample": {"size": 3}}
    ]))

    options = [correct_thai] + [w["thai"] for w in wrong_choices]
    random.shuffle(options)

    return jsonify({
        "word": question["eng"],
        "options": options,
        "answer": correct_thai
    })

# 2. เพิ่ม Route ชื่อ /test เพื่อใช้ "เปิดหน้าเว็บ"
@app.route("/test")
def test_page():
    return render_template('test.html')

>>>>>>> Stashed changes
# เพิ่ม Route สำหรับหน้าคลังคำศัพท์ (mydict)
@app.route('/mydict')
def mydict():
    if 'username' in session:
        # เปิดหน้า mydict.html (เดี๋ยวเราค่อยสร้างไฟล์นี้)
        return render_template('mydict.html', username=session['username'])
    return redirect(url_for('login'))

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