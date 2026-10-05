import firebase_admin
from firebase_admin import credentials, firestore

# 1. Initialize SDK
cred = credentials.Certificate("serviceAccountKey.json")
firebase_admin.initialize_app(cred)
db = firestore.client()

print("Connected to Firestore. Fetching users...")

# 2. Query active users
users_ref = db.collection('users').where('is_active', '==', True).stream()

found_users = 0
for doc in users_ref:
    found_users += 1
    data = doc.to_dict()
    username = data.get("kaggle_username", "Unknown")
    has_kaggle_key = bool(data.get("kaggle_key"))
    has_gemini_key = bool(data.get("gemini_key"))
    
    print(f"\nUser Doc ID: {doc.id}")
    print(f" - Kaggle User: {username}")
    print(f" - Kaggle Key Present: {has_kaggle_key}")
    print(f" - Gemini Key Present: {has_gemini_key}")

if found_users == 0:
    print("\n❌ No active users found. Check if 'is_active' is set to boolean true.")
else:
    print(f"\n✅ SUCCESS! Found {found_users} active user(s).")