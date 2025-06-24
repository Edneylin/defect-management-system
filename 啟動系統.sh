#!/bin/bash

echo "🚀 啟動企業級不良品管理系統..."
echo "================================"

# 切換到系統目錄
cd "/Users/edney/Cursor/defect_management_system "

# 檢查文件是否存在
if [ ! -f "defect_management_system.py" ]; then
    echo "❌ 錯誤：找不到 defect_management_system.py 文件"
    exit 1
fi

# 檢查虛擬環境
if [ ! -d "/Users/edney/Cursor/.venv" ]; then
    echo "❌ 錯誤：找不到虛擬環境"
    exit 1
fi

# 激活虛擬環境並啟動系統
echo "📋 正在啟動系統..."
echo "🌐 系統網址：http://localhost:8507"
echo "🔐 管理員帳號：admin / admin123"
echo "================================"

source "/Users/edney/Cursor/.venv/bin/activate"
streamlit run defect_management_system.py --server.port 8507

echo "系統已關閉" 