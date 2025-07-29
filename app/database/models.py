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
    passing_grade = db.Column(db.Float, default=0.5, nullable=False)
    kuota = db.Column(db.Integer, default=50, nullable=False)

    def __repr__(self):
        return f'<Setting passing_grade={self.passing_grade} kuota={self.kuota}>'

# Model untuk data penerima (Struktur Flat)
class Penerima(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nama = db.Column(db.String(150), nullable=False, index=True)
    provinsi = db.Column(db.String(100), nullable=False, index=True)
    kabupaten = db.Column(db.String(100), nullable=False, index=True)
    kecamatan = db.Column(db.String(100), nullable=False, index=True)
    desa = db.Column(db.String(100), nullable=False, index=True)
    pekerjaan = db.Column(db.String(100), nullable=False, index=True)
    dokumen_pendukung_path = db.Column(db.String(255), nullable=True)

    # --- KRITERIA ---
    # Menggunakan Boolean untuk efisiensi dan integritas data.
    # Nilai default False berarti kriteria tidak terpenuhi.
    
    # Status DTKS
    dtks = db.Column(db.Boolean, default=False, nullable=False, index=True)

    # Kriteria Penambah Skor
    keluarga_miskin_ekstrem = db.Column(db.Boolean, default=False, nullable=False)
    kehilangan_mata_pencaharian = db.Column(db.Boolean, default=False, nullable=False)
    tidak_bekerja = db.Column(db.Boolean, default=False, nullable=False)
    difabel = db.Column(db.Boolean, default=False, nullable=False)
    penyakit_kronis = db.Column(db.Boolean, default=False, nullable=False)
    rumah_tangga_tunggal_lansia = db.Column(db.Boolean, default=False, nullable=False)

    # Kriteria Pengurang Skor
    pkh = db.Column(db.Boolean, default=False, nullable=False)
    kartu_pra_kerja = db.Column(db.Boolean, default=False, nullable=False)
    bst = db.Column(db.Boolean, default=False, nullable=False)
    bansos_lainnya = db.Column(db.Boolean, default=False, nullable=False)
    skor_saw_ternormalisasi = db.Column(db.Float, nullable=True) # New field for SAW score
    status_kelayakan_knn = db.Column(db.String(50), nullable=True) # New field for KNN prediction status

    def to_dict(self):
        return {
            'id': self.id,
            'nama': self.nama,
            'provinsi': self.provinsi,
            'kabupaten': self.kabupaten,
            'kecamatan': self.kecamatan,
            'desa': self.desa,
            'pekerjaan': self.pekerjaan,
            'dtks': self.dtks,
            'keluarga_miskin_ekstrem': self.keluarga_miskin_ekstrem,
            'kehilangan_mata_pencaharian': self.kehilangan_mata_pencaharian,
            'tidak_bekerja': self.tidak_bekerja,
            'difabel': self.difabel,
            'penyakit_kronis': self.penyakit_kronis,
            'rumah_tangga_tunggal_lansia': self.rumah_tangga_tunggal_lansia,
            'pkh': self.pkh,
            'kartu_pra_kerja': self.kartu_pra_kerja,
            'bst': self.bst,
            'bansos_lainnya': self.bansos_lainnya,
            'skor_saw_ternormalisasi': self.skor_saw_ternormalisasi,
            'status_kelayakan_knn': self.status_kelayakan_knn
        }

    def __repr__(self):
        return f'<Penerima {self.nama}>'
