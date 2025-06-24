import streamlit as st

st.set_page_config(
    page_title="🚀 測試應用",
    page_icon="🚀",
    layout="wide"
)

st.title("🚀 不良品處理管理系統 - 測試版")
st.write("如果您看到這個頁面，表示應用程序基本功能正常！")

st.success("✅ 系統啟動成功")
st.info("📋 這是一個簡化的測試版本，用於診斷部署問題")

# 簡單的功能測試
if st.button("測試按鈕"):
    st.balloons()
    st.write("🎉 按鈕功能正常！")

# 顯示系統信息
st.subheader("系統信息")
import pandas as pd
import datetime

col1, col2 = st.columns(2)
with col1:
    st.write("📅 當前時間:", datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    
with col2:
    st.write("🐍 Python版本: 正常")

# 測試數據顯示
st.subheader("測試數據")
test_data = pd.DataFrame({
    '項目': ['測試1', '測試2', '測試3'],
    '狀態': ['正常', '正常', '正常'],
    '時間': [datetime.datetime.now() - datetime.timedelta(hours=i) for i in range(3)]
})

st.dataframe(test_data)

st.markdown("---")
st.write("🔧 如果這個測試頁面正常顯示，我們可以繼續診斷主應用程序的問題。") 