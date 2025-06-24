#!/bin/bash

# 啟動腳本 - 確保 Streamlit 應用正確啟動

echo "🚀 啟動不良品管理系統..."

# 檢查Python環境
echo "Python版本: $(python --version)"
echo "Streamlit版本: $(streamlit version)"

# 檢查必要文件
if [ ! -f "defect_management_system.py" ]; then
    echo "❌ 錯誤: defect_management_system.py 文件不存在"
    exit 1
fi

# 檢查配置文件
if [ ! -f ".streamlit/config.toml" ]; then
    echo "⚠️  警告: .streamlit/config.toml 文件不存在，使用默認配置"
fi

# 創建必要目錄
mkdir -p data
mkdir -p .streamlit

echo "✅ 環境檢查完成"

# 啟動 Streamlit
echo "🌐 啟動 Streamlit 服務器..."
streamlit run defect_management_system.py \
    --server.port=8501 \
    --server.address=0.0.0.0 \
    --server.headless=true \
    --server.enableCORS=false \
    --server.enableXsrfProtection=false \
    --browser.gatherUsageStats=false 