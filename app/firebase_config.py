import firebase_admin
from firebase_admin import credentials, firestore

# Load your Firebase Service Account Key
cred = credentials.Certificate("V:\\Mock interview\\firebase_key.json")  # 🔹 Ensure this file exists
firebase_admin.initialize_app(cred)

# 🔥 Firestore Database Instance
db = firestore.client()
