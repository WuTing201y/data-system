# 完整分析：檢查每個 INSERT 中所有區域的分佈
# 執行: python full_analysis.py

from pathlib import Path
import re
from collections import defaultdict

SQL_PATH = "houseDatabase_version_1.sql"

def split_value_tuples(block: str) -> list:
    """切分 value tuples"""
    parts, buf, level, in_str, esc = [], [], 0, False, False
    for ch in block:
        if esc:
            buf.append(ch); esc=False; continue
        if ch == "\\":
            buf.append(ch); esc=True; continue
        if ch == "'" and not esc:
            in_str = not in_str; buf.append(ch); continue
        if not in_str:
            if ch == "(": level += 1
            if ch == ")": level -= 1
        buf.append(ch)
        if level == 0 and ch == ")":
            t = "".join(buf).strip()
            if not t.startswith("("): t = "(" + t
            if not t.endswith(")"):  t = t + ")"
            parts.append(t); buf=[]
    return parts

def parse_tuple_text(tup: str) -> list:
    """解析單個 tuple"""
    t = tup.strip()
    if not t.startswith("("): t = "(" + t
    if not t.endswith(")"):  t = t + ")"
    s = t[1:-1]
    fields, tok, in_str, esc, level = [], [], False, False, 0
    for ch in s:
        if esc: tok.append(ch); esc=False; continue
        if ch == "\\": tok.append(ch); esc=True; continue
        if ch == "'" and level == 0:
            in_str = not in_str; tok.append(ch); continue
        if not in_str:
            if ch == "(": level += 1; tok.append(ch); continue
            if ch == ")": level -= 1; tok.append(ch); continue
            if ch == "," and level == 0:
                fields.append("".join(tok).strip()); tok=[]; continue
        tok.append(ch)
    if tok: fields.append("".join(tok).strip())
    return fields

def full_analysis(sql_path: str):
    """完整分析每個 INSERT 中的所有資料"""
    text = Path(sql_path).read_text(encoding="utf-8", errors="ignore")
    
    pattern = re.compile(
        r"INSERT\s+INTO\s+`?houses`?\s+VALUES\s*(.+?);",
        flags=re.IGNORECASE | re.DOTALL
    )
    
    print("=" * 80)
    print("🔍 完整分析：檢查每個 INSERT 的所有區域")
    print("=" * 80)
    
    matches = pattern.findall(text)
    insert_districts = []  # 每個 INSERT 的區域統計
    all_districts = defaultdict(int)
    total_rows = 0
    failed_count = 0
    
    for idx, values_blob in enumerate(matches):
        print(f"\n📍 分析 INSERT #{idx + 1}...")
        
        tuples = split_value_tuples(values_blob)
        print(f"   總共 {len(tuples):,} 個 tuples")
        
        district_count = defaultdict(int)
        success = 0
        
        # 解析這個 INSERT 中的所有 tuples
        for i, tup in enumerate(tuples):
            try:
                fields = parse_tuple_text(tup)
                if len(fields) >= 5:
                    district = fields[4].strip().strip("'")
                    district_count[district] += 1
                    all_districts[district] += 1
                    success += 1
            except Exception as e:
                failed_count += 1
                if failed_count <= 3:  # 只顯示前3個錯誤
                    print(f"   ⚠️ 第 {i+1} 個 tuple 失敗: {str(e)[:50]}")
        
        total_rows += success
        print(f"   ✅ 成功: {success:,}/{len(tuples):,} ({success/len(tuples)*100:.1f}%)")
        print(f"   📊 包含 {len(district_count)} 個不同區域:")
        
        # 顯示這個 INSERT 的區域分佈
        for district, count in sorted(district_count.items(), key=lambda x: -x[1])[:5]:
            print(f"      • {district}: {count:,} 筆")
        if len(district_count) > 5:
            print(f"      ... 還有 {len(district_count) - 5} 個區域")
        
        insert_districts.append({
            "insert_num": idx + 1,
            "total_tuples": len(tuples),
            "success": success,
            "districts": dict(district_count)
        })
    
    print("\n" + "=" * 80)
    print("📊 總體統計")
    print("=" * 80)
    print(f"\n總 INSERT 數: {len(matches)}")
    print(f"總成功解析: {total_rows:,} 筆")
    print(f"總失敗: {failed_count:,} 筆")
    print(f"\n發現的所有區域 ({len(all_districts)} 個):")
    
    for district, count in sorted(all_districts.items(), key=lambda x: -x[1]):
        print(f"  • {district}: {count:,} 筆")
    
    # 新北市29區
    NEWTAIPEI_29 = [
        "板橋區","三重區","中和區","永和區","新莊區","新店區","樹林區","鶯歌區","三峽區",
        "淡水區","汐止區","瑞芳區","土城區","蘆洲區","五股區","泰山區","林口區","深坑區",
        "石碇區","坪林區","三芝區","石門區","八里區","平溪區","雙溪區","貢寮區","金山區",
        "萬里區","烏來區"
    ]
    
    missing = [d for d in NEWTAIPEI_29 if d not in all_districts]
    
    print(f"\n✅ 新北市29區覆蓋率: {29 - len(missing)}/29")
    if missing:
        print(f"❌ 缺少的區域 ({len(missing)} 個):")
        for d in missing:
            print(f"  • {d}")
    else:
        print("🎉 所有29區都有資料！")
    
    return insert_districts, all_districts

if __name__ == "__main__":
    insert_info, district_stats = full_analysis(SQL_PATH)
    
    print("\n" + "=" * 80)
    print("💡 結論")
    print("=" * 80)
    
    if len(district_stats) == 29:
        print("\n✅ SQL 檔案包含完整的新北市29區資料")
        print("✅ 你的 app.py 解析邏輯應該是正確的")
        print("\n🔍 如果 /health API 只顯示15個區，可能是:")
        print("   1. pandas DataFrame 合併/去重時出了問題")
        print("   2. _normalize_admin() 函數把某些區域正規化錯了")
        print("   3. 資料載入時某些 INSERT 被跳過了")
        print("\n建議：在 app.py 的 _load_df_from_sql() 加上更多 debug 輸出")
    else:
        print(f"\n⚠️ 只解析出 {len(district_stats)} 個區域")
        print("需要檢查 tuple 解析邏輯")