# parse_sql_to_csv.py — 獨立的 SQL dump 解析器
# 功能：將 MySQL dump 檔案轉換為 CSV 或 Excel
# 執行：python parse_sql_to_csv.py

from pathlib import Path
import pandas as pd
import re
import math
from datetime import datetime

# ==================== 設定 ====================
SQL_PATH = "houseDatabase_version_1.sql"
OUTPUT_CSV = "houses_data.csv"
OUTPUT_EXCEL = "houses_data.xlsx"

DEFAULT_COLS = [
    "trade_date", "year", "quarter", "city", "district", "age_years",
    "area_m2", "area_ping", "price_total", "price_per_ping", "unit_price_m2",
    "usage", "total_floors", "floor", "risk_factor"
]

NEWTAIPEI_29 = [
    "板橋區","三重區","中和區","永和區","新莊區","新店區","樹林區","鶯歌區","三峽區",
    "淡水區","汐止區","瑞芳區","土城區","蘆洲區","五股區","泰山區","林口區","深坑區",
    "石碇區","坪林區","三芝區","石門區","八里區","平溪區","雙溪區","貢寮區","金山區",
    "萬里區","烏來區"
]

# ==================== 解析函數 ====================
def parse_sql_value(val: str):
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

def split_tuples(values_text: str) -> list:
    """使用正則表達式切分並解析 tuple"""
    values_text = values_text.strip()
    rows = []
    
    # 匹配每個 (...)
    tuple_pattern = re.compile(r'\(((?:[^()\'"]|\'(?:[^\']|\\.)*\'|"(?:[^"]|\\.)*")*)\)', re.DOTALL)
    
    for match in tuple_pattern.finditer(values_text):
        inner = match.group(1)
        
        # 解析欄位
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
        parsed_fields = [parse_sql_value(f) for f in fields]
        
        if len(parsed_fields) == len(DEFAULT_COLS):
            rows.append(parsed_fields)
    
    return rows

def load_sql_to_dataframe(sql_path: str) -> pd.DataFrame:
    """載入 SQL dump 並轉換為 DataFrame"""
    print(f"📂 讀取檔案: {sql_path}")
    text = Path(sql_path).read_text(encoding="utf-8", errors="ignore")
    
    print("🔍 尋找 INSERT 語句...")
    pattern = re.compile(
        r"INSERT\s+INTO\s+`?houses`?\s+VALUES\s*(.+?);",
        flags=re.IGNORECASE | re.DOTALL
    )
    
    all_rows = []
    insert_count = 0
    
    for values_blob in pattern.findall(text):
        insert_count += 1
        rows = split_tuples(values_blob)
        all_rows.extend(rows)
        
        if insert_count % 5 == 0:
            print(f"  處理 {insert_count} 個 INSERT，累計 {len(all_rows):,} 筆資料...")
    
    print(f"✅ 共處理 {insert_count} 個 INSERT")
    print(f"✅ 解析出 {len(all_rows):,} 筆資料")
    
    # 建立 DataFrame
    df = pd.DataFrame(all_rows, columns=DEFAULT_COLS)
    
    # 資料型別轉換
    df["trade_date"] = pd.to_datetime(df["trade_date"], errors="coerce")
    df["year"] = pd.to_numeric(df["year"], errors="coerce")
    df["quarter"] = pd.to_numeric(df["quarter"], errors="coerce")
    df["age_years"] = pd.to_numeric(df["age_years"], errors="coerce")
    df["area_m2"] = pd.to_numeric(df["area_m2"], errors="coerce")
    df["area_ping"] = pd.to_numeric(df["area_ping"], errors="coerce")
    df["price_total"] = pd.to_numeric(df["price_total"], errors="coerce")
    df["price_per_ping"] = pd.to_numeric(df["price_per_ping"], errors="coerce")
    df["unit_price_m2"] = pd.to_numeric(df["unit_price_m2"], errors="coerce")
    df["risk_factor"] = pd.to_numeric(df["risk_factor"], errors="coerce")
    
    return df

# ==================== 資料清理 ====================
def clean_string(s: str) -> str:
    """清理字串"""
    if s is None:
        return ""
    s = str(s)
    s = re.sub(r"[\uFEFF\u200B-\u200D\u2060]", "", s)  # 零寬字元
    s = re.sub(r"[\x00-\x1F\x7F]", "", s)  # 控制字元
    s = s.replace("\u3000", "")  # 全形空白
    return s.strip()

def normalize_districts(df: pd.DataFrame) -> pd.DataFrame:
    """正規化行政區名稱"""
    print("🔧 正規化行政區名稱...")
    
    # 清理字串
    for col in ["city", "district", "usage"]:
        if col in df.columns:
            df[col] = df[col].apply(clean_string)
    
    # 城市正規化
    def map_city(x: str) -> str:
        if not x:
            return ""
        key = re.sub(r"[\s_-]+", "", x).lower()
        if x in {"新北市", "新北", "新北縣"}:
            return "新北市"
        if key in {"newtaipei", "newtaipeicity", "newtaipecity"}:
            return "新北市"
        return x
    
    df["city"] = df["city"].apply(map_city)
    
    # 英文區域對照
    en2zh = {
        "banqiao":"板橋區", "sanchong":"三重區", "zhonghe":"中和區", "yonghe":"永和區",
        "xinzhuang":"新莊區", "xindian":"新店區", "shulin":"樹林區", "yingge":"鶯歌區",
        "sanxia":"三峽區", "tamsui":"淡水區", "danshui":"淡水區",
        "xizhi":"汐止區", "ruifang":"瑞芳區", "tucheng":"土城區", "luzhou":"蘆洲區",
        "wugu":"五股區", "taishan":"泰山區", "linkou":"林口區", "shenkeng":"深坑區",
        "shiding":"石碇區", "pinglin":"坪林區", "sanzhi":"三芝區", "shimen":"石門區",
        "bali":"八里區", "pingxi":"平溪區", "shuangxi":"雙溪區", "gongliao":"貢寮區",
        "jinshan":"金山區", "wanli":"萬里區", "wulai":"烏來區"
    }
    
    def norm_dist(x: str) -> str:
        x0 = clean_string(x)
        if not x0:
            return ""
        
        # 中文區域
        zh = "".join(ch for ch in x0 if "\u4e00" <= ch <= "\u9fff")
        if zh:
            if not zh.endswith("區"):
                zh = zh + "區"
            return zh
        
        # 英文區域
        key = re.sub(r"[\s\-_]+", "", x0).lower().replace("district", "")
        return en2zh.get(key, x0)
    
    df["district"] = df["district"].apply(norm_dist)
    df.loc[df["district"].isin(NEWTAIPEI_29), "city"] = "新北市"
    
    # 用途正規化
    usage_map = {
        "住宅": "住家用",
        "住家": "住家用",
        "辦公": "辦公用",
        "商辦": "辦公用"
    }
    df["usage"] = df["usage"].replace(usage_map)
    
    return df

# ==================== 計算衍生欄位 ====================
def calculate_risk_factor(age):
    """計算風險係數（根據屋齡）"""
    if pd.isna(age):
        return 0.5
    a0, k = 30.0, 0.12
    return round(1.0 / (1.0 + math.exp(-k * (float(age) - a0))), 3)

def add_derived_columns(df: pd.DataFrame) -> pd.DataFrame:
    """增加衍生欄位"""
    print("🔧 計算衍生欄位...")
    
    # 填補風險係數
    df["risk_factor"] = df.apply(
        lambda row: calculate_risk_factor(row["age_years"]) if pd.isna(row["risk_factor"]) else row["risk_factor"],
        axis=1
    )
    
    # 調整後每坪單價
    df["adj_price_per_ping"] = df.apply(
        lambda row: None if pd.isna(row["price_per_ping"]) 
                    else row["price_per_ping"] * (1 - row["risk_factor"]),
        axis=1
    )
    
    # 年月欄位
    df["year_month"] = df["trade_date"].dt.to_period("M").astype(str)
    
    return df

# ==================== 統計分析 ====================
def print_statistics(df: pd.DataFrame):
    """輸出統計資訊"""
    print("\n" + "=" * 80)
    print("📊 資料統計")
    print("=" * 80)
    
    print(f"\n總筆數: {len(df):,}")
    print(f"日期範圍: {df['trade_date'].min()} ~ {df['trade_date'].max()}")
    
    # 城市分布
    print(f"\n城市分布:")
    city_counts = df["city"].value_counts()
    for city, count in city_counts.items():
        print(f"  • {city}: {count:,} 筆")
    
    # 新北市區域分布
    newtaipei = df[df["city"] == "新北市"]
    if len(newtaipei) > 0:
        print(f"\n新北市區域分布 (前 15):")
        district_counts = newtaipei["district"].value_counts().head(15)
        for district, count in district_counts.items():
            print(f"  • {district}: {count:,} 筆")
        
        # 檢查29區完整性
        found_districts = set(newtaipei["district"].unique())
        missing = [d for d in NEWTAIPEI_29 if d not in found_districts]
        print(f"\n✅ 新北市29區覆蓋: