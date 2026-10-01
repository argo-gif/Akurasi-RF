# Project Specifications: Demand Planning & Forecast Accuracy Dashboard

## 1. Ringkasan & Tujuan Proyek
Proyek ini bertujuan untuk membangun dashboard analitik interaktif yang memantau akurasi **Rolling Forecast (RF)** terhadap **Actual Sales** secara per periode bulanan. Dashboard ini memberikan visibilitas performa perencanaan berbasis volume (**MAPE**) dan dampak finansial langsung (**WAFE berbasis Margin Profit Rp**) dengan segmentasi portofolio Pareto (80/20) yang dihitung per **GB (Group Barang) MTM** dan per **GB Non-MTM**.

---

## 2. Input Data & File Sumber
1. **Data RF (`Data RF.xlsx`)**:
   - Atribut: `GB`, `KODE_PRODUK`, `NAMA_PRODUK`, `KODE_PRODUK_PRINCIPAL`, `SATUAN_TERKECIL`, `MTM FLAG` (Y/N), `RF` (Forecast Qty per Periode), `Periode`.
2. **Data Sales (`Data sales.xlsx`)**:
   - Atribut: `Periode`, `kode_regional`, `branch_code`, `cabang`, `mtm`, `mtm_alias`, `group_mtm`, `kode_produk`, `nama_produk`, `quantity` (Actual Sales Qty per Periode).
3. **Master Produk (`Master produk.xlsx`)**:
   - Atribut: `Principal_product_code`, `Principal_product_code_lama`, `Product_code`, `Product_code_lama`, `Product_name`, `GB`, `Harga Dasar` (Margin Profit per unit), `KATEGORI`, `Min DOI`, `Max DOI`.

---

## 3. Workflow & Logika Pengolahan Data

### A. Segmentasi Pareto (80/20 Rule) Berbasis Per GB MTM & Per GB Non-MTM
- **Fungsi Actual Sales YTD**: Penjualan Aktual YTD (**Actual Sales Qty YTD × Harga Dasar**) **hanya digunakan khusus untuk menentukan klasifikasi Pareto**.
- **Logika Pengelompokan**:
  - SKU dikelompokkan berdasarkan **`GB`** dan **`MTM FLAG`** (contoh: GB 1 - MTM, GB 1 - Non-MTM, GB 2 - MTM, GB 2 - Non-MTM, dst.).
  - Di dalam setiap kelompok `(GB, MTM)`, SKU diurutkan secara desending berdasarkan Nilai Penjualan YTD.
  - SKU dengan persentase kumulatif nilai penjualan $\le 80\%$ di dalam kelompok GB-nya diklasifikasikan sebagai **Pareto**.
  - SKU sisanya ($> 80\%$) diklasifikasikan sebagai **Non-Pareto**.

### B. Akurasi Per Periode (RF Qty vs Actual Sales Qty Per Periode)
- Perhitungan akurasi dilakukan secara **per periode bulanan** (contoh: 2026-01, 2026-02, 2026-03, dst.):
  1. **MAPE Per Periode**:
     $$\text{MAPE}_{\text{periode}} = \frac{|\text{Actual Qty}_{\text{periode}} - \text{RF Qty}_{\text{periode}}|}{\text{Actual Qty}_{\text{periode}}} \times 100\%$$
  2. **WAFE Margin Profit Rp Per Periode**:
     $$\text{WAFE}_{\text{periode}} = \frac{\sum (|\text{Actual Qty}_{\text{periode}} - \text{RF Qty}_{\text{periode}}| \times \text{Harga Dasar})}{\sum (\text{RF Qty}_{\text{periode}} \times \text{Harga Dasar})} \times 100\%$$
     $$\text{WAFE Accuracy}_{\text{periode}} = 100\% - \text{WAFE}_{\text{periode}}$$
  3. **Total Bias Qty & Value at Risk (Rp) Per Periode**:
     - $\text{Bias Qty}_{\text{periode}} = \text{RF Qty}_{\text{periode}} - \text{Actual Qty}_{\text{periode}}$
     - $\text{Value at Risk (Rp)}_{\text{periode}} = \sum (|\text{Actual Qty}_{\text{periode}} - \text{RF Qty}_{\text{periode}}| \times \text{Harga Dasar})$

---

## 4. Output & Fitur Antarmuka Dashboard

1. **Filter Periode Global**: Filter dropdown periode (Semua Periode / 2026-01 / 2026-02 / ...) untuk melihat performa akurasi per bulan.
2. **Filter Group Barang (GB)**: Filter per GB untuk analisis per kategori produk.
3. **Executive Summary Cards**: Total SKUs, WAFE Accuracy %, MAPE Accuracy %, Total Bias Qty, & Value at Risk (Rp).
4. **Matriks Pareto 4-Kuadran**: Distribusi akurasi per kuadran (MTM Pareto, MTM Non-Pareto, Non-MTM Pareto, Non-MTM Non-Pareto).
5. **Grafik Tren Bulanan**: Pergerakan WAFE Accuracy (%) per periode.
6. **Tabel Deep-Dive SKU**: Detail per SKU dengan pencarian instan, filter GB, filter Kuadran, dan rincian per periode.
