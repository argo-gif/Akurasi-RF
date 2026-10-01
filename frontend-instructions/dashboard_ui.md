# Frontend Dashboard UI Instruction (`dashboard_ui.md`)

## 1. Deskripsi UI & Pengalaman Pengguna
Antarmuka Demand Planning & Forecast Accuracy Dashboard dirancang dengan estetika modern berstandar tinggi (sleek dark mode, glassmorphism, typography elegan Google Fonts, dan visualisasi data yang responsif).

---

## 2. Struktur Modul Utama Dashboard

### A. Header Navigation & Status
- Judul Proyek: **Demand Planning & Forecast Accuracy Dashboard**
- Badge status real-time koneksi ke Backend API Service (`http://localhost:8050`).
- Tombol **Refresh Data** (memanggil ulang API).

### B. Modul 1: Executive Summary KPI Cards
Menampilkan 4 kartu KPI utama:
1. **WAFE Accuracy (Margin Profit Rp)**: Persentase akurasi berbobot margin finansial (Indikator warna: Hijau untuk akurasi tinggi, Kuning/Merah jika rendah).
2. **MAPE Accuracy (Volume)**: Persentase akurasi berbasis volume.
3. **Total Bias Qty**: Menunjukkan deviasi akumulatif (Status **Over-Forecast** atau **Under-Forecast**).
4. **Value at Risk (Rp)**: Total nilai finansial rupiah yang berisiko dari error forecast (Disajikan dalam format mata uang Rupiah `Rp X,XXXB / M`).

### C. Modul 2: Performance Matrix (4 Kuadran Pareto)
Grid 2x2 interaktif yang menampilkan performa 4 kuadran Pareto:
1. **MTM - Pareto** (Make-to-Order Kontributor Utama 80% Value)
2. **MTM - Non-Pareto** (Make-to-Order Long-Tail 20% Value)
3. **Non-MTM - Pareto** (Make-to-Stock Reguler High Volume)
4. **Non-MTM - Non-Pareto** (Make-to-Stock Reguler Slow-Moving)
Setiap kartu kuadran menampilkan SKU Count, Actual Qty, RF Qty, WAFE Accuracy %, dan Value at Risk Rp.

### D. Modul 3: Trend & Gap Analysis
- Grafik tren bulanan menggunakan **Chart.js** yang menggambarkan pergerakan WAFE Accuracy (%) dan Nilai Error Rp per bulan.

### E. Modul 4: Deep-Dive SKU Level Table
- Tabel data SKU interaktif dengan fitur:
  - **Search Box**: Pencarian instan berdasarkan Kode Produk atau Nama Produk.
  - **Quadrant Filter Dropdown**: Filter SKU per kuadran.
  - **Detail Kolom**: Kode SKU, Nama Produk, GB, MTM Flag, Actual Qty, RF Qty, Error Qty, Margin/Harga Dasar (Rp), Error Value (Rp), & Kuadran Badge.

---

## 3. Komponen File Frontend
- `index.html`: Struktur HTML5 semantik.
- `style.css`: Visual styling, CSS Variables, Glassmorphism, Responsive Grid.
- `app.js`: Logika interaktif JavaScript, API Fetching, Chart.js rendering, Filtering & Search.
