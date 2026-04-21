import streamlit as st

st.set_page_config(page_title="測試", page_icon="📈", layout="wide")

st.title("🎉 港股美股技術分析系統")

st.markdown("""
### ✅ 網站成功運行了！

如果你看到這個畫面，表示 Streamlit Cloud 部署成功。

接下來我們可以慢慢恢復完整功能。
""")

st.success("部署成功！")

# 顯示一些系統資訊
import sys
st.write(f"Python 版本: {sys.version}")

st.info("請告訴我你看到這個畫面了！")
