import os
import mysql.connector
from pymongo import MongoClient

MONGO_URL = os.getenv('MONGO_URL', 'mongodb://localhost:27017/')
DB_NAME = os.getenv('MONGO_DB_NAME', 'vocabdb')

def get_mysql_connection():
    try:
        connection = mysql.connector.connect(
            host=os.getenv('MYSQL_HOST', 'localhost'),
            user=os.getenv('MYSQL_USER', 'root'),
            password=os.getenv('MYSQL_PASSWORD', 'rootpassword'),
            database=os.getenv('MYSQL_DATABASE', 'user_db'),
            port=int(os.getenv('MYSQL_PORT', 3307))
        )
        return connection
    except mysql.connector.Error as err:
        print(f"Error connecting to MySQL: {err}")
        return None

def get_mongo_collection():
    try:
        client = MongoClient(os.getenv('MONGO_URL', 'mongodb://localhost:27017/'))
        db = client[os.getenv('MONGO_DB_NAME', 'vocabdb')]
        return db

    except Exception as e:
        print(f"Error connecting to MongoDB: {e}")
        return None

