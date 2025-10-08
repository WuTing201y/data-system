房價資料分析系統 (House Data Analysis)

這是一個以 Python 建立的 房價資料分析專案，可從 .sql 檔（匯出的資料庫 INSERT 語句）中解析出房屋交易資料，並提供：

📊 每月平均單價統計

📈 每年平均單價統計

🏠 估價功能（依照面積、屋齡、區域進行推估）

可選擇以 FastAPI 啟動伺服器提供 API，或直接用 純 Python 腳本批次執行。

📁 專案結構
Database/
│
├── app.py                     # FastAPI 伺服器版本 (API)
├── analyze_houses.py          # 純 Python 離線分析版本
├── parse_houses.py            # SQL 解析模組 (共用邏輯)
├── check_districts.py         # 驗證資料中行政區完整性
├── houseDatabase_version_1.sql# 匯出的 SQL 資料檔
├── queries.json               # 批次查詢設定檔
│
├── stats_monthly_NewTaipei_三重區.csv   # 月統計輸出
├── stats_yearly_NewTaipei_ALL.csv      # 年統計輸出
└── valuations_result.csv               # 估價結果輸出

⚙️ 安裝與環境設定
1️⃣ 建立虛擬環境 (建議)
python -m venv venv
venv\Scripts\activate   # Windows

2️⃣ 安裝必要套件
pip install fastapi uvicorn pandas

🚀 使用方式
A. FastAPI API 伺服器模式

啟動伺服器：

uvicorn app:app --reload


打開瀏覽器訪問：

健康檢查 → http://127.0.0.1:8000/health

月統計 → http://127.0.0.1:8000/stats/monthly?city=NewTaipei&district=三重區&usage=住家用

年統計 → http://127.0.0.1:8000/stats/yearly?city=NewTaipei&district=ALL&usage=ALL

估價 → http://127.0.0.1:8000/valuation?city=NewTaipei&district=板橋區&area_m2=33&age_years=25&usage=住家用&use_adjusted_baseline=true

Swagger 文件（可互動測試）
👉 http://127.0.0.1:8000/docs

B. 純 Python 批次分析模式

直接用 analyze_houses.py，不需要啟動伺服器。

1️⃣ 執行批次任務
python analyze_houses.py --sql houseDatabase_version_1.sql batch --json queries.json


執行後會產生：

stats_monthly_NewTaipei_三重區.csv

stats_yearly_NewTaipei_ALL.csv

valuations_result.csv

2️⃣ 執行單次查詢
# 月統計
python analyze_houses.py --sql houseDatabase_version_1.sql monthly --city NewTaipei --district 三重區 --usage 住家用 --out month.csv

# 年統計
python analyze_houses.py --sql houseDatabase_version_1.sql yearly --city NewTaipei --district ALL --usage ALL --out year.csv

# 估價
python analyze_houses.py --sql houseDatabase_version_1.sql valuation --city NewTaipei --district 板橋區 --area_m2 33 --age_years 25 --usage 住家用 --use_adjusted_baseline true --out val.json

C. 驗證行政區完整性
python check_districts.py


可輸出目前資料中有的區與缺少的區。

🧩 查詢設定檔範例 (queries.json)
{
  "monthly": [
    { "city": "NewTaipei", "district": "三重區", "usage": "住家用" }
  ],
  "yearly": [
    { "city": "NewTaipei", "district": "ALL", "usage": "ALL" }
  ],
  "valuation": [
    { "city": "NewTaipei", "district": "板橋區", "area_m2": 33, "age_years": 25, "usage": "住家用", "use_adjusted_baseline": true }
  ]
}