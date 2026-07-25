# Student Placement System (SSDC Dashboard)

Dashboard ini merupakan aplikasi **Streamlit** yang dikembangkan sebagai sistem pendukung pengambilan keputusan (Decision Support System) bagi **Career Development Center (CDC)** dalam proses penempatan mahasiswa ke perusahaan mitra.

---

# Persyaratan

Sebelum menjalankan aplikasi, pastikan komputer telah memiliki:

- Python 3.10 atau lebih baru
- Koneksi internet (hanya diperlukan saat instalasi package)
- Terminal / Command Prompt / PowerShell

---

# Struktur Folder

Pastikan struktur folder tetap seperti berikut.

```
SSDC2026039_Jaret Ini_Dashboard/
│
├── SSDC2026039_Jaret Ini_Dashboard.py
├── requirements.txt
│
├── assets/
│   └── logo.png
│
└── data/
    ├── company.csv
    ├── status_student.csv
    ├── student_all.csv
    ├── talent_request.csv
    ├── tracking_company.csv
    └── tracking_student.csv
```

**Penting**

- Jangan mengubah nama folder.
- Jangan mengubah nama file CSV.
- Jangan memindahkan file `SSDC2026039_Jaret Ini_Dashboard.py`.

---

# Langkah Menjalankan Dashboard

## 1. Buka Folder Project

Ekstrak file ZIP (jika masih terkompres), kemudian buka folder SSDC2026039_Jaret Ini_Dashboard yang berisi file **SSDC2026039_Jaret Ini_Dashboard.py**, **requirements.txt**, folder **assets**, dan folder **data**.

---

## 2. Buka Command Prompt (CMD)

### Cara Cepat Langsung dari File Explorer

1. Buka folder SSDC2026039_Jaret Ini_Dashboard di **File Explorer**.
2. Klik pada **kolom alamat (Address Bar / Path Bar)** di bagian atas jendela File Explorer.
3. Hapus seluruh isi kolom tersebut.
4. Ketik:

```text
cmd
```

5. Tekan **Enter**.

Command Prompt (CMD) akan otomatis terbuka pada folder project sehingga tidak perlu menggunakan perintah `cd`.

Contoh tampilan:

```text
C:\Users\NamaUser\Documents\SSDC2026039_Jaret Ini_Dashboard>
```

---

## 3. Install Dependency

Pada Command Prompt yang telah terbuka, jalankan perintah berikut:

```bash
pip install -r requirements.txt
```

Tunggu hingga seluruh proses instalasi selesai.

---

## 4. Jalankan Dashboard

Setelah instalasi selesai, jalankan aplikasi dengan perintah berikut:

```bash
streamlit run SSDC2026039_Jaret Ini_Dashboard.py
```

Apabila muncul pesan bahwa perintah `streamlit` tidak dikenali, gunakan salah satu perintah berikut:

```bash
python -m streamlit run SSDC2026039_Jaret Ini_Dashboard.py
```

atau

```bash
py -m streamlit run SSDC2026039_Jaret Ini_Dashboard.py
```

---

## 5. Dashboard Akan Terbuka

Apabila berhasil dijalankan, terminal akan menampilkan alamat seperti berikut:

```text
Local URL: http://localhost:8501
```

Browser biasanya akan terbuka secara otomatis. Jika tidak, salin alamat tersebut ke browser untuk membuka dashboard.

# Fitur Dashboard

Dashboard menyediakan berbagai analisis, di antaranya:

- Executive Dashboard
- Talent Request Analysis
- Talent Matching
- Recruitment Pipeline Monitoring
- Ghosting Detection
- Student Readiness Analysis
- Recommendation System (Decision Support)
- Executive Decision Panel
- Export Executive Report (PDF)

---
