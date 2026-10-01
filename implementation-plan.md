# Implementation Plan: Demand Planning & Forecast Accuracy Dashboard

Dokumen ini melacak rencana kerja berfase untuk pembangunan sistem Demand Planning & Forecast Accuracy Dashboard.

---

## 📌 Status Fase Pengerjaan

- [x] **Fase 1: Inisialisasi & Spesifikasi Proyek** *(Selesai)*
- [x] **Fase 2: Backend - Engine Pengolahan Data Python (`backend/data_processor.py`)** *(Selesai)*
- [x] **Fase 3: Backend - API Server Development (`backend/main.py`)** *(Selesai)*
- [x] **Fase 4: Frontend - Dashboard UI Development (`frontend/`)** *(Selesai)*
- [x] **Fase 5: Integration & Local End-to-End Testing** *(Selesai)*
- [x] **Fase 6: Dokumentasi & Requirements File** *(Selesai)*
- [ ] **Fase 7: Deployment (Render & Vercel) & Live Verification** *(Berikutnya)*
- [ ] **Fase 7: Deployment (Render & Vercel) & Live Verification**

---

## 📋 Detail Rencana Pekerjaan Per Fase

### Fase 1: Inisialisasi & Spesifikasi Proyek `[SELESAI]`
- [x] Membaca dan memahami `instructions.txt` & `project_description.txt`.
- [x] Memeriksa struktur & sampel data dari Excel (`Data RF.xlsx`, `Data sales.xlsx`, `Master produk.xlsx`).
- [x] Membuat dokumen spesifikasi proyek [`project_specs.md`](file:///c:/Argo/Project%20AI/AKURASI%20RF/project_specs.md).
- [x] Mendapatkan approval spesifikasi proyek dari user.

---

### Fase 2: Backend - Engine Pengolahan Data Python `[SELESAI]`
- [x] Buat folder `backend-instructions/` dan `backend/`.
- [x] Buat dokumen instruksi backend [`backend-instructions/data_processor.md`](file:///c:/Argo/Project%20AI/AKURASI%20RF/backend-instructions/data_processor.md).
- [x] Buat script Python [`backend/data_processor.py`](file:///c:/Argo/Project%20AI/AKURASI%20RF/backend/data_processor.py) untuk:
  - Standardisasi kode produk lama ke kode produk aktif.
  - Perhitungan Pareto 80/20 secara independen untuk kelompok MTM & Non-MTM.
  - Perhitungan metrik akurasi: MAPE, WAFE berbobot Margin Profit (Rp), Bias, & Value at Risk.
- [x] Tes lokal `data_processor.py` menggunakan data Excel asli dan verifikasi output-nya.

---

### Fase 3: Backend - API Server Development `[SELESAI]`
- [x] Buat dokumen instruksi API [`backend-instructions/api_service.md`](file:///c:/Argo/Project%20AI/AKURASI%20RF/backend-instructions/api_service.md).
- [x] Buat REST API server [`backend/main.py`](file:///c:/Argo/Project%20AI/AKURASI%20RF/backend/main.py) dengan endpoint:
  - `GET /api/summary`: Metrik executive summary (MAPE Accuracy, WAFE Accuracy, Total Bias, Value at Risk).
  - `GET /api/matrix`: Akurasi per 4 kuadran Pareto (MTM Pareto, MTM Non-Pareto, Non-MTM Pareto, Non-MTM Non-Pareto).
  - `GET /api/skus`: Tabel detail per SKU dengan opsi filtering & sorting.
  - `GET /api/trend`: Data tren bulanan akurasi RF vs Actual.
- [x] Uji coba endpoint API secara lokal.

---

### Fase 4: Frontend - Dashboard UI Development `[SELESAI]`
- [x] Buat folder `frontend-instructions/` dan `frontend/`.
- [x] Buat dokumen instruksi frontend [`frontend-instructions/dashboard_ui.md`](file:///c:/Argo/Project%20AI/AKURASI%20RF/frontend-instructions/dashboard_ui.md).
- [x] Buat antarmuka web modern pada [`frontend/index.html`](file:///c:/Argo/Project%20AI/AKURASI%20RF/frontend/index.html), [`frontend/style.css`](file:///c:/Argo/Project%20AI/AKURASI%20RF/frontend/style.css), & [`frontend/app.js`](file:///c:/Argo/Project%20AI/AKURASI%20RF/frontend/app.js):
  - Executive KPI Cards dengan tampilan menarik & indikator warna.
  - Grid Matriks 4-Kuadran Pareto.
  - Deep-dive SKU Table dengan fitur pencarian & filter.
  - Trend Visual Chart (Grafik tren akurasi bulanan).
- [x] Uji performa & visualisasi UI secara lokal.

---

### Fase 5: Integration & Local End-to-End Testing `[SELESAI]`
- [x] Jalankan backend API server dan frontend bersamaan secara lokal.
- [x] Uji koneksi data end-to-end dari Excel -> Backend Data Processor -> API -> Frontend UI.
- [x] Verifikasi keakuratan perhitungan numerik (520 SKU, 19 Periode Tren, 4-Kuadran Pareto) dan interaktivitas dashboard.

---

### Fase 6: Dokumentasi & Requirements File `[SELESAI]`
- [x] Buat [`backend/requirements.txt`](file:///c:/Argo/Project%20AI/AKURASI%20RF/backend/requirements.txt) dengan daftar library Python yang diperlukan (`openpyxl>=3.0.0`).
- [x] Buat [`backend/README.md`](file:///c:/Argo/Project%20AI/AKURASI%20RF/backend/README.md) dengan instruksi instalasi, API endpoints & rilis backend.
- [x] Buat [`frontend/README.md`](file:///c:/Argo/Project%20AI/AKURASI%20RF/frontend/README.md) dengan instruksi pemanggilan frontend & environment.

---

### Fase 7: Deployment & Live Verification `[PENDING]`
- [ ] Memberikan panduan & mengeksekusi deployment backend ke **Render.com**.
- [ ] Memberikan panduan & mengeksekusi deployment frontend ke **Vercel**.
- [ ] Uji coba sistem secara live (production URL) secara end-to-end.
