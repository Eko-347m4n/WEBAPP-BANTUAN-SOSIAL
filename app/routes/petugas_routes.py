from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app
from flask_login import login_required, current_user
from app import db
from app.database.models import Penerima, KriteriaPenerima, Setting
from app.forms import PenerimaForm, SEMUA_KRITERIA_FORM, PrediksiForm, SettingForm
from app.utils.model_handler import load_and_preprocess_data, predict_individual_status
from werkzeug.utils import secure_filename
import os
import joblib

petugas_bp = Blueprint('petugas', __name__, url_prefix='/petugas')

@petugas_bp.route('/dashboard')
@login_required
def dashboard():
    # Pastikan hanya petugas yang bisa akses, bisa ditambahkan pengecekan role jika ada
    return render_template('dashboard_petugas.html', title='Dashboard Petugas')

@petugas_bp.route('/prediksi', methods=['GET', 'POST'])
@login_required
def prediksi():
    form = PrediksiForm()
    prediction = None

    # Load settings from DB
    setting = Setting.query.first()
    if not setting:
        # Create default setting if none exists
        setting = Setting(passing_grade=10, kuota=50)
        db.session.add(setting)
        db.session.commit()

    if form.validate_on_submit():
        nama = form.nama.data
        pekerjaan_status = form.pekerjaan_status.data

        # Load dataset
        df = load_and_preprocess_data()
        if df.empty:
            flash('Gagal memuat data untuk prediksi.', 'danger')
            return render_template('petugas/form_prediksi.html', title='Prediksi Kelayakan', form=form)

        # Load KNN model
        model_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '../models/knn_model.pkl')
        try:
            knn_model = joblib.load(model_path)
        except Exception as e:
            flash(f'Gagal memuat model prediksi: {str(e)}', 'danger')
            return render_template('petugas/form_prediksi.html', title='Prediksi Kelayakan', form=form)

        passing_grade = setting.passing_grade

        # Call prediction function
        prediction = predict_individual_status(nama, pekerjaan_status, df, knn_model, passing_grade)

        if 'error' in prediction:
            flash(prediction['error'], 'danger')
            prediction = None

    return render_template('petugas/form_prediksi.html', title='Prediksi Kelayakan', form=form, prediction=prediction, setting=setting)

@petugas_bp.route('/settings', methods=['GET', 'POST'])
@login_required
def settings():
    form = SettingForm()
    setting = Setting.query.first()
    if not setting:
        setting = Setting(passing_grade=10, kuota=50)
        db.session.add(setting)
        db.session.commit()

    if form.validate_on_submit():
        setting.passing_grade = form.passing_grade.data
        setting.kuota = form.kuota.data
        try:
            db.session.commit()
            flash('Pengaturan berhasil disimpan.', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'Gagal menyimpan pengaturan: {str(e)}', 'danger')

    # Pre-fill form with current settings
    form.passing_grade.data = setting.passing_grade
    form.kuota.data = setting.kuota

    return render_template('petugas/form_setting.html', title='Pengaturan Kuota dan Passing Grade', form=form)

@petugas_bp.route('/tambah_penerima', methods=['GET', 'POST'])
@login_required
def tambah_penerima():
    form = PenerimaForm()

    # Tambahkan field kriteria secara dinamis ke form
    # Kita akan menggunakan nama kriteria yang di-slugify sebagai nama field
    for kriteria_nama in SEMUA_KRITERIA_FORM:
        field_name = 'kriteria_' + kriteria_nama.lower().replace(' ', '_').replace('(', '').replace(')', '')
        setattr(form, field_name, SelectField(kriteria_nama, choices=[('-', '-'), ('V', 'V')], default='-', validators=[DataRequired()]))

    if form.validate_on_submit():
        # Cek apakah NIK sudah ada
        existing_penerima = Penerima.query.filter_by(nik=form.nik.data).first()
        if existing_penerima:
            flash('NIK sudah terdaftar. Silakan periksa kembali.', 'danger')
            return render_template('petugas/form_input_data.html', title='Input Data Penerima Baru', form=form, kriteria_list=SEMUA_KRITERIA_FORM)

        penerima = Penerima(
            nama=form.nama.data,
            nik=form.nik.data,
            no_kk=form.no_kk.data,
            alamat_lengkap=form.alamat_lengkap.data,
            dtks=form.dtks.data if form.dtks.data else None # Handle '' dari select
        )
        db.session.add(penerima)
        # Perlu db.session.flush() untuk mendapatkan ID penerima sebelum commit,
        # jika kita ingin menyimpan KriteriaPenerima yang merujuk ID tersebut
        # atau commit dulu penerima, baru kriteria.
        # Untuk kesederhanaan, kita commit dulu.
        try:
            db.session.commit() # Commit untuk mendapatkan ID penerima

            # Simpan kriteria
            for kriteria_nama in SEMUA_KRITERIA_FORM:
                field_name = 'kriteria_' + kriteria_nama.lower().replace(' ', '_').replace('(', '').replace(')', '')
                nilai_kriteria_form = getattr(form, field_name).data
                kriteria_entry = KriteriaPenerima(
                    penerima_id=penerima.id,
                    nama_kriteria=kriteria_nama,
                    nilai_kriteria=nilai_kriteria_form
                )
                db.session.add(kriteria_entry)

            # Handle file upload
            file = form.dokumen_pendukung.data
            if file:
                filename = secure_filename(file.filename)
                # Optional: validate file size here if needed
                upload_folder = current_app.config.get('UPLOAD_FOLDER', 'uploads')
                if not os.path.exists(upload_folder):
                    os.makedirs(upload_folder)
                file_path = os.path.join(upload_folder, filename)
                file.save(file_path)
                # Save relative path or filename to penerima
                penerima.dokumen_pendukung_path = file_path

            db.session.commit() # Commit kriteria and file path
            flash('Data penerima berhasil ditambahkan!', 'success')
            return redirect(url_for('petugas.dashboard')) # Atau ke halaman detail penerima
        except Exception as e:
            db.session.rollback()
            flash(f'Terjadi kesalahan saat menyimpan data: {str(e)}', 'danger')

    return render_template('petugas/form_input_data.html', title='Input Data Penerima Baru', form=form, kriteria_list=SEMUA_KRITERIA_FORM)