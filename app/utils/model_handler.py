import numpy as np
import joblib
import os
import requests # Import requests
from flask import current_app

# ===============================
# 0. Konfigurasi Global & Kriteria
# ===============================
DEFAULT_PASSING_GRADE = 10

# These lists now map to boolean field names in the Penerima model
PENAMBAH_KRITERIA_FIELDS = [
    'keluarga_miskin_ekstrem', 'kehilangan_mata_pencaharian', 'tidak_bekerja',
    'difabel', 'penyakit_kronis', 'rumah_tangga_tunggal_lansia'
]
PENGURANG_KRITERIA_FIELDS = [
    'pkh', 'kartu_pra_kerja', 'bst', 'bansos_lainnya'
]

APP_ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
MODEL_PATH = os.path.join(APP_ROOT_DIR, 'models', 'knn_model.pkl')

API_WILAYAH_BASE_URL = "https://www.emsifa.com/api-wilayah-indonesia/api/"

def _get_region_name(region_id, endpoint):
    """Fetches region name from API based on ID."""
    if not region_id:
        return None
    try:
        response = requests.get(f"{API_WILAYAH_BASE_URL}{endpoint}")
        response.raise_for_status() # Raise HTTPError for bad responses (4xx or 5xx)
        data = response.json()
        for item in data:
            if str(item['id']) == str(region_id):
                return item['name']
    except requests.exceptions.RequestException as e:
        current_app.logger.error(f"Error fetching region data from {endpoint} for ID {region_id}: {e}")
    return None

# ===============================
# 1. Fungsi Prediksi Individu (Hybrid: SAW Score + KNN Prediction)
# ===============================
def predict_individual_status(name, db_session, knn_model, passing_grade):
    from app.database.models import Penerima

    individu = db_session.query(Penerima).filter_by(nama=name).first()

    if not individu:
        return {"error": f"Individu dengan nama '{name}' tidak ditemukan."}

    # --- SAW Score Calculation ---
    skor_individu = 0
    alasan_penambah = []
    alasan_pengurang = []

    if individu.dtks:
        skor_individu += 10
        alasan_penambah.append("DTKS")

    for field_name in PENAMBAH_KRITERIA_FIELDS:
        if getattr(individu, field_name):
            skor_individu += 1
            alasan_penambah.append(field_name.replace('_', ' ').title())

    for field_name in PENGURANG_KRITERIA_FIELDS:
        if getattr(individu, field_name):
            skor_individu -= 1
            alasan_pengurang.append(field_name.replace('_', ' ').title())

    skor_individu = max(0, skor_individu)

    # --- KNN Prediction ---
    features_for_knn = PENAMBAH_KRITERIA_FIELDS + PENGURANG_KRITERIA_FIELDS
    X_individual_list = [1 if getattr(individu, field) else 0 for field in features_for_knn]
    X_individual = np.array(X_individual_list).reshape(1, -1)

    if knn_model is None:
        knn_prediction = "Model KNN belum dilatih"
    else:
        try:
            knn_prediction = knn_model.predict(X_individual)[0]
        except Exception as e:
            knn_prediction = f"Error prediksi KNN: {e}"
            current_app.logger.error(f"Error saat prediksi KNN untuk {name}: {e}")

    # --- Final Result ---
    alasan_detail = {
        "DTKS": individu.dtks,
        "Faktor Penambah Skor": alasan_penambah,
        "Faktor Pengurang Skor": alasan_pengurang,
    }

    # For normalization, calculate max score possible
    max_total_nilai_global = 10 + len(PENAMBAH_KRITERIA_FIELDS)
    skor_saw_individu = skor_individu / max_total_nilai_global if max_total_nilai_global != 0 else 0.0

    # Get region names
    provinsi_name = _get_region_name(individu.provinsi, 'provinces.json')
    kabupaten_name = _get_region_name(individu.kabupaten, f'regencies/{individu.provinsi}.json')
    kecamatan_name = _get_region_name(individu.kecamatan, f'districts/{individu.kabupaten}.json')
    desa_name = _get_region_name(individu.desa, f'villages/{individu.kecamatan}.json')

    return {
        "nama": name,
        "provinsi": provinsi_name if provinsi_name else individu.provinsi, # Fallback to ID if name not found
        "kabupaten": kabupaten_name if kabupaten_name else individu.kabupaten,
        "kecamatan": kecamatan_name if kecamatan_name else individu.kecamatan,
        "desa": desa_name if desa_name else individu.desa,
        "skor_total_saw_aktual": skor_individu,
        "skor_saw_ternormalisasi": round(skor_saw_individu, 4),
        "status_kelayakan_knn": knn_prediction,
        "passing_grade_digunakan_saw": passing_grade,
        "alasan": alasan_detail
    }