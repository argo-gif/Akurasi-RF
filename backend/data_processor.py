import zipfile
import xml.etree.ElementTree as ET
import re
import os
import json
from pathlib import Path
from datetime import datetime

def read_xlsx_fast(file_path):
    """
    Membaca file .xlsx dengan cepat menggunakan regex parsing bawaan Python.
    Mengembalikan list of dicts berbasis header baris pertama.
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File tidak ditemukan: {file_path}")

    with zipfile.ZipFile(file_path, 'r') as z:
        shared_strings = []
        if 'xl/sharedStrings.xml' in z.namelist():
            ss_tree = ET.fromstring(z.read('xl/sharedStrings.xml'))
            ns = {'main': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
            for si in ss_tree.findall('.//main:si', ns):
                t_texts = [t.text for t in si.findall('.//main:t', ns) if t.text]
                shared_strings.append(''.join(t_texts))

        sheet_filename = 'xl/worksheets/sheet1.xml'
        xml_content = z.read(sheet_filename).decode('utf-8')

        col_cell_pattern = re.compile(r'<c r="([A-Z]+)\d+"([^>]*)><v>(.*?)</v></c>')
        col_map = {}

        first_row_match = re.search(r'<row r="1".*?>(.*?)</row>', xml_content)
        if first_row_match:
            for col_let, attrs, val in col_cell_pattern.findall(first_row_match.group(1)):
                cell_t = 's' if 't="s"' in attrs else None
                col_name = shared_strings[int(val)] if cell_t == 's' else val
                col_map[col_let] = str(col_name).strip()

        row_pattern = re.compile(r'<row r="\d+".*?>(.*?)</row>')
        row_matches = row_pattern.findall(xml_content)

        result = []
        for row_str in row_matches[1:]:
            row_dict = {}
            for col_let, attrs, val in col_cell_pattern.findall(row_str):
                col_name = col_map.get(col_let)
                if col_name:
                    if 't="s"' in attrs:
                        try:
                            idx = int(val)
                            row_dict[col_name] = shared_strings[idx] if idx < len(shared_strings) else val
                        except ValueError:
                            row_dict[col_name] = val
                    else:
                        try:
                            if '.' in val or 'e' in val.lower():
                                row_dict[col_name] = float(val)
                            else:
                                row_dict[col_name] = int(val)
                        except ValueError:
                            row_dict[col_name] = val
            if row_dict:
                result.append(row_dict)

        return result


def parse_periode(val):
    if val is None or val == "":
        return ""
    if isinstance(val, (int, float)):
        try:
            return datetime.fromordinal(datetime(1899, 12, 30).toordinal() + int(val)).strftime('%Y-%m')
        except Exception:
            return str(val)
    val_str = str(val).strip()
    if len(val_str) >= 7 and val_str[:4].isdigit():
        return val_str[:7]
    return val_str


def process_demand_data(base_dir=".", force_reprocess=False):
    """
    Mengolah data Master Produk, Data Sales, dan Data RF.
    Aturan:
    1. Actual Sales YTD HANYA digunakan untuk menentukan Pareto.
    2. Pareto dibuat berdasar PER GB MTM dan PER GB Non-MTM.
    3. Akurasi (MAPE & WAFE Margin Profit Rp) dihitung per Periode RF vs Actual Sales per Periode.
    """
    cache_file = os.path.join(base_dir, "data_cache.json")
    if not force_reprocess and os.path.exists(cache_file):
        try:
            with open(cache_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass

    rf_file = os.path.join(base_dir, "Data RF.xlsx")
    sales_file = os.path.join(base_dir, "Data sales.xlsx")
    master_file = os.path.join(base_dir, "Master produk.xlsx")

    # 1. Load Data
    master_rows = read_xlsx_fast(master_file)
    sales_rows = read_xlsx_fast(sales_file)
    rf_rows = read_xlsx_fast(rf_file)

    # 2. Master Mapping & Info SKU
    code_to_active = {}
    active_master_info = {}

    for row in master_rows:
        active_code = str(row.get("Product_code") or "").strip()
        old_code = str(row.get("Product_code_lama") or "").strip()
        principal_active = str(row.get("Principal_product_code") or "").strip()
        principal_old = str(row.get("Principal_product_code_lama") or "").strip()
        base_price = row.get("Harga Dasar") or 0.0
        try:
            base_price = float(base_price)
        except (ValueError, TypeError):
            base_price = 0.0

        product_name = str(row.get("Product_name") or "").strip()
        gb = str(row.get("GB") or "").strip() or "GB OTHER"
        kategori = str(row.get("KATEGORI") or "").strip()
        keterangan_produk = str(row.get("Keterangan produk") or row.get("Keterangan") or "").strip()

        if active_code:
            code_to_active[active_code] = active_code
            active_master_info[active_code] = {
                "product_code": active_code,
                "product_name": product_name,
                "base_price": base_price,
                "gb": gb,
                "kategori": kategori,
                "keterangan_produk": keterangan_produk,
                "old_codes": set()
            }
            if old_code and old_code != active_code:
                code_to_active[old_code] = active_code
                active_master_info[active_code]["old_codes"].add(old_code)

        if principal_active and active_code:
            code_to_active[principal_active] = active_code
        if principal_old and active_code:
            code_to_active[principal_old] = active_code

    # 3. Aggregate Actual Sales YTD & Monthly & Sales MTM Status
    actual_sales_ytd_qty = {} # active_code -> float
    sales_monthly = {} # (active_code, periode) -> float
    sales_mtm_y_monthly = {} # (active_code, periode) -> float
    sales_mtm_n_monthly = {} # (active_code, periode) -> float
    sales_mtm_y_qty = {} # active_code -> float (MTM Qty)
    sales_mtm_n_qty = {} # active_code -> float (NON MTM Qty)
    all_periods = set()

    for row in sales_rows:
        raw_code = str(row.get("kode_produk") or "").strip()
        active_code = code_to_active.get(raw_code, raw_code)
        qty = row.get("quantity") or 0.0
        try:
            qty = float(qty)
        except (ValueError, TypeError):
            qty = 0.0

        periode = parse_periode(row.get("Periode") or row.get("periode"))

        info = active_master_info.get(active_code, {})
        gb_prod = str(info.get("gb") or "").strip().upper()

        raw_mtm_s = str(row.get("mtm") or row.get("MTM") or row.get("group_mtm") or "").strip().upper()
        if gb_prod in ["GB ET", "GB ETH", "ETH", "ET"]:
            sales_mtm_n_qty[active_code] = sales_mtm_n_qty.get(active_code, 0.0) + qty
            if periode:
                sales_mtm_n_monthly[(active_code, periode)] = sales_mtm_n_monthly.get((active_code, periode), 0.0) + qty
        elif "NON" in raw_mtm_s or raw_mtm_s in ["T", "N", "NO", "TIDAK"]:
            sales_mtm_n_qty[active_code] = sales_mtm_n_qty.get(active_code, 0.0) + qty
            if periode:
                sales_mtm_n_monthly[(active_code, periode)] = sales_mtm_n_monthly.get((active_code, periode), 0.0) + qty
        elif "MTM" in raw_mtm_s or raw_mtm_s in ["Y", "YA", "YES"]:
            sales_mtm_y_qty[active_code] = sales_mtm_y_qty.get(active_code, 0.0) + qty
            if periode:
                sales_mtm_y_monthly[(active_code, periode)] = sales_mtm_y_monthly.get((active_code, periode), 0.0) + qty

        actual_sales_ytd_qty[active_code] = actual_sales_ytd_qty.get(active_code, 0.0) + qty
        if periode:
            all_periods.add(periode)
            key = (active_code, periode)
            sales_monthly[key] = sales_monthly.get(key, 0.0) + qty

    # 4. Aggregate Rolling Forecast (RF) Monthly & YTD
    rf_qty_ytd_map = {} # active_code -> float
    rf_mtm_y_qty = {} # active_code -> float
    rf_mtm_n_qty = {} # active_code -> float
    rf_monthly = {} # (active_code, periode) -> float
    rf_mtm_y_monthly = {} # (active_code, periode) -> float
    rf_mtm_n_monthly = {} # (active_code, periode) -> float
    rf_gb_map = {} # active_code -> GB string from RF if master missing

    for row in rf_rows:
        raw_code = str(row.get("KODE_PRODUK") or "").strip()
        active_code = code_to_active.get(raw_code, raw_code)
        rf_val = row.get("RF") or 0.0
        try:
            rf_val = float(rf_val)
        except (ValueError, TypeError):
            rf_val = 0.0

        periode = parse_periode(row.get("Periode") or row.get("periode"))
        gb_rf = str(row.get("GB") or "").strip()

        raw_mtm = str(row.get("MTM FLAG") or "N").strip().upper()
        if raw_mtm in ["Y", "YA", "YES", "MTM"] and "NON" not in raw_mtm:
            rf_mtm_y_qty[active_code] = rf_mtm_y_qty.get(active_code, 0.0) + rf_val
            if periode:
                rf_mtm_y_monthly[(active_code, periode)] = rf_mtm_y_monthly.get((active_code, periode), 0.0) + rf_val
        else:
            rf_mtm_n_qty[active_code] = rf_mtm_n_qty.get(active_code, 0.0) + rf_val
            if periode:
                rf_mtm_n_monthly[(active_code, periode)] = rf_mtm_n_monthly.get((active_code, periode), 0.0) + rf_val

        if gb_rf:
            rf_gb_map[active_code] = gb_rf

        rf_qty_ytd_map[active_code] = rf_qty_ytd_map.get(active_code, 0.0) + rf_val
        if periode:
            all_periods.add(periode)
            key = (active_code, periode)
            rf_monthly[key] = rf_monthly.get(key, 0.0) + rf_val

    # Filter: Hanya memproses SKU yang terdaftar di Master Produk
    all_skus = set(active_master_info.keys())

    sku_records = []
    for sku in all_skus:
        info = active_master_info.get(sku, {})
        ket_prod = str(info.get("keterangan_produk") or "").strip().lower()
        rf_ytd_qty = rf_qty_ytd_map.get(sku, 0.0)

        # Aturan Eliminasi Produk:
        # 1. Festive: tidak perlu dihitung akurasinya
        # 2. Streamline tanpa forecast (rf_ytd_qty == 0): tidak perlu dihitung akurasinya
        if "festive" in ket_prod:
            continue
        if "streamline" in ket_prod and rf_ytd_qty == 0:
            continue
        info = active_master_info.get(sku, {})
        prod_name = info.get("product_name", f"SKU {sku}")
        base_price = info.get("base_price", 0.0)
        gb = info.get("gb") or rf_gb_map.get(sku) or "GB OTHER"
        old_codes_str = ", ".join(info.get("old_codes", []))

        act_ytd_qty = actual_sales_ytd_qty.get(sku, 0.0)
        rf_ytd_qty = rf_qty_ytd_map.get(sku, 0.0)
        
        s_y = sales_mtm_y_qty.get(sku, 0.0)
        s_n = sales_mtm_n_qty.get(sku, 0.0)
        rf_y = rf_mtm_y_qty.get(sku, 0.0)
        rf_n = rf_mtm_n_qty.get(sku, 0.0)

        gb_upper = str(gb or "").strip().upper()
        if gb_upper in ["GB ET", "GB ETH", "ETH", "ET"]:
            s_n = s_n + s_y
            s_y = 0.0
            rf_n = rf_n + rf_y
            rf_y = 0.0
            mtm_flag = "N"
        elif s_y > 0 or s_n > 0:
            mtm_flag = "Y" if s_y > s_n else "N"
        else:
            mtm_flag = "Y" if rf_y > rf_n else "N"

        act_ytd_val = act_ytd_qty * base_price
        rf_ytd_val = rf_ytd_qty * base_price

        sku_records.append({
            "product_code": sku,
            "old_code": old_codes_str,
            "product_name": prod_name,
            "gb": gb,
            "mtm_flag": mtm_flag,
            "base_price": base_price,
            "actual_ytd_qty": act_ytd_qty,
            "rf_ytd_qty": rf_ytd_qty,
            "actual_ytd_val": act_ytd_val,
            "rf_ytd_val": rf_ytd_val,
            "act_mtm_y_val": s_y * base_price,
            "act_mtm_n_val": s_n * base_price,
            "rf_mtm_y_val": rf_y * base_price,
            "rf_mtm_n_val": rf_n * base_price,
            "periods": {} # periode -> {act_qty, rf_qty, error_qty, act_val, rf_val, error_val, mape}
        })

    # 5. ATURAN PARETO A: NASIONAL GLOBAL (Dihitung 4-Kuadran MTM vs Non-MTM & Total Pareto)
    # A1. Overall National Total Sales Pareto
    sku_records_sorted = sorted(sku_records, key=lambda x: x["actual_ytd_val"], reverse=True)
    total_national_sales_val = sum(s["actual_ytd_val"] for s in sku_records_sorted)
    running_national_val = 0.0

    for idx, s in enumerate(sku_records_sorted):
        running_national_val += s["actual_ytd_val"]
        ratio = (running_national_val / total_national_sales_val) if total_national_sales_val > 0 else 1.0

        is_pareto = ratio <= 0.80 or (idx == 0 and total_national_sales_val > 0)
        pareto_label = "Pareto" if is_pareto else "Non-Pareto"

        s["pareto_national"] = pareto_label
        s["pareto_national_total"] = pareto_label
        s["quadrant_national"] = f"National - {pareto_label}"

    # A2. National MTM Pareto
    national_mtm_skus = [s for s in sku_records if s["act_mtm_y_val"] > 0 or s["rf_mtm_y_val"] > 0]
    national_mtm_skus.sort(key=lambda x: x["act_mtm_y_val"], reverse=True)
    tot_nat_mtm_val = sum(s["act_mtm_y_val"] for s in national_mtm_skus)
    run_nat_mtm = 0.0
    for idx, s in enumerate(national_mtm_skus):
        run_nat_mtm += s["act_mtm_y_val"]
        ratio = (run_nat_mtm / tot_nat_mtm_val) if tot_nat_mtm_val > 0 else 1.0
        is_pareto = ratio <= 0.80 or (idx == 0 and tot_nat_mtm_val > 0)
        pareto_label = "Pareto" if is_pareto else "Non-Pareto"
        s["quadrant_national_mtm"] = f"MTM - {pareto_label}"
        s["pareto_national_mtm"] = pareto_label

    # A3. National Non-MTM Pareto
    national_non_mtm_skus = [s for s in sku_records if s["act_mtm_n_val"] > 0 or s["rf_mtm_n_val"] > 0]
    national_non_mtm_skus.sort(key=lambda x: x["act_mtm_n_val"], reverse=True)
    tot_nat_non_mtm_val = sum(s["act_mtm_n_val"] for s in national_non_mtm_skus)
    run_nat_non_mtm = 0.0
    for idx, s in enumerate(national_non_mtm_skus):
        run_nat_non_mtm += s["act_mtm_n_val"]
        ratio = (run_nat_non_mtm / tot_nat_non_mtm_val) if tot_nat_non_mtm_val > 0 else 1.0
        is_pareto = ratio <= 0.80 or (idx == 0 and tot_nat_non_mtm_val > 0)
        pareto_label = "Pareto" if is_pareto else "Non-Pareto"
        s["quadrant_national_non_mtm"] = f"Non-MTM - {pareto_label}"
        s["pareto_national_non_mtm"] = pareto_label

    # 5. ATURAN PARETO B: PER GROUP BARANG (GB) (Diurutkan per GB MTM vs Non-MTM secara Row-Level Sales)
    gb_groups = {}
    for s in sku_records:
        gb_name = s["gb"]
        if gb_name not in gb_groups:
            gb_groups[gb_name] = []
        gb_groups[gb_name].append(s)

    for gb_name, group_skus in gb_groups.items():
        # A. MTM Pareto per GB (SKU yang memiliki sales MTM atau forecast MTM)
        mtm_skus = [s for s in group_skus if s["act_mtm_y_val"] > 0 or s["rf_mtm_y_val"] > 0]
        mtm_skus.sort(key=lambda x: x["act_mtm_y_val"], reverse=True)
        total_mtm_val = sum(s["act_mtm_y_val"] for s in mtm_skus)
        running_mtm = 0.0

        for idx, s in enumerate(mtm_skus):
            running_mtm += s["act_mtm_y_val"]
            ratio = (running_mtm / total_mtm_val) if total_mtm_val > 0 else 1.0
            is_pareto = ratio <= 0.80 or (idx == 0 and total_mtm_val > 0)
            pareto_label = "Pareto" if is_pareto else "Non-Pareto"
            s["quadrant_gb_mtm"] = f"MTM - {pareto_label}"
            s["pareto_gb_mtm"] = pareto_label

        # B. Non-MTM Pareto per GB (SKU yang memiliki sales Non-MTM atau forecast Non-MTM)
        non_mtm_skus = [s for s in group_skus if s["act_mtm_n_val"] > 0 or s["rf_mtm_n_val"] > 0]
        non_mtm_skus.sort(key=lambda x: x["act_mtm_n_val"], reverse=True)
        total_non_mtm_val = sum(s["act_mtm_n_val"] for s in non_mtm_skus)
        running_non_mtm = 0.0

        for idx, s in enumerate(non_mtm_skus):
            running_non_mtm += s["act_mtm_n_val"]
            ratio = (running_non_mtm / total_non_mtm_val) if total_non_mtm_val > 0 else 1.0
            is_pareto = ratio <= 0.80 or (idx == 0 and total_non_mtm_val > 0)
            pareto_label = "Pareto" if is_pareto else "Non-Pareto"
            s["quadrant_gb_non_mtm"] = f"Non-MTM - {pareto_label}"
            s["pareto_gb_non_mtm"] = pareto_label

        for s in group_skus:
            if s["mtm_flag"] == "Y":
                s["quadrant_gb"] = s.get("quadrant_gb_mtm", "MTM - Non-Pareto")
                s["pareto_gb"] = s.get("pareto_gb_mtm", "Non-Pareto")
            else:
                s["quadrant_gb"] = s.get("quadrant_gb_non_mtm", "Non-MTM - Non-Pareto")
                s["pareto_gb"] = s.get("pareto_gb_non_mtm", "Non-Pareto")

            s["quadrant"] = s["quadrant_national"]
            s["pareto_class"] = s["pareto_national"]

        # C. Overall Total Sales Pareto per GB (Tanpa Pemisahan Saluran)
        group_skus_sorted = sorted(group_skus, key=lambda x: x["actual_ytd_val"], reverse=True)
        tot_gb_val = sum(s["actual_ytd_val"] for s in group_skus_sorted)
        run_gb_val = 0.0
        for idx, s in enumerate(group_skus_sorted):
            run_gb_val += s["actual_ytd_val"]
            ratio = (run_gb_val / tot_gb_val) if tot_gb_val > 0 else 1.0
            is_pareto = ratio <= 0.80 or (idx == 0 and tot_gb_val > 0)
            s["pareto_gb_total"] = "Pareto" if is_pareto else "Non-Pareto"

    # 6. HITUNG AKURASI PER PERIODE (RF Qty per Periode vs Actual Sales per Periode)
    sorted_periods = sorted(list(all_periods))

    # Populate monthly breakdown for each SKU
    for s in sku_records:
        sku = s["product_code"]
        bp = s["base_price"]

        sku_error_val_sum = 0.0
        sku_rf_val_sum = 0.0
        sku_act_qty_sum = 0.0
        sku_rf_qty_sum = 0.0
        sku_mapes = []

        for p in sorted_periods:
            act_p_qty = sales_monthly.get((sku, p), 0.0)
            rf_p_qty = rf_monthly.get((sku, p), 0.0)
            err_p_qty = abs(act_p_qty - rf_p_qty)

            act_p_val = act_p_qty * bp
            rf_p_val = rf_p_qty * bp
            err_p_val = err_p_qty * bp

            sku_error_val_sum += err_p_val
            sku_rf_val_sum += rf_p_val
            sku_act_qty_sum += act_p_qty
            sku_rf_qty_sum += rf_p_qty

            mape_p = ((err_p_qty / act_p_qty) * 100.0) if act_p_qty > 0 else None
            if mape_p is not None:
                sku_mapes.append(mape_p)

            act_p_mtm_y_qty = sales_mtm_y_monthly.get((sku, p), 0.0)
            act_p_mtm_n_qty = sales_mtm_n_monthly.get((sku, p), 0.0)
            rf_p_mtm_y_qty = rf_mtm_y_monthly.get((sku, p), 0.0)
            rf_p_mtm_n_qty = rf_mtm_n_monthly.get((sku, p), 0.0)

            act_p_mtm_y_val = act_p_mtm_y_qty * bp
            act_p_mtm_n_val = act_p_mtm_n_qty * bp
            rf_p_mtm_y_val = rf_p_mtm_y_qty * bp
            rf_p_mtm_n_val = rf_p_mtm_n_qty * bp

            err_p_mtm_y_val = abs(act_p_mtm_y_qty - rf_p_mtm_y_qty) * bp
            err_p_mtm_n_val = abs(act_p_mtm_n_qty - rf_p_mtm_n_qty) * bp

            s["periods"][p] = {
                "act_qty": act_p_qty,
                "rf_qty": rf_p_qty,
                "error_qty": err_p_qty,
                "act_val": act_p_val,
                "rf_val": rf_p_val,
                "error_val": err_p_val,
                "mape": round(mape_p, 2) if mape_p is not None else None,
                "act_mtm_y_val": act_p_mtm_y_val,
                "act_mtm_n_val": act_p_mtm_n_val,
                "rf_mtm_y_val": rf_p_mtm_y_val,
                "rf_mtm_n_val": rf_p_mtm_n_val,
                "error_mtm_y_val": err_p_mtm_y_val,
                "error_mtm_n_val": err_p_mtm_n_val
            }

        s["total_actual_qty"] = sku_act_qty_sum
        s["total_rf_qty"] = sku_rf_qty_sum
        s["total_error_qty"] = abs(sku_act_qty_sum - sku_rf_qty_sum)
        s["total_error_val"] = sku_error_val_sum
        s["total_rf_val"] = sku_rf_val_sum
        s["overall_mape"] = round(sum(sku_mapes)/len(sku_mapes), 2) if sku_mapes else None

    # 7. METRIK METRIK EXECUTIVE & PERIODE AGGREGATION
    # Helper to calculate summary metrics for a given subset of SKUs and optional period filter
    def compute_summary_metrics(skus_subset, period_filter=None):
        rf_val_total = 0.0
        act_val_total = 0.0
        err_val_total = 0.0
        bias_qty_total = 0.0
        mape_list = []
        valid_sku_count = 0

        for s in skus_subset:
            if period_filter:
                p_data = s["periods"].get(period_filter, {})
                rf_q = p_data.get("rf_qty", 0.0)
                if rf_q == 0:
                    continue

                rf_v = p_data.get("rf_val", 0.0)
                act_v = p_data.get("act_val", 0.0)
                err_v = p_data.get("error_val", 0.0)
                bias_q = rf_q - p_data.get("act_qty", 0.0)
                mape_v = p_data.get("mape")
            else:
                rf_q = s["total_rf_qty"]
                if rf_q == 0:
                    continue

                rf_v = s["total_rf_val"]
                act_v = s.get("actual_ytd_val", 0.0)
                err_v = s["total_error_val"]
                bias_q = rf_q - s["total_actual_qty"]
                mape_v = s["overall_mape"]

            valid_sku_count += 1
            rf_val_total += rf_v
            act_val_total += act_v
            err_val_total += err_v
            bias_qty_total += bias_q
            if mape_v is not None:
                sku_acc = max(0.0, min(100.0, 100.0 - mape_v))
                mape_list.append(sku_acc)

        denom_val = max(rf_val_total, act_val_total)
        if denom_val == 0 or valid_sku_count == 0:
            wafe_acc = None
            mape_acc = None
        else:
            wafe = (err_val_total / denom_val * 100.0)
            raw_wafe_acc = 100.0 - wafe
            wafe_acc = round(max(0.0, min(100.0, raw_wafe_acc)), 2)
            mape_acc = round(sum(mape_list) / len(mape_list), 2) if mape_list else None

        return {
            "total_skus": valid_sku_count,
            "mape_accuracy": mape_acc,
            "wafe_accuracy": wafe_acc,
            "total_bias_qty": round(bias_qty_total, 2),
            "value_at_risk_rp": round(err_val_total, 2)
        }

    overall_summary = compute_summary_metrics(sku_records)

    # Quadrant Matrix Summary
    quadrants_summary = {}
    for quad_name in ["MTM - Pareto", "MTM - Non-Pareto", "Non-MTM - Pareto", "Non-MTM - Non-Pareto"]:
        q_skus = [s for s in sku_records if s.get("quadrant") == quad_name]
        q_metrics = compute_summary_metrics(q_skus)
        
        q_act_qty = sum(s["total_actual_qty"] for s in q_skus if s["total_rf_qty"] > 0)
        q_rf_qty = sum(s["total_rf_qty"] for s in q_skus if s["total_rf_qty"] > 0)
        
        quadrants_summary[quad_name] = {
            "sku_count": q_metrics["total_skus"],
            "actual_qty": round(q_act_qty, 2),
            "rf_qty": round(q_rf_qty, 2),
            "rf_val_rp": round(q_metrics["value_at_risk_rp"], 2),
            "error_val_rp": round(q_metrics["value_at_risk_rp"], 2),
            "wafe_accuracy": q_metrics["wafe_accuracy"],
            "mape_accuracy": q_metrics["mape_accuracy"]
        }

    # Monthly Trend Array (Hanya periode yang memiliki data Rolling Forecast)
    trend_data = []
    valid_periods = []
    for p in sorted_periods:
        p_rf_val = sum(s["periods"].get(p, {}).get("rf_val", 0.0) for s in sku_records)
        p_act_val = sum(s["periods"].get(p, {}).get("act_val", 0.0) for s in sku_records)

        # Abaikan periode tanpa Rolling Forecast (seperti 2025 yang RF-nya 0)
        if p_rf_val > 0:
            p_metrics = compute_summary_metrics(sku_records, period_filter=p)
            valid_periods.append(str(p))
            trend_data.append({
                "periode": str(p),
                "wafe_accuracy": p_metrics["wafe_accuracy"],
                "mape_accuracy": p_metrics["mape_accuracy"],
                "actual_val_rp": round(p_act_val, 2),
                "rf_val_rp": round(p_rf_val, 2),
                "error_val_rp": p_metrics["value_at_risk_rp"]
            })

    # Available GB list for filters
    all_gbs = sorted(list(set(s["gb"] for s in sku_records)))

    result_payload = {
        "summary": overall_summary,
        "matrix": quadrants_summary,
        "trend": trend_data,
        "periods": valid_periods if valid_periods else sorted_periods,
        "gbs": all_gbs,
        "skus": sku_records
    }

    try:
        with open(cache_file, "w", encoding="utf-8") as f:
            json.dump(result_payload, f, indent=2)
    except Exception as e:
        print(f"Warning: Failed to write cache file: {e}")

    return result_payload


if __name__ == "__main__":
    import time
    print("Testing updated data_processor.py...")
    t0 = time.time()
    res = process_demand_data(".", force_reprocess=True)
    t_elapsed = time.time() - t0
    print(f"Data processed successfully in {t_elapsed:.2f} seconds!")
    print("Summary:", json.dumps(res["summary"], indent=2))
    print("Matrix:", json.dumps(res["matrix"], indent=2))
    print("Periods count:", len(res["periods"]))
    print("GBs:", res["gbs"])
