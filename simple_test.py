import streamlit as st
import datetime
import os

st.set_page_config(
    page_title="🚀 部署測試",
    page_icon="🚀",
    layout="wide"
)

st.title("🚀 不良品管理系統 - 部署測試版")

# 基本信息顯示
st.success("✅ 應用程序啟動成功！")
st.info("�� 這是簡化測試版本，用於驗證Zeabur部署配置")

# 系統信息
col1, col2 = st.columns(2)

with col1:
    st.subheader("🔧 系統狀態")
    st.write("📅 當前時間:", datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    st.write("🐍 Python版本: 正常")
    st.write("📦 Streamlit版本: 正常")

with col2:
    st.subheader("🌐 環境變數")
    st.write("🏠 工作目錄:", os.getcwd())
    st.write("🔌 端口:", os.environ.get('STREAMLIT_SERVER_PORT', '8501'))
    st.write("📡 地址:", os.environ.get('STREAMLIT_SERVER_ADDRESS', '0.0.0.0'))

# 互動測試
st.subheader("🎮 功能測試")
if st.button("🎉 測試按鈕"):
    st.balloons()
    st.success("🎊 按鈕功能正常！")

# 輸入測試
user_input = st.text_input("✏️ 輸入測試", "Hello Zeabur!")
if user_input:
    st.write(f"✨ 您輸入了: {user_input}")

# 資料庫目錄測試
st.subheader("📁 目錄結構測試")
try:
    os.makedirs('data', exist_ok=True)
    st.success("✅ data目錄創建成功")
    
    # 列出目錄內容
    current_files = os.listdir('.')
    st.write("📂 當前目錄文件:", current_files)
    
except Exception as e:
    st.error(f"❌ 目錄操作失敗: {e}")

st.markdown("---")
st.markdown("### 🎯 如果您看到這個頁面，表示基本配置正確！")
st.markdown("接下來可以嘗試部署完整版本的應用程序。")
