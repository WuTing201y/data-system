# app.py — FastAPI + Robust MySQL dump parser (no MySQL required)
# Endpoints: /health, /regions, /stats/monthly, /stats/yearly, /valuation

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional
from pathlib import Path
import pandas as pd
import re
import math

# ---------- Config ----------
SQL_PATH = "houseDatabase_version_1.sql"   # 放在和 app.py 同層
PING_PER_M2 = 1 / 3.305785                  # 坪數換算

app = FastAPI(title="House AI Estimation API", version="0.4.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_methods=["*"], allow_headers=["*"], allow_credentials=True
)

# ---------- Low-level SQL parsing ----------
def _split_value_tuples(block: str):
    """
    把 INSERT ... VALUES 區塊中的每一筆 "(...)" 切出來。
    具備：跨行、中文、跳脫字元、字串內逗號保護。
    """
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
            # 保險：確保外層有括號
            if not t.startswith("("): t = "(" + t
            if not t.endswith(")"): t = t + ")"
            parts.append(t)
            buf = []
    return parts

def _parse_tuple_text(tup: str):
    """
    把一筆形如 ('2018-09-18',2018,...,NULL) 的字串轉成 Python list。
    規則：
      - '...' -> 字串（含中文）
      - NULL  -> None
      - 其他  -> 盡力轉 float，不行就保留字串
    """
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
            val = f[1:-1].replace("\\'", "'").replace("\\\\", "\\")
            out.append(val)
        else:
            try:
                out.append(float(f))
            except Exception:
                out.append(f)
    return out

def _load_df_from_sql(sql_path: str) -> pd.DataFrame:
    text = Path(sql_path).read_text(encoding="utf-8", errors="ignore")

    # 抓所有 INSERT INTO houses VALUES ... ;
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
    print(f"✅ 載入 {len(df):,} 筆（略過 {bad} 筆）| 範圍 {df['trade_date'].min()} ~ {df['trade_date'].max()}")
    return df

# ---------- Feature engineering ----------
def _rf_age(age_years: Optional[float]) -> float:
    """屋齡風險（平滑 logistic，避免臨界跳動）"""
    if age_years is None or pd.isna(age_years):
        return 0.5
    a0, k = 30.0, 0.12
    a = float(age_years)
    rf = 1.0 / (1.0 + math.exp(-k * (a - a0)))
    return max(0.03, min(0.98, rf))

def _prepare_df(sql_path: str) -> pd.DataFrame:
    df = _load_df_from_sql(sql_path)
    # 若 dump 內 risk_factor 為空，以屋齡推估
    df["risk_factor"] = df["risk_factor"].where(~df["risk_factor"].isna(), df["age_years"].map(_rf_age))
    # 校正後單價
    df["adj_price_per_ping"] = df.apply(
        lambda r: None if pd.isna(r["price_per_ping"]) else r["price_per_ping"] * (1 - float(r["risk_factor"])),
        axis=1
    )
    return df

DF = _prepare_df(SQL_PATH)

def _filter_df(city: Optional[str]=None, district: Optional[str]=None,
               usage: str="住家用", start_date: Optional[str]=None,
               end_date: Optional[str]=None) -> pd.DataFrame:
    sub = DF.copy()
    if usage and usage != "ALL":
        sub = sub[sub["usage"] == usage]
    if city:
        sub = sub[sub["city"] == city]
    if district and district != "ALL":
        sub = sub[sub["district"] == district]
    if start_date:
        sub = sub[sub["trade_date"] >= pd.to_datetime(start_date)]
    if end_date:
        sub = sub[sub["trade_date"] <= pd.to_datetime(end_date)]
    return sub

# ---------- Endpoints ----------
@app.get("/health")
def health():
    return {
        "status": "ok",
        "rows": int(len(DF)),
        "date_range": [str(DF["trade_date"].min().date()), str(DF["trade_date"].max().date())]
    }

@app.get("/regions")
def regions(city: Optional[str] = None, usage: str = "住家用"):
    sub = _filter_df(city=city, usage=usage)
    if sub.empty:
        return []
    g = (sub.groupby(["city","district"])["trade_date"]
            .agg(min_date="min", max_date="max", n="size")
            .reset_index().sort_values("n", ascending=False))
    g["min_date"] = g["min_date"].dt.date.astype(str)
    g["max_date"] = g["max_date"].dt.date.astype(str)
    return g.to_dict(orient="records")

@app.get("/stats/monthly")
def stats_monthly(
    city: str,
    district: str = "ALL",
    usage: str = "住家用",
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
):
    sub = _filter_df(city, district, usage, start_date, end_date)
    if sub.empty:
        raise HTTPException(404, "no data for given filters")
    sub = sub.copy()
    sub["month"] = sub["trade_date"].dt.to_period("M").dt.to_timestamp()
    monthly = (sub.groupby("month")
                 .agg(avg_raw=("price_per_ping","mean"),
                      avg_adj=("adj_price_per_ping","mean"),
                      n=("price_per_ping","size"))
                 .reset_index())
    return monthly.to_dict(orient="records")

@app.get("/stats/yearly")
def stats_yearly(
    city: str,
    district: str = "ALL",
    usage: str = "住家用",
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
):
    sub = _filter_df(city, district, usage, start_date, end_date)
    if sub.empty:
        raise HTTPException(404, "no data for given filters")
    sub = sub.copy()
    sub["year"] = sub["trade_date"].dt.year
    yearly = (sub.groupby("year")
                .agg(avg_raw=("price_per_ping","mean"),
                     avg_adj=("adj_price_per_ping","mean"),
                     n=("price_per_ping","size"))
                .reset_index())
    return yearly.to_dict(orient="records")

@app.get("/valuation")
def valuation(
    city: str, district: str, area_m2: float,
    age_years: Optional[float] = None,
    usage: str = Query("住家用"),
    use_adjusted_baseline: bool = True,
    window_months: int = 24,
    fallback_months: int = 60,
):
    sub = _filter_df(city=city, district=district, usage=usage)
    if sub.empty:
        raise HTTPException(404, f"no region {city}-{district} ({usage})")

    latest = sub["trade_date"].max()
    cut = latest - pd.DateOffset(months=window_months)
    sample = sub[sub["trade_date"] >= cut]
    if sample.empty and fallback_months:
        cut = latest - pd.DateOffset(months=fallback_months)
        sample = sub[sub["trade_date"] >= cut]
    if sample.empty:
        raise HTTPException(404, f"no data between {cut.date()} and {latest.date()}")

    area_ping = area_m2 * PING_PER_M2

    if use_adjusted_baseline:
        ref_pp = sample["adj_price_per_ping"].dropna().median()
        if pd.isna(ref_pp):
            raise HTTPException(404, "no adjusted baseline")
        est_total = ref_pp * area_ping
        baseline_type = "adjusted_median"
        applied_risk = None
    else:
        ref_pp = sample["price_per_ping"].dropna().median()
        if pd.isna(ref_pp):
            raise HTTPException(404, "no raw baseline")
        rf = _rf_age(age_years)
        est_total = ref_pp * (1 - rf) * area_ping
        baseline_type = "raw_median"
        applied_risk = rf

    lo, hi = est_total * 0.9, est_total * 1.1
    return {
        "city": city, "district": district, "usage": usage,
        "area_m2": area_m2, "area_ping": round(area_ping, 2),
        "baseline_type": baseline_type,
        "baseline_pp_ping": None if pd.isna(ref_pp) else round(ref_pp, 0),
        "applied_risk_factor": applied_risk,
        "est_total": round(est_total, 0),
        "est_range_lo": round(lo, 0),
        "est_range_hi": round(hi, 0),
        "cut_from": str(cut.date()), "cut_to": str(latest.date())
    }

print(f"🔧 SQL: {SQL_PATH}")
print("✅ API ready — run with:  uvicorn app:app --reload")

# 允許: python app.py 直接跑（不一定要用 uvicorn 指令）
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="127.0.0.1", port=8000, reload=True)
