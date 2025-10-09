# 🏠 房屋交易分析平台

> 基於實價登錄資料的房屋交易分析系統，提供月均價、年均價查詢及房屋估價功能（含屋齡風險校正）

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-green.svg)](https://fastapi.tiangolo.com/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## 📋 目錄

- [專題簡介](#-專題簡介)
- [功能特色](#-功能特色)
- [系統架構](#-系統架構)
- [快速開始](#-快速開始)
- [API 使用說明](#-api-使用說明)
- [前端開發指南](#-前端開發指南)
- [Python 腳本使用](#-python-腳本使用)
- [資料說明](#-資料說明)
- [常見問題](#-常見問題)

---

## 🎯 專題簡介

本專題為 **114-1 資料庫期末專題**，實作一個完整的房屋交易分析系統，包含：

- ✅ **240,358 筆**實價登錄資料（新北市 29 區）
- ✅ **FastAPI** 後端 API 服務
- ✅ **MySQL** 資料庫管理
- ✅ **風險校正**機制（基於屋齡）
- ✅ **視覺化**前端介面

### 核心功能
1. 📊 **月均價查詢** - 查看特定區域的月均價趨勢
2. 📅 **年均價統計** - 分析年度價格變化
3. 💰 **房屋估價** - 根據面積和區域估算房價（含風險校正）

---

## ✨ 功能特色

### 1. RESTful API
- 🚀 基於 FastAPI 框架
- 📖 自動生成 API 文件（Swagger UI）
- 🔒 CORS 跨域支援
- ⚡ 快速查詢響應

### 2. 風險校正機制
- 📐 使用 **Sigmoid 函數**計算屋齡風險係數
- 🎯 風險公式：`risk_factor = 1 / (1 + e^(-k*(age-30)))`
- 💡 校正後單價：`adj_price = price × (1 - risk_factor)`

### 3. 資料完整性
- ✅ 新北市 **29 個行政區**完整資料
- ✅ 時間範圍：2018 ~ 2025
- ✅ 支援中英文區域名稱

---

## 🏗️ 系統架構

```
┌─────────────┐         ┌──────────────┐         ┌─────────────┐
│   前端介面   │ ◄─────► │  FastAPI API │ ◄─────► │   MySQL DB  │
│  (demo.html) │  REST   │   (app.py)   │  SQL    │ (240K rows) │
└─────────────┘         └──────────────┘         └─────────────┘
                              │
                              │
                        ┌─────▼─────┐
                        │  分析工具  │
                        │ (.py 腳本) │
                        └───────────┘
```

### 檔案結構

```
database/
├── 📄 app.py                        # FastAPI 主程式（必須）
├── 🌐 demo.html                     # 前端展示頁面
├── 🔧 parse_sql_to_csv.py          # SQL 轉 CSV 工具
├── 📊 query_house_api.py           # API 查詢分析腳本
├── 💾 houseDatabase_version_1.sql  # 原始資料庫檔案
└── 📖 README.md                     # 本文件
```

---

## 🚀 快速開始

### 1. 環境需求

- Python 3.8+
- 套件：`pandas`, `fastapi`, `uvicorn`

### 2. 安裝套件

```bash
pip install fastapi uvicorn pandas
```

### 3. 啟動 API 服務

```bash
python app.py
```

成功後會顯示：
```
⏳ 初始化中...
🔧 載入 SQL: houseDatabase_version_1.sql
  處理 5 個 INSERT，累計 44,650 筆資料...
  處理 10 個 INSERT，累計 89,270 筆資料...
  ...
✅ 載入 240,358 筆 | 範圍 2018-01-01 ~ 2025-12-31
✅ 新北市發現 29 個區域
✅ 載入完成！共 240,358 筆資料
🚀 API ready!
INFO:     Uvicorn running on http://127.0.0.1:8000
```

### 4. 測試 API

開啟瀏覽器訪問：
- **API 文件**：http://127.0.0.1:8000/docs
- **健康檢查**：http://127.0.0.1:8000/health
- **前端介面**：直接開啟 `demo.html`

---

## 📡 API 使用說明

### 基礎 URL
```
http://127.0.0.1:8000
```

### 端點列表

#### 1. 健康檢查
```http
GET /health
```

**回應範例：**
```json
{
  "status": "ok",
  "rows": 240358,
  "date_range": ["2018-01-01", "2025-12-31"],
  "districts_in_NewTaipei": 29,
  "district_list": ["板橋區", "三重區", "中和區", ...],
  "missing_districts": []
}
```

#### 2. 查詢區域資訊
```http
GET /regions?city=NewTaipei&usage=住家用
```

**回應範例：**
```json
[
  {
    "city": "NewTaipei",
    "district": "板橋區",
    "min_date": "2018-01-01",
    "max_date": "2025-12-31",
    "n": 28023
  }
]
```

#### 3. 月均價查詢
```http
GET /stats/monthly?city=NewTaipei&district=板橋區&usage=住家用
```

**參數：**
- `city` (必填): 城市名稱（如 `NewTaipei`）
- `district` (必填): 行政區（如 `板橋區`）
- `usage` (選填): 用途（預設 `住家用`）

**回應範例：**
```json
[
  {
    "month": "2024-01-01T00:00:00",
    "avg_raw": 45.67,
    "avg_adj": 38.23,
    "n": 1234
  }
]
```

#### 4. 年均價查詢
```http
GET /stats/yearly?city=NewTaipei&district=ALL&usage=住家用
```

**參數：**
- `district`: 可設為 `ALL` 查詢全市

**回應範例：**
```json
[
  {
    "year": 2024,
    "avg_raw": 43.36,
    "avg_adj": 28.92,
    "n": 35208
  }
]
```

#### 5. 房屋估價
```http
GET /valuation?city=NewTaipei&district=板橋區&area_m2=80&usage=住家用
```

**參數：**
- `area_m2` (必填): 房屋面積（平方公尺）

**回應範例：**
```json
{
  "city": "NewTaipei",
  "district": "板橋區",
  "area_m2": 80,
  "area_ping": 24.2,
  "baseline_pp_ping": 29,
  "est_total": 702
}
```

**說明：**
- `baseline_pp_ping`: 每坪單價（萬元），已包含風險校正
- `est_total`: 預估總價（萬元）

---

## 🎨 前端開發指南

### 快速開始

#### 1. 確保 API 正在運行
```bash
python app.py
```

#### 2. 開啟前端頁面
直接用瀏覽器開啟 `demo.html` 或使用 Live Server

### JavaScript 呼叫範例

#### 範例 1：取得系統資訊
```javascript
async function getSystemInfo() {
  const response = await fetch('http://127.0.0.1:8000/health');
  const data = await response.json();
  console.log('總資料筆數:', data.rows);
  console.log('區域列表:', data.district_list);
}
```

#### 範例 2：查詢月均價
```javascript
async function getMonthlyPrice(district) {
  const response = await fetch(
    `http://127.0.0.1:8000/stats/monthly?city=NewTaipei&district=${encodeURIComponent(district)}&usage=住家用`
  );
  const data = await response.json();
  
  // 繪製圖表
  data.forEach(item => {
    console.log(`${item.month}: ${item.avg_raw} 萬/坪`);
  });
}
```

#### 範例 3：房屋估價
```javascript
async function estimatePrice(district, area_m2) {
  const response = await fetch(
    `http://127.0.0.1:8000/valuation?city=NewTaipei&district=${encodeURIComponent(district)}&area_m2=${area_m2}&usage=住家用`
  );
  const result = await response.json();
  
  console.log(`預估總價: ${result.est_total} 萬元`);
  console.log(`每坪單價: ${result.baseline_pp_ping} 萬`);
}
```

### 圖表繪製（使用 Chart.js）

```html
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<canvas id="myChart"></canvas>

<script>
async function drawPriceChart(district) {
  const response = await fetch(
    `http://127.0.0.1:8000/stats/monthly?city=NewTaipei&district=${district}&usage=住家用`
  );
  const data = await response.json();
  
  const ctx = document.getElementById('myChart').getContext('2d');
  new Chart(ctx, {
    type: 'line',
    data: {
      labels: data.map(d => d.month.substring(0, 7)),
      datasets: [{
        label: '均價',
        data: data.map(d => d.avg_raw),
        borderColor: '#667eea',
        tension: 0.4
      }]
    }
  });
}
</script>
```

### CORS 注意事項

API 已經設定 CORS，允許所有來源：
```python
allow_origins=["*"]
```

如果遇到 CORS 錯誤，確認 `app.py` 的 CORS 設定是否正確。

---

## 🐍 Python 腳本使用

### 1. 資料處理腳本

**功能：** 將 SQL dump 轉換為 CSV/Excel

```bash
python parse_sql_to_csv.py
```

**輸出：**
- `houses_data.csv` - CSV 格式資料
- `houses_data.xlsx` - Excel 格式資料

### 2. API 查詢腳本

**功能：** 互動式查詢與分析

```bash
python query_house_api.py
```

**主要功能：**
1. 🏥 系統健康檢查
2. 📊 TOP 10 區域分析
3. 📈 區域比較（含圖表）
4. 💰 房屋估價（單次/批次）
5. 📄 匯出 Excel 報表

**互動式選單：**
```
選擇功能:
  1. 查看交易量 TOP 10 區域
  2. 比較多個區域年均價
  3. 查看特定區域月均價趨勢
  4. 房屋估價（單次）
  5. 批次估價（多種坪數）
  6. 匯出區域資料到 Excel
  7. 查看所有區域列表
  0. 離開
```

---

## 📊 資料說明

### 資料來源
- **來源：** 實價登錄 2.0
- **範圍：** 新北市 29 個行政區
- **期間：** 2018 年 ~ 2025 年
- **筆數：** 240,358 筆

### 新北市 29 區列表
```
板橋區、三重區、中和區、永和區、新莊區、新店區、樹林區、鶯歌區、三峽區
淡水區、汐止區、瑞芳區、土城區、蘆洲區、五股區、泰山區、林口區、深坑區
石碇區、坪林區、三芝區、石門區、八里區、平溪區、雙溪區、貢寮區、金山區
萬里區、烏來區
```

### 欄位說明

| 欄位 | 說明 | 單位 |
|------|------|------|
| `trade_date` | 交易日期 | YYYY-MM-DD |
| `district` | 行政區 | 文字 |
| `area_m2` | 建物面積 | 平方公尺 |
| `area_ping` | 建物面積 | 坪 |
| `price_total` | 總價 | 元 |
| `price_per_ping` | 每坪單價 | 萬元/坪 |
| `age_years` | 屋齡 | 年 |
| `risk_factor` | 風險係數 | 0~1 |
| `adj_price_per_ping` | 校正後單價 | 萬元/坪 |

### 風險係數計算

```python
def calculate_risk_factor(age_years):
    """
    基於屋齡的風險係數（Sigmoid 函數）
    age_years: 房屋屋齡（年）
    return: 0~1 的風險值
    """
    a0, k = 30.0, 0.12
    return 1.0 / (1.0 + math.exp(-k * (age_years - a0)))
```

**風險等級對照：**
- 0 歲：0.002（極低風險）
- 10 歲：0.074（低風險）
- 20 歲：0.259（中低風險）
- **30 歲：0.500**（臨界點）
- 40 歲：0.741（高風險）
- 50 歲：0.926（極高風險）

---

## ❓ 常見問題

### Q1: API 無法啟動？
**A:** 檢查以下事項：
- Python 版本是否 3.8+
- 是否安裝所有必要套件
- Port 8000 是否被佔用
- SQL 檔案是否存在

### Q2: 前端無法連接 API？
**A:** 
1. 確認 API 是否正在運行（`python app.py`）
2. 檢查瀏覽器 Console 是否有 CORS 錯誤
3. 確認 API URL 是否正確（`http://127.0.0.1:8000`）

### Q3: 為什麼有些區域查不到資料？
**A:** 
- 某些區域（如坪林區、烏來區）交易量較少
- 嘗試調整時間範圍或用途類型

### Q4: 估價結果準確嗎？
**A:** 
- 估價基於**近 24 個月**的中位數價格
- 已考慮**屋齡風險**校正
- 僅供參考，實際價格受多種因素影響

### Q5: 如何新增其他城市的資料？
**A:** 
1. 下載實價登錄資料
2. 轉換為相同格式的 SQL
3. 修改 `app.py` 的城市映射邏輯

### Q6: API 回應速度慢？
**A:** 
- 初次啟動需載入 24 萬筆資料（約 10-30 秒）
- 之後查詢會很快（< 1 秒）
- 可考慮加入 Redis 快取優化

---

## 📚 技術文件

### API 文件
啟動服務後訪問：http://127.0.0.1:8000/docs

### 開發工具
- **FastAPI**: https://fastapi.tiangolo.com/
- **Pandas**: https://pandas.pydata.org/
- **Chart.js**: https://www.chartjs.org/

---

## 👥 團隊成員

- **資料組** - 資料收集與清理
- **資料庫組** - MySQL 設計與查詢
- **AI 組** - 風險模型與估價算法
- **前端組** - 介面設計與整合

---

## 📝 授權

本專題為教育用途，資料來源為政府開放資料。

---

## 🎯 下一步計劃

- [ ] 加入 LightGBM 預測模型
- [ ] SHAP 可解釋性分析
- [ ] 整合淹水、液化潛勢資料
- [ ] 地圖視覺化（Folium）
- [ ] Redis 快取優化

---

**最後更新：** 2025-01-09  
**專題版本：** v1.0.0

如有問題請聯繫專題負責人或參考 [API 文件](http://127.0.0.1:8000/docs)。