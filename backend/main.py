import sys
import os
import json
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import parse_qs, urlparse

# Pastikan folder backend masuk ke sys.path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from data_processor import process_demand_data

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_PAYLOAD = None

def get_data(force_reprocess=False):
    global DATA_PAYLOAD
    cache_file = os.path.join(BASE_DIR, "data_cache.json")
    if force_reprocess:
        DATA_PAYLOAD = process_demand_data(base_dir=BASE_DIR, force_reprocess=True)
    elif os.path.exists(cache_file):
        try:
            with open(cache_file, "r", encoding="utf-8") as f:
                DATA_PAYLOAD = json.load(f)
        except Exception:
            DATA_PAYLOAD = process_demand_data(base_dir=BASE_DIR, force_reprocess=False)
    else:
        DATA_PAYLOAD = process_demand_data(base_dir=BASE_DIR, force_reprocess=False)
    return DATA_PAYLOAD


def extract_sku_period_data(s, selected_period):
    """
    Helper untuk mengekstrak data periode untuk SKU s.
    - jika selected_period None/kosong: kembalikan total YTD seluruh periode.
    - jika selected_period 4 digit (cth: '2025' atau '2026'): akumulasikan seluruh bulan di tahun tersebut.
    - jika selected_period spesifik (cth: '2025-01'): kembalikan data bulan tersebut.
    """
    if not selected_period:
        rf_q = s.get("total_rf_qty", 0.0)
        if rf_q == 0 and s.get("total_actual_qty", 0.0) == 0:
            return None
        return {
            "rf_qty": rf_q,
            "act_qty": s.get("total_actual_qty", 0.0),
            "rf_val": s.get("total_rf_val", 0.0),
            "act_val": s.get("actual_ytd_val", 0.0),
            "error_val": s.get("total_error_val", 0.0),
            "mape": s.get("overall_mape"),
            "rf_mtm_y_val": s.get("rf_mtm_y_val", 0.0),
            "act_mtm_y_val": s.get("act_mtm_y_val", 0.0),
            "error_mtm_y_val": abs(s.get("act_mtm_y_val", 0.0) - s.get("rf_mtm_y_val", 0.0)),
            "rf_mtm_n_val": s.get("rf_mtm_n_val", 0.0),
            "act_mtm_n_val": s.get("act_mtm_n_val", 0.0),
            "error_mtm_n_val": abs(s.get("act_mtm_n_val", 0.0) - s.get("rf_mtm_n_val", 0.0)),
        }
    elif len(selected_period) == 4 and selected_period.isdigit():
        prefix = selected_period + "-"
        matching = [p_data for p_name, p_data in s.get("periods", {}).items() if p_name.startswith(prefix)]
        if not matching:
            return None
        rf_q = sum(p.get("rf_qty", 0.0) for p in matching)
        act_q = sum(p.get("act_qty", 0.0) for p in matching)
        if rf_q == 0 and act_q == 0:
            return None
        rf_v = sum(p.get("rf_val", 0.0) for p in matching)
        act_v = sum(p.get("act_val", 0.0) for p in matching)
        err_v = sum(p.get("error_val", 0.0) for p in matching)

        rf_mtm_y_v = sum(p.get("rf_mtm_y_val", 0.0) for p in matching)
        act_mtm_y_v = sum(p.get("act_mtm_y_val", 0.0) for p in matching)
        err_mtm_y_v = sum(p.get("error_mtm_y_val", 0.0) for p in matching)

        rf_mtm_n_v = sum(p.get("rf_mtm_n_val", 0.0) for p in matching)
        act_mtm_n_v = sum(p.get("act_mtm_n_val", 0.0) for p in matching)
        err_mtm_n_v = sum(p.get("error_mtm_n_val", 0.0) for p in matching)

        mapes = [p.get("mape") for p in matching if p.get("mape") is not None]
        avg_mape = round(sum(mapes) / len(mapes), 2) if mapes else None

        return {
            "rf_qty": rf_q,
            "act_qty": act_q,
            "rf_val": rf_v,
            "act_val": act_v,
            "error_val": err_v,
            "mape": avg_mape,
            "rf_mtm_y_val": rf_mtm_y_v,
            "act_mtm_y_val": act_mtm_y_v,
            "error_mtm_y_val": err_mtm_y_v,
            "rf_mtm_n_val": rf_mtm_n_v,
            "act_mtm_n_val": act_mtm_n_v,
            "error_mtm_n_val": err_mtm_n_v,
        }
    else:
        p_data = s.get("periods", {}).get(selected_period)
        if not p_data:
            return None
        rf_q = p_data.get("rf_qty", 0.0)
        act_q = p_data.get("act_qty", 0.0)
        if rf_q == 0 and act_q == 0:
            return None
        return p_data


class APIRequestHandler(BaseHTTPRequestHandler):

    def _set_headers(self, status=200, content_type="application/json"):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.end_headers()

    def do_OPTIONS(self):
        self._set_headers(200)

    def do_GET(self):
        parsed_path = urlparse(self.path)
        path = parsed_path.path
        query_params = parse_qs(parsed_path.query)

        try:
            payload = get_data()

            if path in ["/", "/api/health"]:
                self._set_headers(200)
                res = {
                    "status": "ok",
                    "message": "Demand Planning & Forecast Accuracy API is active",
                    "total_skus": payload["summary"]["total_skus"],
                    "periods": payload["periods"],
                    "gbs": payload["gbs"]
                }
                self.wfile.write(json.dumps(res).encode("utf-8"))

            elif path == "/api/summary":
                # Support period, year & gb filtering for summary
                selected_period = query_params.get("periode", [None])[0]
                selected_year = query_params.get("tahun", [None])[0]
                effective_period = selected_period if selected_period else selected_year
                selected_gb = query_params.get("gb", [None])[0]

                skus = payload["skus"]
                if selected_gb:
                    skus = [s for s in skus if s.get("gb", "").lower() == selected_gb.lower()]

                rf_val_total = 0.0
                act_val_total = 0.0
                err_val_total = 0.0
                bias_qty_total = 0.0
                mape_list = []
                valid_sku_count = 0

                for s in skus:
                    p_data = extract_sku_period_data(s, effective_period)
                    if not p_data:
                        continue

                    rf_q = p_data.get("rf_qty", 0.0)
                    rf_v = p_data.get("rf_val", 0.0)
                    act_v = p_data.get("act_val", 0.0)
                    err_v = p_data.get("error_val", 0.0)
                    bias_q = rf_q - p_data.get("act_qty", 0.0)
                    mape_v = p_data.get("mape")

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

                self._set_headers(200)
                res = {
                    "status": "success",
                    "data": {
                        "total_skus": valid_sku_count,
                        "mape_accuracy": mape_acc,
                        "wafe_accuracy": wafe_acc,
                        "total_bias_qty": round(bias_qty_total, 2),
                        "value_at_risk_rp": round(err_val_total, 2)
                    }
                }
                self.wfile.write(json.dumps(res).encode("utf-8"))

            elif path == "/api/matrix":
                selected_period = query_params.get("periode", [None])[0]
                selected_year = query_params.get("tahun", [None])[0]
                effective_period = selected_period if selected_period else selected_year
                selected_gb = query_params.get("gb", [None])[0]
                skus = payload["skus"]
                if selected_gb:
                    gb_skus = [s for s in skus if s.get("gb", "").lower() == selected_gb.lower()]
                else:
                    gb_skus = list(skus)
                
                target_quadrants = ["MTM - Pareto", "MTM - Non-Pareto", "Non-MTM - Pareto", "Non-MTM - Non-Pareto"]

                def calc_skus_summary(q_skus, mode="total"):
                    rf_val_total = 0.0
                    act_val_total = 0.0
                    err_val_total = 0.0
                    q_act_qty = 0.0
                    q_rf_qty = 0.0
                    q_valid_count = 0
                    mape_list = []

                    for s in q_skus:
                        p_data = extract_sku_period_data(s, effective_period)
                        if not p_data:
                            continue

                        if mode == "mtm":
                            rf_v = p_data.get("rf_mtm_y_val", 0.0)
                            act_v = p_data.get("act_mtm_y_val", 0.0)
                            err_v = p_data.get("error_mtm_y_val", 0.0)
                        elif mode == "non_mtm":
                            rf_v = p_data.get("rf_mtm_n_val", 0.0)
                            act_v = p_data.get("act_mtm_n_val", 0.0)
                            err_v = p_data.get("error_mtm_n_val", 0.0)
                        else:
                            rf_v = p_data.get("rf_val", 0.0)
                            act_v = p_data.get("act_val", 0.0)
                            err_v = p_data.get("error_val", 0.0)

                        act_q = p_data.get("act_qty", 0.0)
                        rf_q_val = p_data.get("rf_qty", 0.0)
                        mape_v = (err_v / act_v * 100.0) if act_v > 0 else None

                        q_valid_count += 1
                        rf_val_total += rf_v
                        act_val_total += act_v
                        err_val_total += err_v
                        q_act_qty += act_q
                        q_rf_qty += rf_q_val
                        if mape_v is not None:
                            sku_acc = max(0.0, min(100.0, 100.0 - mape_v))
                            mape_list.append(sku_acc)

                    denom_val = max(rf_val_total, act_val_total)
                    if denom_val == 0 or q_valid_count == 0:
                        wafe_acc = None
                        mape_acc = None
                    else:
                        wafe = (err_val_total / denom_val * 100.0)
                        raw_wafe_acc_q = 100.0 - wafe
                        wafe_acc = round(max(0.0, min(100.0, raw_wafe_acc_q)), 2)
                        mape_acc = round(sum(mape_list) / len(mape_list), 2) if mape_list else None

                    return {
                        "sku_count": q_valid_count,
                        "actual_qty": round(q_act_qty, 2),
                        "rf_qty": round(q_rf_qty, 2),
                        "rf_val_rp": round(rf_val_total, 2),
                        "error_val_rp": round(err_val_total, 2),
                        "wafe_accuracy": wafe_acc,
                        "mape_accuracy": mape_acc
                    }

                quadrants_summary = {}
                for quad_name in target_quadrants:
                    if quad_name.startswith("MTM"):
                        q_skus = [s for s in gb_skus if (s.get("quadrant_gb_mtm") if selected_gb else s.get("quadrant_national_mtm")) == quad_name]
                        quadrants_summary[quad_name] = calc_skus_summary(q_skus, mode="mtm")
                    else:
                        q_skus = [s for s in gb_skus if (s.get("quadrant_gb_non_mtm") if selected_gb else s.get("quadrant_national_non_mtm")) == quad_name]
                        quadrants_summary[quad_name] = calc_skus_summary(q_skus, mode="non_mtm")

                # Totals summary
                totals_summary = {
                    "Total MTM": calc_skus_summary([s for s in gb_skus if (s.get("quadrant_gb_mtm") if selected_gb else s.get("quadrant_national_mtm")) is not None], mode="mtm"),
                    "Total NON-MTM": calc_skus_summary([s for s in gb_skus if (s.get("quadrant_gb_non_mtm") if selected_gb else s.get("quadrant_national_non_mtm")) is not None], mode="non_mtm"),
                    "Total Pareto": calc_skus_summary([s for s in gb_skus if (s.get("pareto_gb_total") if selected_gb else s.get("pareto_national_total")) == "Pareto"], mode="total"),
                    "Total Non-Pareto": calc_skus_summary([s for s in gb_skus if (s.get("pareto_gb_total") if selected_gb else s.get("pareto_national_total")) == "Non-Pareto"], mode="total")
                }

                self._set_headers(200)
                res = {
                    "status": "success",
                    "data": quadrants_summary,
                    "totals": totals_summary
                }
                self.wfile.write(json.dumps(res).encode("utf-8"))

            elif path == "/api/trend":
                self._set_headers(200)
                res = {
                    "status": "success",
                    "data": payload["trend"]
                }
                self.wfile.write(json.dumps(res).encode("utf-8"))

            elif path == "/api/options":
                self._set_headers(200)
                res = {
                    "status": "success",
                    "periods": payload["periods"],
                    "gbs": payload["gbs"]
                }
                self.wfile.write(json.dumps(res).encode("utf-8"))

            elif path == "/api/skus":
                selected_period = query_params.get("periode", [None])[0]
                selected_year = query_params.get("tahun", [None])[0]
                effective_period = selected_period if selected_period else selected_year
                quadrant_filter = query_params.get("quadrant", [None])[0]
                gb_filter = query_params.get("gb", [None])[0]
                search_query = query_params.get("search", [None])[0]
                limit_str = query_params.get("limit", [None])[0]

                skus = payload["skus"]
                res_skus = []
                for s in skus:
                    p_data = extract_sku_period_data(s, effective_period)
                    if not p_data:
                        continue

                    s_copy = dict(s)
                    if quadrant_filter and quadrant_filter.lower().startswith("mtm"):
                        s_copy["quadrant"] = s.get("quadrant_gb_mtm" if gb_filter else "quadrant_national_mtm")
                        s_copy["pareto_class"] = s.get("pareto_gb_mtm" if gb_filter else "pareto_national_mtm")
                    elif quadrant_filter and quadrant_filter.lower().startswith("non-mtm"):
                        s_copy["quadrant"] = s.get("quadrant_gb_non_mtm" if gb_filter else "quadrant_national_non_mtm")
                        s_copy["pareto_class"] = s.get("pareto_gb_non_mtm" if gb_filter else "pareto_national_non_mtm")
                    else:
                        s_copy["quadrant"] = s.get("quadrant_gb" if gb_filter else "quadrant_national")
                        s_copy["pareto_class"] = s.get("pareto_gb" if gb_filter else "pareto_national")
                    res_skus.append(s_copy)

                if gb_filter:
                    res_skus = [s for s in res_skus if s.get("gb", "").lower() == gb_filter.lower()]

                if quadrant_filter:
                    q_lower = quadrant_filter.lower()
                    if q_lower == "total mtm":
                        res_skus = [s for s in res_skus if s.get("quadrant_gb_mtm" if gb_filter else "quadrant_national_mtm") is not None]
                    elif q_lower in ["total non-mtm", "total non mtm"]:
                        res_skus = [s for s in res_skus if s.get("quadrant_gb_non_mtm" if gb_filter else "quadrant_national_non_mtm") is not None]
                    elif q_lower == "total pareto":
                        res_skus = [s for s in res_skus if s.get("pareto_gb_total" if gb_filter else "pareto_national_total") == "Pareto"]
                    elif q_lower in ["total non-pareto", "total non pareto"]:
                        res_skus = [s for s in res_skus if s.get("pareto_gb_total" if gb_filter else "pareto_national_total") == "Non-Pareto"]
                    elif q_lower.startswith("mtm"):
                        res_skus = [s for s in res_skus if str(s.get("quadrant_gb_mtm" if gb_filter else "quadrant_national_mtm", "")).lower() == q_lower]
                    elif q_lower.startswith("non-mtm"):
                        res_skus = [s for s in res_skus if str(s.get("quadrant_gb_non_mtm" if gb_filter else "quadrant_national_non_mtm", "")).lower() == q_lower]
                    else:
                        res_skus = [s for s in res_skus if str(s.get("quadrant_gb" if gb_filter else "quadrant_national", "")).lower() == q_lower]

                if search_query:
                    sq = search_query.lower()
                    res_skus = [
                        s for s in res_skus
                        if sq in s.get("product_code", "").lower()
                        or sq in s.get("product_name", "").lower()
                        or sq in s.get("old_code", "").lower()
                    ]

                if limit_str:
                    try:
                        limit_val = int(limit_str)
                        if limit_val > 0:
                            res_skus = res_skus[:limit_val]
                    except ValueError:
                        pass

                self._set_headers(200)
                res = {
                    "status": "success",
                    "count": len(res_skus),
                    "data": res_skus
                }
                self.wfile.write(json.dumps(res).encode("utf-8"))

            elif path == "/api/reprocess":
                new_payload = get_data(force_reprocess=True)
                self._set_headers(200)
                res = {
                    "status": "success",
                    "message": "Data successfully reprocessed with Pareto per GB & Period Accuracy",
                    "summary": new_payload["summary"]
                }
                self.wfile.write(json.dumps(res).encode("utf-8"))

            else:
                self._set_headers(404)
                res = {"status": "error", "message": f"Endpoint '{path}' not found"}
                self.wfile.write(json.dumps(res).encode("utf-8"))

        except Exception as e:
            self._set_headers(500)
            res = {"status": "error", "message": str(e)}
            self.wfile.write(json.dumps(res).encode("utf-8"))

    def do_POST(self):
        parsed_path = urlparse(self.path)
        if parsed_path.path == "/api/reprocess":
            new_payload = get_data(force_reprocess=True)
            self._set_headers(200)
            res = {
                "status": "success",
                "message": "Data successfully reprocessed",
                "summary": new_payload["summary"]
            }
            self.wfile.write(json.dumps(res).encode("utf-8"))
        else:
            self.do_GET()

    def log_message(self, format, *args):
        sys.stderr.write(f"[{self.log_date_time_string()}] {format % args}\n")


def run_server(port=8050):
    print(f"Initializing demand planning data...")
    get_data()
    server_address = ("", port)
    httpd = HTTPServer(server_address, APIRequestHandler)
    print(f"API Server listening on http://localhost:{port}")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down API Server...")
        httpd.server_close()


if __name__ == "__main__":
    port_env = os.environ.get("PORT", "8050")
    try:
        p = int(port_env)
    except ValueError:
        p = 8050
    run_server(p)
