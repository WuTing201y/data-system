from app import DF  # 從你的 app.py 匯入已載入的 DataFrame

all_23 = [
    '板橋區','三重區','中和區','永和區','新莊區','新店區','樹林區','鶯歌區',
    '三峽區','淡水區','汐止區','瑞芳區','土城區','蘆洲區','五股區','泰山區',
    '林口區','深坑區','石碇區','坪林區','三芝區','石門區','烏來區'
]

existing = sorted(DF["district"].dropna().unique().tolist())
missing = [d for d in all_23 if d not in existing]

print("✅ 資料中有的：", existing)
print("❌ 缺少的區：", missing)
