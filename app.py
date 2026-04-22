import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import json
import os
import re
import warnings
warnings.filterwarnings('ignore')

st.set_page_config(page_title="港股美股技術分析系統", page_icon="📈", layout="wide")

# ==================== 測試數據 ====================
MOCK_STOCK_DATA = {
    '00700': {'name': '騰訊控股', 'price': 385.6, 'turnover': 85.3, 'volume': 2210,
              'ma5': 382.5, 'ma10': 380.2, 'ma15': 378.5, 'ma20': 375.2, 'ma50': 368.5, 'ma60': 365.2, 'ma250': 350.5,
              'boll_upper': 395.2, 'boll_mid': 375.2, 'boll_lower': 355.2,
              'rsi6': 62.5, 'rsi14': 58.5, 'rsi24': 55.2,
              'macd_dif': 1.23, 'macd_dea': 1.05,
              'kdj_k': 68.5, 'kdj_d': 62.3, 'kdj_j': 80.9,
              'high_52w': 420.0, 'low_52w': 280.0},
    '09988': {'name': '阿里巴巴', 'price': 82.5, 'turnover': 45.2, 'volume': 5480,
              'ma5': 81.2, 'ma10': 80.5, 'ma15': 79.8, 'ma20': 79.2, 'ma50': 76.5, 'ma60': 75.2, 'ma250': 72.5,
              'boll_upper': 85.2, 'boll_mid': 79.2, 'boll_lower': 73.2,
              'rsi6': 65.2, 'rsi14': 62.3, 'rsi24': 58.5,
              'macd_dif': 0.85, 'macd_dea': 0.72,
              'kdj_k': 72.5, 'kdj_d': 65.2, 'kdj_j': 87.1,
              'high_52w': 95.0, 'low_52w': 60.0},
    '01810': {'name': '小米集團', 'price': 42.8, 'turnover': 28.6, 'volume': 6680,
              'ma5': 42.2, 'ma10': 41.8, 'ma15': 41.5, 'ma20': 41.2, 'ma50': 40.2, 'ma60': 39.8, 'ma250': 38.5,
              'boll_upper': 43.8, 'boll_mid': 41.2, 'boll_lower': 38.6,
              'rsi6': 58.2, 'rsi14': 55.2, 'rsi24': 52.5,
              'macd_dif': 0.45, 'macd_dea': 0.38,
              'kdj_k': 58.5, 'kdj_d': 55.2, 'kdj_j': 65.1,
              'high_52w': 50.0, 'low_52w': 30.0},
    '03690': {'name': '美團', 'price': 168.2, 'turnover': 52.8, 'volume': 3140,
              'ma5': 166.5, 'ma10': 165.2, 'ma15': 164.5, 'ma20': 163.8, 'ma50': 158.5, 'ma60': 156.2, 'ma250': 148.5,
              'boll_upper': 172.5, 'boll_mid': 163.8, 'boll_lower': 155.1,
              'rsi6': 62.5, 'rsi14': 60.1, 'rsi24': 57.2,
              'macd_dif': 1.56, 'macd_dea': 1.32,
              'kdj_k': 65.2, 'kdj_d': 60.5, 'kdj_j': 74.6,
              'high_52w': 200.0, 'low_52w': 120.0},
    '01024': {'name': '快手', 'price': 52.3, 'turnover': 18.4, 'volume': 3520,
              'ma5': 51.8, 'ma10': 51.2, 'ma15': 50.8, 'ma20': 50.5, 'ma50': 49.2, 'ma60': 48.5, 'ma250': 46.5,
              'boll_upper': 53.5, 'boll_mid': 50.5, 'boll_lower': 47.5,
              'rsi6': 55.2, 'rsi14': 52.5, 'rsi24': 50.2,
              'macd_dif': 0.32, 'macd_dea': 0.28,
              'kdj_k': 52.5, 'kdj_d': 50.2, 'kdj_j': 57.1,
              'high_52w': 65.0, 'low_52w': 40.0},
}

# 檔案路徑（雲端部署用）
EXPORT_FOLDER = os.path.join(os.path.dirname(__file__), 'data')
os.makedirs(EXPORT_FOLDER, exist_ok=True)
WATCHLIST_FILE = os.path.join(EXPORT_FOLDER, 'watchlist.json')
PORTFOLIO_FILE = os.path.join(EXPORT_FOLDER, 'portfolio.json')
JOURNAL_FILE = os.path.join(EXPORT_FOLDER, 'journal.json')

def get_mock_stock_data(code):
    code = code.upper().strip()
    if code in MOCK_STOCK_DATA:
        return MOCK_STOCK_DATA[code].copy()
    return None

def parse_number(value):
    if value is None or value == "":
        return 0.0
    try:
        return float(value)
    except:
        return 0.0

def get_macd_status(dif, dea):
    return "金叉" if dif > dea else "死叉" if dif < dea else "持平"

def calculate_risk_reward(entry_price, target_price, stop_loss_price):
    if entry_price <= 0:
        return None, None, None
    risk = abs(entry_price - stop_loss_price) if stop_loss_price > 0 else 0
    reward = abs(target_price - entry_price) if target_price > 0 else 0
    if risk == 0:
        return None, None, None
    rr_ratio = reward / risk
    risk_pct = (risk / entry_price) * 100
    reward_pct = (reward / entry_price) * 100
    return rr_ratio, risk_pct, reward_pct

def load_watchlist():
    if os.path.exists(WATCHLIST_FILE):
        with open(WATCHLIST_FILE, 'r') as f:
            return json.load(f)
    return []

def save_watchlist(wl):
    with open(WATCHLIST_FILE, 'w') as f:
        json.dump(wl, f, indent=2)

def load_portfolio():
    if os.path.exists(PORTFOLIO_FILE):
        with open(PORTFOLIO_FILE, 'r') as f:
            return json.load(f)
    return []

def save_portfolio(pf):
    with open(PORTFOLIO_FILE, 'w') as f:
        json.dump(pf, f, indent=2)

def load_journal(code=None):
    if os.path.exists(JOURNAL_FILE):
        with open(JOURNAL_FILE, 'r', encoding='utf-8') as f:
            j = json.load(f)
            if code is not None:
                return j.get(code, [])
            return j
    return {} if code is None else []

def save_journal(code, entry):
    j = {}
    if os.path.exists(JOURNAL_FILE):
        with open(JOURNAL_FILE, 'r', encoding='utf-8') as f:
            j = json.load(f)
    j.setdefault(code, []).append(entry)
    with open(JOURNAL_FILE, 'w', encoding='utf-8') as f:
        json.dump(j, f, ensure_ascii=False, indent=2)

# ==================== 初始化 Session State ====================
if 'page' not in st.session_state:
    st.session_state.page = "🔍 港股分析"
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
if 'high_52w' not in st.session_state:
    st.session_state.high_52w = ""
if 'low_52w' not in st.session_state:
    st.session_state.low_52w = ""
if 'short_volume' not in st.session_state:
    st.session_state.short_volume = ""
if 'short_turnover' not in st.session_state:
    st.session_state.short_turnover = ""

# ==================== 側邊欄 ====================
with st.sidebar:
    st.image("https://img.icons8.com/color/96/000000/stock.png", width=50)
    st.title("📈 功能選單")
    st.divider()
    st.markdown("**📡 系統狀態**")
    st.success("✅ 完整版運行中")
    st.caption(f"啟動時間: {datetime.now().strftime('%H:%M:%S')}")
    st.divider()
    
    pages = ["🔍 港股分析", "⭐ 自選股", "📊 投資組合", "📝 交易日誌", "⚙️ 設定"]
    for p in pages:
        if st.button(p, use_container_width=True):
            st.session_state.page = p
            st.rerun()
    
    st.divider()
    st.markdown("### 可用測試代碼")
    st.code("""
00700 - 騰訊控股
09988 - 阿里巴巴
01810 - 小米集團
03690 - 美團
01024 - 快手
    """)

# ==================== 1. 港股分析頁面 ====================
if st.session_state.page == "🔍 港股分析":
    st.markdown("""
    <div style="text-align:center; padding:1rem; background:linear-gradient(135deg,#667eea,#764ba2); border-radius:10px; margin-bottom:2rem">
        <h1 style="color:white">📈 港股技術分析</h1>
        <p style="color:rgba(255,255,255,0.8)">移動平均線 | 布林帶 | RSI | MACD | KDJ | 量價配合 | 風險報酬比</p>
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
                if st.session_state.stock_data:
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
                    st.session_state.high_52w = str(data.get('high_52w', ''))
                    st.session_state.low_52w = str(data.get('low_52w', ''))
                    st.success(f"✅ 已載入 {data['name']}")
                else:
                    st.error("找不到股票代碼")
                    st.session_state.stock_data = None
                st.rerun()
    
    st.divider()
    
    if st.session_state.stock_data:
        data = st.session_state.stock_data
        
        # ========== 基本數據 ==========
        st.subheader("📊 基本數據")
        col1, col2, col3, col4, col5 = st.columns(5)
        with col1:
            stock_name = st.text_input("股票名稱", value=data['name'], key="stock_name")
        with col2:
            price = st.number_input("股價", value=data['price'], step=0.1, format="%.2f", key="price")
        with col3:
            volume = st.number_input("成交量 (萬股)", value=data.get('volume', 0), step=100, format="%.0f", key="volume")
        with col4:
            turnover = st.number_input("成交額 (億)", value=data['turnover'], step=0.1, format="%.2f", key="turnover")
        with col5:
            st.caption("52週高/低")
            col_a, col_b = st.columns(2)
            with col_a:
                high_52w = st.text_input("高", value=st.session_state.high_52w, placeholder="高", key="high_52w", label_visibility="collapsed")
            with col_b:
                low_52w = st.text_input("低", value=st.session_state.low_52w, placeholder="低", key="low_52w", label_visibility="collapsed")
        
        st.caption("💡 做空數據（選填）")
        col1, col2 = st.columns(2)
        with col1:
            st.text_input("做空成交量 (萬股)", value=st.session_state.short_volume, placeholder="選填", key="short_volume")
        with col2:
            st.text_input("做空成交額 (億)", value=st.session_state.short_turnover, placeholder="選填", key="short_turnover")
        
        st.divider()
        
        # ========== 移動平均線 ==========
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
        
        # ========== 布林帶 ==========
        st.subheader("📊 布林帶 (BOLL 20,2)")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.text_input("BOLL上軌", value=st.session_state.boll_upper, placeholder="0", key="boll_upper")
        with col2:
            st.text_input("BOLL中軌", value=st.session_state.boll_mid, placeholder="0", key="boll_mid")
        with col3:
            st.text_input("BOLL下軌", value=st.session_state.boll_lower, placeholder="0", key="boll_lower")
        
        st.divider()
        
        # ========== RSI ==========
        st.subheader("📊 RSI (相對強弱指數)")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.text_input("RSI(6)", value=st.session_state.rsi6, placeholder="0", key="rsi6")
        with col2:
            st.text_input("RSI(14)", value=st.session_state.rsi14, placeholder="0", key="rsi14")
        with col3:
            st.text_input("RSI(24)", value=st.session_state.rsi24, placeholder="0", key="rsi24")
        
        st.divider()
        
        # ========== MACD ==========
        st.subheader("📉 MACD (12,26,9)")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.text_input("DIF", value=st.session_state.macd_dif, placeholder="0", key="macd_dif")
        with col2:
            st.text_input("DEA", value=st.session_state.macd_dea, placeholder="0", key="macd_dea")
        with col3:
            st.text_input("MACD柱", value=st.session_state.macd_hist, placeholder="0", key="macd_hist", disabled=True)
        
        st.divider()
        
        # ========== KDJ ==========
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
        p = price
        ma20_num = parse_number(st.session_state.ma20)
        ma5_num = parse_number(st.session_state.ma5)
        ma10_num = parse_number(st.session_state.ma10)
        ma50_num = parse_number(st.session_state.ma50)
        ma60_num = parse_number(st.session_state.ma60)
        ma250_num = parse_number(st.session_state.ma250)
        r6 = parse_number(st.session_state.rsi6)
        r14 = parse_number(st.session_state.rsi14)
        r24 = parse_number(st.session_state.rsi24)
        dif = parse_number(st.session_state.macd_dif)
        dea = parse_number(st.session_state.macd_dea)
        kk = parse_number(st.session_state.kdj_k)
        dd = parse_number(st.session_state.kdj_d)
        jj = parse_number(st.session_state.kdj_j)
        to = turnover
        boll_upper_num = parse_number(st.session_state.boll_upper)
        boll_lower_num = parse_number(st.session_state.boll_lower)
        bias20 = (p - ma20_num) / ma20_num * 100 if ma20_num > 0 else 0
        
        # ========== MACD 狀態 ==========
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
        
        # ========== 交易信號 ==========
        st.subheader("🎯 交易信號")
        
        cond1 = p > ma20_num if ma20_num > 0 else False
        cond2 = (r6 > 50) and (r14 > 50) and (r24 > 50) if (r6 > 0 or r14 > 0 or r24 > 0) else False
        cond3 = dif > dea
        cond4 = to > 0.3 if to > 0 else False
        cond5 = -4 <= bias20 <= 5 if ma20_num > 0 else False
        
        total_score = sum([cond1, cond2, cond3, cond4, cond5])
        
        if boll_lower_num > 0 and p < boll_lower_num:
            total_score += 1
            boll_signal = "🟢 跌破下軌，反彈機會"
        elif boll_upper_num > 0 and p > boll_upper_num:
            total_score -= 1
            boll_signal = "🔴 突破上軌，可能過熱"
        else:
            boll_signal = "🟡 在通道內"
        
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
        
        # ========== 量價配合分析 ==========
        st.subheader("📊 量價配合分析")
        
        if p > 0 and to > 0 and volume > 0:
            # 計算價格變動（需要前收盤價，這裡用模擬）
            price_change = 0  # 簡化，實際可從歷史數據獲取
            
            if price_change > 0:
                if to > 0.5:
                    vp_text = "✅ 價漲量增（健康上漲，動能充足）"
                    vp_color = "green"
                elif to > 0.3:
                    vp_text = "🟡 價漲量平（上漲動能一般）"
                    vp_color = "yellow"
                else:
                    vp_text = "⚠️ 價漲量縮（上漲乏力，可能反轉）"
                    vp_color = "orange"
            elif price_change < 0:
                if to > 0.5:
                    vp_text = "❌ 價跌量增（下跌動能強，風險較大）"
                    vp_color = "red"
                elif to > 0.3:
                    vp_text = "🟡 價跌量平（下跌動能一般）"
                    vp_color = "yellow"
                else:
                    vp_text = "✅ 價跌量縮（下跌動能減弱，可能止跌）"
                    vp_color = "green"
            else:
                vp_text = "⚪ 價格持平，量能參考意義有限"
                vp_color = "gray"
            
            st.markdown(f'<div style="background-color:{vp_color}; color:white; padding:5px; border-radius:5px; text-align:center">{vp_text}</div>', unsafe_allow_html=True)
            
            col1, col2 = st.columns(2)
            with col1:
                st.metric("今日成交額", f"{to:.2f}億")
            with col2:
                st.metric("成交量", f"{volume:.0f}萬股")
        else:
            st.info("請輸入股價、成交量和成交額以分析量價配合")
        
        st.divider()
        
        # ========== 風險報酬比計算 ==========
        st.subheader("📊 風險報酬比計算")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            target_price = st.number_input("目標價", value=None, step=0.1, format="%.2f", placeholder="目標價", key="target_price")
        with col2:
            stop_loss_price = st.number_input("止損價", value=None, step=0.1, format="%.2f", placeholder="止損價", key="stop_loss_price")
        with col3:
            entry_price = st.number_input("入場價", value=p if p > 0 else None, step=0.1, format="%.2f", placeholder="入場價", key="entry_price")
        
        if target_price and target_price > 0 and stop_loss_price and stop_loss_price > 0 and entry_price and entry_price > 0:
            rr_ratio, risk_pct, reward_pct = calculate_risk_reward(entry_price, target_price, stop_loss_price)
            if rr_ratio:
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("風險報酬比", f"1 : {rr_ratio:.2f}")
                with col2:
                    st.metric("潛在虧損", f"{risk_pct:.2f}%")
                with col3:
                    st.metric("潛在獲利", f"{reward_pct:.2f}%")
                with col4:
                    if rr_ratio >= 2:
                        st.success("✅ 符合標準 (≥2)")
                    elif rr_ratio >= 1:
                        st.warning("🟡 尚可 (1~2)")
                    else:
                        st.error("❌ 風險過高 (<1)")
        else:
            st.info("請輸入目標價、止損價和入場價以計算風險報酬比")
        
        st.divider()
        
        # ========== 止損建議 ==========
        st.subheader("🛡️ 止損建議")
        entry_price_input = st.number_input("你的買入價 (若已持倉)", value=None, step=0.1, format="%.2f", placeholder="留空則使用 MA20", key="entry_price_stop")
        
        if entry_price_input and entry_price_input > 0:
            stop_loss = entry_price_input * 0.95
            stop_loss_pct = -5.0
            method = "入場價 -5%"
        elif ma20_num > 0:
            stop_loss = ma20_num * 0.97
            stop_loss_pct = -3.0
            method = "MA20 下方 3%"
        else:
            stop_loss = None
            method = None
        
        if stop_loss:
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("建議止損價", f"${stop_loss:.2f}")
            with col2:
                st.metric("止損幅度", f"{stop_loss_pct:.1f}%")
            with col3:
                distance_pct = (stop_loss - p) / p * 100 if p > 0 else 0
                if distance_pct < 0:
                    st.metric("距離止損", f"{distance_pct:.1f}%", delta="⚠️ 已接近止損", delta_color="inverse")
                else:
                    st.metric("距離止損", f"{distance_pct:.1f}%")
            st.caption(f"📌 計算方式：{method}")
        else:
            st.info("請輸入 MA20 或買入價以計算止損")
        
        st.divider()
        
        # ========== 條件詳細判斷 ==========
        with st.expander("📋 5項條件詳細判斷"):
            st.write(f"① 股價 > 20天線: {p:.2f} > {ma20_num:.2f} → {'✅' if p > ma20_num else '❌' if ma20_num > 0 else '⚠️ 無數據'}")
            st.write(f"② RSI(6/14/24) > 50: {r6:.2f}/{r14:.2f}/{r24:.2f} → {'✅' if (r6>50 and r14>50 and r24>50) else '❌' if (r6>0 or r14>0 or r24>0) else '⚠️ 無數據'}")
            st.write(f"③ MACD 金叉: {dif:.4f} > {dea:.4f} → {'✅' if dif > dea else '❌' if dif != 0 or dea != 0 else '⚠️ 無數據'}")
            st.write(f"④ 成交額 > 0.3億: {to:.2f} > 0.3 → {'✅' if to > 0.3 else '❌' if to > 0 else '⚠️ 無數據'}")
            st.write(f"⑤ 乖離率(20) -4% ~ +5%: {bias20:.2f}% → {'✅' if -4 <= bias20 <= 5 else '❌' if ma20_num > 0 else '⚠️ 無數據'}")
            if boll_upper_num > 0 and boll_lower_num > 0:
                st.write(f"⑥ 布林帶: {boll_signal}")
        
        st.divider()
        
        # ========== 數據匯出與 AI 分析 ==========
        st.subheader("📎 數據匯出與 AI 分析")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("📎 產生 Excel 報告", use_container_width=True, type="primary"):
                export_data = {
                    '股票代碼': st.session_state.current_stock,
                    '股票名稱': stock_name,
                    '股價': p,
                    '成交量(萬股)': volume,
                    '成交額(億)': to,
                    'MA5': ma5_num, 'MA10': ma10_num, 'MA15': parse_number(st.session_state.ma15),
                    'MA20': ma20_num, 'MA50': ma50_num, 'MA60': ma60_num, 'MA250': ma250_num,
                    'BOLL上軌': boll_upper_num, 'BOLL中軌': parse_number(st.session_state.boll_mid), 'BOLL下軌': boll_lower_num,
                    'RSI6': r6, 'RSI14': r14, 'RSI24': r24,
                    'MACD DIF': dif, 'MACD DEA': dea, 'MACD柱': dif - dea,
                    'KDJ_K': kk, 'KDJ_D': dd, 'KDJ_J': jj,
                    '52週高': high_52w, '52週低': low_52w,
                    '交易信號': signal
                }
                df = pd.DataFrame([export_data])
                filename = f"港股分析_{st.session_state.current_stock}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
                filepath = os.path.join(EXPORT_FOLDER, filename)
                df.to_excel(filepath, index=False)
                st.success(f"✅ Excel 已儲存")
                with open(filepath, "rb") as f:
                    excel_data = f.read()
                st.download_button(label="📥 點擊下載 Excel", data=excel_data, file_name=filename, mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True)
        
        with col2:
            wl = load_watchlist()
            if st.session_state.current_stock in wl:
                st.button("⭐ 已加入自選股", disabled=True, use_container_width=True)
            else:
                if st.button("➕ 加入自選股", use_container_width=True):
                    wl.append(st.session_state.current_stock)
                    save_watchlist(wl)
                    st.success("✅ 已加入自選股")
                    st.rerun()
        
        with st.expander("📋 點擊展開 AI 分析指令（複製後貼到 DeepSeek）"):
            ai_instruction = f"""📊 港股分析報告 - {st.session_state.current_stock} {stock_name}

【分析日期】{datetime.now().strftime('%Y-%m-%d %H:%M')}

【基本數據】
- 股價：${p:.2f}
- 成交額：{to:.2f}億
- 成交量：{volume:.0f}萬股

【技術指標】
- MA5：${ma5_num:.2f}
- MA10：${ma10_num:.2f}
- MA20：${ma20_num:.2f}
- MA50：${ma50_num:.2f}
- MA60：${ma60_num:.2f}
- MA250：${ma250_num:.2f}
- RSI14：{r14:.1f}
- MACD：DIF={dif:.4f}, DEA={dea:.4f}
- 乖離率：{bias20:.2f}%
- KDJ：K={kk:.1f}, D={dd:.1f}, J={jj:.1f}

【五項條件判斷】
- 股價 > 20天線：{'✅' if p > ma20_num else '❌'}
- RSI14 > 50：{'✅' if r14 > 50 else '❌'}
- MACD 金叉：{'✅' if dif > dea else '❌'}
- 成交額 > 0.3億：{'✅' if to > 0.3 else '❌'}
- 乖離率 -4% ~ +5%：{'✅' if -4 <= bias20 <= 5 else '❌'}

【交易信號】
{signal}

請根據以上數據提供專業分析建議。"""
            st.code(ai_instruction, language="markdown", line_numbers=False)
            st.caption("💡 提示：點擊右上角複製圖標複製指令 → 貼到 DeepSeek 即可獲得 AI 分析")

# ==================== 2. 自選股頁面 ====================
elif st.session_state.page == "⭐ 自選股":
    st.markdown("""
    <div style="text-align:center; padding:1rem; background:linear-gradient(135deg,#667eea,#764ba2); border-radius:10px; margin-bottom:2rem">
        <h1 style="color:white">⭐ 自選股列表</h1>
        <p style="color:rgba(255,255,255,0.8)">追蹤股票 | 快速分析</p>
    </div>
    """, unsafe_allow_html=True)
    
    watchlist = load_watchlist()
    
    if not watchlist:
        st.info("暫無自選股，請在「港股分析」頁面加入")
    else:
        for code in watchlist:
            col1, col2, col3 = st.columns([3, 1, 1])
            with col1:
                data = get_mock_stock_data(code)
                if data:
                    st.write(f"**{code}** - {data['name']}")
                    st.caption(f"股價: ${data['price']:.2f} | 成交額: {data['turnover']:.1f}億")
                else:
                    st.write(f"**{code}**")
            with col2:
                if st.button("分析", key=f"analyze_{code}"):
                    st.session_state.current_stock = code
                    st.session_state.page = "🔍 港股分析"
                    st.rerun()
            with col3:
                if st.button("刪除", key=f"del_{code}"):
                    watchlist.remove(code)
                    save_watchlist(watchlist)
                    st.rerun()
    
    with st.expander("➕ 添加自選股"):
        new_code = st.text_input("股票代碼", placeholder="例如: 00700", key="new_watchlist")
        if st.button("添加", use_container_width=True):
            if new_code:
                new_code = new_code.upper().strip()
                watchlist = load_watchlist()
                if new_code not in watchlist:
                    watchlist.append(new_code)
                    save_watchlist(watchlist)
                    st.success(f"已添加 {new_code}")
                    st.rerun()
                else:
                    st.warning("股票已在自選股中")

# ==================== 3. 投資組合頁面 ====================
elif st.session_state.page == "📊 投資組合":
    st.markdown("""
    <div style="text-align:center; padding:1rem; background:linear-gradient(135deg,#667eea,#764ba2); border-radius:10px; margin-bottom:2rem">
        <h1 style="color:white">📊 投資組合</h1>
        <p style="color:rgba(255,255,255,0.8)">記錄買入賣出 | 計算盈虧</p>
    </div>
    """, unsafe_allow_html=True)
    
    portfolio = load_portfolio()
    
    with st.expander("➕ 新增交易", expanded=True):
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            trade_code = st.text_input("股票代碼", placeholder="例如: 00700", key="trade_code")
        with col2:
            trade_type = st.selectbox("類型", ["買入", "賣出"], key="trade_type")
        with col3:
            trade_price = st.number_input("價格", value=0.0, step=0.1, format="%.2f", key="trade_price")
        with col4:
            trade_shares = st.number_input("股數", value=0, step=100, key="trade_shares")
        
        col1, col2 = st.columns(2)
        with col1:
            trade_date = st.date_input("日期", value=datetime.now().date(), key="trade_date")
        with col2:
            trade_note = st.text_input("備註", placeholder="選填", key="trade_note")
        
        if st.button("💾 儲存交易", use_container_width=True):
            if trade_code and trade_price > 0 and trade_shares > 0:
                portfolio.append({
                    'code': trade_code.upper(),
                    'type': trade_type,
                    'price': trade_price,
                    'shares': trade_shares,
                    'date': trade_date.strftime('%Y-%m-%d'),
                    'note': trade_note
                })
                save_portfolio(portfolio)
                st.success("已儲存")
                st.rerun()
            else:
                st.warning("請填寫完整資料")
    
    if portfolio:
        df = pd.DataFrame(portfolio)
        st.dataframe(df, use_container_width=True)
        
        # 計算持倉盈虧
        holdings = {}
        for t in portfolio:
            code = t['code']
            if code not in holdings:
                holdings[code] = {'shares': 0, 'cost': 0}
            if t['type'] == '買入':
                holdings[code]['shares'] += t['shares']
                holdings[code]['cost'] += t['price'] * t['shares']
            else:
                holdings[code]['shares'] -= t['shares']
                holdings[code]['cost'] -= t['price'] * t['shares']
        
        st.subheader("📊 持倉摘要")
        summary_data = []
        for code, data in holdings.items():
            if data['shares'] > 0:
                stock_data = get_mock_stock_data(code)
                current_price = stock_data['price'] if stock_data else 0
                current_value = current_price * data['shares']
                avg_cost = data['cost'] / data['shares']
                profit = current_value - data['cost']
                profit_pct = (profit / data['cost']) * 100 if data['cost'] > 0 else 0
                summary_data.append({
                    '股票': code,
                    '持股': data['shares'],
                    '平均成本': f"${avg_cost:.2f}",
                    '現價': f"${current_price:.2f}",
                    '市值': f"${current_value:,.2f}",
                    '盈虧': f"${profit:+,.2f}",
                    '盈虧%': f"{profit_pct:+.2f}%"
                })
        if summary_data:
            st.dataframe(pd.DataFrame(summary_data), use_container_width=True)
        
        if st.button("🗑️ 清空所有記錄", use_container_width=True):
            save_portfolio([])
            st.rerun()
    else:
        st.info("暫無交易記錄")

# ==================== 4. 交易日誌頁面 ====================
elif st.session_state.page == "📝 交易日誌":
    st.markdown("""
    <div style="text-align:center; padding:1rem; background:linear-gradient(135deg,#667eea,#764ba2); border-radius:10px; margin-bottom:2rem">
        <h1 style="color:white">📝 交易日誌</h1>
        <p style="color:rgba(255,255,255,0.8)">記錄交易想法 | 操作檢討</p>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2 = st.columns([1, 2])
    with col1:
        journal_code = st.text_input("股票代碼", placeholder="例如: 00700", key="journal_code")
    
    if journal_code:
        notes = load_journal(journal_code.upper())
        
        with st.form("journal_form"):
            title = st.text_input("標題", placeholder="例如: 買入理由")
            content = st.text_area("內容", height=150, placeholder="記錄你的分析想法、操作反思...")
            tags = st.text_input("標籤", placeholder="例如: 買入,技術分析 (用逗號分隔)")
            
            if st.form_submit_button("💾 儲存", use_container_width=True):
                if title or content:
                    save_journal(journal_code.upper(), {
                        'title': title,
                        'content': content,
                        'tags': tags.split(',') if tags else [],
                        'date': datetime.now().strftime('%Y-%m-%d %H:%M')
                    })
                    st.success("已儲存")
                    st.rerun()
        
        if notes:
            st.subheader(f"📋 {journal_code} 的記錄")
            for n in reversed(notes):
                with st.container():
                    st.markdown(f"**📌 {n.get('title', '無標題')}**")
                    st.caption(f"{n.get('date', '')} | 標籤: {', '.join(n.get('tags', []))}")
                    st.write(n.get('content', ''))
                    st.divider()
    else:
        st.info("請輸入股票代碼開始記錄")

# ==================== 5. 設定頁面 ====================
elif st.session_state.page == "⚙️ 設定":
    st.markdown("""
    <div style="text-align:center; padding:1rem; background:linear-gradient(135deg,#667eea,#764ba2); border-radius:10px; margin-bottom:2rem">
        <h1 style="color:white">⚙️ 設定</h1>
        <p style="color:rgba(255,255,255,0.8)">系統設定 | 數據源配置</p>
    </div>
    """, unsafe_allow_html=True)
    
    st.subheader("📊 顯示設定")
    
    col1, col2 = st.columns(2)
    with col1:
        st.selectbox("小數點位數", [2, 3, 4], index=0, key="decimal_places")
    with col2:
        st.selectbox("主題顏色", ["深色", "淺色"], index=0, key="theme")
    
    st.divider()
    
    st.subheader("📡 數據源設定")
    st.info("""
    **目前使用模擬數據**
    
    正式版將連接以下數據源：
    - 港股：akshare / yfinance
    - 美股：yfinance
    
    由於 Streamlit Cloud 記憶體限制 (1GB)，建議保持使用模擬數據或減少分析數量。
    """)
    
    st.divider()
    
    st.subheader("🗑️ 資料管理")
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("清空自選股", use_container_width=True):
            save_watchlist([])
            st.success("已清空")
            st.rerun()
    with col2:
        if st.button("清空投資組合", use_container_width=True):
            save_portfolio([])
            st.success("已清空")
            st.rerun()
    
    st.divider()
    st.caption(f"📁 數據儲存位置: {EXPORT_FOLDER}")
    st.caption(f"📅 系統時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

st.divider()
st.caption("📌 完整版 | 使用模擬數據 | 正式版將連接真實數據源")
