from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app
from flask_login import login_required
from app import db
from app.database.models import Penerima, Setting
from app.forms import PenerimaForm, PrediksiForm, SettingForm
from app.utils.model_handler import predict_individual_status
from werkzeug.utils import secure_filename
import os
import joblib

petugas_bp = Blueprint('petugas', __name__, url_prefix='/petugas')

def str_to_bool(s):
    """Converts a string to a boolean."""
    return s.lower() in ['true', 't', 'yes', '1']

@petugas_bp.route('/dashboard')
@login_required
def dashboard():
    return render_template('/petugas/dashboard.html', title='Dashboard Petugas')

@petugas_bp.route('/prediksi', methods=['GET', 'POST'])
@login_required
def prediksi():
    form = PrediksiForm()
    prediction = None
    setting = Setting.query.first()
    if not setting:
        setting = Setting(passing_grade=10, kuota=50)
        db.session.add(setting)
        db.session.commit()

    if form.validate_on_submit():
        nama = form.nama.data
        model_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '../models/knn_model.pkl')
        try:
            knn_model = joblib.load(model_path)
        except Exception as e:
            flash(f'Gagal memuat model prediksi: {str(e)}', 'danger')
            return render_template('petugas/form_prediksi.html', title='Prediksi Kelayakan', form=form)

        passing_grade = setting.passing_grade
        prediction = predict_individual_status(nama, db.session, knn_model, passing_grade)

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
        db.session.commit()
        flash('Pengaturan berhasil disimpan.', 'success')
    
    form.passing_grade.data = setting.passing_grade
    form.kuota.data = setting.kuota
    return render_template('petugas/form_setting.html', title='Pengaturan Kuota dan Passing Grade', form=form)

@petugas_bp.route('/tambah_penerima', methods=['GET', 'POST'])
@login_required
def tambah_penerima():
    form = PenerimaForm()
    if form.validate_on_submit():
        penerima = Penerima(
            nama=form.nama.data,
            provinsi=request.form.get('provinsi'),
            kabupaten=request.form.get('kabupaten'),
            kecamatan=request.form.get('kecamatan'),
            desa=request.form.get('desa'),
            pekerjaan=form.pekerjaan.data,
            dtks=str_to_bool(form.dtks.data),
            keluarga_miskin_ekstrem=str_to_bool(form.keluarga_miskin_ekstrem.data),
            kehilangan_mata_pencaharian=str_to_bool(form.kehilangan_mata_pencaharian.data),
            tidak_bekerja=str_to_bool(form.tidak_bekerja.data),
            difabel=str_to_bool(form.difabel.data),
            penyakit_kronis=str_to_bool(form.penyakit_kronis.data),
            rumah_tangga_tunggal_lansia=str_to_bool(form.rumah_tangga_tunggal_lansia.data),
            pkh=str_to_bool(form.pkh.data),
            kartu_pra_kerja=str_to_bool(form.kartu_pra_kerja.data),
            bst=str_to_bool(form.bst.data),
            bansos_lainnya=str_to_bool(form.bansos_lainnya.data)
        )

        if form.dokumen_pendukung.data:
            file = form.dokumen_pendukung.data
            filename = secure_filename(file.filename)
            upload_folder = current_app.config.get('UPLOAD_FOLDER', 'uploads')
            file_path = os.path.join(upload_folder, filename)
            file.save(file_path)
            penerima.dokumen_pendukung_path = file_path

        db.session.add(penerima)
        db.session.commit()
        flash('Data penerima berhasil ditambahkan!', 'success')
        return redirect(url_for('petugas.list_penerima'))
        
    return render_template('petugas/form_input_data.html', title='Input Data Penerima Baru', form=form)

@petugas_bp.route('/list_penerima')
@login_required
def list_penerima():
    all_penerima = Penerima.query.all()
    return render_template('petugas/list_penerima.html', title='Daftar Penerima Bantuan', penerima_list=all_penerima)

@petugas_bp.route('/edit_penerima/<int:penerima_id>', methods=['GET', 'POST'])
@login_required
def edit_penerima(penerima_id):
    penerima = Penerima.query.get_or_404(penerima_id)
    form = PenerimaForm(obj=penerima)

    if form.validate_on_submit():
        form.populate_obj(penerima)
        # Handle boolean conversion from form
        penerima.dtks = str_to_bool(form.dtks.data)
        penerima.keluarga_miskin_ekstrem = str_to_bool(form.keluarga_miskin_ekstrem.data)
        penerima.kehilangan_mata_pencaharian = str_to_bool(form.kehilangan_mata_pencaharian.data)
        penerima.tidak_bekerja = str_to_bool(form.tidak_bekerja.data)
        penerima.difabel = str_to_bool(form.difabel.data)
        penerima.penyakit_kronis = str_to_bool(form.penyakit_kronis.data)
        penerima.rumah_tangga_tunggal_lansia = str_to_bool(form.rumah_tangga_tunggal_lansia.data)
        penerima.pkh = str_to_bool(form.pkh.data)
        penerima.kartu_pra_kerja = str_to_bool(form.kartu_pra_kerja.data)
        penerima.bst = str_to_bool(form.bst.data)
        penerima.bansos_lainnya = str_to_bool(form.bansos_lainnya.data)
        
        if form.dokumen_pendukung.data:
            file = form.dokumen_pendukung.data
            filename = secure_filename(file.filename)
            upload_folder = current_app.config['UPLOAD_FOLDER']
            file_path = os.path.join(upload_folder, filename)
            file.save(file_path)
            penerima.dokumen_pendukung_path = file_path

        db.session.commit()
        flash('Data penerima berhasil diperbarui!', 'success')
        return redirect(url_for('petugas.list_penerima'))

    # Pre-populate form with boolean as string for SelectField
    form.dtks.data = str(penerima.dtks)
    form.keluarga_miskin_ekstrem.data = str(penerima.keluarga_miskin_ekstrem)
    form.kehilangan_mata_pencaharian.data = str(penerima.kehilangan_mata_pencaharian)
    form.tidak_bekerja.data = str(penerima.tidak_bekerja)
    form.difabel.data = str(penerima.difabel)
    form.penyakit_kronis.data = str(penerima.penyakit_kronis)
    form.rumah_tangga_tunggal_lansia.data = str(penerima.rumah_tangga_tunggal_lansia)
    form.pkh.data = str(penerima.pkh)
    form.kartu_pra_kerja.data = str(penerima.kartu_pra_kerja)
    form.bst.data = str(penerima.bst)
    form.bansos_lainnya.data = str(penerima.bansos_lainnya)

    return render_template('petugas/form_input_data.html', title='Edit Data Penerima', form=form, is_edit=True)

@petugas_bp.route('/hapus_penerima/<int:penerima_id>', methods=['POST'])
@login_required
def hapus_penerima(penerima_id):
    penerima = Penerima.query.get_or_404(penerima_id)
    db.session.delete(penerima)
    db.session.commit()
    flash('Data penerima berhasil dihapus.', 'success')
    return redirect(url_for('petugas.list_penerima'))
