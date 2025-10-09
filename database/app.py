# app.py — FastAPI + 修正版 MySQL dump 解析器
# 修正：使用正則表達式解析 tuple，成功解析所有 29 區

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional, List, Dict
from pathlib import Path
import pandas as pd
import re, math, io, sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

SQL_PATH = "houseDatabase_version_1.sql"
PING_PER_M2 = 1 / 3.305785

NEWTAIPEI_29 = [
    "板橋區","三重區","中和區","永和區","新莊區","新店區","樹林區","鶯歌區","三峽區",
    "淡水區","汐止區","瑞芳區","土城區","蘆洲區","五股區","泰山區","林口區","深坑區",
    "石碇區","坪林區","三芝區","石門區","八里區","平溪區","雙溪區","貢寮區","金山區",
    "萬里區","烏來區"
]
BASE29 = [d[:-1] for d in NEWTAIPEI_29]
BASE_MAP = {b: b + "區" for b in BASE29}

app = FastAPI(title="House AI Estimation API", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_methods=["*"], allow_headers=["*"], allow_credentials=True
)

# ===================== 解析邏輯（已修正）=====================
DEFAULT_COLS = [
    "trade_date","year","quarter","city","district","age_years",
    "area_m2","area_ping","price_total","price_per_ping","unit_price_m2",
    "usage","total_floors","floor","risk_factor"
]

COL_ALIASES = {
    "date":"trade_date", "tradedate":"trade_date",
    "yr":"year", "yyyy":"year",
    "q":"quarter","quart":"quarter",
    "cty":"city","cityname":"city","city_name":"city",
    "dist":"district","districtname":"district","district_name":"district",
    "town":"district","region":"district","area_name":"district",
    "age":"age_years","ageyear":"age_years",
    "aream2":"area_m2","m2":"area_m2",
    "areaping":"area_ping","ping":"area_ping",
    "totalprice":"price_total","total_price":"price_total",
    "pp_ping":"price_per_ping","priceperping":"price_per_ping",
    "unitprice":"unit_price_m2","unitpricem2":"unit_price_m2",
    "use":"usage","purpose":"usage",
    "floors":"total_floors","totalfloor":"total_floors","total_floors":"total_floors",
    "floorno":"floor","floor_num":"floor",
    "risk":"risk_factor","riskfactor":"risk_factor"
}

def _norm_colname(s: str) -> str:
    """正規化欄位名稱"""
    if not s: return s
    k = s.strip().strip("`").strip()
    k = re.sub(r"\s+", "", k)
    k = k.replace("__", "_").replace("-", "_").lower()
    k = k.replace(" ", "").replace("\t","").replace("\r","").replace("\n","")
    if k in DEFAULT_COLS:
        return k
    k2 = COL_ALIASES.get(k, k)
    return k2

def _parse_sql_value(val: str):
    """解析單個 SQL 值"""
    val = val.strip()
    if val.upper() == "NULL":
        return None
    if val.startswith("'") and val.endswith("'"):
        return val[1:-1].replace("\\'", "'").replace("\\\\", "\\")
    try:
        if "." in val:
            return float(val)
        return int(val)
    except ValueError:
        return val

def _split_tuples_improved(values_text: str) -> list:
    """改進的 tuple 切分與解析 - 使用正則表達式"""
    values_text = values_text.strip()
    rows = []
    
    # 使用正則表達式匹配每個 tuple
    tuple_pattern = re.compile(r'\(((?:[^()\'"]|\'(?:[^\']|\\.)*\'|"(?:[^"]|\\.)*")*)\)', re.DOTALL)
    
    for match in tuple_pattern.finditer(values_text):
        inner = match.group(1)
        
        # 解析 tuple 內的欄位
        fields = []
        current = []
        in_quote = False
        quote_char = None
        escape_next = False
        
        for ch in inner:
            if escape_next:
                current.append(ch)
                escape_next = False
                continue
                
            if ch == '\\':
                current.append(ch)
                escape_next = True
                continue
            
            if ch in ("'", '"') and not in_quote:
                in_quote = True
                quote_char = ch
                current.append(ch)
                continue
            
            if ch == quote_char and in_quote:
                in_quote = False
                quote_char = None
                current.append(ch)
                continue
            
            if ch == ',' and not in_quote:
                fields.append(''.join(current).strip())
                current = []
                continue
            
            current.append(ch)
        
        if current:
            fields.append(''.join(current).strip())
        
        # 解析每個欄位的值
        parsed_fields = [_parse_sql_value(f) for f in fields]
        
        if len(parsed_fields) == len(DEFAULT_COLS):
            rows.append(parsed_fields)
    
    return rows

def _load_df_from_sql(sql_path: str) -> pd.DataFrame:
    """載入並解析 SQL dump 檔案"""
    text = Path(sql_path).read_text(encoding="utf-8", errors="ignore")

    pattern = re.compile(
        r"INSERT\s+INTO\s+`?houses`?\s*(\([^)]+\))?\s+VALUES\s*(.+?);",
        flags=re.IGNORECASE | re.DOTALL
    )

    all_rows = []
    insert_count = 0

    for colgrp, values_blob in pattern.findall(text):
        insert_count += 1
        
        # 取得欄位順序（如果有的話）
        if colgrp:
            raw_cols = [c.strip() for c in colgrp.strip()[1:-1].split(",")]
            col_names = [_norm_colname(c) for c in raw_cols]
        else:
            col_names = DEFAULT_COLS.copy()

        # 解析這個 INSERT 的所有 tuples
        rows = _split_tuples_improved(values_blob)
        
        # 對齊欄位
        for vals in rows:
            if len(vals) < len(col_names):
                vals += [None] * (len(col_names) - len(vals))
            elif len(vals) > len(col_names):
                vals = vals[:len(col_names)]
            
            row_map = dict(zip(col_names, vals))
            row = [row_map.get(c, None) for c in DEFAULT_COLS]
            all_rows.append(row)
        
        if insert_count % 5 == 0:
            print(f"  處理 INSERT #{insert_count}，累計 {len(all_rows):,} 筆...")

    df = pd.DataFrame(all_rows, columns=DEFAULT_COLS)
    df["trade_date"] = pd.to_datetime(df["trade_date"], errors="coerce")
    
    print(f"✅ 載入 {len(df):,} 筆 | 範圍 {df['trade_date'].min()} ~ {df['trade_date'].max()}")
    
    return df

# ===================== 正規化行政區 =====================
def _clean_str(s: str) -> str:
    if s is None: return ""
    s = str(s)
    s = re.sub(r"[\uFEFF\u200B-\u200D\u2060]", "", s)
    s = re.sub(r"[\x00-\x1F\x7F]", "", s)
    s = s.replace("\u3000","")
    return s.strip()

def _normalize_admin(df: pd.DataFrame) -> pd.DataFrame:
    if "district_raw" not in df.columns:
        df["district_raw"] = df["district"]

    for c in ["city","district","usage","total_floors"]:
        if c in df.columns:
            df[c] = df[c].apply(_clean_str)

    def map_city(x: str) -> str:
        if not x: return ""
        key = re.sub(r"[\s_-]+","", x).lower()
        if x in {"新北市","新北","新北縣"}: return "NewTaipei"
        if key in {"newtaipei","newtaipeicity","newtaipecity"}: return "NewTaipei"
        return x
    df["city"] = df["city"].apply(map_city)

    en2zh = {
        "banqiao":"板橋區","sanchong":"三重區","zhonghe":"中和區","yonghe":"永和區",
        "xinzhuang":"新莊區","xindian":"新店區","shulin":"樹林區","yingge":"鶯歌區",
        "sanxia":"三峽區","tamsui":"淡水區","danshui":"淡水區",
        "xizhi":"汐止區","ruifang":"瑞芳區","tucheng":"土城區","luzhou":"蘆洲區",
        "wugu":"五股區","taishan":"泰山區","linkou":"林口區","shenkeng":"深坑區",
        "shiding":"石碇區","pinglin":"坪林區","sanzhi":"三芝區","shimen":"石門區",
        "bali":"八里區","pingxi":"平溪區","shuangxi":"雙溪區","gongliao":"貢寮區",
        "jinshan":"金山區","wanli":"萬里區","wulai":"烏來區"
    }

    def to_en_key(s: str) -> str:
        return re.sub(r"[\s\-_]+","", s).lower()

    def norm_dist(x: str) -> str:
        x0 = _clean_str(x)
        if not x0: return ""
        zh = "".join(ch for ch in x0 if "\u4e00" <= ch <= "\u9fff")
        if zh:
            base = re.sub(r"(區|鎮|鄉|市)$", "", zh)
            if base in BASE29: return base + "區"
            return zh if zh.endswith("區") else zh + "區"
        key = to_en_key(x0)
        if key in en2zh: return en2zh[key]
        key = re.sub(r"district$", "", key)
        if key in en2zh: return en2zh[key]
        return x0

    df["district"] = df["district"].apply(norm_dist)
    df.loc[df["district"].isin(NEWTAIPEI_29), "city"] = "NewTaipei"

    usage_map = {"住宅":"住家用","住家":"住家用","住家用":"住家用",
                 "辦公":"辦公用","商辦":"辦公用","辦公用":"辦公用"}
    df["usage"] = df["usage"].replace(usage_map)
    return df

# ===================== 風險 & 準備 =====================
def _rf_age(a):
    if a is None or pd.isna(a): return 0.5
    a0, k = 30.0, 0.12
    return round(1.0 / (1.0 + math.exp(-k * (float(a) - a0))), 3)

def _prepare_df(sql_path: str):
    print(f"🔧 載入 SQL: {sql_path}")
    df = _load_df_from_sql(sql_path)
    
    print("🔧 正規化行政區...")
    df = _normalize_admin(df)
    
    print("🔧 計算風險係數...")
    df["risk_factor"] = df["risk_factor"].where(~df["risk_factor"].isna(), df["age_years"].map(_rf_age))
    df["adj_price_per_ping"] = df.apply(
        lambda r: None if pd.isna(r["price_per_ping"]) else r["price_per_ping"] * (1 - float(r["risk_factor"])),
        axis=1
    )
    
    # 統計區域
    districts = df.loc[df["city"]=="NewTaipei","district"].dropna().unique()
    print(f"✅ 新北市發現 {len(districts)} 個區域")
    
    return df

print("⏳ 初始化中...")
DF = _prepare_df(SQL_PATH)
print(f"✅ 載入完成！共 {len(DF):,} 筆資料")

# ===================== 篩選 =====================
def _filter_df(city=None, district=None, usage="住家用", start_date=None, end_date=None):
    sub = DF.copy()
    if usage and usage != "ALL": sub = sub[sub["usage"] == usage]
    if city: sub = sub[sub["city"] == city]
    if district and district != "ALL": sub = sub[sub["district"] == district]
    if start_date: sub = sub[sub["trade_date"] >= pd.to_datetime(start_date)]
    if end_date: sub = sub[sub["trade_date"] <= pd.to_datetime(end_date)]
    return sub

# ===================== API =====================
@app.get("/health")
def health():
    districts = DF.loc[DF["city"]=="NewTaipei","district"].dropna().unique().tolist()
    missing = [d for d in NEWTAIPEI_29 if d not in districts]
    return {
        "status":"ok",
        "rows":int(len(DF)),
        "date_range":[str(DF["trade_date"].min().date()), str(DF["trade_date"].max().date())],
        "districts_in_NewTaipei": len(districts),
        "district_list": sorted(districts),
        "missing_districts": missing
    }

@app.get("/regions")
def regions(city: Optional[str]=None, usage: str="住家用"):
    sub = _filter_df(city=city, usage=usage)
    if sub.empty: return []
    g = (sub.groupby(["city","district"])["trade_date"]
           .agg(min_date="min", max_date="max", n="size")
           .reset_index().sort_values("n", ascending=False))
    g["min_date"] = g["min_date"].dt.date.astype(str)
    g["max_date"] = g["max_date"].dt.date.astype(str)
    return g.to_dict(orient="records")

@app.get("/stats/monthly")
def stats_monthly(city: str, district: str="ALL", usage: str="住家用"):
    sub = _filter_df(city, district, usage)
    if sub.empty: raise HTTPException(404, "no data")
    sub["month"] = sub["trade_date"].dt.to_period("M").dt.to_timestamp()
    monthly = (sub.groupby("month")
               .agg(avg_raw=("price_per_ping","mean"),
                    avg_adj=("adj_price_per_ping","mean"),
                    n=("price_per_ping","size")).reset_index())
    return monthly.to_dict(orient="records")

@app.get("/stats/yearly")
def stats_yearly(city: str, district: str="ALL", usage: str="住家用"):
    sub = _filter_df(city, district, usage)
    if sub.empty: raise HTTPException(404, "no data")
    sub["year"] = sub["trade_date"].dt.year
    yearly = (sub.groupby("year")
              .agg(avg_raw=("price_per_ping","mean"),
                   avg_adj=("adj_price_per_ping","mean"),
                   n=("price_per_ping","size")).reset_index())
    return yearly.to_dict(orient="records")

@app.get("/valuation")
def valuation(city:str, district:str, area_m2:float, age_years:Optional[float]=None, usage:str="住家用"):
    sub = _filter_df(city=city, district=district, usage=usage)
    if sub.empty: raise HTTPException(404, "no region")
    latest = sub["trade_date"].max()
    cut = latest - pd.DateOffset(months=24)
    sample = sub[sub["trade_date"] >= cut]
    area_ping = area_m2 * PING_PER_M2
    ref_pp = sample["adj_price_per_ping"].dropna().median()
    if pd.isna(ref_pp): raise HTTPException(404, "no baseline")
    est_total = ref_pp * area_ping
    return {
        "city":city,"district":district,"area_m2":area_m2,"area_ping":round(area_ping,2),
        "baseline_pp_ping":round(ref_pp,0),"est_total":round(est_total,0)
    }

# ===================== Debug =====================
@app.get("/debug/districts")
def debug_districts():
    g = (DF.groupby("district").size().reset_index(name="n").sort_values("n", ascending=False))
    return {"unique_count":int(g.shape[0]),"top":g.head(50).to_dict(orient="records")}

@app.get("/debug/districts_full")
def debug_districts_full(limit:int=200):
    g = (DF.groupby(["district_raw","district"]).size().reset_index(name="n").sort_values("n",ascending=False))
    return {"unique_pairs":int(g.shape[0]),"top":g.head(limit).to_dict(orient="records")}

print(f"🔧 SQL: {SQL_PATH}")
print("✅ API ready — run with: uvicorn app:app --reload")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="127.0.0.1", port=8000, reload=True)