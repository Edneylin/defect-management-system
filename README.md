# 不良品管理系統

## 系統概述

這是一個基於 Streamlit 框架開發的智能不良品處理管理系統，採用淺藍色科技風格設計，提供友善直覺的用戶界面。系統整合了多種功能模組，支援完整的不良品處理流程管理。

## 主要功能模組

### 🎯 核心功能
- **即時儀表板** - 即時監控不良品統計資訊
- **不良品登錄** - 支援包數管理的不良品資料輸入
- **處理追蹤** - 簽核流程管理（主要/次要單位責任制）
- **統計分析** - AI智能分析與報告生成
- **系統設定** - 人員、產品、通知等設定管理

### 🔄 簽核流程
- **外觀相關不良品**：品保主責 → 工程次責
- **其他不良類型**：工程主責 → 品保次責
- **簽核機制**：提交簽核 → 通過/退回機制

### 🔧 管理功能
- **人員管理** - 使用者權限與認證系統
- **產品管理** - 產品與零件供應商管理
- **通知系統** - 郵件、Telegram 多渠道通知
- **權限控制** - 多層級權限管理

## 系統架構

```
不良品管理系統/
├── defect_management_system.py    # 主系統程式
├── defect_management.db          # SQLite 資料庫
├── run_system.py                 # 系統啟動腳本
├── requirements.txt              # Python 依賴套件
├── 配置文件/                     # 系統配置檔案
│   ├── notification_settings.json
│   ├── operator_settings.json
│   ├── personnel_settings.json
│   └── product_settings.json
└── 文檔說明/                     # 功能說明文件
    ├── README_不良品管理系統.md
    ├── README_AI智能分析總結功能說明.md
    ├── README_人員管理功能說明.md
    ├── README_通知功能使用說明.md
    └── ... (其他功能說明文件)
```

## 快速開始

### 1. 安裝依賴
```bash
cd 不良品管理系統
pip install -r requirements.txt
```

### 2. 啟動系統
```bash
# 方法一：使用啟動腳本
python run_system.py

# 方法二：直接啟動
streamlit run defect_management_system.py
```

### 3. 訪問系統
系統啟動後會自動開啟瀏覽器，或手動訪問：`http://localhost:8501`

## 主要特色

### 🎨 界面設計
- 採用淺藍色科技感配色方案
- 響應式設計，支援多種螢幕尺寸
- 友善直覺的用戶體驗

### 🤖 AI 智能功能
- 智能分析與報告生成
- 異常趨勢檢測
- 自動化處理建議

### 📊 數據管理
- SQLite 輕量級資料庫
- 完整的資料備份與恢復
- 多格式資料導出（Excel、CSV）

### 🔔 通知系統
- 多渠道通知支援（郵件、Telegram）
- 可自定義通知規則
- 即時處理狀態推送

## 配置說明

### 通知設定
- 編輯 `配置文件/notification_settings.json`
- 設定郵件服務器和 Telegram Bot 資訊

### 人員管理
- 編輯 `配置文件/personnel_settings.json`
- 設定用戶權限和部門資訊

### 產品設定
- 編輯 `配置文件/product_settings.json`
- 設定產品類型和供應商資訊

## 技術規格

- **框架**: Streamlit
- **資料庫**: SQLite
- **語言**: Python 3.x
- **主要套件**: pandas, plotly, sqlite3
- **支援平台**: Windows, macOS, Linux

## 版本更新

系統持續優化中，詳細的功能更新說明請參考 `文檔說明/` 資料夾中的各項功能說明文件。

## 支援與維護

如需技術支援或功能改進建議，請參考相關文檔或聯繫系統管理員。

---

**開發團隊**: 內部研發部門  
**最後更新**: 2024年