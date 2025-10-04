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

# tool: 民國->西元
def to_AD_date(s):
    s = str(s).strip()  # .strip() 移除字串前後可能存在的空白字符
    if not s.isdigit() or len(s) > 7:
        return pd.NaT  # NaT 是 Pandas 用來表示日期/時間格式中缺失值或無效值的標準記號
    y, m, d = int(s[:3])+1911, int(s[3:5]), int(s[5:7])
    try:
        return pd.Timestamp(year=y, month=m, day=d)
    except Exception:
        return pd.NaT
    
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



