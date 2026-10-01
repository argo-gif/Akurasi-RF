# Backend Data Processor Instruction (`data_processor.py`)

## 1. Deskripsi Module
`data_processor.py` bertanggung jawab untuk membaca, mentransformasi, memetakan master data, mengklasifikasikan produk (Pareto 80/20 MTM & Non-MTM), dan menghitung metrik performa demand planning (MAPE, WAFE berbasis Margin Profit Rp, Bias, dan Value at Risk).

---

## 2. File Input & Sumber Data
- `Data RF.xlsx`: Berisi Rolling Forecast Qty per SKU dan atribut `MTM FLAG`.
- `Data sales.xlsx`: Berisi Penjualan Aktual (Actual Sales Qty) YTD 2026.
- `Master produk.xlsx`: Berisi pemetaan kode produk lama vs baru, Harga Dasar (Margin Profit per unit), GB, dan Kategori.

---

## 3. Tahapan Pengolahan Data

### A. Mapping & Aggregation SKU Level
1. **Master Mapping**:
   - Petakan `Product_code_lama` ke `Product_code` aktif.
   - Ambil `Harga Dasar` (Base Price) per `Product_code`.
2. **Agregasi Actual Sales YTD 2026**:
   - Jumlahkan `quantity` (Actual Qty) per `kode_produk` untuk semua periode YTD 2026.
3. **Agregasi Rolling Forecast (RF)**:
   - Jumlahkan `RF` (Forecast Qty) per `KODE_PRODUK` dan pertahankan `MTM FLAG`.

### B. Segmentasi Pareto (80/20 Rule)
- Hitung Nilai Penjualan Aktual (Actual Revenue = Actual Qty × Harga Dasar).
- Urutkan SKU secara desending berdasarkan Nilai Penjualan Aktual.
- Hitung persentase kumulatif nilai penjualan secara terpisah untuk:
  - Kelompok **MTM** (`MTM FLAG` == 'Y')
  - Kelompok **Non-MTM** (`MTM FLAG` == 'N')
- Klasifikasi SKU:
  - Kumulatif <= 80%: **Pareto** (Top 80% Value)
  - Kumulatif > 80%: **Non-Pareto** (Bottom 20% Value)

---

## 4. Metrik & Rumusan Akurasi

### A. MAPE (Mean Absolute Percentage Error)
$$\text{Error Qty} = |\text{Actual Qty} - \text{RF Qty}|$$
$$\text{MAPE per SKU} = \frac{\text{Error Qty}}{\text{Actual Qty}} \quad (\text{jika Actual Qty} > 0)$$
$$\text{MAPE Overall} = \text{Rata-rata MAPE per SKU} \times 100\%$$
$$\text{MAPE Accuracy} = 100\% - \text{MAPE Overall}$$

### B. WAFE (Weighted Absolute Percentage Error berbasis Margin Profit Rp)
$$\text{Margin Profit RF (Rp)} = \text{RF Qty} \times \text{Harga Dasar}$$
$$\text{Absolute Error Value (Rp)} = \text{Error Qty} \times \text{Harga Dasar}$$
$$\text{WAFE} = \frac{\sum \text{Absolute Error Value (Rp)}}{\sum \text{Margin Profit RF (Rp)}} \times 100\%$$
$$\text{WAFE Accuracy} = 100\% - \text{WAFE}$$

### C. Bias & Value at Risk
$$\text{Bias Qty} = \text{RF Qty} - \text{Actual Qty} \quad (\text{Positive} = \text{Over-forecast}, \text{Negative} = \text{Under-forecast})$$
$$\text{Value at Risk (Rp)} = \sum (\text{Error Qty} \times \text{Harga Dasar})$$

---

## 5. Output Data Payload (JSON API Friendly)
Function `process_demand_data()` mengembalikan struktur dictionary:
- `summary`: High-level KPI (MAPE Accuracy, WAFE Accuracy, Total Bias Qty, Total Value at Risk Rp).
- `matrix`: Ringkasan akurasi untuk 4 kuadran Pareto (MTM Pareto, MTM Non-Pareto, Non-MTM Pareto, Non-MTM Non-Pareto).
- `skus`: List per SKU berisi detail Actual, RF, Error, Harga Dasar, WAFE, MAPE, Kuadran Pareto.
- `trend`: Tren akurasi per periode bulanan.
