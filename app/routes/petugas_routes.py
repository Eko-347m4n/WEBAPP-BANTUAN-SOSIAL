from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app, jsonify, session
from flask_login import login_required
from app import db
from app.database.models import Penerima, Setting
from app.forms import PenerimaForm, IndexPredictionForm, SettingForm, MassPredictionForm
from app.utils.model_handler import predict_individual_status
from werkzeug.utils import secure_filename
from flask import current_app as app
from threading import Lock
import os
import joblib
import threading
import time
from datetime import datetime

# Global state for mass prediction progress
_mass_predict_progress_state = {
    'running': False,
    'total': 0,
    'processed': 0,
    'percentage': 0,
    'start_time': None,
    'elapsed_time': 0,
    'estimated_time_remaining': 0,
    'status': 'idle', # idle, processing, completed, error
    'error': None
}
progress_lock = threading.Lock()

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
    form = IndexPredictionForm()
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
        prediction = predict_individual_status(nama=nama, db_session=db.session, knn_model=knn_model, passing_grade=passing_grade)

        if 'error' in prediction:
            flash(prediction['error'], 'danger')
            prediction = None

    return render_template('petugas/form_prediksi.html', title='Prediksi Kelayakan', form=form, prediction=prediction, setting=setting)

def run_mass_prediction_in_background(app, all_penerima_ids, passing_grade, model_path):
    global _mass_predict_progress_state
    with app.app_context(): # Create app context within the thread
        try:
            knn_model = joblib.load(model_path)
            updated_penerima_objects = []

            with db.session.no_autoflush():
                for i, penerima_id in enumerate(all_penerima_ids):
                    # Use db.session within the app_context of this thread
                    penerima_obj = Penerima.query.get(penerima_id)
                    if penerima_obj:
                        prediction_result = predict_individual_status(
                            nama=penerima_obj.nama,
                            db_session=db.session,
                            knn_model=knn_model,
                            passing_grade=passing_grade,
                            penerima_obj=penerima_obj
                        )
                        if 'error' not in prediction_result:
                            penerima_obj.status_kelayakan_knn = prediction_result['status_kelayakan_knn']
                            penerima_obj.skor_saw_ternormalisasi = prediction_result['skor_saw_ternormalisasi']
                            updated_penerima_objects.append(penerima_obj)
                    
                    with progress_lock:
                        _mass_predict_progress_state['processed'] = i + 1
                        _mass_predict_progress_state['percentage'] = int((_mass_predict_progress_state['processed'] / _mass_predict_progress_state['total']) * 100)
                        _mass_predict_progress_state['elapsed_time'] = (datetime.now() - _mass_predict_progress_state['start_time']).total_seconds()
                        if _mass_predict_progress_state['processed'] > 0:
                            time_per_item = _mass_predict_progress_state['elapsed_time'] / _mass_predict_progress_state['processed']
                            remaining_items = _mass_predict_progress_state['total'] - _mass_predict_progress_state['processed']
                            _mass_predict_progress_state['estimated_time_remaining'] = int(remaining_items * time_per_item)
                        else:
                            _mass_predict_progress_state['estimated_time_remaining'] = 0

            if updated_penerima_objects:
                db.session.bulk_save_objects(updated_penerima_objects)
                db.session.commit()
            
            with progress_lock:
                _mass_predict_progress_state['status'] = 'completed'

        except Exception as e:
            with progress_lock:
                _mass_predict_progress_state['status'] = 'error'
                _mass_predict_progress_state['error'] = str(e)
        finally:
            # Ensure the session is removed/closed for this thread's context
            db.session.remove()
            with progress_lock:
                _mass_predict_progress_state['running'] = False

@petugas_bp.route('/mass_predict', methods=['GET', 'POST'])
@login_required
def mass_predict():
    form = MassPredictionForm()
    if form.validate_on_submit():
        # Reset progress state before starting a new prediction
        with progress_lock:
            _mass_predict_progress_state['running'] = False
            _mass_predict_progress_state['total'] = 0
            _mass_predict_progress_state['processed'] = 0
            _mass_predict_progress_state['percentage'] = 0
            _mass_predict_progress_state['start_time'] = None
            _mass_predict_progress_state['elapsed_time'] = 0
            _mass_predict_progress_state['estimated_time_remaining'] = 0
            _mass_predict_progress_state['status'] = 'idle'
            _mass_predict_progress_state['error'] = None

        setting = Setting.query.first()
        if not setting:
            setting = Setting()
            db.session.add(setting)
        
        setting.passing_grade = form.passing_grade.data
        setting.kuota = form.kuota.data
        db.session.commit()

        all_penerima_ids = [p.id for p in Penerima.query.with_entities(Penerima.id).all()]
        model_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '../models/knn_model.pkl')

        with progress_lock:
            _mass_predict_progress_state['running'] = True
            _mass_predict_progress_state['total'] = len(all_penerima_ids)
            _mass_predict_progress_state['start_time'] = datetime.now()
            _mass_predict_progress_state['status'] = 'processing'

        app_instance = current_app._get_current_object()
        threading.Thread(target=run_mass_prediction_in_background, args=(app_instance, all_penerima_ids, setting.passing_grade, model_path)).start()

        return jsonify({'status': 'started', 'message': 'Proses prediksi massal dimulai di latar belakang.'})

    return render_template('petugas/mass_predict.html', title='Prediksi Massal Kelayakan', form=form)

@petugas_bp.route('/mass_predict_progress')
@login_required
def get_mass_predict_progress():
    global _mass_predict_progress_state
    with progress_lock:
        return jsonify(_mass_predict_progress_state)



@petugas_bp.route('/train_model_now')
@login_required
def train_model_now():
    from app.utils.model_handler import train_knn_model
    train_knn_model(db.session)
    flash('Model KNN berhasil dilatih ulang!', 'success')
    
    return redirect(url_for('petugas.dashboard'))




@petugas_bp.route('/eligible_recipients')
@login_required
def eligible_recipients():
    setting = Setting.query.first()
    if not setting:
        flash('Pengaturan passing grade dan kuota belum ditentukan. Harap atur di Pengaturan Sistem.', 'danger')
        return redirect(url_for('petugas.settings'))

    passing_grade = setting.passing_grade
    kuota = setting.kuota

    # Fetch eligible recipients based on KNN status and SAW score
    eligible_list = Penerima.query.filter(
        Penerima.status_kelayakan_knn == 'Layak',
        Penerima.skor_saw_ternormalisasi >= passing_grade
    ).order_by(Penerima.skor_saw_ternormalisasi.desc()).limit(kuota).all()

    return render_template('petugas/eligible_recipients.html', title='Daftar Penerima Layak', eligible_list=eligible_list, passing_grade=passing_grade, kuota=kuota)

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
    return render_template('petugas/list_penerima.html', title='Rakyat Negara', penerima_list=all_penerima)

@petugas_bp.route('/edit_penerima/<int:penerima_id>', methods=['GET', 'POST'])
@login_required
def edit_penerima(penerima_id):
    penerima = Penerima.query.get_or_404(penerima_id)
    form = PenerimaForm(obj=penerima)

    if form.validate_on_submit():
        # Store original location data
        original_provinsi = penerima.provinsi
        original_kabupaten = penerima.kabupaten
        original_kecamatan = penerima.kecamatan
        original_desa = penerima.desa

        form.populate_obj(penerima)

        # Restore original location data to prevent changes
        penerima.provinsi = original_provinsi
        penerima.kabupaten = original_kabupaten
        penerima.kecamatan = original_kecamatan
        penerima.desa = original_desa

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
            upload_folder = current_app.config.get('UPLOAD_FOLDER', 'uploads')
            file_path = os.path.join(upload_folder, filename)
            file.save(file_path)
            penerima.dokumen_pendukung_path = file_path

        db.session.add(penerima)
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
