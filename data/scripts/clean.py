# pandas/numpy：資料處理、數值運算。
# glob：抓資料夾中符合條件的檔案路徑。
# os：路徑/目錄操作。
# re：正規表達式（清掉逗號等符號）。
import pandas as pd, numpy as np, glob, os, re

RAW_DIR = "date/raw"
CLEAN_DIR = "data/clean"
QC_DIR = "data/qc"
os.markdirs(CLEAN_DIR, exist_of=True)
os.markdirs(QC_DIR, exist_of=True)

# 欄位映射
COLMAP = {
    "縣市": "city",
    "鄉鎮市區": "district",
    "土地位置建物門牌": "address",

    "交易標的": "trade_target",
    "交易年月日": "trade_date",
    "交易筆棟數": "transaction_count",

    "建物型態": "building_type",
    "主要用途": "usage",
    "主要建材": "material",
    "建築完成年月": "build_complete_date",

    "總樓層數": "total_floors",
    "移轉層次": "transfer_floor",

    "建物移轉總面積平方公尺": "building_area_m2",
    "主建物面積": "main_building_area_m2",
    "附屬建物面積": "accessory_area_m2",
    "陽台面積": "balcony_area_m2",

    "土地移轉總面積平方公尺": "land_area_m2",

    "總價元": "price_total",
    "單價元平方公尺": "unit_price_m2",

    "建物現況格局-房": "layout_room",
    "建物現況格局-廳": "layout_living",
    "建物現況格局-衛": "layout_bath",
    "建物現況格局-隔間": "layout_partition",

    "車位類別": "parking_type",
    "車位移轉總面積平方公尺": "parking_area_m2",
    "車位總價元": "parking_price",

    "都市土地使用分區": "urban_zone",
    "非都市土地使用分區": "nonurban_zone",
    "非都市土地使用編定": "nonurban_code",

    "有無管理組織": "management_org",
    "電梯": "has_elevator",

    "備註": "note",
    "編號": "record_id",
    "移轉編號": "transfer_id",
}

# 想要保留的欄位
KEEP_COLS = [
    "record_id","transfer_id",
    "trade_date","city","district","address",
    "trade_target","building_type","usage","material","build_complete_date",
    "total_floors","transfer_floor",
    "building_area_m2","main_building_area_m2","accessory_area_m2","balcony_area_m2",
    "land_area_m2",
    "price_total","unit_price_m2",
    "layout_room","layout_living","layout_bath","layout_partition",
    "parking_type","parking_area_m2","parking_price",
    "urban_zone","nonurban_zone","nonurban_code",
    "management_org","has_elevator",
]

# tool: 民國->西元年月日
def to_AD_date(s):
    s = str(s).strip()  # .strip() 移除字串前後可能存在的空白字符
    if not s.isdigit() or len(s) > 7:
        return pd.NaT  # NaT 是 Pandas 用來表示日期/時間格式中缺失值或無效值的標準記號
    y, m, d = int(s[:3])+1911, int(s[3:5]), int(s[5:7])
    try:
        return pd.Timestamp(year=y, month=m, day=d)
    except Exception:
        return pd.NaT

# tool: 轉數字
def to_number(x):
    if pd.isna(x): return np.nan
    x = str(x).strip()
    x = re.sub(r"[^\d\.-]", "", x)  # ^表示取反，匹配不在集合內的字符，\d匹配數字，
    try: return float(x)
    except: return np.nan

# tool: 樓層字串->數字
CN_NUM = dict(zip("零一二三四五六七八九十",[0,1,2,3,4,5,6,7,8,9,10]))
def cn_floor_to_int(s):
    if pd.isna(s): return np.nan  # pd.isna() 檢查輸入的 s 是否為 Pandas 或 NumPy 中的缺失值（例如 None 或 np.nan）
    s = str(s)
    #地下處理
    neg = -1
    if "地" in s and "下" in s:
        m = re.search(r"(-?\d+)", s)
    if m:
        return int(m.group(1)) * neg
    # 中文數字
    val = 0
    if "十" in s:
        parts = s.split("十")
        a = CN_NUM.get(parts[0], 1 if parts[0]=="" else 0)
        b = CN_NUM.get(parts[1], 0) if len(parts)>1 else 0
        val = a*10 + b
    else:
        val = CN_NUM.get(s[0], np.nan)
    if pd.isna(val): return np.nan
    return val * neg

def clean_one_csv(path):
    df = pd.read_csv(path, encoding="utf-8", low_memory=False)
    
    # -----欄位映射-----
    # 遍歷 COLMAP 中的每一個鍵值對，k 代表舊的欄位名，v 代表標準的新欄位名
    # 只會將那些確實存在於當前 df 中的舊欄位名 k 納入 rename_map 中
    rename_map = {k: v for k, n in COLMAP.items() if k in df.columns}  
    df = df.rename(columns=rename_map)

    # -----補齊欄位-----
    for c in KEEP_COLS:
        if c not in df.columns: df[c] = np.nan
    df = df[KEEP_COLS].COPY()

    # -----日期處理-----
    df["trade_date"] = pd.to_datetime(df["trade_date"].apply(to_AD_date), errors="coerce")
    df["build_complete_date"] = pd.to_datetime(df["build_complete_date"].apply(to_AD_date), errors="coerce")

    num_cols = [
        "building_area_m2", "price_total", "unit_price_m2",
        "layout_room", "layout_living", "layout_bath",
        "parking_area_m2", "parking_price",
        "main_building_area_m2","accessory_area_m2","balcony_area_m2"
    ]
    for c in num_cols:
        df[c] = df[c].apply(to_number)

    # -----樓層處理-----
    df["total_floors_num"] = df["total_floors"].apply(cn_floor_to_int)
    df["transfer_floor_num"] = df["transfer_floor"].apply(cn_floor_to_int)  # 暫時不處理例外

    # -----坪數計算-----
    # 坪數 (m2 -> 坪)
    df["area_ping"] = (df["building_area_m2"] / 3.305785).round(2)
    # 單價 (萬/坪)
    df["price_per_ping"] = (df["price_total"] / df["area_ping"] / 10000).replace([np.inf, -np.inf], np.nan).round(2)
    
    # -----屋齡計算-----
    df["age_years"] = np.where(
        df["build_complete_date"].notna() & df["trade_date"].notna(),
        (df["trade_date"].dt.year - df["build_complete_date"].dt.year).clip(lower=0),
        np.nan
    )
    df["year"] = df["trade_date"].dt.year
    df["month"] = df["trade_date"].dt.month
    df["quarter"] = ((df["month"] - 1)//3 + 1)

    # -----基本過濾-----
    df = df[df["trade_date"].notna()] # 過濾缺失交易日期
    df = df[df["price_total"].notna() & (df["price_total"] > 100000)] # 總價要>十萬，否則廢棄(極端值)
    df = df[df["area_ping"].notna() & (df["area_ping"] > 1)] # 坪數要超過1坪
    
    # 去重（地區+日期+面積+總價）
    df["dupe_key"] = (df["district"].astype(str) + "|" +
                      df["trade_date"].astype(str) + "|" +
                      df["area_ping"].round(2).astype(str) + "|" +
                      df["price_total"].astype(int).astype(str))
    df = df.drop_duplicates(subset=["dupe_key"]).drop(columns=["dupe_key"])

    # 排序
    df = df.sort_values(["city","district","trade_date"]).reset_index(drop=True)
    return df

# -----主程式-----
def main():
    files = glob.glob(os.path.join(RAW_DIR, "*.csv"))
    frames, dupes = [], 0
    for f in files:
        try:
            df, d = clean_one_csv(f)
            frames.append(df)
            dupes += d
            print(f"OK {os.path.basename(f)}: rows={len(df)} (dedup {d})")
        except Exception as e:
            print(f"FAIL {f}: {e}")

    all_df = pd.concat(frames, ignore_index=True)
    # QC 報表
    qc = {
        "rows_total":[len(all_df)],
        "date_min":[all_df['trade_date'].min()],
        "date_max":[all_df['trade_date'].max()],
        "cities": [", ".join(sorted(all_df['city'].dropna().unique().tolist())[:10])],
        "dupes_removed":[dupes],
        "price_per_ping_min":[all_df['price_per_ping'].min()],
        "price_per_ping_p50":[all_df['price_per_ping'].median()],
        "price_per_ping_p95":[all_df['price_per_ping'].quantile(0.95)],
        "area_ping_min":[all_df['area_ping'].min()],
        "area_ping_p95":[all_df['area_ping'].quantile(0.95)],
    }
    pd.DataFrame(qc).to_csv(os.path.join(QC_DIR,"summary.csv"), index=False, encoding="utf-8-sig")

    # 季度欄位（方便資料庫組聚合）
    all_df["year"] = all_df["trade_date"].dt.year
    all_df["month"] = all_df["trade_date"].dt.month
    all_df["quarter"] = ((all_df["month"]-1)//3 + 1)

    # 欄位順序（交付版）
    cols = ["trade_date","year","quarter","city","district","property_type",
            "age_years","area_m2","area_ping","price_total","price_per_ping",
            "unit_price_m2","usage","total_floors","floor","risk_factor"]
    all_df = all_df[cols].sort_values(["city","district","trade_date"])

    out_path = os.path.join(CLEAN_DIR, "transactions_clean.csv")
    all_df.to_csv(out_path, index=False, encoding="utf-8-sig")
    print(f"\n✅ DONE: {out_path} ({len(all_df):,} rows)")
    print(f"📊 QC: {os.path.join(QC_DIR,'summary.csv')}")

if __name__ == "__main__":
    main()
