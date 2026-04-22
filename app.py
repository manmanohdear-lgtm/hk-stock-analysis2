import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

st.set_page_config(page_title="港股分析系統", page_icon="📈", layout="wide")

# ==================== 測試數據 ====================
MOCK_STOCK_DATA = {
    '00700': {'name': '騰訊控股', 'price': 385.6, 'ma20': 380.2, 'rsi14': 58.5, 'turnover': 85.3, 'macd_dif': 1.23, 'macd_dea': 1.05},
    '09988': {'name': '阿里巴巴', 'price': 82.5, 'ma20': 80.1, 'rsi14': 62.3, 'turnover': 45.2, 'macd_dif': 0.85, 'macd_dea': 0.72},
    '01810': {'name': '小米集團', 'price': 42.8, 'ma20': 41.5, 'rsi14': 55.2, 'turnover': 28.6, 'macd_dif': 0.45, 'macd_dea': 0.38},
    '03690': {'name': '美團', 'price': 168.2, 'ma20': 165.0, 'rsi14': 60.1, 'turnover': 52.8, 'macd_dif': 1.56, 'macd_dea': 1.32},
    '01024': {'name': '快手', 'price': 52.3, 'ma20': 50.8, 'rsi14': 52.5, 'turnover': 18.4, 'macd_dif': 0.32, 'macd_dea': 0.28},
}

def get_mock_stock_data(code):
    """獲取測試數據"""
    code = code.upper().strip()
    if code in MOCK_STOCK_DATA:
        return MOCK_STOCK_DATA[code]
    # 默認返回騰訊數據
    return MOCK_STOCK_DATA['00700']

# ==================== 初始化 Session State ====================
if 'current_stock' not in st.session_state:
    st.session_state.current_stock = "00700"
if 'stock_data' not in st.session_state:
    st.session_state.stock_data = None

# ==================== 側邊欄 ====================
with st.sidebar:
    st.title("📈 功能選單")
    st.divider()
    st.markdown("**📡 系統狀態**")
    st.success("✅ 測試版運行中")
    st.caption(f"啟動時間: {datetime.now().strftime('%H:%M:%S')}")
    st.divider()
    st.markdown("### 可用測試代碼")
    st.code("""
00700 - 騰訊控股
09988 - 阿里巴巴
01810 - 小米集團
03690 - 美團
01024 - 快手
    """)
    st.info("💡 輸入股票代碼後點擊「載入數據」")

# ==================== 主頁面 ====================
st.markdown("""
<div style="text-align:center; padding:1rem; background:linear-gradient(135deg,#667eea,#764ba2); border-radius:10px; margin-bottom:2rem">
    <h1 style="color:white">📈 港股技術分析</h1>
    <p style="color:rgba(255,255,255,0.8)">測試版本 | 使用模擬數據</p>
</div>
""", unsafe_allow_html=True)

# 股票搜尋
col1, col2 = st.columns([3, 1])
with col1:
    stock_code = st.text_input("股票代碼", value=st.session_state.current_stock, placeholder="例如：00700", key="stock_code")
with col2:
    if st.button("🔍 載入數據", type="primary", use_container_width=True):
        if stock_code:
            st.session_state.current_stock = stock_code.upper().strip()
            st.session_state.stock_data = get_mock_stock_data(st.session_state.current_stock)
            st.rerun()

st.divider()

# 顯示數據
if st.session_state.stock_data:
    data = st.session_state.stock_data
    
    st.subheader("📊 基本數據")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("股票名稱", data['name'])
    with col2:
        st.metric("股價", f"${data['price']:.2f}")
    with col3:
        st.metric("成交額", f"{data['turnover']:.1f}億")
    with col4:
        st.metric("RSI(14)", f"{data['rsi14']:.1f}")
    
    st.divider()
    
    st.subheader("📈 移動平均線")
    col1, col2, col3 = st.columns(3)
    with col1:
        ma20 = st.number_input("MA20", value=data['ma20'], step=0.1, format="%.2f")
    with col2:
        st.metric("乖離率", f"{(data['price'] - ma20) / ma20 * 100:.2f}%")
    with col3:
        pass
    
    st.divider()
    
    st.subheader("📉 MACD 狀態")
    col1, col2 = st.columns(2)
    with col1:
        st.metric("DIF", f"{data['macd_dif']:.4f}")
    with col2:
        st.metric("DEA", f"{data['macd_dea']:.4f}")
    
    if data['macd_dif'] > data['macd_dea']:
        st.success("✅ 金叉 (黃金交叉)")
    else:
        st.error("❌ 死叉 (死亡交叉)")
    
    st.divider()
    
    st.subheader("🎯 交易信號")
    
    # 計算信號
    cond1 = data['price'] > ma20
    cond2 = data['rsi14'] > 50
    cond3 = data['macd_dif'] > data['macd_dea']
    cond4 = data['turnover'] > 0.3
    
    total_score = sum([cond1, cond2, cond3, cond4])
    
    if total_score >= 4:
        signal = "🔴 強烈買入"
        color = "#00ff00"
    elif total_score >= 3:
        signal = "🟢 買入"
        color = "#00cc00"
    elif total_score >= 2:
        signal = "🟡 持有 / 觀望"
        color = "#ffaa00"
    elif total_score >= 1:
        signal = "⚪ 謹慎"
        color = "#ff8800"
    else:
        signal = "⚫ 賣出 / 迴避"
        color = "#ff4444"
    
    st.markdown(f'<div style="background-color:{color}; color:#000; padding:10px; border-radius:5px; font-weight:bold; text-align:center">{signal}</div>', unsafe_allow_html=True)
    
    # 詳細判斷
    with st.expander("📋 條件詳細判斷"):
        st.write(f"① 股價 > MA20: {data['price']:.2f} > {ma20:.2f} → {'✅' if cond1 else '❌'}")
        st.write(f"② RSI(14) > 50: {data['rsi14']:.1f} > 50 → {'✅' if cond2 else '❌'}")
        st.write(f"③ MACD 金叉: {data['macd_dif']:.4f} > {data['macd_dea']:.4f} → {'✅' if cond3 else '❌'}")
        st.write(f"④ 成交額 > 0.3億: {data['turnover']:.2f} > 0.3 → {'✅' if cond4 else '❌'}")
    
else:
    st.info("請輸入股票代碼並點擊「載入數據」開始分析")
    st.markdown("""
    ### 📌 可用測試代碼：
    - `00700` - 騰訊控股
    - `09988` - 阿里巴巴
    - `01810` - 小米集團
    - `03690` - 美團
    - `01024` - 快手
    """)

# ==================== 頁腳 ====================
st.divider()
st.caption("📌 測試版本 | 使用模擬數據 | 正式版將連接真實數據源")
