from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager  # Akan diaktifkan nanti

from config import Config
import os

db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()  # Akan diaktifkan nanti
login_manager.login_view = 'auth.login'  # Tentukan route login
login_manager.login_message_category = 'info'

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)  # Akan diaktifkan nanti

    # Impor dan daftarkan Blueprint di sini
    from app.routes.auth_routes import auth_bp
    from app.routes.main_routes import main_bp

    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(main_bp)

    return app
