import os
from dotenv import load_dotenv

load_dotenv() # Muat variabel dari file .env

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'ganti-dengan-kunci-rahasia-yang-kuat'
    DEBUG = os.environ.get('FLASK_DEBUG') or True # Default ke True untuk development

    # Konfigurasi database
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'sqlite:///' + os.path.join(os.path.abspath(os.path.dirname(__file__)), 'app.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
