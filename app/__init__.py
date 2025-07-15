import os
import joblib
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager  # Akan diaktifkan nanti
from flask_wtf.csrf import CSRFProtect # Tambahkan impor ini
from config import Config


db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()  # Akan diaktifkan nanti
csrf = CSRFProtect() # Buat instance CSRFProtect
login_manager.login_view = 'auth.login'  # Tentukan route login
login_manager.login_message_category = 'info'

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)  # Akan diaktifkan nanti
    csrf.init_app(app) # Inisialisasi CSRFProtect dengan aplikasi

    with app.app_context():
        # Load model once
        try:
            model_path = os.path.join(os.path.dirname(__file__), 'models', 'knn_model.pkl')
            if os.path.exists(model_path):
                app.extensions['knn_model'] = joblib.load(model_path)
                app.logger.info("Model KNN berhasil dimuat saat aplikasi dimulai.")
            else:
                app.extensions['knn_model'] = None
                app.logger.error(f"Model KNN tidak ditemukan di {model_path} saat aplikasi dimulai.")
        except Exception as e:
            app.extensions['knn_model'] = None
            app.logger.error(f"Error memuat model KNN saat aplikasi dimulai: {str(e)}")

    # Impor dan daftarkan Blueprint di sini
    from app.routes.auth_routes import auth_bp
    from app.routes.admin_routes import admin_bp
    from app.routes.petugas_routes import petugas_bp

    app.register_blueprint(auth_bp) # url_prefix dihapus agar auth.index menjadi '/'
    app.register_blueprint(admin_bp, url_prefix='/admin')
    app.register_blueprint(petugas_bp, url_prefix='/petugas')

    return app
