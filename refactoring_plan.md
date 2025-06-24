# 🏗️ 不良品管理系統重構計劃

## 📋 重構目標

將4,861行的單一文件重構為模塊化、可維護的架構

## 🗂️ 建議的文件結構

```
不良品管理系統/
├── main.py                    # 主入口點 (簡化版)
├── config/
│   ├── __init__.py
│   ├── database.py           # 數據庫配置
│   └── settings.py           # 系統設置
├── models/
│   ├── __init__.py
│   ├── user.py               # 用戶模型
│   ├── defect.py             # 不良品模型
│   └── notification.py       # 通知模型
├── services/
│   ├── __init__.py
│   ├── auth_service.py       # 認證服務
│   ├── defect_service.py     # 不良品業務邏輯
│   ├── notification_service.py # 通知服務
│   └── analytics_service.py  # 分析服務
├── pages/
│   ├── __init__.py
│   ├── dashboard.py          # 儀表板頁面
│   ├── registration.py       # 登記頁面
│   ├── tracking.py           # 追蹤頁面
│   ├── analytics.py          # 分析頁面
│   └── settings.py           # 設置頁面
├── utils/
│   ├── __init__.py
│   ├── database_utils.py     # 數據庫工具
│   ├── ui_components.py      # UI組件
│   └── validators.py         # 驗證工具
└── tests/
    ├── __init__.py
    ├── test_models.py
    ├── test_services.py
    └── test_utils.py
```

## 🔧 重構步驟

### 步驟1: 提取模型層
```python
# models/defect.py
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

@dataclass
class Defect:
    id: Optional[int] = None
    work_order: str = ""
    product_name: str = ""
    defect_type: str = ""
    defect_level: str = ""
    quantity: int = 0
    description: str = ""
    responsible_dept: str = ""
    status: str = "待處理"
    created_time: Optional[datetime] = None
    updated_time: Optional[datetime] = None
    deadline: Optional[datetime] = None
    assigned_person: str = ""
    resolution: str = ""
    completion_time: Optional[datetime] = None
    logged_by: str = "系統"
```

### 步驟2: 提取服務層
```python
# services/defect_service.py
from typing import List, Optional
from models.defect import Defect
from utils.database_utils import DatabaseConnection

class DefectService:
    def __init__(self):
        self.db = DatabaseConnection()
    
    def add_defect(self, defect: Defect) -> bool:
        """添加不良品記錄"""
        # 業務邏輯實現
        pass
    
    def get_defects(self, status: Optional[str] = None) -> List[Defect]:
        """獲取不良品列表"""
        # 業務邏輯實現
        pass
    
    def update_defect_status(self, defect_id: int, new_status: str) -> bool:
        """更新不良品狀態"""
        # 業務邏輯實現
        pass
```

### 步驟3: 提取頁面組件
```python
# pages/dashboard.py
import streamlit as st
from services.defect_service import DefectService
from utils.ui_components import create_metric_card, create_chart

class DashboardPage:
    def __init__(self):
        self.defect_service = DefectService()
    
    def render(self):
        """渲染儀表板頁面"""
        st.header("📊 不良品管理儀表板")
        
        # 獲取數據
        defects = self.defect_service.get_defects()
        
        # 渲染指標卡片
        self._render_metrics(defects)
        
        # 渲染圖表
        self._render_charts(defects)
    
    def _render_metrics(self, defects):
        """渲染指標"""
        # 實現細節
        pass
    
    def _render_charts(self, defects):
        """渲染圖表"""
        # 實現細節
        pass
```

### 步驟4: 簡化主入口
```python
# main.py (重構後)
import streamlit as st
from services.auth_service import AuthService
from pages.dashboard import DashboardPage
from pages.registration import RegistrationPage
from pages.tracking import TrackingPage
from pages.analytics import AnalyticsPage
from pages.settings import SettingsPage
from config.database import init_database

def main():
    """主入口點"""
    # 初始化
    init_database()
    auth_service = AuthService()
    
    # 認證檢查
    if not auth_service.is_authenticated():
        auth_service.render_login_page()
        return
    
    # 頁面路由
    page_router = PageRouter()
    page_router.render()

class PageRouter:
    """頁面路由器"""
    
    def __init__(self):
        self.pages = {
            "📊 即時儀表板": DashboardPage(),
            "📋 不良品登錄": RegistrationPage(),
            "🔍 處理追蹤": TrackingPage(),
            "📈 統計分析": AnalyticsPage(),
            "⚙️ 系統設定": SettingsPage(),
        }
    
    def render(self):
        """渲染當前頁面"""
        page_name = st.sidebar.selectbox("選擇功能", list(self.pages.keys()))
        self.pages[page_name].render()

if __name__ == "__main__":
    main()
```

## 📈 重構效益

### 代碼質量改善
- ✅ **可維護性**: 每個模塊職責單一，易於維護
- ✅ **可測試性**: 分離的組件便於單元測試
- ✅ **可擴展性**: 新功能可以獨立開發
- ✅ **可讀性**: 代碼結構清晰，易於理解

### 開發效率提升
- ✅ **並行開發**: 多人可以同時開發不同模塊
- ✅ **錯誤隔離**: 問題定位更精確
- ✅ **重用性**: 組件可以在其他項目中重用

## ⏱️ 實施時間表

| 階段 | 時間 | 任務 |
|------|------|------|
| 第1週 | 1-2天 | 創建新的文件結構，提取模型層 |
| 第2週 | 2-3天 | 提取服務層，實現業務邏輯分離 |
| 第3週 | 2-3天 | 提取頁面組件，實現UI分離 |
| 第4週 | 1-2天 | 測試、調試、文檔更新 |

## 🧪 測試策略

### 單元測試
```python
# tests/test_defect_service.py
import unittest
from services.defect_service import DefectService
from models.defect import Defect

class TestDefectService(unittest.TestCase):
    
    def setUp(self):
        self.service = DefectService()
    
    def test_add_defect(self):
        """測試添加不良品"""
        defect = Defect(
            work_order="WO001",
            product_name="測試產品",
            defect_type="外觀不良",
            quantity=10
        )
        result = self.service.add_defect(defect)
        self.assertTrue(result)
    
    def test_get_defects(self):
        """測試獲取不良品列表"""
        defects = self.service.get_defects()
        self.assertIsInstance(defects, list)
```

## 🎯 成功指標

- [ ] 代碼行數: 主文件 < 200行
- [ ] 函數長度: 平均 < 20行
- [ ] 測試覆蓋率: > 80%
- [ ] Flake8檢查: 0個錯誤
- [ ] 啟動時間: < 3秒 