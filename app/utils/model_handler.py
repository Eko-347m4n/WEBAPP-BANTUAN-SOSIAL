import numpy as np
import joblib
import os
import requests # Import requests
from flask import current_app
from app import db # Import db

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
def predict_individual_status(nama, knn_model, passing_grade, db_session, penerima_obj=None, location_data=None):
    from app.database.models import Penerima

    if penerima_obj:
        individu = penerima_obj
    else:
        query = db_session.query(Penerima).filter_by(nama=nama)
        if location_data:
            if location_data.get('provinsi') and location_data['provinsi'] != '-- Pilih Provinsi --':
                query = query.filter_by(provinsi=location_data['provinsi'])
            if location_data.get('kabupaten') and location_data['kabupaten'] != '-- Pilih Kabupaten/Kota --':
                query = query.filter_by(kabupaten=location_data['kabupaten'])
            if location_data.get('kecamatan') and location_data['kecamatan'] != '-- Pilih Kecamatan --':
                query = query.filter_by(kecamatan=location_data['kecamatan'])
            if location_data.get('desa') and location_data['desa'] != '-- Pilih Desa --':
                query = query.filter_by(desa=location_data['desa'])
        individu = query.first()

    if not individu:
        return {"error": f"Individu dengan nama '{nama}' tidak ditemukan."}

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
            raw_prediction = knn_model.predict(X_individual)[0]
            knn_prediction = "Layak" if raw_prediction == 1 else "Tidak Layak"
        except Exception as e:
            knn_prediction = f"Error prediksi KNN: {e}"
            current_app.logger.error(f"Error saat prediksi KNN untuk {nama}: {e}")

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
        "nama": nama,
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

# ===============================
# 2. Fungsi Pelatihan Model (Jika diperlukan)
# ===============================
def train_knn_model(db_session):
    from app.database.models import Penerima
    from sklearn.neighbors import KNeighborsClassifier
    from sklearn.model_selection import train_test_split
    from sklearn.metrics import accuracy_score

    all_penerima = Penerima.query.all()
    if not all_penerima:
        current_app.logger.warning("Tidak ada data penerima untuk melatih model KNN.")
        return False

    # Prepare data for training
    data = []
    target = [] # 1 for Layak, 0 for Tidak Layak (based on some criteria, e.g., SAW score > passing_grade)

    # Define features based on PENAMBAH_KRITERIA_FIELDS and PENGURANG_KRITERIA_FIELDS
    feature_columns = PENAMBAH_KRITERIA_FIELDS + PENGURANG_KRITERIA_FIELDS

    # Assuming 'status_kelayakan_knn' is the ground truth for training
    # You might need to define how 'Layak' or 'Tidak Layak' is determined for training data
    # For example, if you have a manual label or a threshold on SAW score
    for p in all_penerima:
        row_features = [getattr(p, col) for col in feature_columns]
        data.append(row_features)
        # Convert 'Layak' to 1, 'Tidak Layak' to 0 based on SAW score and passing grade
        # This allows initial training even if KNN status is not yet set
        target.append(1 if p.skor_saw_ternormalisasi is not None and p.skor_saw_ternormalisasi >= current_app.config.get('DEFAULT_PASSING_GRADE', 10) else 0) 

    X = np.array(data)
    y = np.array(target)

    if len(np.unique(y)) < 2:
        current_app.logger.warning("Hanya ada satu kelas di data target. Tidak dapat melatih model KNN.")
        return False

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    knn = KNeighborsClassifier(n_neighbors=3) # You can tune n_neighbors
    knn.fit(X_train, y_train)

    # Ensure feature_names_in_ is not saved with the model
    if hasattr(knn, 'feature_names_in_'):
        del knn.feature_names_in_

    y_pred = knn.predict(X_test)
    accuracy = accuracy_score(y_test, y_pred)
    current_app.logger.info(f"Model KNN dilatih dengan akurasi: {accuracy}")

    # Save the trained model
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
