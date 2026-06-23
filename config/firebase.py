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
            # Check if running in a Google Cloud environment or GOOGLE_APPLICATION_CREDENTIALS is set
            if os.environ.get('GOOGLE_APPLICATION_CREDENTIALS') or os.environ.get('GAE_ENV'):
                firebase_admin.initialize_app()
                print("Firebase connected using Google default credentials!")
            else:
                raise ValueError(
                    "Firebase credentials not found. Please set the 'FIREBASE_CREDENTIALS_JSON' "
                    "environment variable in your Render dashboard, or ensure that "
                    f"'{os.path.basename(FIREBASE_CREDS_PATH)}' exists."
                )
    except Exception as e:
        print(f"Error connecting to Firebase: {e}")
        raise e

# Create a Firestore database client that you can import and use anywhere
db = firestore.client()
