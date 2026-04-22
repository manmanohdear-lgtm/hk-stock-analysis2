import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

st.set_page_config(page_title="港股技術分析系統", page_icon="📈", layout="wide")

# ==================== 測試數據 ====================
MOCK_STOCK_DATA = {
    '00700': {'name': '騰訊控股', 'price': 385.6, 'turnover': 85.3,
              'ma5': 382.5, 'ma10': 380.2, 'ma15': 378.5, 'ma20': 375.2, 'ma50': 368.5, 'ma60': 365.2, 'ma250': 350.5,
              'boll_upper': 395.2, 'boll_mid': 375.2, 'boll_lower': 355.2,
              'rsi6': 62.5, 'rsi14': 58.5, 'rsi24': 55.2,
              'macd_dif': 1.23, 'macd_dea': 1.05,
              'kdj_k': 68.5, 'kdj_d': 62.3, 'kdj_j': 80.9},
    '09988': {'name': '阿里巴巴', 'price': 82.5, 'turnover': 45.2,
              'ma5': 81.2, 'ma10': 80.5, 'ma15': 79.8, 'ma20': 79.2, 'ma50': 76.5, 'ma60': 75.2, 'ma250': 72.5,
              'boll_upper': 85.2, 'boll_mid': 79.2, 'boll_lower': 73.2,
              'rsi6': 65.2, 'rsi14': 62.3, 'rsi24': 58.5,
              'macd_dif': 0.85, 'macd_dea': 0.72,
              'kdj_k': 72.5, 'kdj_d': 65.2, 'kdj_j': 87.1},
    '01810': {'name': '小米集團', 'price': 42.8, 'turnover': 28.6,
              'ma5': 42.2, 'ma10': 41.8, 'ma15': 41.5, 'ma20': 41.2, 'ma50': 40.2, 'ma60': 39.8, 'ma250': 38.5,
              'boll_upper': 43.8, 'boll_mid': 41.2, 'boll_lower': 38.6,
              'rsi6': 58.2, 'rsi14': 55.2, 'rsi24': 52.5,
              'macd_dif': 0.45, 'macd_dea': 0.38,
              'kdj_k': 58.5, 'kdj_d': 55.2, 'kdj_j': 65.1},
    '03690': {'name': '美團', 'price': 168.2, 'turnover': 52.8,
              'ma5': 166.5, 'ma10': 165.2, 'ma15': 164.5, 'ma20': 163.8, 'ma50': 158.5, 'ma60': 156.2, 'ma250': 148.5,
              'boll_upper': 172.5, 'boll_mid': 163.8, 'boll_lower': 155.1,
              'rsi6': 62.5, 'rsi14': 60.1, 'rsi24': 57.2,
              'macd_dif': 1.56, 'macd_dea': 1.32,
              'kdj_k': 65.2, 'kdj_d': 60.5, 'kdj_j': 74.6},
    '01024': {'name': '快手', 'price': 52.3, 'turnover': 18.4,
              'ma5': 51.8, 'ma10': 51.2, 'ma15': 50.8, 'ma20': 50.5, 'ma50': 49.2, 'ma60': 48.5, 'ma250': 46.5,
              'boll_upper': 53.5, 'boll_mid': 50.5, 'boll_lower': 47.5,
              'rsi6': 55.2, 'rsi14': 52.5, 'rsi24': 50.2,
              'macd_dif': 0.32, 'macd_dea': 0.28,
              'kdj_k': 52.5, 'kdj_d': 50.2, 'kdj_j': 57.1},
}

def get_mock_stock_data(code):
    code = code.upper().strip()
    if code in MOCK_STOCK_DATA:
        return MOCK_STOCK_DATA[code]
    return MOCK_STOCK_DATA['00700']

def parse_number(value):
    if value is None or value == "":
        return 0.0
    try:
        return float(value)
    except:
        return 0.0

def get_macd_status(dif, dea):
    return "金叉" if dif > dea else "死叉" if dif < dea else "持平"

# ==================== 初始化 Session State ====================
if 'current_stock' not in st.session_state:
    st.session_state.current_stock = "00700"
if 'stock_data' not in st.session_state:
    st.session_state.stock_data = None
if 'ma5' not in st.session_state:
    st.session_state.ma5 = ""
if 'ma10' not in st.session_state:
    st.session_state.ma10 = ""
if 'ma15' not in st.session_state:
    st.session_state.ma15 = ""
if 'ma20' not in st.session_state:
    st.session_state.ma20 = ""
if 'ma50' not in st.session_state:
    st.session_state.ma50 = ""
if 'ma60' not in st.session_state:
    st.session_state.ma60 = ""
if 'ma250' not in st.session_state:
    st.session_state.ma250 = ""
if 'boll_upper' not in st.session_state:
    st.session_state.boll_upper = ""
if 'boll_mid' not in st.session_state:
    st.session_state.boll_mid = ""
if 'boll_lower' not in st.session_state:
    st.session_state.boll_lower = ""
if 'rsi6' not in st.session_state:
    st.session_state.rsi6 = ""
if 'rsi14' not in st.session_state:
    st.session_state.rsi14 = ""
if 'rsi24' not in st.session_state:
    st.session_state.rsi24 = ""
if 'macd_dif' not in st.session_state:
    st.session_state.macd_dif = ""
if 'macd_dea' not in st.session_state:
    st.session_state.macd_dea = ""
if 'macd_hist' not in st.session_state:
    st.session_state.macd_hist = ""
if 'kdj_k' not in st.session_state:
    st.session_state.kdj_k = ""
if 'kdj_d' not in st.session_state:
    st.session_state.kdj_d = ""
if 'kdj_j' not in st.session_state:
    st.session_state.kdj_j = ""

# ==================== 側邊欄 ====================
with st.sidebar:
    st.title("📈 功能選單")
    st.divider()
    st.markdown("**📡 系統狀態**")
    st.success("✅ 雲端版運行中")
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

# ==================== 主頁面 ====================
st.markdown("""
<div style="text-align:center; padding:1rem; background:linear-gradient(135deg,#667eea,#764ba2); border-radius:10px; margin-bottom:2rem">
    <h1 style="color:white">📈 港股技術分析</h1>
    <p style="color:rgba(255,255,255,0.8)">移動平均線 | 布林帶 | RSI | MACD | KDJ</p>
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
            data = st.session_state.stock_data
            st.session_state.ma5 = str(data['ma5'])
            st.session_state.ma10 = str(data['ma10'])
            st.session_state.ma15 = str(data['ma15'])
            st.session_state.ma20 = str(data['ma20'])
            st.session_state.ma50 = str(data['ma50'])
            st.session_state.ma60 = str(data['ma60'])
            st.session_state.ma250 = str(data['ma250'])
            st.session_state.boll_upper = str(data['boll_upper'])
            st.session_state.boll_mid = str(data['boll_mid'])
            st.session_state.boll_lower = str(data['boll_lower'])
            st.session_state.rsi6 = str(data['rsi6'])
            st.session_state.rsi14 = str(data['rsi14'])
            st.session_state.rsi24 = str(data['rsi24'])
            st.session_state.macd_dif = str(data['macd_dif'])
            st.session_state.macd_dea = str(data['macd_dea'])
            st.session_state.macd_hist = f"{data['macd_dif'] - data['macd_dea']:.4f}"
            st.session_state.kdj_k = str(data['kdj_k'])
            st.session_state.kdj_d = str(data['kdj_d'])
            st.session_state.kdj_j = str(data['kdj_j'])
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
        price = st.number_input("股價", value=data['price'], step=0.1, format="%.2f", key="price_input")
    with col3:
        st.metric("成交額", f"{data['turnover']:.1f}億")
    with col4:
        st.caption("52週高/低")
        st.number_input("52週高", value=None, step=0.1, format="%.2f", placeholder="高", key="high_52w", label_visibility="collapsed")
        st.number_input("52週低", value=None, step=0.1, format="%.2f", placeholder="低", key="low_52w", label_visibility="collapsed")
    
    st.caption("💡 做空數據（選填）")
    col1, col2 = st.columns(2)
    with col1:
        st.number_input("做空成交量 (萬股)", value=None, step=1.0, format="%.0f", placeholder="選填", key="short_volume")
    with col2:
        st.number_input("做空成交額 (億)", value=None, step=0.1, format="%.2f", placeholder="選填", key="short_turnover")
    
    st.divider()
    
    # 移動平均線 MA
    st.subheader("📈 移動平均線 (MA)")
    st.caption("💡 直接輸入數字，按 Tab 跳到下一欄")
    
    col1, col2, col3, col4, col5, col6, col7 = st.columns(7)
    with col1:
        st.text_input("MA5", value=st.session_state.ma5, placeholder="0", key="ma5")
    with col2:
        st.text_input("MA10", value=st.session_state.ma10, placeholder="0", key="ma10")
    with col3:
        st.text_input("MA15", value=st.session_state.ma15, placeholder="0", key="ma15")
    with col4:
        st.text_input("MA20", value=st.session_state.ma20, placeholder="0", key="ma20")
    with col5:
        st.text_input("MA50", value=st.session_state.ma50, placeholder="0", key="ma50")
    with col6:
        st.text_input("MA60", value=st.session_state.ma60, placeholder="0", key="ma60")
    with col7:
        st.text_input("MA250", value=st.session_state.ma250, placeholder="0", key="ma250")
    
    st.divider()
    
    # 布林帶 BOLL
    st.subheader("📊 布林帶 (BOLL 20,2)")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.text_input("BOLL上軌", value=st.session_state.boll_upper, placeholder="0", key="boll_upper")
    with col2:
        st.text_input("BOLL中軌", value=st.session_state.boll_mid, placeholder="0", key="boll_mid")
    with col3:
        st.text_input("BOLL下軌", value=st.session_state.boll_lower, placeholder="0", key="boll_lower")
    
    st.divider()
    
    # RSI
    st.subheader("📊 RSI (相對強弱指數)")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.text_input("RSI(6)", value=st.session_state.rsi6, placeholder="0", key="rsi6")
    with col2:
        st.text_input("RSI(14)", value=st.session_state.rsi14, placeholder="0", key="rsi14")
    with col3:
        st.text_input("RSI(24)", value=st.session_state.rsi24, placeholder="0", key="rsi24")
    
    st.divider()
    
    # MACD
    st.subheader("📉 MACD (12,26,9)")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.text_input("DIF", value=st.session_state.macd_dif, placeholder="0", key="macd_dif")
    with col2:
        st.text_input("DEA", value=st.session_state.macd_dea, placeholder="0", key="macd_dea")
    with col3:
        st.text_input("MACD柱", value=st.session_state.macd_hist, placeholder="0", key="macd_hist", disabled=True)
    
    st.divider()
    
    # KDJ
    st.subheader("📈 KDJ (9,3,3)")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.text_input("K值", value=st.session_state.kdj_k, placeholder="0", key="kdj_k")
    with col2:
        st.text_input("D值", value=st.session_state.kdj_d, placeholder="0", key="kdj_d")
    with col3:
        st.text_input("J值", value=st.session_state.kdj_j, placeholder="0", key="kdj_j")
    
    st.divider()
    
    # 解析數值
    p = price if isinstance(price, (int, float)) else data['price']
    ma20_num = parse_number(st.session_state.ma20)
    r14 = parse_number(st.session_state.rsi14)
    dif = parse_number(st.session_state.macd_dif)
    dea = parse_number(st.session_state.macd_dea)
    to = data['turnover']
    bias20 = (p - ma20_num) / ma20_num * 100 if ma20_num > 0 else 0
    boll_upper_num = parse_number(st.session_state.boll_upper)
    boll_lower_num = parse_number(st.session_state.boll_lower)
    
    # MACD 狀態
    st.subheader("📉 MACD 狀態")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("DIF", f"{dif:.4f}")
    with col2:
        st.metric("DEA", f"{dea:.4f}")
    with col3:
        st.metric("MACD柱", f"{dif - dea:.4f}")
    
    macd_status = get_macd_status(dif, dea)
    if macd_status == "金叉":
        st.success("✅ 金叉 (黃金交叉)")
    elif macd_status == "死叉":
        st.error("❌ 死叉 (死亡交叉)")
    else:
        st.info("📊 MACD 持平")
    
    st.divider()
    
    # 交易信號
    st.subheader("🎯 交易信號")
    
    cond1 = p > ma20_num if ma20_num > 0 else False
    cond2 = r14 > 50 if r14 > 0 else False
    cond3 = dif > dea
    cond4 = to > 0.3
    
    total_score = sum([cond1, cond2, cond3, cond4])
    
    if boll_lower_num > 0 and p < boll_lower_num:
        total_score += 1
    elif boll_upper_num > 0 and p > boll_upper_num:
        total_score -= 1
    
    if total_score >= 5:
        signal = "🔴 強烈買入"
        color = "#00ff00"
    elif total_score >= 4:
        signal = "🟢 買入"
        color = "#00cc00"
    elif total_score >= 3:
        signal = "🟡 持有 / 觀望"
        color = "#ffaa00"
    elif total_score >= 2:
        signal = "⚪ 謹慎"
        color = "#ff8800"
    else:
        signal = "⚫ 賣出 / 迴避"
        color = "#ff4444"
    
    st.markdown(f'<div style="background-color:{color}; color:#000; padding:10px; border-radius:5px; font-weight:bold; text-align:center">{signal}</div>', unsafe_allow_html=True)
    
    st.divider()
    
    # 條件詳細判斷
    with st.expander("📋 條件詳細判斷"):
        st.write(f"① 股價 > MA20: {p:.2f} > {ma20_num:.2f} → {'✅' if cond1 else '❌'}")
        st.write(f"② RSI(14) > 50: {r14:.1f} > 50 → {'✅' if cond2 else '❌'}")
        st.write(f"③ MACD 金叉: {dif:.4f} > {dea:.4f} → {'✅' if cond3 else '❌'}")
        st.write(f"④ 成交額 > 0.3億: {to:.2f} > 0.3 → {'✅' if cond4 else '❌'}")
        if boll_upper_num > 0 and boll_lower_num > 0:
            if p < boll_lower_num:
                st.write(f"⑤ 布林帶: 🟢 跌破下軌，反彈機會")
            elif p > boll_upper_num:
                st.write(f"⑤ 布林帶: 🔴 突破上軌，可能過熱")
            else:
                st.write(f"⑤ 布林帶: 🟡 在通道內")
    
else:
    st.info("請輸入股票代碼並點擊「載入數據」開始分析")
    st.markdown("""
    ### 📌 可用測試代碼：
    | 代碼 | 名稱 |
    |:---|:---|
    | 00700 | 騰訊控股 |
    | 09988 | 阿里巴巴 |
    | 01810 | 小米集團 |
    | 03690 | 美團 |
    | 01024 | 快手 |
    """)

st.divider()
st.caption("📌 測試版本 | 使用模擬數據 | 正式版將連接真實數據源")
