#!/bin/bash

# 🚀 不良品管理系統 - Zeabur 快速部署腳本

echo "🚀 開始準備 Zeabur 部署..."

# 檢查 Git 狀態
echo "📋 檢查 Git 狀態..."
git status

# 確認所有文件已添加
echo "✅ 添加所有文件到 Git..."
git add .

# 提交更改
echo "💾 提交更改..."
git commit -m "準備 Zeabur 部署 - $(date '+%Y-%m-%d %H:%M:%S')"

echo "
🎯 下一步驟：

1. 創建 GitHub 儲存庫：
   - 前往：https://github.com/new
   - 名稱：defect-management-system
   - 不要初始化任何文件

2. 推送代碼到 GitHub：
   請替換 'YOUR_USERNAME' 為您的 GitHub 用戶名
   
   git remote add origin https://github.com/YOUR_USERNAME/defect-management-system.git
   git push -u origin main

3. 在 Zeabur 部署：
   - 前往：https://zeabur.com
   - 點擊 'Create Project'
   - 選擇 'Deploy from GitHub'
   - 選擇您的 defect-management-system 儲存庫
   - 點擊 'Deploy'

4. 設置環境變數（在 Zeabur 控制台）：
   STREAMLIT_SERVER_PORT=8501
   STREAMLIT_SERVER_ADDRESS=0.0.0.0

✅ 所有配置文件已準備完成！
📖 詳細說明請參考：ZEABUR_DEPLOYMENT.md
"

# 檢查配置文件
echo "🔍 檢查配置文件..."
ls -la requirements.txt Dockerfile zeabur.json .streamlit/config.toml .gitignore

echo "�� 部署準備完成！請按照上述步驟進行！" 