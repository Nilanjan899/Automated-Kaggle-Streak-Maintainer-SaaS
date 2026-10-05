import json
import logging
import firebase_admin
from firebase_admin import credentials, firestore

db = None

def initialize_firebase(creds_json_str: str):
    """Initializes the Firebase Admin SDK using the JSON credentials."""
    global db
    if not firebase_admin._apps:
        creds_dict = json.loads(creds_json_str)
        cred = credentials.Certificate(creds_dict)
        firebase_admin.initialize_app(cred)
        db = firestore.client()
        logging.info("Firebase initialized successfully.")

def get_active_users():
    """
    Fetches all active users from the 'users' collection.
    Expected Firestore Document Structure:
    { "is_active": true, "encrypted_gemini_key": "gAAAAABk..." }
    """
    users = []
    if db is None:
        logging.error("Database not initialized.")
        return users
    
    docs = db.collection('users').where('is_active', '==', True).stream()
    for doc in docs:
        data = doc.to_dict()
        if 'encrypted_gemini_key' in data:
            users.append({
                'id': doc.id, 
                'encrypted_gemini_key': data['encrypted_gemini_key']
            })
    return users