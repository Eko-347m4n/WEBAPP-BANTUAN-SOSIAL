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
# Sesuaikan field-field ini dengan kebutuhan aplikasi Anda.
# Ini menggantikan/mengimplementasikan konsep 'DataPenduduk' dari project.json
class Penerima(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nama = db.Column(db.String(150), nullable=False)
    nik = db.Column(db.String(16), unique=True, nullable=False, index=True)
    no_kk = db.Column(db.String(16), nullable=False, index=True)
    alamat_lengkap = db.Column(db.Text, nullable=True)
    dtks = db.Column(db.String(10), nullable=True) # Misal: 'V' atau '-' atau NULL
    # Tambahkan field lain yang relevan seperti tanggal lahir, jenis kelamin, dll.
    
    # Path untuk dokumen pendukung, jika ada
    dokumen_pendukung_path = db.Column(db.String(255), nullable=True)

    # Relasi ke kriteria
    kriteria = db.relationship('KriteriaPenerima', backref='penerima', lazy='dynamic', cascade="all, delete-orphan")

    def __repr__(self):
        return f'<Penerima {self.nik} - {self.nama}>'

class KriteriaPenerima(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    penerima_id = db.Column(db.Integer, db.ForeignKey('penerima.id'), nullable=False)
    nama_kriteria = db.Column(db.String(100), nullable=False) # e.g., 'Keluarga Miskin Ekstrem'
    nilai_kriteria = db.Column(db.String(10), nullable=False) # e.g., 'V' atau '-'
    # Tambahkan field lain jika perlu, misal bobot kriteria saat itu, dll.

    def __repr__(self):
        return f'<KriteriaPenerima {self.penerima_id} - {self.nama_kriteria}: {self.nilai_kriteria}>'
