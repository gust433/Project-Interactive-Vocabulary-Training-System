from flask import Flask, request, jsonify
from flask_cors import CORS
from db import get_mongo_collection, get_mysql_connection
import mysql.connector
import random
from bson.objectid import ObjectId
import json
from datetime import date
import bcrypt
import os
from flask_jwt_extended import create_access_token, get_jwt_identity, verify_jwt_in_request
from flask_jwt_extended import JWTManager
from functools import wraps

app = Flask(__name__)
CORS(app)

try:
    from local_config import CONFIG_JWT_SECRET
except:
    CONFIG_JWT_SECRET = 'fdslkfjsdlkufewhjroiewurewrewqwe'

app.config['JWT_SECRET_KEY'] = os.getenv('JWT_SECRET_KEY', CONFIG_JWT_SECRET)
app.config['MONGO_URL'] = os.getenv('MONGO_URL', 'mongodb://localhost:27017/')
app.config['MONGO_DB_NAME'] = os.getenv('MONGO_DB_NAME', 'vocabdb')


jwt = JWTManager(app)

def jwt_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        try:
            verify_jwt_in_request()
        except Exception as e:
            return jsonify({"status": "error", "message": str(e) or "Invalid token"}), 401
        return f(*args, **kwargs)
    return wrapper

@app.route('/api/login', methods=['POST'])
def login():
    username = request.form.get('username') or (request.json and request.json.get('username'))
    password = request.form.get('password') or (request.json and request.json.get('password'))

    if not username or not password:
        return jsonify({"status": "error", "message": "Missing username or password"}), 400

    conn = None
    cursor = None
    try:
        conn = get_mysql_connection()
        if not conn:
            return jsonify({"status": "error", "message": "Database connection failed"}), 500
        
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT username, password FROM users WHERE username = %s", (username,))
        user = cursor.fetchone()

        if user and bcrypt.checkpw(password.encode('utf-8'), user['password'].encode('utf-8')):
            token = create_access_token(identity=username)
            return jsonify({
                "status": "success",
                "message": "Login successful",
                "username": username,
                "token": token
            }), 200
        else:
            return jsonify({"status": "error", "message": "Invalid username or password"}), 401
            
    except mysql.connector.Error as err:
        return jsonify({"status": "error", "message": str(err)}), 500
    finally:
        if cursor: cursor.close()
        if conn: conn.close()

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
                email VARCHAR(100) NOT NULL UNIQUE,
                score INT DEFAULT 0,
                `rank` VARCHAR(25) DEFAULT 'Bronze',
                last_play_date DATE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """)

            try:
                cursor.execute("ALTER TABLE users ADD COLUMN last_play_date DATE")
            except :
                pass
            conn.commit()
            print("MySQL table 'users' initialized successfully.")
            
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

def seed_vocabulary():
    if db is not None:
        collection = db["words"]
        if collection.count_documents({}) == 0:
            try:
                with open('Oxford-3000.json', 'r', encoding='utf-8') as f:
                    words_data = json.load(f)
                    collection.insert_many(words_data)
                print(f"✅ นำเข้าคำศัพท์สำเร็จ {len(words_data)} คำ!")
            except FileNotFoundError:
                print("Error: 'Oxford-3000.json' file not found.")
            except Exception as e:
                print(f"Error seeding vocabulary: {e}")

@app.route('/api/register', methods=['POST'])
def register():
    username = request.form.get('username') or (request.json and request.json.get('username'))
    password = request.form.get('password') or (request.json and request.json.get('password'))
    email = request.form.get('email') or (request.json and request.json.get('email'))

    # ดักจับกรณีที่ส่งข้อมูลมาไม่ครบ
    if not username or not password or not email:
        return jsonify({"status": "error", "message": "Please fill in all fields."}), 400

    # hash password
    hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        
    conn = None
    cursor = None
    try:
        conn = get_mysql_connection()
        if not conn:
            return jsonify({"status": "error", "message": "Could not connect to the database."}), 500
            
        cursor = conn.cursor(dictionary=True)
        
        # เช็คว่ามี username นี้ในระบบหรือยัง
        cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
        if cursor.fetchone():
            return jsonify({"status": "error", "message": "Username already exists. Please choose a different one."}), 409
        
        cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
        if cursor.fetchone():
            return jsonify({"status": "error", "message": "Email already exists. Please choose a different one."}), 409
        
        # บันทึกข้อมูลผู้ใช้ใหม่ (password hashed)
        cursor.execute("INSERT INTO users (username, password, email, score, `rank`) VALUES (%s, %s, %s, %s, %s)", 
                       (username, hashed_password, email, 0, 'Bronze'))
        conn.commit()

        # (ถ้ามีการใช้ MongoDB ควบคู่กัน สามารถเพิ่มโค้ด insert_one ได้ที่นี่)

        # สร้าง JWT token ให้ผู้ใช้หลังลงทะเบียนสำเร็จ
        token = create_access_token(identity=username)

        return jsonify({
            "status": "success",
            "message": "Registration successful",
            "username": username,
            "token": token
        }), 201
        
    except mysql.connector.Error as err:
        return jsonify({"status": "error", "message": str(err)}), 500
    finally:
        if cursor: cursor.close()
        if conn: conn.close()

@app.route('/api/profile/<username>', methods=['GET'], endpoint='get_profile')
@jwt_required
def get_profile(username):
    current_user = get_jwt_identity()
    if current_user != username:
        return jsonify({"status": "error", "message": "Forbidden: access denied."}), 403

    conn = None
    cursor = None
    try:
        conn = get_mysql_connection()
        if not conn:
            return jsonify({"status": "error", "message": "Database connection failed"}), 500
        
        cursor = conn.cursor(dictionary=True)
        # ดึงข้อมูลจาก MySQL (ไม่เอา Password มาแสดงเพื่อความปลอดภัย)
        cursor.execute("SELECT username, email, score, `rank` FROM users WHERE username = %s", (username,))
        user_data = cursor.fetchone()

        if user_data:
            # ถ้าเจอข้อมูล ส่งกลับไปเป็น JSON
            return jsonify({
                "status": "success",
                "data": user_data
            }), 200
        else:
            return jsonify({"status": "error", "message": "ไม่พบข้อมูลผู้ใช้"}), 404
            
    except mysql.connector.Error as err:
        return jsonify({"status": "error", "message": str(err)}), 500
    finally:
        if cursor: cursor.close()
        if conn: conn.close()

@app.route('/api/leaderboard', methods=['GET'], endpoint='leaderboard')
@jwt_required
def get_leaderboard():
    current_user = get_jwt_identity()
    conn = None
    cursor = None
    try:
        conn = get_mysql_connection()
        if not conn:
            return jsonify({"status": "error", "message": "Database connection failed"}), 500
        
        cursor = conn.cursor(dictionary=True)
        # ดึงรายชื่อ 10 อันดับแรกที่มีคะแนนสูงสุด
        cursor.execute("SELECT username, score, `rank` FROM users ORDER BY score DESC LIMIT 50")
        top_players = cursor.fetchall()

        return jsonify({
            "status": "success",
            "data": top_players
        }), 200
            
    except mysql.connector.Error as err:
        return jsonify({"status": "error", "message": str(err)}), 500
    finally:
        if cursor: cursor.close()
        if conn: conn.close()

# 1. เพื่อใช้ส่ง "ข้อมูล" อย่างเดียว
@app.route("/api/get_word", endpoint='get_word')
@jwt_required
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

# API: ดึงคำศัพท์ทั้งหมดของผู้ใช้นั้นๆ
@app.route('/api/mydict/<username>', methods=['GET'], endpoint='get_my_dict')
@jwt_required
def get_my_dict(username):
    current_user = get_jwt_identity()
    if current_user != username:
        return jsonify({"status": "error", "message": "Forbidden: access denied."}), 403

    try:
        # ใช้/สร้าง Collection ชื่อ user_dict ใน MongoDB
        collection = db["user_dict"] 
        # ค้นหาคำศัพท์ทั้งหมดที่เป็นของ username นี้
        words_cursor = collection.find({"username": username})
        
        my_words = []
        for word in words_cursor:
            my_words.append({
                "id": str(word["_id"]), # ต้องแปลง ObjectId ของ Mongo ให้เป็น Text ก่อนส่ง
                "vocab": word["vocab"],
                "meaning": word["meaning"],
                "note": word.get("note", " ") # ถ้าไม่มี note ให้ส่งเป็น string ว่าง
            })
        
        return jsonify({"status": "success", "data": my_words}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

# API: ลบคำศัพท์ออกจากคลัง
@app.route('/api/mydict/<word_id>', methods=['DELETE'], endpoint='delete_my_word')
@jwt_required
def delete_my_word(word_id):
    current_user = get_jwt_identity()
    try:
        collection = db["user_dict"]
        # ค้นหาไอดีของคำศัพท์เพื่อยืนยันเจ้าของข้อมูล
        word = collection.find_one({"_id": ObjectId(word_id)})
        if not word:
            return jsonify({"status": "error", "message": "ไม่พบคำศัพท์นี้"}), 404
        if word.get('username') != current_user:
            return jsonify({"status": "error", "message": "Forbidden: access denied."}), 403

        # ค้นหาและลบข้อมูลด้วย _id ของ MongoDB
        result = collection.delete_one({"_id": ObjectId(word_id)})
        
        if result.deleted_count > 0:
            return jsonify({"status": "success", "message": "ลบคำศัพท์เรียบร้อย"}), 200
        else:
            return jsonify({"status": "error", "message": "ไม่พบคำศัพท์นี้"}), 404
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

# API: บันทึกคำศัพท์ใหม่ (เตรียมไว้ให้หน้า test.html)
@app.route('/api/save_word', methods=['POST'], endpoint='save_word')
@jwt_required
def save_word():
    current_user = get_jwt_identity()
    data = request.json
    username = data.get('username')
    vocab = data.get('vocab')
    meaning = data.get('meaning')

    if username != current_user:
        return jsonify({"status": "error", "message": "Forbidden: access denied."}), 403
    
    if not username or not vocab or not meaning:
        return jsonify({"status": "error", "message": "ข้อมูลไม่ครบถ้วน"}), 400
        
    try:
        collection = db["user_dict"]
        # เช็คว่าเคยเซฟคำนี้ไว้แล้วหรือยัง
        existing = collection.find_one({"username": username, "vocab": vocab})
        if existing:
            return jsonify({"status": "error", "message": "คำศัพท์นี้อยู่ในคลังแล้ว"}), 400
            
        # บันทึกลง Mongo
        collection.insert_one({
            "username": username,
            "vocab": vocab,
            "meaning": meaning,
            "note": "" # เพิ่มฟิลด์ note เผื่อไว้ให้ผู้ใช้จดบันทึกเพิ่มเติมในอนาคต
        })
        return jsonify({"status": "success", "message": "บันทึกคำศัพท์เรียบร้อย"}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500
    
@app.route('/api/save_note/<word_id>', methods=['POST'], endpoint='update_note')
@jwt_required
def update_note(word_id):
    current_user = get_jwt_identity()
    data = request.json
    note = data.get('note', '') # อนุญาตให้ลบโน้ตจนว่างเปล่าได้
    
    try:
        collection = db["user_dict"]
        word = collection.find_one({"_id": ObjectId(word_id)})
        if not word:
            return jsonify({"status": "error", "message": "ไม่พบคำศัพท์นี้ในระบบ"}), 404
        if word.get('username') != current_user:
            return jsonify({"status": "error", "message": "Forbidden: access denied."}), 403
        # อัปเดตข้อมูล note โดยหาจาก _id ของคำศัพท์นั้นๆ
        result = collection.update_one(
            {"_id": ObjectId(word_id)},
            {"$set": {"note": note}}
        )
        
        if result.matched_count > 0:
            return jsonify({"status": "success", "message": "บันทึกโน้ตเรียบร้อย"}), 200
        else:
            return jsonify({"status": "error", "message": "ไม่พบคำศัพท์นี้ในระบบ"}), 404
            
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/check_play_status/<username>', methods=['GET'], endpoint='check_play_status')
@jwt_required
def check_play_status(username):
    current_user = get_jwt_identity()
    if current_user != username:
        return jsonify({"status": "error", "message": "Forbidden: access denied."}), 403

    conn = None
    cursor = None
    try:
        conn = get_mysql_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT last_play_date, `rank` FROM users WHERE username = %s", (username,))
        user = cursor.fetchone()
        
        if not user:
            return jsonify({"status": "error", "message": "ไม่พบผู้ใช้"}), 404
            
        today = date.today()
        user_rank = user.get('rank', 'Bronze')
        
        # ถ้าเคยเล่นแล้วและตรงกับวันที่วันนี้ ให้สถานะเล่นแล้ว
        if user['last_play_date'] and user['last_play_date'] == today:
            return jsonify({"status": "played", "can_play": False, "rank": user_rank}), 200
        else:
            return jsonify({"status": "success", "can_play": True, "rank": user_rank}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500
    finally:
        if cursor: cursor.close()
        if conn: conn.close()

@app.route('/api/profile/<username>', methods=['DELETE'], endpoint='delete_account')
@jwt_required
def delete_account(username):
    current_user = get_jwt_identity()
    if current_user != username:
        return jsonify({"status": "error", "message": "Forbidden: access denied."}), 403

    try:
        # 1. เชื่อมต่อ Database (ปรับบรรทัดนี้ให้ตรงกับตัวแปรที่คุณใช้ในโปรเจกต์)
        conn = get_mysql_connection()
        cursor = conn.cursor()

        # 2. ตรวจสอบก่อนว่ามี User นี้อยู่จริงไหม (Option เสริม)
        cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
        user = cursor.fetchone()
        
        if not user:
            return jsonify({"status": "error", "message": "ไม่พบผู้ใช้งานนี้ในระบบ"}), 404

        # 3. สั่งลบข้อมูล
        cursor.execute("DELETE FROM users WHERE username = %s", (username,))
        conn.commit() # อย่าลืม commit เพื่อยืนยันการลบ

        # 4. ปิดการเชื่อมต่อ
        cursor.close()
        # conn.close() # ปิดคอนเนคชันถ้าไม่ได้ใช้ Pool

        return jsonify({
            "status": "success", 
            "message": "ลบบัญชีเรียบร้อยแล้ว"
        }), 200

    except Exception as e:
        print("Error deleting account:", e)
        return jsonify({
            "status": "error", 
            "message": "เกิดข้อผิดพลาดที่เซิร์ฟเวอร์: " + str(e)
        }), 500
@app.route('/api/update_score', methods=['POST'], endpoint='update_score')
@jwt_required
def update_score():
    current_user = get_jwt_identity()
    data = request.json
    username = data.get('username')
    added_score = data.get('score', 0) # คะแนนที่ได้จากการเล่นรอบนี้
    
    if not username:
        return jsonify({"status": "error", "message": "ไม่พบชื่อผู้ใช้"}), 400
    if username != current_user:
        return jsonify({"status": "error", "message": "Forbidden: access denied."}), 403

    conn = None
    cursor = None
    try:
        conn = get_mysql_connection()
        cursor = conn.cursor(dictionary=True)
        
        # ดึงข้อมูลผู้ใช้
        cursor.execute("SELECT score, last_play_date FROM users WHERE username = %s", (username,))
        user = cursor.fetchone()

        if not user:
            return jsonify({"status": "error", "message": "ไม่พบผู้ใช้"}), 404

        today = date.today()

        # 🔴 ถ้าเล่นแล้ววันนี้ ห้ามเล่นซ้ำ (กรณีหลุดจาก Frontend)
        if user['last_play_date'] and user['last_play_date'] == today:
            return jsonify({
                "status": "error",
                "message": "วันนี้คุณเล่นไปแล้ว! พรุ่งนี้ค่อยมาใหม่นะ 😊"
            }), 403

        current_score = user['score'] if user['score'] else 0
        new_total_score = current_score + added_score # เอาคะแนนเก่า + คะแนนใหม่
        if new_total_score < 0:
            new_total_score = 0
        
        # 2. คำนวณ Rank ใหม่ (คุณสามารถปรับเกณฑ์คะแนนตรงนี้ได้ตามใจชอบ)
        new_rank = 'Bronze'
        if new_total_score >= 750:
            new_rank = 'Diamond 💎'
        elif new_total_score >= 500:
            new_rank = 'Platinum 🏆'
        elif new_total_score >= 250:
            new_rank = 'Gold 🥇'
        elif new_total_score >= 100:
            new_rank = 'Silver 🥈'

        # 3. อัปเดตคะแนนและ Rank กลับลงไปในฐานข้อมูล MySQL
        cursor.execute("""
            UPDATE users
            SET score = %s, `rank` = %s, last_play_date = %s
            WHERE username = %s
        """, (new_total_score, new_rank, today, username))

        conn.commit()

        return jsonify({
            "status": "success", 
            "message": "อัปเดตคะแนนสำเร็จ",
            "new_total_score": new_total_score,
            "new_rank": new_rank
        }), 200

    except mysql.connector.Error as err:
        return jsonify({"status": "error", "message": str(err)}), 500
    finally:
        if cursor: cursor.close()
        if conn: conn.close()

if __name__ == '__main__':
    db = get_mongo_collection()
    try:
        init_databases()
        seed_vocabulary()
    except Exception as e:
        print(f"Warning: DB init failed: {e}")

    app.run(host='0.0.0.0', port=5001, debug=True)
