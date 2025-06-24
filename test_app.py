import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import json

# 設置頁面配置
st.set_page_config(
    page_title="不良品管理系統 - 測試版",
    page_icon="🔧",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 自定義CSS
st.markdown("""
<style>
    .main-header {
        background: linear-gradient(90deg, #2563eb, #3b82f6);
        color: white;
        padding: 1rem;
        border-radius: 10px;
        text-align: center;
        margin-bottom: 2rem;
    }
    .metric-card {
        background: #f8fafc;
        padding: 1rem;
        border-radius: 8px;
        border-left: 4px solid #2563eb;
    }
</style>
""", unsafe_allow_html=True)

def main():
    # 頁面標題
    st.markdown('<div class="main-header"><h1>🔧 不良品管理系統 - 測試版</h1></div>', unsafe_allow_html=True)
    
    # 側邊欄
    with st.sidebar:
        st.header("📋 系統功能")
        page = st.selectbox(
            "選擇功能",
            ["儀表板", "測試數據", "系統狀態"]
        )
    
    if page == "儀表板":
        show_dashboard()
    elif page == "測試數據":
        show_test_data()
    elif page == "系統狀態":
        show_system_status()

def show_dashboard():
    st.header("📊 系統儀表板")
    
    # 基本指標
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("總產品數", "1,234", "12")
    with col2:
        st.metric("不良品數", "45", "-3")
    with col3:
        st.metric("合格率", "96.4%", "0.2%")
    with col4:
        st.metric("供應商數", "23", "1")
    
    # 簡單圖表
    st.subheader("📈 每日不良品趨勢")
    
    # 生成測試數據
    dates = pd.date_range(start='2024-06-01', end='2024-06-24', freq='D')
    data = pd.DataFrame({
        '日期': dates,
        '不良品數量': [2, 1, 3, 0, 2, 4, 1, 2, 3, 1, 0, 2, 1, 3, 2, 1, 4, 0, 2, 1, 3, 2, 1, 0]
    })
    
    fig = px.line(data, x='日期', y='不良品數量', 
                  title='每日不良品數量趨勢',
                  color_discrete_sequence=['#2563eb'])
    st.plotly_chart(fig, use_container_width=True)

def show_test_data():
    st.header("🧪 測試數據")
    
    # 創建測試數據
    test_data = pd.DataFrame({
        '產品編號': ['P001', 'P002', 'P003', 'P004', 'P005'],
        '產品名稱': ['電路板A', '電路板B', '電路板C', '電路板D', '電路板E'],
        '狀態': ['正常', '不良', '正常', '正常', '不良'],
        '檢測日期': ['2024-06-24', '2024-06-23', '2024-06-22', '2024-06-21', '2024-06-20']
    })
    
    st.dataframe(test_data, use_container_width=True)
    
    # 狀態分布圖
    status_counts = test_data['狀態'].value_counts()
    fig = px.pie(values=status_counts.values, names=status_counts.index,
                 title='產品狀態分布',
                 color_discrete_sequence=['#10b981', '#ef4444'])
    st.plotly_chart(fig, use_container_width=True)

def show_system_status():
    st.header("⚙️ 系統狀態")
    
    # 系統信息
    st.success("✅ 系統運行正常")
    st.info(f"📅 當前時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 環境信息
    with st.expander("🔧 環境信息"):
        st.write("- Python 版本: 3.11")
        st.write("- Streamlit 版本: 1.29.0")
        st.write("- 部署平台: Zeabur")
        st.write("- 狀態: 測試版運行中")
    
    # 測試按鈕
    if st.button("🧪 運行系統測試"):
        with st.spinner("正在運行測試..."):
            import time
            time.sleep(2)
        st.success("所有測試通過！")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        st.error(f"應用程序錯誤: {str(e)}")
        st.write("請聯繫系統管理員") 