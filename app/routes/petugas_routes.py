from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app
from flask_login import login_required, current_user
from app import db
from app.database.models import Penerima, KriteriaPenerima, Setting
from app.forms import (
    PenerimaForm, SEMUA_KRITERIA_FORM, PrediksiForm, SettingForm,
    TAHAP1_KRITERIA_NAMES,
    KRITERIA_CHOICES_DEFAULT_STYLE, DEFAULT_KRITERIA_PROMPT)
from app.utils.model_handler import load_and_preprocess_data, predict_individual_status
from werkzeug.utils import secure_filename
from wtforms import SelectField
from wtforms.validators import DataRequired
import os
import joblib

petugas_bp = Blueprint('petugas', __name__, url_prefix='/petugas')

# Helper function to create form class dynamically
def get_dynamic_penerima_form_class(base_class, kriteria_names_list,
                                    tahap1_names, tahap1_choices,
                                    default_choices, default_prompt):
    """Creates a new form class inheriting from base_class with dynamic kriteria fields."""
    class DynamicPenerimaForm(base_class):
        pass

    for kriteria_nama in kriteria_names_list:
        field_name_slug = 'kriteria_' + kriteria_nama.lower().replace(' ', '_').replace('(', '').replace(')', '').replace('/', '_')
        
        current_field_choices_style = default_choices
        if kriteria_nama in tahap1_names:
            current_field_choices_style = tahap1_choices
        
        # Add the prompt as the first option
        final_choices = [default_prompt] + current_field_choices_style
        
        # Define field as a class attribute (UnboundField)
        field = SelectField(kriteria_nama, choices=final_choices, validators=[DataRequired(message=f"{kriteria_nama} harus diisi.")])
        setattr(DynamicPenerimaForm, field_name_slug, field)
    
    return DynamicPenerimaForm

@petugas_bp.route('/dashboard')
@login_required
def dashboard():
    # Pastikan hanya petugas yang bisa akses, bisa ditambahkan pengecekan role jika ada
    return render_template('/petugas/dashboard.html', title='Dashboard Petugas')

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
    # Dynamically create the form class with kriteria fields based on PenerimaForm
    # SEMUA_KRITERIA_FORM should be imported from app.forms
    # PenerimaForm (base class) should also be imported from app.forms
    ActualPenerimaForm = get_dynamic_penerima_form_class(
        PenerimaForm, SEMUA_KRITERIA_FORM,
        TAHAP1_KRITERIA_NAMES,
        KRITERIA_CHOICES_DEFAULT_STYLE,
        KRITERIA_CHOICES_DEFAULT_STYLE,
        DEFAULT_KRITERIA_PROMPT)
    
    # Instantiate the dynamically created form class
    form = ActualPenerimaForm() # FlaskForm handles request.form internally

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
            dtks=form.dtks.data if hasattr(form, 'dtks') and form.dtks.data else None 
        )
        db.session.add(penerima)
        
        try:
            # Flush untuk mendapatkan ID penerima sebelum menyimpan KriteriaPenerima
            # Ini penting jika KriteriaPenerima memiliki foreign key ke Penerima.id
            db.session.flush() 

            # Simpan kriteria
            kriteria_entries_to_add = []
            for kriteria_nama in SEMUA_KRITERIA_FORM:
                field_name_slug = 'kriteria_' + kriteria_nama.lower().replace(' ', '_').replace('(', '').replace(')', '').replace('/', '_')
                # Akses data dari field yang sekarang sudah terdefinisi dengan baik di kelas form
                nilai_kriteria_form = getattr(form, field_name_slug).data
                kriteria_entry = KriteriaPenerima(
                    penerima_id=penerima.id,
                    nama_kriteria=kriteria_nama,
                    nilai_kriteria=nilai_kriteria_form
                )
                db.session.add(kriteria_entry)
            # db.session.add_all(kriteria_entries_to_add) # Alternatif jika banyak

            # Handle file upload
            if hasattr(form, 'dokumen_pendukung') and form.dokumen_pendukung.data:
                file = form.dokumen_pendukung.data
                if file: # Pastikan file benar-benar ada
                    filename = secure_filename(file.filename)
                    # Konfigurasi UPLOAD_FOLDER sebaiknya path absolut atau relatif terhadap instance_path
                    upload_folder_config = current_app.config.get('UPLOAD_FOLDER', 'uploads')
                    if not os.path.isabs(upload_folder_config):
                        upload_folder = os.path.join(current_app.root_path, upload_folder_config)
                    else:
                        upload_folder = upload_folder_config
                    
                    os.makedirs(upload_folder, exist_ok=True)
                    file_path = os.path.join(upload_folder, filename)
                    file.save(file_path)
                    # Pertimbangkan menyimpan path relatif atau hanya nama file
                    penerima.dokumen_pendukung_path = file_path # atau os.path.relpath(file_path, current_app.root_path)

            db.session.commit() # Commit semua perubahan (penerima, kriteria, path file)
            flash('Data penerima berhasil ditambahkan!', 'success')
            return redirect(url_for('petugas.list_penerima')) # Redirect ke daftar untuk UX lebih baik
        except Exception as e:
            db.session.rollback()
            flash(f'Terjadi kesalahan saat menyimpan data: {str(e)}', 'danger')
            current_app.logger.error(f"Error saving new penerima: {e}", exc_info=True)

    return render_template('petugas/form_input_data.html', title='Input Data Penerima Baru', form=form, kriteria_list=SEMUA_KRITERIA_FORM)

@petugas_bp.route('/list_penerima')
@login_required
def list_penerima():
    try:
        all_penerima = Penerima.query.all()
        return render_template('petugas/list_penerima.html', title='Daftar Penerima Bantuan', penerima_list=all_penerima)
    except Exception as e:
        flash(f'Gagal memuat daftar penerima: {str(e)}', 'danger')
        return render_template('petugas/list_penerima.html', title='Daftar Penerima Bantuan', penerima_list=[])