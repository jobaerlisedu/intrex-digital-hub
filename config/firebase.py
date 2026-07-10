import os
import json
import logging
import firebase_admin
from firebase_admin import credentials, firestore, storage
from dotenv import load_dotenv
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv(os.path.join(BASE_DIR, '.env'))

logger = logging.getLogger('config.firebase')

FIREBASE_CREDS_PATH_ENV = os.environ.get('FIREBASE_CREDENTIALS_PATH')
_debug = os.environ.get('DJANGO_DEBUG', 'False').lower() == 'true'

if not firebase_admin._apps:
    try:
        firebase_creds_json = os.environ.get('FIREBASE_CREDENTIALS_JSON')
        if firebase_creds_json:
            creds_dict = json.loads(firebase_creds_json)
            cred = credentials.Certificate(creds_dict)
            firebase_admin.initialize_app(cred)
            logger.info("Firebase connected using FIREBASE_CREDENTIALS_JSON env var")
        elif FIREBASE_CREDS_PATH_ENV:
            creds_path = os.path.join(BASE_DIR, FIREBASE_CREDS_PATH_ENV) if not os.path.isabs(FIREBASE_CREDS_PATH_ENV) else FIREBASE_CREDS_PATH_ENV
            if os.path.exists(creds_path):
                logger.warning("Firebase connected using file-based credentials. Prefer FIREBASE_CREDENTIALS_JSON env var for production.")
                cred = credentials.Certificate(creds_path)
                firebase_admin.initialize_app(cred)
            else:
                raise FileNotFoundError(f"Firebase credentials file not found at: {creds_path}")
        else:
            if os.environ.get('GOOGLE_APPLICATION_CREDENTIALS') or os.environ.get('GAE_ENV'):
                firebase_admin.initialize_app()
                logger.info("Firebase connected using Google default credentials")
            else:
                default_path = os.path.join(BASE_DIR, 'firebase-credentials.json')
                if os.path.exists(default_path):
                    logger.warning("FIREBASE_CREDENTIALS_PATH not set, loading default firebase-credentials.json. Set FIREBASE_CREDENTIALS_JSON env var for production.")
                    cred = credentials.Certificate(default_path)
                    firebase_admin.initialize_app(cred)
                else:
                    raise FileNotFoundError(
                        f"Firebase credentials file not found at default path: {default_path}. "
                        "Set FIREBASE_CREDENTIALS_JSON env var (recommended) or upload the "
                        "credentials file to your deployment."
                    )
    except Exception as e:
        logger.error(f"Firebase connection failed: {e}")
        raise

db = firestore.client()
bucket = storage.bucket()


# Tenant-scoped Firestore accessor.
# Wraps db.collection() to auto-add org_id filtering and tagging.
# Module views should use `tenant_db` for tenant-isolated operations.
class TenantScopedFirestore:
    def __getattr__(self, name):
        return getattr(db, name)

    def collection(self, collection_path):
        from config.firestore_utils import fs_scope_query
        return fs_scope_query(db.collection(collection_path))


tenant_db = TenantScopedFirestore()
