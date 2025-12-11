# 🇮🇩 Sosial Kita App
**Sistem Pendukung Keputusan Kelayakan Bantuan Sosial (Hybrid SAW & KNN)**

![Python](https://img.shields.io/badge/Python-3.8%2B-blue)
![Flask](https://img.shields.io/badge/Framework-Flask-green)
![Database](https://img.shields.io/badge/Database-SQLite-lightgrey)
![Status](https://img.shields.io/badge/Status-Development-orange)

---

## 📖 Tentang Proyek

**Sosial Kita App** adalah aplikasi berbasis web yang dirancang untuk membantu petugas kelurahan/dinas sosial dalam menentukan kelayakan penerima bantuan sosial secara objektif, transparan, dan efisien.

Aplikasi ini menggunakan pendekatan **Hybrid Decision Support System**:
1.  **Metode SAW (Simple Additive Weighting):** Menghitung skor prioritas berdasarkan aturan bobot kriteria pemerintah (Deterministik).
2.  **Algoritma KNN (K-Nearest Neighbors):** Memvalidasi kelayakan berdasarkan pola data historis penerima bantuan sebelumnya (Probabilistik).

### ✨ Fitur Unggulan
*   **Prediksi Individu & Massal:** Hitung kelayakan satu orang atau seluruh desa sekaligus dengan *Background Processing*.
*   **Laporan Otomatis:** Filter penerima berdasarkan kuota dan passing grade, lalu cetak PDF siap tanda tangan.
*   **Integrasi Wilayah:** Data Provinsi s/d Desa otomatis terhubung dengan API EMSIFA (seluruh Indonesia).
*   **Keamanan:** Role-based access (Admin/Petugas), Hashed Passwords, dan CSRF Protection.

---

## 🛠️ Tech Stack & Arsitektur

Kami memilih teknologi yang **Ringan, Efisien, dan Mudah Dikelola**:

| Komponen | Teknologi | Alasan Pemilihan |
| :--- | :--- | :--- |
| **Backend** | Python Flask | Ringan, modular, dan kompatibel native dengan library AI (Scikit-learn). |
| **Database** | SQLite + SQLAlchemy | Serverless (mudah di-deploy), portable, dengan abstraksi ORM yang kuat. |
| **Frontend** | Bootstrap 4 + Jinja2 | UI Responsif cepat, rendering aman di sisi server (SSR). |
| **AI Engine** | Scikit-learn (KNN) | Efisien untuk data tabular, cepat untuk dilatih ulang (*retrain*) oleh user. |
| **Report** | WeasyPrint | Konversi HTML ke PDF yang presisi (WYSIWYG). |

---

## 🚀 Panduan Instalasi & Penggunaan

Ikuti langkah ini untuk menjalankan aplikasi di komputer lokal Anda (Linux/Mac/Windows).

### 1. Prasyarat
Pastikan Python 3.8+ dan pip sudah terinstal.
```bash
python --version
pip --version
```

### 2. Instalasi Dependensi
Clone repository (jika ada) atau masuk ke folder proyek, lalu instal paket yang dibutuhkan:
```bash
pip install -r requirements.txt
```
*Jika `requirements.txt` belum ada, instal manual paket utamanya:*
```bash
pip install Flask Flask-SQLAlchemy Flask-Migrate Flask-Login Flask-WTF email_validator joblib numpy pandas openpyxl requests scikit-learn WeasyPrint
```

### 3. Inisialisasi Database
Siapkan struktur database SQLite:
```bash
flask db init      # Hanya dijalankan sekali di awal (jika folder migrations belum ada)
flask db migrate -m "Initial setup"
flask db upgrade   # Menerapkan tabel ke database
```

### 4. Membuat User Admin Pertama
Karena belum ada fitur registrasi publik, buat user lewat shell Python:
```bash
python
```
```python
>>> from app import db, create_app
>>> from app.database.models import User
>>> app = create_app()
>>> app.app_context().push()
>>> # Buat Admin
>>> u = User(username='admin', email='admin@example.com', role='admin')
>>> u.set_password('admin123') # Ganti password sesuka hati
>>> db.session.add(u)
>>> # Buat Petugas (Opsional)
>>> p = User(username='petugas', email='petugas@example.com', role='petugas')
>>> p.set_password('petugas123')
>>> db.session.add(p)
>>> db.session.commit()
>>> exit()
```

### 5. Menjalankan Aplikasi
```bash
python run.py
```
Buka browser dan akses: `http://127.0.0.1:5000`

---

## 📚 Dokumentasi Alur Kerja (Workflow)

### A. Peran Admin
1.  **Login** sebagai Admin.
2.  **Manajemen User:** Tambah/Edit/Hapus akun petugas lapangan.
3.  **Pengaturan Sistem:** Tentukan `Passing Grade` (Standard Kelayakan, misal: 0.5) dan `Kuota` penerima bantuan.

### B. Peran Petugas
1.  **Login** sebagai Petugas.
2.  **Input Data Warga:** Masukkan data NIK, Nama, Wilayah, dan Kriteria Ekonomi (Miskin, Difabel, dll).
3.  **Prediksi Individu:** Cek status kelayakan warga tertentu secara instan.
4.  **Prediksi Massal:** Lakukan update status kelayakan untuk **seluruh** data warga di database. (Gunakan fitur ini setelah input data massal).
5.  **Cetak Laporan:** Buka menu "Daftar Penerima Layak". Sistem otomatis menyaring warga yang **Layak** dan memiliki **Skor Tertinggi** sesuai kuota. Unduh PDF.

---

## 🔍 Logika Bisnis & Scoring

Keputusan akhir diambil berdasarkan kombinasi dua metode:

1.  **Skor SAW (Prioritas):**
    *   Rumus: `(Kriteria Positif - Kriteria Negatif) + Bonus DTKS`
    *   Skor dinormalisasi ke skala `0.0` - `1.0`.
    *   Semakin tinggi skor, semakin prioritas untuk dibantu.

2.  **Prediksi KNN (Validasi):**
    *   Mencocokkan profil warga dengan pola data historis.
    *   Menghasilkan status: "Layak" atau "Tidak Layak".

**Syarat Lolos:** Warga harus berstatus "Layak" menurut KNN **DAN** memiliki Skor SAW >= Passing Grade.

---

## 🛡️ Keamanan & Optimasi
*   **CSRF Protection:** Melindungi semua formulir dari serangan lintas situs.
*   **Input Validation:** Mencegah input data sampah/berbahaya (misal: upload file .exe diblokir).
*   **Background Worker:** Proses prediksi massal berjalan di latar belakang (Threading) agar antarmuka tidak macet (hang).
*   **Caching Wilayah:** Data nama desa disimpan di memori (RAM) untuk mempercepat loading halaman hingga 10x lipat.

---

## 📞 Kontak & Support
Jika menemukan *bug* atau error (seperti Error 500), silakan cek terminal/console log aplikasi untuk detail errornya, atau hubungi tim pengembang.

---
*Dibuat untuk memenuhi Tugas Akhir Mata Kuliah Pemrograman Web Lanjut.*
