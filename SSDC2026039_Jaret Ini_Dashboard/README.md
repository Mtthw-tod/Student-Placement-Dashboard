# SSDC — CDC Dashboard (Streamlit)

## Cara menjalankan
1. Pastikan Python 3.9+ terpasang.
2. Buka terminal di folder ini, lalu install dependency:
   ```
   pip install -r requirements.txt
   ```
3. Jalankan aplikasi:
   ```
   streamlit run app_cdc.py
   ```
4. Browser akan otomatis terbuka ke `http://localhost:8501`.

## Struktur folder
```
streamlit_cdc_dashboard/
├── app_cdc.py          # kode utama dashboard
├── requirements.txt
├── README.md
└── data/                # 6 CSV sumber data (sudah disertakan)
    ├── company.csv
    ├── talent_request.csv
    ├── student_all.csv
    ├── status_student.csv
    ├── tracking_company.csv
    └── tracking_student.csv
```

Kalau ingin memakai data yang lebih baru, cukup ganti isi file CSV di folder `data/`
dengan nama file yang sama — dashboard akan otomatis membaca ulang saat direfresh.

## Fitur
- Filter global di sidebar: periode talent request, jenis penempatan, sektor industri, program studi.
- 5 tab sesuai business task (BT-01 s.d. BT-08):
  1. **Ringkasan** — KPI eksekutif, trend, top prodi placement
  2. **Permintaan & Matching** — volume request, skema kerja, daftar prioritas talent request
  3. **Pipeline Seleksi** — funnel tahapan seleksi, catatan kualitas data
  4. **Ghosting & Follow-up** — perusahaan paling sering ghosting vs acceptance rate terbaik
  5. **Kesiapan Mahasiswa** — eligibility checklist, IPK, domisili, alasan belum eligible
- Tombol unduh CSV hasil filter (talent request & mahasiswa eligible).

## Catatan
Ini adalah versi untuk sudut pandang **Career Development Center (CDC)**.
Versi untuk sudut pandang pelamar/mahasiswa dan perusahaan mitra dapat dibuat
menyusul dengan struktur multi-page (`pages/2_Pelamar.py`, `pages/3_Perusahaan.py`)
yang memfilter data berdasarkan NIM atau id_company.
