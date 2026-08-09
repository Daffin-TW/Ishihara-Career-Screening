# 👁️ ODZ Screening – Skrining Buta Warna & Rekomendasi Karier

**ODZ Screening** adalah aplikasi web full-stack berbasis **Flask (Python)** dan **XGBoost Machine Learning** yang dirancang untuk melakukan skrining tingkat buta warna menggunakan **Tes Ishihara** serta memprediksi kesesuaian karier pengguna berdasarkan hasil tes, kemampuan identifikasi warna, dan profil minat **RIASEC**.

---

## ✨ Fitur Utama

- 🎨 **Tes Ishihara Digital (11 Plat)**: Penyajian gambar plat warna Ishihara interaktif slide-by-slide dengan pencatatan skor otomatis (jumlah benar, salah, dan persentase).
- 📊 **Evaluasi Tingkat Keparahan**: Mengategorikan tingkat defisiensi warna pengguna (*Normal*, *Ringan*, *Sedang*, *Berat*) berdasarkan threshold persentase identifikasi.
- 🎯 **Kuesioner Kemampuan Warna & RIASEC**: Pengumpulan data kemampuan mengenali 7 spektrum warna dan 30 pertanyaan tipe kepribadian kerja RIASEC (Realistic, Investigative, Artistic, Social, Enterprising, Conventional).
- 🤖 **Prediksi Model Machine Learning XGBoost**: Inferensi otomatis kesesuaian pilihan karier (*Direkomendasikan*, *Kurang Direkomendasikan*, atau *Tidak Direkomendasikan*) beserta *confidence score*.
- 📈 **Visualisasi Hasil Interaktif**:
  - **Gauge Chart** untuk persentase identifikasi warna.
  - **Confidence Circle** & Distribusi Probabilitas Prediksi.
  - **Radar Chart (Chart.js)** untuk profil minat RIASEC.
  - Ringkasan komprehensif seluruh jawaban pengguna.
- 🌓 **Mode Terang & Gelap (Light / Dark Mode)**: Dilengkapi toggle tema dengan penyimpanan pilihan via `localStorage`.
- 📱 **Desain Modern & Responsif**: Menggunakan Bootstrap 5, Glassmorphism, Soft UI, micro-animations, serta validasi real-time berbasis JavaScript.

---

## 📁 Struktur Folder Project

```text
Ishihara-Career-Screening/
├── app.py                     # Entry point utama aplikasi Flask
├── config.py                  # Konfigurasi aplikasi & path resource
├── requirements.txt           # Dependency Python
├── .env.example               # Template environment variables
├── README.md                  # Dokumentasi proyek
│
├── routes/                    # Blueprint routing Flask
│   ├── __init__.py
│   ├── main.py                # Route halaman utama (Home)
│   └── screening.py           # Route form skrining, prediksi, dan hasil
│
├── utils/                     # Modul utilitas & preprocessing
│   ├── __init__.py
│   ├── preprocessor.py        # Preprocessing data form, Ishihara, RIASEC, & feature engineering
│   └── predictor.py           # Pemuatan model XGBoost, encoder, dan inferensi
│
├── templates/                 # Template HTML Jinja2
│   ├── base.html              # Layout utama (Navbar, Footer, Dark Mode Toggle)
│   ├── home.html              # Landing page & penjelasan fitur
│   ├── form.html              # Multi-step wizard form (6 langkah)
│   ├── result.html            # Dashboard hasil analisis & rekomendasi
│   └── errors/                # Halaman error custom (404, 500)
│       ├── 404.html
│       └── 500.html
│
├── static/                    # Asset statis
│   ├── css/
│   │   └── style.css          # Stylesheet kustom (Glassmorphism & animations)
│   └── js/
│       ├── form.js            # Logika wizard form, validasi, & Ishihara slider
│       └── result.js          # Chart.js, gauge canvas, & animasi hasil
│
└── src/                       # Resource model & dataset bawaan
    ├── data/
    │   ├── dummy_data.csv     # Dataset acuan struktur data
    │   └── questions.txt      # Sumber pertanyaan form & karier
    ├── img/
    │   └── ishihara/          # Gambar plat tes Ishihara (1-12.png, dll.)
    └── model/
        ├── model_production.pkl  # Model XGBoost terlatih
        ├── encoders.pkl           # Label encoders untuk variabel kategorikal
        ├── feature_list.json      # Urutan 19 fitur input model
        └── best_params.json       # Dokumentasi hyperparameter training
```

---

## ⚙️ Persyaratan Sistem & Instalasi

### 1. Prasyarat
- **Python 3.9+** (Direkomendasikan Python 3.10 atau 3.12)
- `pip` dan `virtualenv`

### 2. Langkah Instalasi

1. **Clone repository ini** (atau buka terminal di direktori proyek):
   ```bash
   git clone https://github.com/Daffin-TW/Ishihara-Career-Screening.git
   cd Ishihara-Career-Screening
   ```

2. **Buat dan aktifkan Virtual Environment**:
   - **Windows (PowerShell)**:
     ```powershell
     python -m venv venv
     .\venv\Scripts\Activate.ps1
     ```
   - **Linux / macOS**:
     ```bash
     python3 -m venv venv
     source venv/bin/activate
     ```

3. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

---

## 🚀 Cara Jalankan Aplikasi

Setelah seluruh dependensi terinstall dan virtual environment aktif:

### Menjalankan dengan Flask CLI:
```bash
flask run
```
Atau menggunakan `python app.py`:
```bash
python app.py
```

Aplikasi akan berjalan di:
👉 **`http://127.0.0.1:5000`**

---

## 📝 Alur Skrining Aplikasi (Wizard Form)

1. **Step 1 - Data Diri**: Pengisian Nama, Usia, Jenis Kelamin, Pendidikan, Riwayat Keluarga, serta Penggunaan Alat Bantu/Penyakit Mata.
2. **Step 2 - Tes Ishihara**: Penampilan 11 gambar plat Ishihara secara bergantian untuk menebak angka yang terlihat.
3. **Step 3 - Identifikasi Warna**: Penilaian tingkat kemudahan pengenalan 7 spektrum warna (skala 1–5).
4. **Step 4 - Kuesioner RIASEC**: Pengisian 30 item minat karir yang terbagi dalam 6 dimensi RIASEC (skala Likert 1–5).
5. **Step 5 - Pilihan Karier**: Pemilihan 1 bidang pekerjaan yang paling diminati dari opsi yang tersedia.
6. **Step 6 - Review & Submit**: Ringkasan jawaban sebelum dikirim untuk proses inferensi oleh model Machine Learning XGBoost.

---

## 🛠️ Teknologi yang Digunakan

- **Backend**: Python 3, Flask, Jinja2, Werkzeug
- **Machine Learning & Data**: XGBoost, Scikit-Learn, Pandas, NumPy, Joblib
- **Frontend**: HTML5, CSS3 (Vanilla), JavaScript (ES6+), Bootstrap 5, Bootstrap Icons, Chart.js

---

## 📄 Lisensi

Proyek ini dibuat untuk keperluan akademik dan pengembangan skrining kesehatan & karier.
