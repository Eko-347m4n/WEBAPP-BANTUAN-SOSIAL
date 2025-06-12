from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app
from flask_login import login_user, logout_user, login_required, current_user
from app.database.models import User, Setting
from app import db
from app.forms import LoginForm, RegistrationForm, PrediksiForm # Tambahkan PrediksiForm
from app.utils.model_handler import predict_individual_status # Hanya butuh fungsi prediksi

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/', methods=['GET', 'POST'])
def index():
    form = PrediksiForm()
    prediction_data = None
    knn_model = current_app.extensions.get('knn_model')
    df_original = current_app.extensions.get('df_original')

    if form.validate_on_submit():
        nama = form.nama.data
        pekerjaan_status = form.pekerjaan_status.data
        
        setting = Setting.query.first()
        # Gunakan nilai default jika setting tidak ditemukan di DB
        passing_grade = setting.passing_grade if setting else 10 

        if knn_model is None:
            flash("Model prediksi tidak tersedia atau gagal dimuat. Silakan hubungi admin.", "danger")
        elif df_original is None or df_original.empty:
            flash("Data referensi untuk prediksi tidak tersedia atau gagal dimuat. Silakan hubungi admin.", "danger")
        else:
            prediction_result = predict_individual_status(nama, pekerjaan_status, df_original, knn_model, passing_grade)
            if "error" in prediction_result:
                flash(prediction_result["error"], "warning")
            else:
                prediction_data = prediction_result

    return render_template('index.html', title='Cek Kelayakan Bantuan Sosial', form=form, prediction=prediction_data)

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
            # Pastikan next_page aman dan merupakan path lokal
            if next_page and next_page.startswith('/'):
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
