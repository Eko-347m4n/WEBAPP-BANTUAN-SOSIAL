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

from wtforms import FloatField

class MassPredictionForm(FlaskForm):
    passing_grade = FloatField('Passing Grade', validators=[DataRequired(), NumberRange(min=0, max=1)])
    kuota = IntegerField('Kuota', validators=[DataRequired(), NumberRange(min=1)])
    submit = SubmitField('Mulai Prediksi Massal')

class IndexPredictionForm(FlaskForm):
    nama = StringField('Nama', validators=[DataRequired(), Length(min=2, max=150)])
    submit = SubmitField('Cari Data')

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
    dokumen_pendukung = FileField('Dokumen Pendukung', validators=[FileAllowed(['jpg', 'png', 'pdf'], 'Hanya gambar dan PDF!')])

    # --- KRITERIA ---
    boolean_choices_with_prompt = [
        ('', '-- Pilih Status --'), 
        ('True', 'Ya'), 
        ('False', 'Tidak')
    ]

    # Status DTKS
    dtks = SelectField('Terdaftar di DTKS?', choices=boolean_choices_with_prompt, validators=[DataRequired(message="Pilih status DTKS.")])

    # Kriteria Penambah Skor
    keluarga_miskin_ekstrem = SelectField('Keluarga Miskin Ekstrem?', choices=boolean_choices_with_prompt, validators=[DataRequired(message="Pilih status.")])
    kehilangan_mata_pencaharian = SelectField('Kehilangan Mata Pencaharian?', choices=boolean_choices_with_prompt, validators=[DataRequired(message="Pilih status.")])
    tidak_bekerja = SelectField('Tidak Bekerja?', choices=boolean_choices_with_prompt, validators=[DataRequired(message="Pilih status.")])
    difabel = SelectField('Difabel?', choices=boolean_choices_with_prompt, validators=[DataRequired(message="Pilih status.")])
    penyakit_kronis = SelectField('Penyakit Kronis?', choices=boolean_choices_with_prompt, validators=[DataRequired(message="Pilih status.")])
    rumah_tangga_tunggal_lansia = SelectField('Rumah Tangga Tunggal / Lansia?', choices=boolean_choices_with_prompt, validators=[DataRequired(message="Pilih status.")])

    # Kriteria Pengurang Skor
    pkh = SelectField('Menerima PKH?', choices=boolean_choices_with_prompt, validators=[DataRequired(message="Pilih status.")])
    kartu_pra_kerja = SelectField('Menerima Kartu Pra Kerja?', choices=boolean_choices_with_prompt, validators=[DataRequired(message="Pilih status.")])
    bst = SelectField('Menerima BST?', choices=boolean_choices_with_prompt, validators=[DataRequired(message="Pilih status.")])
    bansos_lainnya = SelectField('Menerima Bansos Pemerintah Lainnya?', choices=boolean_choices_with_prompt, validators=[DataRequired(message="Pilih status.")])

    submit = SubmitField('Simpan Data Penerima')
