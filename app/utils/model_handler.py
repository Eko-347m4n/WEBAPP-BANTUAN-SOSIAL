import numpy as np
import joblib
import os
import requests
from flask import current_app
from datetime import datetime

# ===============================
# 0. Konfigurasi Global & Kriteria
# ===============================
DEFAULT_PASSING_GRADE = 0.5 # Changed from 10 to 0.5 for normalized SAW scores

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

_region_name_cache = {}

def _get_region_name(region_id, endpoint, logger):
    if not region_id:
        return None
    # Check cache first
    if endpoint in _region_name_cache and region_id in _region_name_cache[endpoint]:
        return _region_name_cache[endpoint][region_id]
    
    try:
        response = requests.get(f"{API_WILAYAH_BASE_URL}{endpoint}")
        response.raise_for_status()
        data = response.json()
        # Populate cache for the entire endpoint
        if endpoint not in _region_name_cache:
            _region_name_cache[endpoint] = {str(item['id']): item['name'] for item in data}
        
        return _region_name_cache[endpoint].get(str(region_id))

    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching region data from {endpoint} for ID {region_id}: {e}")
    return "Tidak Diketahui"

# ===============================
# 1. Fungsi Prediksi Individu (Hybrid: SAW Score + KNN Prediction)
# ===============================
def predict_individual_status(penerima_obj, knn_model, passing_grade, logger):
    # --- SAW Score Calculation ---
    skor_individu = 0
    alasan_penambah = []
    alasan_pengurang = []

    if penerima_obj.dtks:
        skor_individu += 10
        alasan_penambah.append("DTKS")

    for field_name in PENAMBAH_KRITERIA_FIELDS:
        if getattr(penerima_obj, field_name):
            skor_individu += 1
            alasan_penambah.append(field_name.replace('_', ' ').title())

    for field_name in PENGURANG_KRITERIA_FIELDS:
        if getattr(penerima_obj, field_name):
            skor_individu -= 1
            alasan_pengurang.append(field_name.replace('_', ' ').title())

    skor_individu = max(0, skor_individu)

    # --- KNN Prediction ---
    features_for_knn = PENAMBAH_KRITERIA_FIELDS + PENGURANG_KRITERIA_FIELDS
    X_individual_list = [1 if getattr(penerima_obj, field) else 0 for field in features_for_knn]
    X_individual = np.array(X_individual_list).reshape(1, -1)

    if knn_model is None:
        knn_prediction = "Model KNN belum dilatih"
    else:
        try:
            raw_prediction = knn_model.predict(X_individual)[0]
            knn_prediction = "Layak" if raw_prediction == 1 else "Tidak Layak"
        except Exception as e:
            knn_prediction = f"Error prediksi KNN: {e}"
            logger.error(f"Error saat prediksi KNN untuk {penerima_obj.nama}: {e}")

    # --- Final Result ---
    alasan_detail = {
        "DTKS": penerima_obj.dtks,
        "Faktor Penambah Skor": alasan_penambah,
        "Faktor Pengurang Skor": alasan_pengurang,
    }

    max_total_nilai_global = 10 + len(PENAMBAH_KRITERIA_FIELDS)
    skor_saw_individu = skor_individu / max_total_nilai_global if max_total_nilai_global != 0 else 0.0

    provinsi_name = _get_region_name(penerima_obj.provinsi, 'provinces.json', logger)
    kabupaten_name = _get_region_name(penerima_obj.kabupaten, f'regencies/{penerima_obj.provinsi}.json', logger)
    kecamatan_name = _get_region_name(penerima_obj.kecamatan, f'districts/{penerima_obj.kabupaten}.json', logger)
    desa_name = _get_region_name(penerima_obj.desa, f'villages/{penerima_obj.kecamatan}.json', logger)

    return {
        "nama": penerima_obj.nama,
        "provinsi": provinsi_name if provinsi_name else penerima_obj.provinsi,
        "kabupaten": kabupaten_name if kabupaten_name else penerima_obj.kabupaten,
        "kecamatan": kecamatan_name if kecamatan_name else penerima_obj.kecamatan,
        "desa": desa_name if desa_name else penerima_obj.desa,
        "skor_total_saw_aktual": skor_individu,
        "skor_saw_ternormalisasi": round(skor_saw_individu, 4),
        "status_kelayakan_knn": knn_prediction,
        "passing_grade_digunakan_saw": passing_grade,
        "alasan": alasan_detail,
        "timestamp": datetime.now().strftime("%d-%m-%Y %H:%M:%S")
    }

# ===============================
# 2. Fungsi Pelatihan Model (Jika diperlukan)
# ===============================
def train_knn_model(db_session):
    from app.database.models import Penerima, Setting
    from sklearn.neighbors import KNeighborsClassifier
    from sklearn.model_selection import train_test_split
    from sklearn.metrics import accuracy_score

    setting = db_session.query(Setting).first()
    if not setting:
        current_app.logger.warning("Pengaturan passing grade tidak ditemukan saat melatih model KNN. Menggunakan nilai default 0.5.")
        training_passing_grade = 0.5
    else:
        training_passing_grade = setting.passing_grade

    all_penerima = Penerima.query.all()
    if not all_penerima:
        current_app.logger.warning("Tidak ada data penerima untuk melatih model KNN.")
        return False

    data = []
    target = []

    feature_columns = PENAMBAH_KRITERIA_FIELDS + PENGURANG_KRITERIA_FIELDS

    for p in all_penerima:
        row_features = [getattr(p, col) for col in feature_columns]
        data.append(row_features)
        target.append(1 if p.skor_saw_ternormalisasi is not None and p.skor_saw_ternormalisasi >= training_passing_grade else 0)

    X = np.array(data)
    y = np.array(target)

    if len(np.unique(y)) < 2:
        warning_message = "Hanya ada satu kelas di data target. Model KNN mungkin tidak dapat dilatih dengan baik atau akan sangat bias. Pastikan data pelatihan memiliki variasi yang cukup dalam status kelayakan (Layak/Tidak Layak)."
        current_app.logger.warning(warning_message)
        # Optionally, you might want to return False here if you want to prevent training with biased data
        # For now, we'll allow it but log a warning.
        # return False

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    knn = KNeighborsClassifier(n_neighbors=3)
    knn.fit(X_train, y_train)

    if hasattr(knn, 'feature_names_in_'):
        del knn.feature_names_in_

    y_pred = knn.predict(X_test)
    accuracy = accuracy_score(y_test, y_pred)
    current_app.logger.info(f"Model KNN dilatih dengan akurasi: {accuracy}")

    os.makedirs(os.path.dirname(MODEL_PATH), exist_ok=True)
    joblib.dump(knn, MODEL_PATH)
    current_app.logger.info(f"Model KNN berhasil disimpan di: {MODEL_PATH}")
    return True

# ===============================
# 3. Fungsi untuk memuat model (dipanggil saat aplikasi dimulai)
# ===============================
def load_knn_model():
    if os.path.exists(MODEL_PATH):
        try:
            model = joblib.load(MODEL_PATH)
            if hasattr(model, 'feature_names_in_'):
                current_app.logger.info("feature_names_in_ ditemukan dan akan dihapus.")
                del model.feature_names_in_
            current_app.logger.info("Model KNN berhasil dimuat.")
            return model
        except Exception as e:
            current_app.logger.error(f"Gagal memuat model KNN: {e}")
            return None
    current_app.logger.warning("Model KNN tidak ditemukan. Harap latih model terlebih dahulu.")
    return None