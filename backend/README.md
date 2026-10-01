# Backend - Demand Planning & Forecast Accuracy API Engine

Folder ini berisi seluruh komponen backend Python untuk pengolahan data Excel, kalkulasi metrik demand planning (MAPE & WAFE Margin Profit Rp), klasifikasi Pareto 80/20 MTM & Non-MTM, serta server HTTP REST API.

---

## 📁 Struktur Berkas

```
backend/
├── data_processor.py   # Engine pengolahan data Excel & Pareto logic
├── main.py             # HTTP REST API server dengan CORS enabled
├── requirements.txt   # Daftar dependensi Python
└── README.md           # Dokumentasi backend
```

---

## ⚙️ Persyaratan Sistem & Dependensi

- **Python Version**: Python 3.9+
- **Dependensi Utama**: `openpyxl>=3.0.0`
- **Standard Library Digunakan**: `zipfile`, `xml.etree.ElementTree`, `re`, `http.server`, `urllib.parse`, `json`.

---

## 🚀 Cara Menjalankan Secara Lokal

1. **Pastikan File Data Excel Tersedia**:
   Pastikan 3 file Excel utama berikut ada di root folder proyek:
   - `Data RF.xlsx`
   - `Data sales.xlsx`
   - `Master produk.xlsx`

2. **Jalankan API Server**:
   ```bash
   python backend/main.py
   ```
   Server akan otomatis berjalan di **`http://localhost:8050`** dan siap melayani request API.

---

## 🔌 Dokumentasi REST API Endpoints

- **`GET /api/health`**: Cek status server API.
- **`GET /api/summary`**: Mendapatkan metrik Executive Summary (MAPE Accuracy, WAFE Accuracy, Total Bias Qty, & Value at Risk Rp).
- **`GET /api/matrix`**: Ringkasan data 4 Kuadran Pareto (MTM Pareto, MTM Non-Pareto, Non-MTM Pareto, Non-MTM Non-Pareto).
- **`GET /api/skus`**: Data detail per SKU. Menyerahkan filter query string:
  - `?quadrant=MTM - Pareto` (Filter kuadran)
  - `?search=ANA005` (Pencarian kode/nama produk)
  - `?limit=100` (Batas jumlah data)
- **`GET /api/trend`**: Data tren akurasi bulanan WAFE & nilai error Rp.
- **`POST /api/reprocess`**: Memaksa hitung ulang data Excel dari scratch dan memperbarui file cache JSON (`data_cache.json`).

---

## ☁️ Petunjuk Deployment ke Render.com

1. Buat **Web Service** baru di dashboard Render.com.
2. Hubungkan repository Git proyek ini.
3. Atur konfigurasi sebagai berikut:
   - **Root Directory**: `backend` (atau biarkan kosong jika root)
   - **Environment**: `Python 3`
   - **Build Command**: `pip install -r backend/requirements.txt`
   - **Start Command**: `python backend/main.py`
4. Render secara otomatis menyediakan variabel environment `PORT`.
