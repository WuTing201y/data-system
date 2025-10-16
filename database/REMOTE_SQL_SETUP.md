# 遠端 SQL 檔案設定指引

## 🎯 目的
讓 Render 部署時自動從遠端下載 SQL 檔案，避免 Git 推送 27MB 大檔案的問題。

## 📋 設定步驟

### 方案 A：使用 GitHub Release（推薦）

1. **建立 Release 並上傳 SQL 檔案**
   
   在你的終端機執行：
   ```powershell
   # 1. 確保所有變更已提交
   git add .
   git commit -m "feat: support remote SQL download"
   git push origin main
   
   # 2. 建立 tag
   git tag v1.0
   git push origin v1.0
   ```

2. **在 GitHub 手動上傳 SQL 檔案**
   
   a. 到 https://github.com/WuTing201y/data-system/releases
   
   b. 點擊 "Create a new release"
   
   c. 選擇 tag: `v1.0`
   
   d. Release title: `v1.0 - Initial Data Release`
   
   e. 在 "Attach binaries" 區域，上傳 `houseDatabase_version_1.sql`
   
   f. 點擊 "Publish release"

3. **確認 URL**
   
   上傳後，右鍵點擊檔案 → "Copy link address"
   
   URL 應該類似：
   ```
   https://github.com/WuTing201y/data-system/releases/download/v1.0/houseDatabase_version_1.sql
   ```

4. **在 Render 設定環境變數（可選）**
   
   如果 URL 不同，到 Render Dashboard → Environment → 新增：
   ```
   REMOTE_SQL_URL=你的實際URL
   ```

### 方案 B：使用 Dropbox / Google Drive

1. **上傳檔案到雲端**
   
   - Dropbox: 取得分享連結，並將 `?dl=0` 改成 `?dl=1`
   - Google Drive: 需要設定為「任何人都可檢視」，並使用直接下載連結

2. **在 Render 設定環境變數**
   ```
   REMOTE_SQL_URL=你的雲端直接下載連結
   ```

### 方案 C：使用其他 Git Hosting

如 GitLab、Bitbucket 的 Release 或 LFS。

---

## 🔄 更新資料流程

之後當你有新資料時：

1. **更新本地 SQL 檔案**
   ```powershell
   # 假設你有新的資料匯出
   # 替換 houseDatabase_version_1.sql
   ```

2. **上傳新版本到 GitHub Release**
   ```powershell
   git tag v1.1
   git push origin v1.1
   ```
   
   然後到 GitHub 建立新 Release 並上傳新檔案

3. **更新 Render 環境變數**（如果 URL 改變）
   ```
   REMOTE_SQL_URL=https://github.com/WuTing201y/data-system/releases/download/v1.1/houseDatabase_version_1.sql
   ```

4. **觸發 Render 重新部署**
   
   方法 1：在 Render Dashboard 點擊 "Manual Deploy"
   
   方法 2：推送任何 commit 到 main

5. **清除舊快取（如果需要）**
   
   在 Render Shell 執行：
   ```bash
   rm /opt/render/project/src/database/houseDatabase_version_1.sql
   ```
   然後重新啟動服務

---

## ✅ 測試

本地測試：
```powershell
# 刪除本地 SQL 檔案測試自動下載
Remove-Item houseDatabase_version_1.sql
python -c "from app import _download_sql_if_needed; _download_sql_if_needed()"
```

---

## 🔍 故障排除

### 問題：下載失敗 404
- 檢查 Release 是否已發布
- 確認檔案名稱完全正確（大小寫）
- 確認 repository 是 public 或有正確權限

### 問題：下載太慢
- GitHub Release 下載速度通常很快
- 考慮使用 CDN 或其他檔案託管服務

### 問題：檔案太大無法上傳到 GitHub Release
- GitHub Release 單檔上限 2 GB，你的 27 MB 完全沒問題
- 如果真的太大，考慮壓縮（gzip）

---

## 📝 當前配置

- SQL 檔案大小: 27 MB
- 預設 URL: `https://github.com/WuTing201y/data-system/releases/download/v1.0/houseDatabase_version_1.sql`
- 本地快取位置: `database/houseDatabase_version_1.sql`
