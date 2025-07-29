from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app, session
from flask_login import login_user, logout_user, login_required, current_user
from urllib.parse import urlparse
from app.database.models import User, Setting, Penerima
from app import db
from app.forms import LoginForm, RegistrationForm, IndexPredictionForm
from app.utils.model_handler import predict_individual_status
import os
import joblib

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/', methods=['GET', 'POST'])
def index():
    form = IndexPredictionForm()
    prediction = None
    setting = Setting.query.first()
    if not setting:
        setting = Setting(passing_grade=0.5, kuota=50) # Default value for float
        db.session.add(setting)
        db.session.commit()

    if form.validate_on_submit():
        nama = form.nama.data
        provinsi_id = request.form.get('provinsi')
        kabupaten_id = request.form.get('kabupaten')
        kecamatan_id = request.form.get('kecamatan')
        desa_id = request.form.get('desa')

        penerima_obj = Penerima.query.filter_by(nama=nama).first()

        if not penerima_obj:
            flash(f'Individu dengan nama \'{nama}\' tidak ditemukan.', 'danger')
            return redirect(url_for('auth.index'))

        knn_model = current_app.extensions.get('knn_model')
        if knn_model is None:
            flash('Model prediksi belum dimuat. Harap hubungi administrator.', 'danger')
            return redirect(url_for('auth.index'))

        passing_grade = setting.passing_grade
        prediction_result = predict_individual_status(
            penerima_obj=penerima_obj,
            knn_model=knn_model,
            passing_grade=passing_grade,
            logger=current_app.logger
        )

        if 'error' in prediction_result:
            flash(prediction_result['error'], 'danger')
        else:
            session['prediction_data'] = prediction_result

        return redirect(url_for('auth.index'))

    if 'prediction_data' in session:
        prediction = session.pop('prediction_data', None)

    return render_template('index.html', title='Cek Kelayakan Masyarakat', form=form, prediction=prediction)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        # Jika pengguna sudah login, arahkan berdasarkan peran
        if current_user.role == 'admin':
            return redirect(url_for('admin.dashboard')) # Arahkan ke dashboard admin
        elif current_user.role == 'petugas':
            # Asumsikan ada 'petugas.dashboard', jika tidak, sesuaikan atau gunakan auth.index
            return redirect(url_for('petugas.dashboard')) 
        else:
            return redirect(url_for('auth.index')) # Halaman default untuk peran lain
            
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user and user.check_password(form.password.data): # Asumsi User model punya check_password
            login_user(user, remember=form.remember_me.data)
            flash('Login berhasil!', 'success') # Pindahkan flash message ke sini
            
            next_page = request.args.get('next')
            if next_page and urlparse(next_page).netloc == '' and urlparse(next_page).scheme == '':
                return redirect(next_page)
            else:
                # Jika tidak ada next_page yang valid, arahkan berdasarkan peran
                if current_user.role == 'admin':
                    return redirect(url_for('admin.dashboard'))
                elif current_user.role == 'petugas':
                    return redirect(url_for('petugas.dashboard')) # Sesuaikan jika perlu
                else:
                    return redirect(url_for('auth.index'))
        else:
            flash('Login gagal. Periksa kembali username dan password Anda.', 'danger')
    return render_template('login.html', title='Login', form=form)

@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Anda telah berhasil logout.', 'info')
    return redirect(url_for('auth.login'))