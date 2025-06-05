import pandas as pd
pd.set_option('future.no_silent_downcasting', True)
import numpy as np
from sklearn.neighbors import KNeighborsClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, accuracy_score
from sklearn.utils import resample
import json
import joblib # Import joblib for saving/loading models
import os # Import os for directory creation

# ===============================
# 0. Konfigurasi Global & Kriteria
# ===============================
DEFAULT_PASSING_GRADE = 10
DEFAULT_KUOTA = 50 # Contoh kuota, bisa disesuaikan

PENAMBAH_KRITERIA = [
    'Keluarga Miskin Ekstrem', 'Kehilangan Mata Pencaharian', 'Tidak Berkerja',
    'Difabel', 'Penyakit Menahun / Kronis', 'Rumah Tangga Tunggal / Lansia'
]
PENGURANG_KRITERIA = [
    'PKH', 'Kartu Pra Kerja', 'BST', 'Bansos Pemerintah Lainnya'
]

# Define model path based on project.json structure
MODEL_PATH = '/home/b47m4n/KULIAH/SMS6/Project SPK/WEBAPPS/app/models/knn_model.pkl'
MODEL_DIR = os.path.dirname(MODEL_PATH)
DATASET_PATH = '/home/b47m4n/KULIAH/SMS6/Project SPK/WEBAPPS/app/data/dataset.csv' # Use CSV path

# ===============================
# 1. Fungsi Pemuatan dan Pemrosesan Data Awal
# ===============================
# Modified to load CSV
def load_and_preprocess_data(file_path=DATASET_PATH):
    try:
        # Change to read_csv
        df = pd.read_csv(file_path)
    except FileNotFoundError:
        print(f"Error: File dataset tidak ditemukan di {file_path}")
        return pd.DataFrame()
    except Exception as e:
        print(f"Error saat memuat atau membaca file CSV: {e}")
        return pd.DataFrame()

    # Inisialisasi skor awal berdasarkan DTKS
    # Ensure 'DTKS' column exists before accessing
    if 'DTKS' in df.columns:
        # Ensure 'DTKS' column is string type to avoid issues with mixed types
        df['DTKS'] = df['DTKS'].astype(str)
        df['Total_Nilai'] = np.where(df['DTKS'] == 'V', 10, 0)
    else:
        print("Peringatan: Kolom 'DTKS' tidak ditemukan. 'Total_Nilai' diinisialisasi ke 0.")
        df['Total_Nilai'] = 0

    # Tambahkan poin dari kriteria penambah
    for col in PENAMBAH_KRITERIA:
        if col in df.columns:
             # Ensure column is string type before comparison
            df[col] = df[col].astype(str)
            df['Total_Nilai'] += (df[col] == 'V').astype(int)
        else:
            print(f"Peringatan: Kolom penambah '{col}' tidak ditemukan.")

    # Kurangi poin dari kriteria pengurang
    for col in PENGURANG_KRITERIA:
        if col in df.columns:
            # Ensure column is string type before comparison
            df[col] = df[col].astype(str)
            df['Total_Nilai'] -= (df[col] == 'V').astype(int)
        else:
            print(f"Peringatan: Kolom pengurang '{col}' tidak ditemukan.")

    # Handle potential negative Total_Nilai if needed, though current logic makes it unlikely
    # df['Total_Nilai'] = df['Total_Nilai'].clip(lower=0) # Optional: ensure score is not negative

    return df

# ===============================
# 2. Fungsi Klasifikasi KNN (Dasar)
# ===============================
# Modified to save the model
def train_and_evaluate_knn(df_input):
    features_for_knn = PENAMBAH_KRITERIA + PENGURANG_KRITERIA
    existing_features_for_knn = [f for f in features_for_knn if f in df_input.columns]

    if not existing_features_for_knn:
        print("Error: Tidak ada fitur KNN yang tersedia dalam dataset.")
        return None, None

    if 'Total_Nilai' not in df_input.columns:
        print("Error: Kolom 'Total_Nilai' tidak ada untuk menentukan target KNN.")
        return None, None

    # Prepare features (X) - ensure correct dtypes and handle missing/non-'V' values
    # Use .loc for setting values to avoid SettingWithCopyWarning
    X = df_input[existing_features_for_knn].copy() # Work on a copy
    for col in existing_features_for_knn:
         # Ensure column is string type before replacement
        X[col] = X[col].astype(str).replace({'V': 1, '-': 0, np.nan: 0, 'nan': 0})
    # Ensure all feature columns are numeric
    X = X.apply(pd.to_numeric, errors='coerce').fillna(0)


    # Prepare target (y)
    df_input['Layak_KNN_Target'] = df_input['Total_Nilai'].apply(lambda x: 'Ya' if x >= DEFAULT_PASSING_GRADE else 'Tidak')
    y = df_input['Layak_KNN_Target']

    if y.nunique() < 2:
        print("Peringatan: Target variable 'Layak_KNN_Target' hanya memiliki satu kelas. KNN mungkin tidak optimal.")
        # Melatih pada seluruh data jika hanya satu kelas
        if X.empty:
            print("Error: Data fitur (X) kosong.")
            return None, None
        n_neighbors_single_class = min(5, len(X)) if len(X) > 0 else 1
        if n_neighbors_single_class == 0: n_neighbors_single_class = 1

        clf = KNeighborsClassifier(n_neighbors=n_neighbors_single_class)
        clf.fit(X, y)
        print("\n=== MODEL KNN (Dilatih pada data dengan kelas tunggal) ===")

        # Save the model even if single class
        os.makedirs(MODEL_DIR, exist_ok=True)
        joblib.dump(clf, MODEL_PATH)
        print(f"Model KNN disimpan ke {MODEL_PATH}")

        return clf, "Model dilatih pada data dengan kelas tunggal, evaluasi penuh tidak dilakukan."

    # Oversampling data minoritas
    df_model = pd.concat([X, y.rename('Layak_KNN_Target')], axis=1)
    majority_class_series = df_model['Layak_KNN_Target'].mode()

    if majority_class_series.empty:
        print("Error: Tidak dapat menentukan kelas mayoritas untuk oversampling.")
        return None, None
    majority_class = majority_class_series[0]

    df_majority = df_model[df_model['Layak_KNN_Target'] == majority_class]
    df_minority = df_model[df_model['Layak_KNN_Target'] != majority_class]

    X_balanced, y_balanced = X, y
    if not df_minority.empty and len(df_minority) < len(df_majority):
        df_minority_upsampled = resample(
            df_minority,
            replace=True,
            n_samples=len(df_majority),
            random_state=42
        )
        df_balanced_data = pd.concat([df_majority, df_minority_upsampled])
        X_balanced = df_balanced_data[existing_features_for_knn]
        y_balanced = df_balanced_data['Layak_KNN_Target']
        print("Info: Oversampling dilakukan pada kelas minoritas.")
    elif df_minority.empty:
        print("Peringatan: Tidak ada kelas minoritas untuk di-oversample.")
    else:
        print("Info: Distribusi kelas seimbang atau kelas minoritas tidak lebih kecil. Tidak melakukan oversampling.")

    if X_balanced.empty or y_balanced.empty:
        print("Error: X_balanced atau y_balanced kosong setelah potensi oversampling.")
        return None, None

    # Split data latih dan uji
    try:
        X_train, X_test, y_train, y_test = train_test_split(
            X_balanced, y_balanced, test_size=0.2, random_state=42, stratify=y_balanced
        )
    except ValueError as e: # Fallback jika stratifikasi gagal (misal, kelas terlalu kecil setelah split)
        print(f"Peringatan: Stratifikasi gagal ({e}). Melakukan split tanpa stratifikasi.")
        X_train, X_test, y_train, y_test = train_test_split(
            X_balanced, y_balanced, test_size=0.2, random_state=42
        )

    n_neighbors = min(5, len(X_train)) if len(X_train) > 0 else 1
    if n_neighbors == 0: n_neighbors = 1

    clf = KNeighborsClassifier(n_neighbors=n_neighbors)
    clf.fit(X_train, y_train)

    # Save the trained model
    os.makedirs(MODEL_DIR, exist_ok=True)
    joblib.dump(clf, MODEL_PATH)
    print(f"Model KNN disimpan ke {MODEL_PATH}")


    print("\n=== EVALUASI MODEL KNN ===")
    if not X_test.empty:
        y_pred = clf.predict(X_test)
        accuracy = accuracy_score(y_test, y_pred)
        report = classification_report(y_test, y_pred, zero_division=0)
        print(f"Akurasi: {accuracy}")
        print(report)
        return clf, classification_report(y_test, y_pred, output_dict=True, zero_division=0)
    else:
        print("Tidak ada data tes untuk evaluasi.")
        return clf, "Tidak ada data tes untuk evaluasi."

# ===============================
# 3. Fungsi SAW (Pembobotan + Perangkingan)
# ===============================
# This function is for ranking the *entire dataset* based on SAW score.
# It's useful for generating the list of recipients based on kuota and passing grade.
# It doesn't use the KNN model.
def apply_saw_ranking(df_input, passing_grade, kuota):
    if 'Total_Nilai' not in df_input.columns:
        print("Error: Kolom 'Total_Nilai' tidak ditemukan untuk SAW ranking.")
        return pd.DataFrame()
    if df_input.empty:
        print("Error: DataFrame input untuk SAW ranking kosong.")
        return pd.DataFrame()

    df_saw = df_input.copy()
    max_total_nilai = df_saw['Total_Nilai'].max()

    if max_total_nilai == 0:  # Hindari pembagian dengan nol jika semua nilai 0
        df_saw['Skor_SAW'] = 0.0
    else:
        df_saw.loc[:, 'Skor_SAW'] = df_saw['Total_Nilai'] / max_total_nilai # Use .loc here too

    df_saw = df_saw.sort_values(by='Skor_SAW', ascending=False)

    # Filter by passing grade first, then apply kuota
    df_lulus_passing_grade = df_saw[df_saw['Total_Nilai'] >= passing_grade].copy()

    # Apply kuota to those who passed the grade
    # Create a deep copy here to ensure modifications are on an independent DataFrame
    df_final_ranked = df_lulus_passing_grade.head(kuota).copy()

    # Add status kelayakan akhir hanya untuk yang masuk ranking final
    if not df_final_ranked.empty:
        df_final_ranked.loc[:, 'Status_Kelayakan_SAW'] = 'Layak' # Use .loc to avoid SettingWithCopyWarning

    # Kolom yang ingin ditampilkan
    display_cols = ['Nama', 'Total_Nilai', 'Skor_SAW']
    # Add status only if the column exists (i.e., df_final_ranked is not empty)
    if 'Status_Kelayakan_SAW' in df_final_ranked.columns:
         display_cols.append('Status_Kelayakan_SAW')

    # Add criteria columns for context in the ranking output
    criteria_cols_in_df = [col for col in PENAMBAH_KRITERIA + PENGURANG_KRITERIA if col in df_final_ranked.columns]
    display_cols = ['Nama'] + criteria_cols_in_df + ['Total_Nilai', 'Skor_SAW']
    if 'Status_Kelayakan_SAW' in df_final_ranked.columns:
         display_cols.append('Status_Kelayakan_SAW')


    return df_final_ranked[display_cols]

# ===============================
# 4. Fungsi Prediksi Individu (Hybrid: SAW Score + KNN Prediction)
# ===============================
# Modified to use the trained KNN model
def predict_individual_status(name, pekerjaan_status, df_original, knn_model, passing_grade):
    if 'Nama' not in df_original.columns:
        return {"error": "Kolom 'Nama' tidak ditemukan di DataFrame."}

    individu_data_list = df_original[df_original['Nama'] == name]
    if individu_data_list.empty:
        return {"error": f"Individu dengan nama '{name}' tidak ditemukan."}

    # Use .iloc[[0]].copy() to get a copy of the first row
    individu_data = individu_data_list.iloc[[0]].copy()

    # Store original values for logging/reasons
    original_tidak_bekerja = individu_data['Tidak Berkerja'].iloc[0] if 'Tidak Berkerja' in individu_data.columns else 'N/A'
    original_kehilangan_pencaharian = individu_data['Kehilangan Mata Pencaharian'].iloc[0] if 'Kehilangan Mata Pencaharian' in individu_data.columns else 'N/A'

    # Update fitur berdasarkan pekerjaan_status
    # Use .loc for assignment to avoid SettingWithCopyWarning
    if 'Tidak Berkerja' in individu_data.columns and 'Kehilangan Mata Pencaharian' in individu_data.columns:
        if pekerjaan_status == "Tidak Bekerja":
            individu_data.loc[:, 'Tidak Berkerja'] = 'V'
            individu_data.loc[:, 'Kehilangan Mata Pencaharian'] = '-'
        elif pekerjaan_status == "Kehilangan Pekerjaan":
            individu_data.loc[:, 'Tidak Berkerja'] = 'V'
            individu_data.loc[:, 'Kehilangan Mata Pencaharian'] = 'V'
        elif pekerjaan_status == "Bekerja":
            individu_data.loc[:, 'Tidak Berkerja'] = '-'
            individu_data.loc[:, 'Kehilangan Mata Pencaharian'] = '-'
        else:
            print(f"Status pekerjaan '{pekerjaan_status}' tidak dikenali, fitur pekerjaan tidak diubah.")
    else:
        print("Peringatan: Kolom 'Tidak Berkerja' atau 'Kehilangan Mata Pencaharian' tidak ada. Update status pekerjaan dilewati.")


    # --- SAW Score Calculation (based on potentially updated data) ---
    skor_individu = 0
    alasan_penambah = []
    alasan_pengurang = []

    if 'DTKS' in individu_data.columns and individu_data['DTKS'].iloc[0] == 'V':
        skor_individu += 10 # DTKS gives 10 points
        alasan_penambah.append("DTKS")

    for col in PENAMBAH_KRITERIA:
        if col in individu_data.columns and individu_data[col].iloc[0] == 'V':
            skor_individu += 1 # Other criteria give 1 point
            alasan_penambah.append(col)

    for col in PENGURANG_KRITERIA:
        if col in individu_data.columns and individu_data[col].iloc[0] == 'V':
            skor_individu -= 1 # Pengurang criteria subtract 1 point
            alasan_pengurang.append(col)

    # Ensure score is not negative
    skor_individu = max(0, skor_individu)

    # Normalize SAW score based on the max score in the *original* dataset
    max_total_nilai_global = df_original['Total_Nilai'].max()
    skor_saw_individu = skor_individu / max_total_nilai_global if max_total_nilai_global != 0 else 0.0

    # --- KNN Prediction ---
    features_for_knn = PENAMBAH_KRITERIA + PENGURANG_KRITERIA
    existing_features_for_knn = [f for f in features_for_knn if f in individu_data.columns]

    if not existing_features_for_knn:
         knn_prediction = "Tidak dapat diprediksi (fitur KNN tidak ada)"
         print("Peringatan: Tidak ada fitur KNN yang tersedia untuk prediksi individu.")
    elif knn_model is None:
         knn_prediction = "Model KNN belum dilatih"
         print("Peringatan: Model KNN tidak tersedia untuk prediksi individu.")
    else:
        # Prepare individual features for KNN prediction
        X_individual = individu_data[existing_features_for_knn].copy()
        for col in existing_features_for_knn:
            X_individual[col] = X_individual[col].astype(str).replace({'V': 1, '-': 0, np.nan: 0, 'nan': 0})
        X_individual = X_individual.apply(pd.to_numeric, errors='coerce').fillna(0)

        # Ensure the order of columns matches the training data if possible (more robust)
        # This requires knowing the feature order from training, which isn't stored in the model by default.
        # A more robust approach would save the feature list with the model.
        # For now, assume the order from existing_features_for_knn is consistent.
        # A safer way is to re-create the feature list used during training.
        # Let's assume the order is consistent for this example.

        try:
            knn_prediction = knn_model.predict(X_individual)[0]
        except Exception as e:
            knn_prediction = f"Error prediksi KNN: {e}"
            print(f"Error saat prediksi KNN untuk {name}: {e}")


    # Determine final status (e.g., based on KNN prediction)
    # The 'status_kelayakan' here is the KNN prediction result.
    # The SAW score ('skor_total_aktual') is also returned for context.
    final_status = knn_prediction # Use KNN prediction as the primary status


    alasan_detail = {
        "DTKS": True if 'DTKS' in individu_data.columns and individu_data['DTKS'].iloc[0] == 'V' else False,
        "Faktor Penambah Skor": alasan_penambah,
        "Faktor Pengurang Skor": alasan_pengurang,
        "Update Pekerjaan": {
            "status_input": pekerjaan_status,
            "Tidak Berkerja": f"Sebelum: {original_tidak_bekerja}, Sesudah: {individu_data['Tidak Berkerja'].iloc[0] if 'Tidak Berkerja' in individu_data.columns else 'N/A'}",
            "Kehilangan Mata Pencaharian": f"Sebelum: {original_kehilangan_pencaharian}, Sesudah: {individu_data['Kehilangan Mata Pencaharian'].iloc[0] if 'Kehilangan Mata Pencaharian' in individu_data.columns else 'N/A'}"
        }
    }

    return {
        "nama": name,
        "skor_total_saw_aktual": skor_individu, # Renamed for clarity
        "skor_saw_ternormalisasi": round(skor_saw_individu, 4),
        "status_kelayakan_knn": final_status, # Indicate this is KNN prediction
        "passing_grade_digunakan_saw": passing_grade, # Indicate this is for SAW score context
        "alasan": alasan_detail
    }

# ===============================
# Contoh Penggunaan Utama
# ===============================
if __name__ == "__main__":
    # Ensure model directory exists
    os.makedirs(MODEL_DIR, exist_ok=True)

    df_processed = load_and_preprocess_data() # Load from CSV

    if df_processed.empty:
        print("Gagal memuat atau memproses data. Program berhenti.")
        exit()

    print("\n=== DATASET AWAL SETELAH PEMROSESAN NILAI (5 Data Pertama) ===")
    cols_to_show = ['Nama', 'DTKS'] + [col for col in PENAMBAH_KRITERIA if col in df_processed.columns] + \
                     [col for col in PENGURANG_KRITERIA if col in df_processed.columns] + ['Total_Nilai']
    print(df_processed[cols_to_show].head())

    # Train and save the KNN model
    knn_model, knn_report_dict = train_and_evaluate_knn(df_processed.copy()) # Pass a copy to avoid modifying original df

    if knn_model:
        print("Model KNN berhasil dilatih/dievaluasi dan disimpan.")
    else:
        print("Gagal melatih/mengevaluasi model KNN.")

    # Load the saved model for demonstration (in a real app, you'd load it once)
    loaded_knn_model = None
    if os.path.exists(MODEL_PATH):
        try:
            loaded_knn_model = joblib.load(MODEL_PATH)
            print(f"Model KNN berhasil dimuat dari {MODEL_PATH}")
        except Exception as e:
            print(f"Error memuat model KNN dari {MODEL_PATH}: {e}")
    else:
        print(f"Model KNN tidak ditemukan di {MODEL_PATH}. Tidak dapat melakukan prediksi individu.")


    passing_grade_saw = 10
    kuota_penerima = 5

    print(f"\n=== RANKING DATA DENGAN PASSING GRADE {passing_grade_saw} DAN KUOTA {kuota_penerima} (SAW) ===")
    # Use the original df_processed for SAW ranking as it has the Total_Nilai column
    df_ranked_saw = apply_saw_ranking(df_processed.copy(), passing_grade_saw, kuota_penerima) # Pass a copy
    if not df_ranked_saw.empty:
        print(df_ranked_saw)
    else:
        print("Tidak ada data yang memenuhi kriteria ranking SAW atau terjadi error.")

    print("\n=== PREDIKSI STATUS INDIVIDU (Menggunakan Model KNN yang Dilatih) ===")
    if loaded_knn_model and not df_processed.empty and 'Nama' in df_processed.columns and not df_processed['Nama'].empty:
        sample_name = df_processed['Nama'].iloc[0]

        # Use the loaded_knn_model for individual prediction
        prediksi1 = predict_individual_status(sample_name, "Tidak Bekerja", df_processed, loaded_knn_model, passing_grade_saw)
        print(f"\nPrediksi untuk '{sample_name}' jika status pekerjaan 'Tidak Bekerja':")
        print(json.dumps(prediksi1, indent=2, ensure_ascii=False))

        prediksi2 = predict_individual_status(sample_name, "Bekerja", df_processed, loaded_knn_model, passing_grade_saw)
        print(f"\nPrediksi untuk '{sample_name}' jika status pekerjaan 'Bekerja':")
        print(json.dumps(prediksi2, indent=2, ensure_ascii=False))

        prediksi_tidak_ada = predict_individual_status("Nama", "Bekerja", df_processed, loaded_knn_model, passing_grade_saw)
        print(f"\nPrediksi untuk 'Nama':")
        print(json.dumps(prediksi_tidak_ada, indent=2, ensure_ascii=False))
    elif not loaded_knn_model:
        print("Tidak dapat menjalankan prediksi individu: Model KNN tidak tersedia.")
    else:
         print("Tidak dapat menjalankan prediksi individu: data kosong atau kolom 'Nama' tidak ada/kosong.")