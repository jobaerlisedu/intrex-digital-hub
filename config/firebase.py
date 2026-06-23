import os
import firebase_admin
from firebase_admin import credentials, firestore
from dotenv import load_dotenv  # pyrefly: ignore [missing-import]
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

# Load environment variables from .env
load_dotenv(os.path.join(BASE_DIR, '.env'))

# Initialize Firebase
FIREBASE_CREDS_PATH = os.path.join(BASE_DIR, os.environ.get('FIREBASE_CREDENTIALS_PATH', 'firebase-credentials.json'))

if not firebase_admin._apps:
    try:
        firebase_creds_json = os.environ.get('FIREBASE_CREDENTIALS_JSON')
        if firebase_creds_json:
            import json
            creds_dict = json.loads(firebase_creds_json)
            cred = credentials.Certificate(creds_dict)
            firebase_admin.initialize_app(cred)
            print("Firebase successfully connected using JSON env var!")
        elif os.path.exists(FIREBASE_CREDS_PATH):
            cred = credentials.Certificate(FIREBASE_CREDS_PATH)
            firebase_admin.initialize_app(cred)
            print("Firebase successfully connected using credentials file!")
        else:
            # Fallback to default credentials (e.g., if Google Application Default Credentials are set)
            firebase_admin.initialize_app()
            print("Firebase connected using default credentials!")
    except Exception as e:
        print(f"Error connecting to Firebase: {e}")
        raise e

# Create a Firestore database client that you can import and use anywhere
db = firestore.client()
