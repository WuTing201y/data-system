# analyze_houses.py — Offline batch runner (no FastAPI)
# 功能：從 MySQL dump 解析出 DataFrame，提供月/年統計、估價，支援 CLI 與 JSON 批次。

from pathlib import Path
from typing import Optional, Literal
import pandas as pd
import math, re, json, argparse

# ---------- 基本設定 ----------
SQL_PATH_DEFAULT = "houseDatabase_version_1.sql"
PING_PER_M2 = 1 / 3.305785

# ---------- 解析 INSERT VALUES ----------
def _split_value_tuples(block: str):
    parts, buf, level, in_str, esc = [], [], 0, False, False
    for ch in block:
        if esc:
            buf.append(ch); esc = False; continue
        if ch == "\\":
            buf.append(ch); esc = True; continue
        if ch == "'" and not esc:
            in_str = not in_str
            buf.append(ch); continue
        if not in_str:
            if ch == "(": level += 1
            if ch == ")": level -= 1
        buf.append(ch)
        if level == 0 and ch == ")":
            t = "".join(buf).strip()
            if not t.startswith("("): t = "(" + t
            if not t.endswith(")"):  t = t + ")"
            parts.append(t)
            buf = []
    return parts

def _parse_tuple_text(tup: str):
    t = tup.strip()
    if not t.startswith("("): t = "(" + t
    if not t.endswith(")"):  t = t + ")"
    s = t[1:-1]

    fields, tok, in_str, esc, level = [], [], False, False, 0
    for ch in s:
        if esc:
            tok.append(ch); esc = False; continue
        if ch == "\\":
            tok.append(ch); esc = True; continue
        if ch == "'" and level == 0:
            in_str = not in_str
            tok.append(ch); continue
        if not in_str:
            if ch == "(":
                level += 1; tok.append(ch); continue
            if ch == ")":
                level -= 1; tok.append(ch); continue
            if ch == "," and level == 0:
                fields.append("".join(tok).strip()); tok = []; continue
        tok.append(ch)
    if tok:
        fields.append("".join(tok).strip())

    out = []
    for f in fields:
        fu = f.upper()
        if fu == "NULL":
            out.append(None)
        elif len(f) >= 2 and f[0] == "'" and f[-1] == "'":
            out.append(f[1:-1].replace("\\'", "'").replace("\\\\", "\\"))
        else:
            try: out.append(float(f))
            except: out.append(f)
    return out

def load_df_from_sql(sql_path: str) -> pd.DataFrame:
    text = Path(sql_path).read_text(encoding="utf-8", errors="ignore")
    inserts = re.findall(
        r"INSERT\s+INTO\s+`?houses`?\s+VALUES\s*(.*?);",
        text, flags=re.IGNORECASE | re.DOTALL
    )
    rows, bad = [], 0
    for block in inserts:
        for tup in _split_value_tuples(block):
            try:
                rows.append(_parse_tuple_text(tup))
            except Exception as e:
                bad += 1
                print("❌ parse fail:", str(e)[:100], "| sample:", tup[:120])

    cols = [
        "trade_date","year","quarter","city","district","age_years",
        "area_m2","area_ping","price_total","price_per_ping","unit_price_m2",
        "usage","total_floors","floor","risk_factor"
    ]
    df = pd.DataFrame(rows, columns=cols)
    df["trade_date"] = pd.to_datetime(df["trade_date"], errors="coerce")
    print(f"✅ 載入 {len(df):,} 筆（略過 {bad}）| 範圍 {df['trade_date'].min()} ~ {df['trade_date'].max()}")
    return df

# ---------- 特徵 & 公用 ----------
def rf_age(age_years: Optional[float]) -> float:
    if age_years is None or pd.isna(age_years): return 0.5
    a0, k = 30.0, 0.12
    a = float(age_years)
    v = 1.0 / (1.0 + math.exp(-k * (a - a0)))
    return max(0.03, min(0.98, v))

def prepare_df(sql_path: str) -> pd.DataFrame:
    df = load_df_from_sql(sql_path)
    df["risk_factor"] = df["risk_factor"].where(~df["risk_factor"].isna(), df["age_years"].map(rf_age))
    df["adj_price_per_ping"] = df.apply(
        lambda r: None if pd.isna(r["price_per_ping"]) else r["price_per_ping"] * (1 - float(r["risk_factor"])),
        axis=1
    )
    return df

def filter_df(DF: pd.DataFrame, city: Optional[str]=None, district: Optional[str]=None,
              usage: str="住家用", start_date: Optional[str]=None, end_date: Optional[str]=None) -> pd.DataFrame:
    sub = DF.copy()
    if usage and usage != "ALL": sub = sub[sub["usage"] == usage]
    if city: sub = sub[sub["city"] == city]
    if district and district != "ALL": sub = sub[sub["district"] == district]
    if start_date: sub = sub[sub["trade_date"] >= pd.to_datetime(start_date)]
    if end_date:   sub = sub[sub["trade_date"] <= pd.to_datetime(end_date)]
    return sub

# ---------- 主要功能 ----------
def stats_monthly(DF: pd.DataFrame, city: str, district: str="ALL", usage: str="住家用",
                  start_date: Optional[str]=None, end_date: Optional[str]=None) -> pd.DataFrame:
    sub = filter_df(DF, city, district, usage, start_date, end_date)
    if sub.empty: return pd.DataFrame(columns=["month","avg_raw","avg_adj","n"])
    sub = sub.copy()
    sub["month"] = sub["trade_date"].dt.to_period("M").dt.to_timestamp()
    monthly = (sub.groupby("month")
                 .agg(avg_raw=("price_per_ping","mean"),
                      avg_adj=("adj_price_per_ping","mean"),
                      n=("price_per_ping","size"))
                 .reset_index())
    return monthly

def stats_yearly(DF: pd.DataFrame, city: str, district: str="ALL", usage: str="住家用",
                 start_date: Optional[str]=None, end_date: Optional[str]=None) -> pd.DataFrame:
    sub = filter_df(DF, city, district, usage, start_date, end_date)
    if sub.empty: return pd.DataFrame(columns=["year","avg_raw","avg_adj","n"])
    sub = sub.copy()
    sub["year"] = sub["trade_date"].dt.year
    yearly = (sub.groupby("year")
                .agg(avg_raw=("price_per_ping","mean"),
                     avg_adj=("adj_price_per_ping","mean"),
                     n=("price_per_ping","size"))
                .reset_index())
    return yearly

def valuation(DF: pd.DataFrame, city: str, district: str, area_m2: float,
              age_years: Optional[float]=None, usage: str="住家用",
              use_adjusted_baseline: bool=True,
              window_months: int=24, fallback_months: int=60) -> dict:
    sub = filter_df(DF, city, district, usage)
    if sub.empty: raise ValueError(f"no region {city}-{district} ({usage})")

    latest = sub["trade_date"].max()
    cut = latest - pd.DateOffset(months=window_months)
    sample = sub[sub["trade_date"] >= cut]
    if sample.empty and fallback_months:
        cut = latest - pd.DateOffset(months=fallback_months)
        sample = sub[sub["trade_date"] >= cut]
    if sample.empty:
        raise ValueError(f"no data between {cut.date()} and {latest.date()}")

    area_ping = area_m2 * PING_PER_M2

    if use_adjusted_baseline:
        ref_pp = sample["adj_price_per_ping"].dropna().median()
        if pd.isna(ref_pp): raise ValueError("no adjusted baseline")
        est_total = ref_pp * area_ping
        baseline_type = "adjusted_median"
        applied_risk = None
    else:
        ref_pp = sample["price_per_ping"].dropna().median()
        if pd.isna(ref_pp): raise ValueError("no raw baseline")
        rf = rf_age(age_years)
        est_total = ref_pp * (1 - rf) * area_ping
        baseline_type = "raw_median"
        applied_risk = rf

    lo, hi = est_total*0.9, est_total*1.1
    return {
        "city": city, "district": district, "usage": usage,
        "area_m2": area_m2, "area_ping": round(area_ping,2),
        "baseline_type": baseline_type,
        "baseline_pp_ping": None if pd.isna(ref_pp) else round(ref_pp,0),
        "applied_risk_factor": applied_risk,
        "est_total": round(est_total,0),
        "est_range_lo": round(lo,0),
        "est_range_hi": round(hi,0),
        "cut_from": str(cut.date()), "cut_to": str(latest.date())
    }

# ---------- CLI ----------
def run_cli():
    p = argparse.ArgumentParser(description="Offline house analytics (no server).")
    p.add_argument("--sql", default=SQL_PATH_DEFAULT, help="path to .sql dump")
    subp = p.add_subparsers(dest="cmd", required=True)

    sp_m = subp.add_parser("monthly")
    sp_m.add_argument("--city", required=True)
    sp_m.add_argument("--district", default="ALL")
    sp_m.add_argument("--usage", default="住家用")
    sp_m.add_argument("--start_date")
    sp_m.add_argument("--end_date")
    sp_m.add_argument("--out", default="stats_monthly.csv")

    sp_y = subp.add_parser("yearly")
    sp_y.add_argument("--city", required=True)
    sp_y.add_argument("--district", default="ALL")
    sp_y.add_argument("--usage", default="住家用")
    sp_y.add_argument("--start_date")
    sp_y.add_argument("--end_date")
    sp_y.add_argument("--out", default="stats_yearly.csv")

    sp_v = subp.add_parser("valuation")
    sp_v.add_argument("--city", required=True)
    sp_v.add_argument("--district", required=True)
    sp_v.add_argument("--area_m2", type=float, required=True)
    sp_v.add_argument("--age_years", type=float)
    sp_v.add_argument("--usage", default="住家用")
    sp_v.add_argument("--use_adjusted_baseline", type=lambda x: str(x).lower()!="false", default=True)
    sp_v.add_argument("--out", default="valuation_result.json")

    sp_b = subp.add_parser("batch")
    sp_b.add_argument("--json", default="queries.json", help="batch file (同之前定義)")

    args = p.parse_args()

    DF = prepare_df(args.sql)

    if args.cmd == "monthly":
        df = stats_monthly(DF, args.city, args.district, args.usage, args.start_date, args.end_date)
        df.to_csv(args.out, index=False, encoding="utf-8-sig")
        print("✅ exported:", args.out)

    elif args.cmd == "yearly":
        df = stats_yearly(DF, args.city, args.district, args.usage, args.start_date, args.end_date)
        df.to_csv(args.out, index=False, encoding="utf-8-sig")
        print("✅ exported:", args.out)

    elif args.cmd == "valuation":
        res = valuation(DF, args.city, args.district, args.area_m2, args.age_years,
                        args.usage, args.use_adjusted_baseline)
        Path(args.out).write_text(json.dumps(res, ensure_ascii=False, indent=2), encoding="utf-8")
        print("✅ exported:", args.out)

    elif args.cmd == "batch":
        data = json.loads(Path(args.json).read_text(encoding="utf-8"))
        # 跟我們之前約定的格式一致：
        # {
        #   "monthly": [{"city":"NewTaipei","district":"三重區","usage":"住家用"}],
        #   "yearly":  [{"city":"NewTaipei","district":"ALL","usage":"ALL"}],
        #   "valuation":[{"city":"NewTaipei","district":"板橋區","area_m2":33,"age_years":25,"usage":"住家用","use_adjusted_baseline":true}]
        # }
        if "monthly" in data:
            for q in data["monthly"]:
                out = f"stats_monthly_{q['city']}_{q['district']}.csv".replace("/","_")
                df = stats_monthly(DF, q["city"], q.get("district","ALL"), q.get("usage","住家用"),
                                   q.get("start_date"), q.get("end_date"))
                df.to_csv(out, index=False, encoding="utf-8-sig")
                print("✅ monthly ->", out)
        if "yearly" in data:
            for q in data["yearly"]:
                out = f"stats_yearly_{q['city']}_{q['district']}.csv".replace("/","_")
                df = stats_yearly(DF, q["city"], q.get("district","ALL"), q.get("usage","住家用"),
                                   q.get("start_date"), q.get("end_date"))
                df.to_csv(out, index=False, encoding="utf-8-sig")
                print("✅ yearly ->", out)
        if "valuation" in data:
            rows = []
            for q in data["valuation"]:
                res = valuation(DF, q["city"], q["district"], float(q["area_m2"]),
                                q.get("age_years"), q.get("usage","住家用"),
                                bool(q.get("use_adjusted_baseline", True)))
                rows.append(res)
            pd.DataFrame(rows).to_csv("valuations_result.csv", index=False, encoding="utf-8-sig")
            print("✅ valuation -> valuations_result.csv")

if __name__ == "__main__":
    run_cli()
