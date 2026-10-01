# Frontend - Demand Planning & Forecast Accuracy Dashboard UI

Folder ini berisi kode antarmuka pengguna (User Interface) berbasis Single Page Application (SPA) dengan desain modern, sleek dark mode, glassmorphism, dan grafik interaktif Chart.js.

---

## 📁 Struktur Berkas

```
frontend/
├── index.html    # Struktur HTML5 Dashboard
├── style.css     # Styling Design System, Modern Dark Theme & Responsive Grid
├── app.js        # Logika aplikasi, Fetch API Backend, Rendering Chart & Tabel Interaktif
└── README.md     # Dokumentasi frontend
```

---

## 🎨 Tampilan & Komponen Dashboard

1. **Header & Status Connection**:
   - Menampilkan judul dashboard & indikator status koneksi real-time ke API Backend.
   - Tombol **Refresh Data** untuk memanggil ulang API.

2. **Executive KPI Cards**:
   - **WAFE Accuracy (Margin Profit Rp)**
   - **MAPE Accuracy (Volume)**
   - **Total Bias Qty (Over / Under Forecast)**
   - **Value at Risk (Rp)**

3. **Matriks Pareto 4-Kuadran**:
   - Grid 2x2 interaktif (MTM Pareto, MTM Non-Pareto, Non-MTM Pareto, Non-MTM Non-Pareto).

4. **Visualisasi Tren Bulanan (Chart.js)**:
   - Grafik tren pergerakan WAFE Accuracy (%) bulanan.

5. **Tabel Deep-Dive SKU Level**:
   - Fitur pencarian kata kunci (*Search Box*).
   - Fitur filter kuadran (*Dropdown Filter*).
   - Tampilan detail SKU: Kode, Nama, Kuadran, Harga Dasar (Rp), Actual Qty, RF Qty, Error Qty, Error Margin (Rp), & MAPE %.

---

## 🚀 Cara Menjalankan Secara Lokal

1. **Jalankan Backend Server**:
   Pastikan backend API server sudah aktif di `http://localhost:8050`.

2. **Jalankan Web Server Frontend**:
   Buka terminal di root proyek dan jalankan:
   ```bash
   python -m http.server 3000 --directory frontend
   ```

3. **Buka di Browser**:
   Buka URL **`http://localhost:3000`** pada web browser Anda.

---

## ☁️ Petunjuk Deployment ke Vercel

1. Buka dashboard [Vercel](https://vercel.com).
2. Import project repository Git ini.
3. Atur konfigurasi sebagai berikut:
   - **Root Directory**: `frontend`
   - **Framework Preset**: `Other` / `Static Site`
   - **Build Command**: (Biarkan kosong)
   - **Output Directory**: `.`
4. Deploy! Vercel akan langsung memberikan URL live HTTPS untuk frontend Anda.
