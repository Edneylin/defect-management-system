# 🚀 不良品管理系統 - Zeabur 部署指南

## 📋 部署前準備

### 1. 確認文件準備完成
- ✅ `requirements.txt` - Python 依賴套件
- ✅ `Dockerfile` - 容器配置
- ✅ `zeabur.json` - Zeabur 配置
- ✅ `.streamlit/config.toml` - Streamlit 配置
- ✅ `.gitignore` - Git 忽略文件
- ✅ `defect_management_system.py` - 主程式

### 2. Git 儲存庫
```bash
# 已完成初始化
git status  # 確認提交狀態
```

## 🌐 部署到 Zeabur

### 步驟 1：創建 GitHub 儲存庫

1. **前往 GitHub**：https://github.com
2. **創建新儲存庫**：
   - 點擊 "+" → "New repository"
   - Repository name: `defect-management-system`
   - Description: `不良品管理系統 - Streamlit Web 應用`
   - 設為 Public 或 Private
   - **不要**初始化 README、.gitignore、license

3. **推送本地代碼**：
```bash
git remote add origin https://github.com/您的用戶名/defect-management-system.git
git branch -M main
git push -u origin main
```

### 步驟 2：在 Zeabur 部署

1. **前往 Zeabur**：https://zeabur.com
2. **註冊/登錄帳號**
3. **創建新專案**：
   - 點擊 "Create Project"
   - 選擇 "Deploy from GitHub"
   - 選擇您的 `defect-management-system` 儲存庫

4. **配置部署設置**：
   - **Service Name**: `defect-management-system`
   - **Environment**: Production
   - **Build Command**: 自動檢測（使用 Dockerfile）
   - **Start Command**: 自動檢測

5. **環境變數設置**：
   ```
   STREAMLIT_SERVER_PORT=8501
   STREAMLIT_SERVER_ADDRESS=0.0.0.0
   ```

6. **點擊 Deploy**

### 步驟 3：域名設置

1. **生成域名**：
   - 部署完成後，Zeabur 會自動分配一個域名
   - 格式：`https://your-app-name.zeabur.app`

2. **自定義域名**（可選）：
   - 在 Zeabur 控制台設置自定義域名
   - 配置 DNS 記錄

## ⚙️ 部署配置說明

### 自動檢測配置
Zeabur 會自動檢測：
- **Python 版本**：從 `runtime.txt` 或 Dockerfile
- **依賴套件**：從 `requirements.txt`
- **啟動命令**：從 `Dockerfile` 的 CMD

### 資料庫配置
- 使用 SQLite 資料庫
- 自動創建必要的表格
- 資料會持久化在容器中

### 主題配色
使用科技感淺藍色配色方案：
- 主色：`#2563eb`
- 背景：`#ffffff`
- 次要背景：`#f8fafc`
- 文字：`#1e293b`

## 🔧 故障排除

### 常見問題

1. **部署失敗**：
   ```bash
   # 檢查 requirements.txt 格式
   pip install -r requirements.txt
   
   # 測試本地運行
   streamlit run defect_management_system.py
   ```

2. **端口問題**：
   - Zeabur 自動處理端口映射
   - 確保 Dockerfile 暴露 8501 端口

3. **依賴問題**：
   ```bash
   # 更新依賴
   pip freeze > requirements.txt
   git add requirements.txt
   git commit -m "更新依賴"
   git push
   ```

### 監控和日誌
- 在 Zeabur 控制台查看部署日誌
- 監控應用程式狀態
- 查看運行時錯誤

## 📊 功能確認清單

部署完成後確認以下功能：

- [ ] 🔐 用戶登錄系統
- [ ] 📝 不良品登錄功能
- [ ] 📈 數據分析儀表板
- [ ] 🔍 不良品查詢功能
- [ ] 📧 通知系統（如已配置）
- [ ] 👥 人員管理
- [ ] 🏭 供應商管理
- [ ] 📊 統計報表

## 🎯 後續維護

### 更新部署
```bash
# 修改代碼後
git add .
git commit -m "功能更新"
git push

# Zeabur 會自動重新部署
```

### 備份資料
- 定期下載 SQLite 資料庫文件
- 備份配置文件

## 🔗 相關連結

- **Zeabur 文檔**：https://docs.zeabur.com
- **Streamlit 文檔**：https://docs.streamlit.io
- **支援聯絡**：請聯繫系統管理員

---
**部署完成！** 🎉 您的不良品管理系統現在可以在雲端訪問了！ 