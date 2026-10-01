# Backend API Service Instruction (`main.py`)

## 1. Deskripsi Module
`main.py` adalah HTTP REST API server untuk Demand Planning & Forecast Accuracy Dashboard. Service ini menyajikan data hasil pengolahan `data_processor.py` ke antarmuka frontend melalui format JSON.

---

## 2. Fitur & Atribut Utama Server
- **CORS Support**: Mengirimkan header `Access-Control-Allow-Origin: *` agar frontend dapat diakses secara lokal maupun via Vercel tanpa isu cross-origin.
- **Auto Data Cache**: Memanggil `data_processor.process_demand_data()` saat server dimulai untuk pengisian cache instan.
- **Port Server**: Default running pada port `8050` (dapat disesuaikan via variabel environment `PORT`).

---

## 3. Daftar Endpoint API

### A. Health Check
- **Endpoint**: `GET /` atau `GET /api/health`
- **Response**: `{"status": "ok", "message": "Demand Planning API Service is running"}`

### B. Executive Summary
- **Endpoint**: `GET /api/summary`
- **Response**:
  ```json
  {
    "status": "success",
    "data": {
      "total_skus": 520,
      "mape_accuracy": 33.71,
      "wafe_accuracy": 0.0,
      "total_bias_qty": -528303633.0,
      "value_at_risk_rp": 1437397386822.95
    }
  }
  ```

### C. Matrix 4-Kuadran Pareto
- **Endpoint**: `GET /api/matrix`
- **Response**:
  Ringkasan data untuk 4 kuadran: `MTM - Pareto`, `MTM - Non-Pareto`, `Non-MTM - Pareto`, `Non-MTM - Non-Pareto`.

### D. SKU Deep-Dive Level Table
- **Endpoint**: `GET /api/skus`
- **Query Parameters**:
  - `quadrant`: Filter berdasarkan kuadran (contoh: `MTM - Pareto`)
  - `search`: Pencarian SKU (kode atau nama produk)
  - `limit`: Batas baris data (default: `100`)
- **Response**: List detail per SKU (Actual Qty, RF Qty, Error Qty, Base Price, Error Margin Rp, MAPE, Kuadran).

### E. Monthly Trend
- **Endpoint**: `GET /api/trend`
- **Response**: Data tren bulanan WAFE accuracy & error value Rp.

### F. Reprocess Data Trigger
- **Endpoint**: `POST /api/reprocess` atau `GET /api/reprocess`
- **Response**: Memaksa hitung ulang data Excel dari scratch dan memperbarui `data_cache.json`.
