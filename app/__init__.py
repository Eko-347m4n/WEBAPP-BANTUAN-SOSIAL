import os
import joblib
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager  # Akan diaktifkan nanti
from flask_wtf.csrf import CSRFProtect # Tambahkan impor ini
from config import Config
from app.utils.model_handler import load_and_preprocess_data, MODEL_PATH, DATASET_PATH

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
        # Load model and dataset once
        try:
            if os.path.exists(MODEL_PATH):
                app.extensions['knn_model'] = joblib.load(MODEL_PATH)
                app.logger.info("Model KNN berhasil dimuat saat aplikasi dimulai.")
            else:
                app.extensions['knn_model'] = None
                app.logger.error(f"Model KNN tidak ditemukan di {MODEL_PATH} saat aplikasi dimulai.")
        except Exception as e:
            app.extensions['knn_model'] = None
            app.logger.error(f"Error memuat model KNN saat aplikasi dimulai: {str(e)}")

        app.extensions['df_original'] = load_and_preprocess_data(DATASET_PATH)
        if app.extensions['df_original'].empty:
            app.logger.error("Dataset original gagal dimuat atau kosong saat aplikasi dimulai.")
        else:
            app.logger.info("Dataset original berhasil dimuat saat aplikasi dimulai.")

    # Impor dan daftarkan Blueprint di sini
    from app.routes.auth_routes import auth_bp
    from app.routes.admin_routes import admin_bp
    from app.routes.petugas_routes import petugas_bp

    app.register_blueprint(auth_bp) # url_prefix dihapus agar auth.index menjadi '/'
    app.register_blueprint(admin_bp, url_prefix='/admin')
    app.register_blueprint(petugas_bp, url_prefix='/petugas')

    return app
