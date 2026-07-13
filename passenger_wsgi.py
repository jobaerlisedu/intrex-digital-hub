import os
import sys
from dotenv import load_dotenv
from pathlib import Path


sys.path.insert(0, os.path.dirname(__file__))


_env_file = Path(__file__).parent / '.env'
if _env_file.exists():
    load_dotenv(_env_file)


os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')


from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()
