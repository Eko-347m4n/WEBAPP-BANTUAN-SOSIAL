from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import StringField, PasswordField, BooleanField, SubmitField, SelectField, IntegerField, TextAreaField, HiddenField
from wtforms.validators import DataRequired, Email, EqualTo, ValidationError, Length, NumberRange
from app.database.models import User

class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=4, max=64)])
    password = PasswordField('Password', validators=[DataRequired()])
    remember_me = BooleanField('Ingat Saya')
    submit = SubmitField('Login')

class RegistrationForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=4, max=64)])
    email = StringField('Email', validators=[DataRequired(), Email(), Length(max=120)])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=6)])
    password2 = PasswordField(
        'Ulangi Password', validators=[DataRequired(), EqualTo('password', message='Password harus sama.')])
    submit = SubmitField('Daftar')

    def validate_username(self, username):
        user = User.query.filter_by(username=username.data).first()
        if user:
            raise ValidationError('Username ini sudah digunakan. Silakan pilih yang lain.')

    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user:
            raise ValidationError('Email ini sudah terdaftar. Silakan gunakan email lain.')

class EmptyForm(FlaskForm): # Contoh form kosong, bisa berguna untuk tombol logout
    submit = SubmitField('Submit')

class EditUserForm(FlaskForm):
    # Username tidak diubah, hanya ditampilkan atau di-pass sebagai hidden field jika perlu
    email = StringField('Email', validators=[DataRequired(), Email(), Length(max=120)])
    password = PasswordField('Password Baru (kosongkan jika tidak ingin mengubah)',
                             validators=[EqualTo('password2', message='Password harus sama.'), Length(min=6, max=128, message="Password minimal 6 karakter."), DataRequired(message="Password tidak boleh kosong jika diisi.")],
                             render_kw={"placeholder": "Kosongkan jika tidak ingin mengubah"})
    password2 = PasswordField('Konfirmasi Password Baru')
    # Role tidak diubah melalui form ini oleh admin, untuk menjaga integritas.
    submit = SubmitField('Update User')

class PrediksiForm(FlaskForm):
    nama = StringField('Nama', validators=[DataRequired(), Length(min=2, max=150)])
    submit = SubmitField('Prediksi')

class SettingForm(FlaskForm):
    passing_grade = IntegerField('Passing Grade', validators=[DataRequired(), NumberRange(min=0)])
    kuota = IntegerField('Kuota', validators=[DataRequired(), NumberRange(min=1)])
    submit = SubmitField('Simpan')

class PenerimaForm(FlaskForm):
    nama = StringField('Nama Lengkap', validators=[DataRequired(), Length(max=150)])
    pekerjaan = SelectField('Pekerjaan', choices=[
        ('', '-- Pilih Pekerjaan --'),
        ('PNS', 'PNS'),
        ('Swasta', 'Swasta'),
        ('Wiraswasta', 'Wiraswasta'),
        ('Petani', 'Petani'),
        ('Nelayan', 'Nelayan'),
        ('Lainnya', 'Lainnya')
    ], validators=[DataRequired()])
    dtks = SelectField('Status DTKS', choices=[
        ('', '-- Pilih Status DTKS --'),
        ('Ya', 'Terdaftar'),
        ('Tidak', 'Tidak Terdaftar')
    ], validators=[DataRequired()])
    dokumen_pendukung = FileField('Dokumen Pendukung', validators=[FileAllowed(['jpg', 'png', 'pdf'], 'Hanya gambar dan PDF!')])
    submit = SubmitField('Simpan Data Penerima')

# Anda bisa mendefinisikan SEMUA_KRITERIA_FORM di sini atau di config
SEMUA_KRITERIA_FORM = [
    'Keluarga Miskin Ekstrem', 'Kehilangan Mata Pencaharian', 'Tidak Bekerja',
    'Difabel', 'Penyakit Menahun / Kronis', 'Rumah Tangga Tunggal / Lansia',
    'PKH', 'Kartu Pra Kerja', 'BST', 'Bansos Pemerintah Lainnya'
]

# Konstanta untuk membantu pengelolaan field kriteria dinamis di routes
TAHAP1_KRITERIA_NAMES = ['PKH', 'Kartu Pra Kerja', 'BST', 'Bansos Pemerintah Lainnya']
TAHAP2_KRITERIA_NAMES = [
    'Keluarga Miskin Ekstrem', 'Kehilangan Mata Pencaharian', 'Tidak Bekerja',
    'Difabel', 'Penyakit Menahun / Kronis', 'Rumah Tangga Tunggal / Lansia'
]

# Pilihan default
KRITERIA_CHOICES_DEFAULT_STYLE = [
    ('Ya', 'Ya'),
    ('Tidak', 'Tidak')
]

DEFAULT_KRITERIA_PROMPT = ('', '-- Pilih Status --')
