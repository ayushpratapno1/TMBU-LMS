import os
import django

# Replace 'your_project_name' with your actual Django project folder name
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'lmsproject.settings')
django.setup()

from django.contrib.auth.models import User
from lmsapp.models import Login 

# Fetch credentials from environment variables (Set these in Render/Netlify dashboard)
# It uses defaults here just for fallback, but in prod, environment variables are safer.
SUPERUSER_NAME = os.environ.get('SUPERUSER_NAME')
SUPERUSER_EMAIL = os.environ.get('SUPERUSER_EMAIL')
SUPERUSER_PASSWORD = os.environ.get('SUPERUSER_PASSWORD')

def setup_superuser():
    # 1. Create the Django superuser if it doesn't exist
    if not User.objects.filter(username=SUPERUSER_NAME).exists():
        User.objects.create_superuser(SUPERUSER_NAME, SUPERUSER_EMAIL, SUPERUSER_PASSWORD)
        print(f"✅ Django Superuser '{SUPERUSER_NAME}' created.")
    else:
        print(f"⚠️ Django Superuser '{SUPERUSER_NAME}' already exists.")

    # 2. Automatically sync it to your custom Login table
    if not Login.objects.filter(userid=SUPERUSER_NAME).exists():
        Login.objects.create(userid=SUPERUSER_NAME, password=SUPERUSER_PASSWORD, usertype='admin')
        print(f"✅ Custom Login entry for '{SUPERUSER_NAME}' created.")
    else:
        print(f"⚠️ Custom Login entry for '{SUPERUSER_NAME}' already exists.")

if __name__ == '__main__':
    setup_superuser()