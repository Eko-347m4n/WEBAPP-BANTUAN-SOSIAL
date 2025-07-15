from app import db, login_manager
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), index=True, unique=True, nullable=False)
    email = db.Column(db.String(120), index=True, unique=True, nullable=False)
    password_hash = db.Column(db.String(256)) # Panjang ditambah untuk hash yang lebih kuat
    role = db.Column(db.String(20), nullable=False)  # Role: 'admin' atau 'petugas'

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f'<User {self.username} ({self.role})>'

class Setting(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    passing_grade = db.Column(db.Integer, default=10, nullable=False)
    kuota = db.Column(db.Integer, default=50, nullable=False)

    def __repr__(self):
        return f'<Setting passing_grade={self.passing_grade} kuota={self.kuota}>'

# Model untuk data penerima (sesuai penggunaan di petugas_routes.py)
# Disesuaikan dengan form di index.html
class Penerima(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nama = db.Column(db.String(150), nullable=False, index=True)
    provinsi = db.Column(db.String(100), nullable=True)
    kabupaten = db.Column(db.String(100), nullable=True)
    kecamatan = db.Column(db.String(100), nullable=True)
    desa = db.Column(db.String(100), nullable=True)
    pekerjaan = db.Column(db.String(100), nullable=True)
    dtks = db.Column(db.String(10), nullable=True)
    dokumen_pendukung_path = db.Column(db.String(255), nullable=True)

    # Relasi ke kriteria
    kriteria = db.relationship('KriteriaPenerima', backref='penerima', lazy='dynamic', cascade="all, delete-orphan")

    def __repr__(self):
        return f'<Penerima {self.nama}>'

class KriteriaPenerima(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    penerima_id = db.Column(db.Integer, db.ForeignKey('penerima.id'), nullable=False)
    nama_kriteria = db.Column(db.String(100), nullable=False)
    nilai_kriteria = db.Column(db.String(10), nullable=False)

    def __repr__(self):
        return f'<KriteriaPenerima {self.penerima_id} - {self.nama_kriteria}: {self.nilai_kriteria}>'
