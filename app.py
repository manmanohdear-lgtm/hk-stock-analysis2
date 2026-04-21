import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
import re
import os
import json
from io import BytesIO
import warnings
import sys
warnings.filterwarnings('ignore')

sys.setrecursionlimit(1000000)

try:
    import akshare as ak
    AKSHARE_AVAILABLE = True
except:
    AKSHARE_AVAILABLE = False

try:
    import yfinance as yf
    YFINANCE_AVAILABLE = True
except:
    YFINANCE_AVAILABLE = False

st.set_page_config(page_title="港股美股技術分析系統", page_icon="📈", layout="wide")

# ==================== 雲端部署路徑 ====================
EXPORT_FOLDER = os.path.join(os.path.dirname(__file__), 'data')
os.makedirs(EXPORT_FOLDER, exist_ok=True)

WATCHLIST_FILE = os.path.join(EXPORT_FOLDER, 'watchlist.json')
PORTFOLIO_FILE = os.path.join(EXPORT_FOLDER, 'portfolio.json')
JOURNAL_FILE = os.path.join(EXPORT_FOLDER, 'journal.json')
TRADE_RECORDS_FILE = os.path.join(EXPORT_FOLDER, 'trade_records.json')

# ==================== 股票名稱對照表 ====================
STOCK_NAME_MAP = {
    '00700': '騰訊控股', '09988': '阿里巴巴', '01810': '小米集團', '03690': '美團',
    '01024': '快手', '09999': '網易', '09618': '京東集團', '09888': '百度集團',
    '00005': '匯豐控股', '02318': '中國平安', '01299': '友邦保險', '00388': '香港交易所',
    '00941': '中國移動', '00883': '中國海洋石油', '03317': '智譜', '03318': 'MINIMAX-W',
    '01211': '比亞迪股份', '00981': '中芯國際', '01347': '華虹半導體', '02269': '藥明生物',
    'AAPL': '蘋果', 'NVDA': '英偉達', 'TSLA': '特斯拉', 'MSFT': '微軟',
}

SECTOR_KEYWORDS = {
    'AI/科技': ['AI', '人工智能', '騰訊', '阿里', '百度', '網易', '美團', '快手', '京東'],
    '半導體': ['半導體', '芯片', '中芯', '華虹'],
    '新能源/電動車': ['新能源', '電動車', '比亞迪', '理想', '蔚來', '小鵬', '特斯拉'],
    '醫藥/生物科技': ['醫藥', '生物科技', '藥明', '石藥'],
    '金融/保險': ['銀行', '保險', '證券', '匯豐', '友邦', '平保', '港交所'],
    '其他': []
}

SCREENING_CONFIG = {
    'turnover_threshold': 0.3,
    'bias_lower': -4,
    'bias_upper': 5,
    'rsi_threshold': 50,
}

# ==================== 輔助函數 ====================
def normalize_code(code):
    if code is None:
        return ""
    code_raw = re.sub(r'[^0-9]', '', str(code).strip())
    if code_raw:
        return code_raw.zfill(5)
    return str(code).strip()

def parse_number(value):
    return float(value) if value and value != "" else 0.0

def get_stock_sector(name):
    name_lower = name.lower() if name else ""
    for sector, keywords in SECTOR_KEYWORDS.items():
        for kw in keywords:
            if kw.lower() in name_lower:
                return sector
    return "其他"

def get_macd_status(dif, dea):
    return ("金叉", "golden") if dif > dea else ("死叉", "death") if dif < dea else ("持平", "neutral")

def get_hsi_trend(days=20):
    try:
        if not YFINANCE_AVAILABLE:
            return "無法獲取", 0, None
        hsi = yf.Ticker("^HSI")
        hist = hsi.history(period=f"{days+5}d")
        if len(hist) < days:
            return "數據不足", 0, None
        closes = hist['Close'].values
        current = closes[-1]
        ma20 = np.mean(closes[-20:]) if len(closes) >= 20 else current
        ma50 = np.mean(closes[-50:]) if len(closes) >= 50 else current
        change_pct = (closes[-1] - closes[-days]) / closes[-days] * 100 if len(closes) >= days else 0
        if current > ma20 and ma20 > ma50:
            trend = "多頭趨勢"
            is_bullish = True
        elif current < ma20 and ma20 < ma50:
            trend = "空頭趨勢"
            is_bullish = False
        else:
            trend = "盤整震盪"
            is_bullish = None
        return trend, change_pct, is_bullish
    except Exception as e:
        return f"獲取失敗: {e}", 0, None

def calculate_risk_reward(entry_price, target_price, stop_loss_price):
    if entry_price <= 0:
        return None, None, None
    risk = abs(entry_price - stop_loss_price) if stop_loss_price > 0 else 0
    reward = abs(target_price - entry_price) if target_price > 0 else 0
    if risk == 0:
        return None, None, None
    risk_reward_ratio = reward / risk
    risk_pct = (risk / entry_price) * 100
    reward_pct = (reward / entry_price) * 100
    return risk_reward_ratio, risk_pct, reward_pct

def get_stop_loss_suggestion(price, ma20, entry_price=None):
    if entry_price and entry_price > 0:
        stop_loss = entry_price * 0.95
        stop_loss_pct = -5.0
        method = "入場價 -5%"
    elif ma20 and ma20 > 0:
        stop_loss = ma20 * 0.97
        stop_loss_pct = -3.0
        method = "MA20 下方 3%"
    else:
        return None, None, None, None
    distance_pct = (stop_loss - price) / price * 100 if price > 0 else 0
    return stop_loss, stop_loss_pct, distance_pct, method

# ==================== 技術數據獲取 ====================
def get_tech_data(code):
    try:
        df = ak.stock_hk_daily(symbol=code, adjust='qfq')
        if df is None or len(df) < 20:
            return None
        
        df = df.sort_values('date')
        closes = df['close'].values
        opens = df['open'].values
        highs = df['high'].values
        lows = df['low'].values
        turnovers = df['turnover'].values if 'turnover' in df.columns else df['volume'].values * closes
        
        price = closes[-1]
        open_price = opens[-1]
        ma10 = np.mean(closes[-10:]) if len(closes) >= 10 else price
        ma20 = np.mean(closes[-20:]) if len(closes) >= 20 else price
        ma50 = np.mean(closes[-50:]) if len(closes) >= 50 else price
        
        if len(closes) >= 15:
            deltas = np.diff(closes[-15:])
            gains = np.where(deltas > 0, deltas, 0)
            losses = np.where(deltas < 0, -deltas, 0)
            avg_gain = np.mean(gains[-14:]) if len(gains) >= 14 else 0
            avg_loss = np.mean(losses[-14:]) if len(losses) >= 14 else 0
            rsi14 = 100 - (100 / (1 + avg_gain/avg_loss)) if avg_loss > 0 else 100
        else:
            rsi14 = 50
        
        bias20 = (price - ma20) / ma20 * 100 if ma20 > 0 else 0
        current_turnover = turnovers[-1] / 100000000
        
        # MACD 計算
        if len(closes) >= 26:
            exp1 = pd.Series(closes).ewm(span=12, adjust=False).mean()
            exp2 = pd.Series(closes).ewm(span=26, adjust=False).mean()
            dif = exp1 - exp2
            dea = dif.ewm(span=9, adjust=False).mean()
            macd_dif = dif.iloc[-1]
            macd_dea = dea.iloc[-1]
        else:
            macd_dif = 0
            macd_dea = 0
        
        # KDJ 計算
        if len(closes) >= 9:
            low_9 = np.min(lows[-9:])
            high_9 = np.max(highs[-9:])
            rsv = (price - low_9) / (high_9 - low_9) * 100 if high_9 > low_9 else 50
            k = 2/3 * 50 + 1/3 * rsv
            d = 2/3 * 50 + 1/3 * k
            j = 3 * k - 2 * d
        else:
            k, d, j = 50, 50, 50
        
        return {
            'price': price, 'open': open_price, 'high': highs[-1], 'low': lows[-1],
            'ma10': ma10, 'ma20': ma20, 'ma50': ma50,
            'rsi14': rsi14, 'bias20': bias20, 'turnover': current_turnover,
            'macd_dif': macd_dif, 'macd_dea': macd_dea,
            'kdj_k': k, 'kdj_d': d, 'kdj_j': j,
            'success': True
        }
    except Exception as e:
        return None

# ==================== 每日選股函數（雲端優化版）====================
def run_screening(progress_bar, status_text):
    if not AKSHARE_AVAILABLE:
        status_text.text("請安裝 akshare")
        return pd.DataFrame()
    
    status_text.text("獲取港股列表...")
    try:
        stocks = ak.stock_hk_spot()
    except Exception as e:
        status_text.text(f"失敗: {e}")
        return pd.DataFrame()
    
    if stocks is None or stocks.empty:
        return pd.DataFrame()
    
    stocks['成交额'] = pd.to_numeric(stocks['成交额'], errors='coerce')
    stocks['最新价'] = pd.to_numeric(stocks['最新价'], errors='coerce')
    stocks = stocks[(stocks['成交额'] > 50000000) & (stocks['最新价'] > 1)]
    
    MAX_ANALYSIS = 10
    if len(stocks) > MAX_ANALYSIS:
        stocks = stocks.head(MAX_ANALYSIS)
    
    if stocks.empty:
        return pd.DataFrame()
    
    progress_bar.progress(0.2)
    results = []
    total = len(stocks)
    
    for i, (_, row) in enumerate(stocks.iterrows()):
        code = row['代码']
        name = row.get('中文名称', code)
        progress_bar.progress(0.2 + 0.6 * (i / total))
        status_text.text(f"[{i+1}/{total}] {code}")
        
        tech = get_tech_data(code)
        if not tech:
            continue
        
        cond1 = tech['price'] > tech['ma20']
        cond2 = tech['rsi14'] > SCREENING_CONFIG['rsi_threshold']
        cond3 = tech['turnover'] > SCREENING_CONFIG['turnover_threshold']
        cond4 = SCREENING_CONFIG['bias_lower'] <= tech['bias20'] <= SCREENING_CONFIG['bias_upper']
        tech_score = sum([cond1, cond2, cond3, cond4])
        
        if tech_score < 2:
            continue
        
        sector = get_stock_sector(name)
        total_score = tech_score * 10 + min(tech['turnover'], 10) * 2
        
        results.append({
            '代碼': code, '名稱': name[:20], '股價': round(tech['price'], 2),
            '成交額': round(tech['turnover'], 2), 'RSI': round(tech['rsi14'], 1),
            '板塊': sector, '總分': round(total_score, 2)
        })
    
    results.sort(key=lambda x: x['總分'], reverse=True)
    progress_bar.progress(1.0)
    status_text.text(f"完成! 找到 {len(results)} 隻")
    
    return pd.DataFrame(results[:50])

# ==================== 載入/儲存函數 ====================
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

def load_trade_records():
    if os.path.exists(TRADE_RECORDS_FILE):
        with open(TRADE_RECORDS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return []

def save_trade_records(records):
    with open(TRADE_RECORDS_FILE, 'w', encoding='utf-8') as f:
        json.dump(records, f, ensure_ascii=False, indent=2)

def set_page(p):
    st.session_state.page = p
    st.rerun()

# ==================== 港股分析頁面核心函數 ====================
def perform_search(code):
    if not code:
        return
    norm = normalize_code(code)
    st.session_state.current_stock = norm
    if norm not in [h['code'] for h in st.session_state.search_history]:
        st.session_state.search_history.append({'code': norm, 'time': datetime.now().strftime('%H:%M:%S')})
    
    tech = get_tech_data(norm)
    if tech:
        st.session_state.hk_stock_name = code
        st.session_state.hk_stock_price = tech['price']
        st.session_state.hk_stock_turnover = tech['turnover']
        st.session_state.tech_data = tech
        st.success(f"✅ 已載入 {norm} 股價: ${tech['price']:.2f}")
    else:
        st.warning(f"無法獲取 {norm} 數據")
    st.rerun()

# ==================== 初始化 Session State ====================
if 'page' not in st.session_state:
    st.session_state.page = "📋 每日工作流"
if 'screening_results' not in st.session_state:
    st.session_state.screening_results = None
if 'current_stock' not in st.session_state:
    st.session_state.current_stock = ""
if 'search_history' not in st.session_state:
    st.session_state.search_history = []
if 'hk_stock_name' not in st.session_state:
    st.session_state.hk_stock_name = ""
if 'hk_stock_price' not in st.session_state:
    st.session_state.hk_stock_price = 0.0
if 'hk_stock_turnover' not in st.session_state:
    st.session_state.hk_stock_turnover = 0.0
if 'tech_data' not in st.session_state:
    st.session_state.tech_data = None
if 'ma10' not in st.session_state:
    st.session_state.ma10 = ""
if 'ma20' not in st.session_state:
    st.session_state.ma20 = ""
if 'ma50' not in st.session_state:
    st.session_state.ma50 = ""
if 'rsi14' not in st.session_state:
    st.session_state.rsi14 = ""
if 'macd_dif' not in st.session_state:
    st.session_state.macd_dif = ""
if 'macd_dea' not in st.session_state:
    st.session_state.macd_dea = ""
if 'kdj_k' not in st.session_state:
    st.session_state.kdj_k = ""
if 'kdj_d' not in st.session_state:
    st.session_state.kdj_d = ""
if 'kdj_j' not in st.session_state:
    st.session_state.kdj_j = ""

# ==================== 側邊欄 ====================
with st.sidebar:
    st.image("https://img.icons8.com/color/96/000000/stock.png", width=50)
    st.title("📈 功能選單")
    st.divider()
    st.markdown("**📡 系統狀態**")
    st.success("✅ 雲端版運行中")
    st.divider()
    pages = ["📋 每日工作流", "🔍 港股分析", "⭐ 自選股", "📊 投資組合", "📝 交易日誌", "📊 交易記錄與檢討", "🎯 每日選股", "⚙️ 設定"]
    for p in pages:
        if st.button(p, use_container_width=True):
            set_page(p)

# ==================== 頁面內容 ====================

# 0. 每日工作流儀表板
if st.session_state.page == "📋 每日工作流":
    st.markdown("""
    <div style="text-align:center; padding:1rem; background:linear-gradient(135deg,#667eea,#764ba2); border-radius:10px; margin-bottom:2rem">
        <h1 style="color:white">📋 每日工作流</h1>
        <p style="color:rgba(255,255,255,0.8)">市場走勢 → 選股 → 記錄</p>
    </div>
    """, unsafe_allow_html=True)
    
    with st.expander("📊 步驟 1：市場走勢", expanded=True):
        hsi_trend, hsi_change, hsi_bullish = get_hsi_trend()
        if hsi_bullish is True:
            st.success(f"✅ 大盤多頭趨勢 ({hsi_change:+.2f}%)")
        elif hsi_bullish is False:
            st.error(f"⚠️ 大盤空頭趨勢 ({hsi_change:+.2f}%)")
        else:
            st.warning(f"🟡 大盤盤整震盪 ({hsi_change:+.2f}%)")
    
    with st.expander("🎯 步驟 2：今日可留意股票", expanded=True):
        if st.button("🔄 開始選股", type="primary"):
            with st.spinner("正在篩選股票..."):
                progress_bar = st.progress(0)
                status_text = st.empty()
                results_df = run_screening(progress_bar, status_text)
                if not results_df.empty:
                    st.session_state.screening_results = results_df
                    st.success(f"✅ 找到 {len(results_df)} 隻股票")
                else:
                    st.warning("沒有符合條件的股票")
        
        if st.session_state.screening_results is not None:
            st.dataframe(st.session_state.screening_results, use_container_width=True)
    
    with st.expander("📝 步驟 3：今日操作記錄", expanded=False):
        today = datetime.now().strftime('%Y-%m-%d')
        with st.form("daily_journal"):
            trade_stock = st.text_input("股票代碼")
            trade_action = st.selectbox("操作", ["買入", "賣出", "觀望"])
            trade_price = st.number_input("價格", value=0.0, step=0.1)
            review = st.text_area("檢討", height=80)
            if st.form_submit_button("💾 儲存"):
                if trade_stock:
                    save_journal(today, {
                        'stock': trade_stock, 'action': trade_action,
                        'price': trade_price, 'review': review,
                        'timestamp': datetime.now().strftime('%H:%M')
                    })
                    st.success("已儲存！")
                    st.rerun()

# ==================== 1. 港股分析頁面（完整版）====================
elif st.session_state.page == "🔍 港股分析":
    st.markdown("""
    <div style="text-align:center; padding:1rem; background:linear-gradient(135deg,#667eea,#764ba2); border-radius:10px; margin-bottom:2rem">
        <h1 style="color:white">📈 港股技術分析</h1>
        <p style="color:rgba(255,255,255,0.8)">自動抓取數據 | 技術指標 | 買賣信號</p>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2 = st.columns([3, 1])
    with col1:
        code = st.text_input("股票代碼", placeholder="例如：00700、09988", key="stock_code_input")
    with col2:
        if st.button("🔍 載入", type="primary", use_container_width=True):
            if code:
                perform_search(code)
    
    if st.session_state.current_stock:
        st.caption(f"當前股票: {st.session_state.current_stock}")
    st.divider()
    
    st.subheader("📊 基本數據")
    col1, col2 = st.columns(2)
    with col1:
        stock_name = st.text_input("股票名稱", value=st.session_state.hk_stock_name, placeholder="例如: 騰訊控股")
        st.session_state.hk_stock_name = stock_name
    with col2:
        price = st.number_input("股價 (港元)", value=st.session_state.hk_stock_price if st.session_state.hk_stock_price > 0 else None, step=0.1, format="%.3f", placeholder="請輸入股價")
        if price is not None:
            st.session_state.hk_stock_price = price
    
    st.divider()
    
    st.subheader("📊 技術指標（可手動輸入）")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("**📈 移動平均線**")
        ma10 = st.text_input("MA10", value=st.session_state.ma10, placeholder="例如: 510.200")
        ma20 = st.text_input("MA20", value=st.session_state.ma20, placeholder="例如: 502.700")
        ma50 = st.text_input("MA50", value=st.session_state.ma50, placeholder="例如: 495.300")
    
    with col2:
        st.markdown("**📊 RSI / MACD**")
        rsi14 = st.text_input("RSI(14)", value=st.session_state.rsi14, placeholder="例如: 62.5")
        macd_dif = st.text_input("MACD DIF", value=st.session_state.macd_dif, placeholder="例如: 1.234")
        macd_dea = st.text_input("MACD DEA", value=st.session_state.macd_dea, placeholder="例如: 1.123")
    
    with col3:
        st.markdown("**📈 KDJ**")
        kdj_k = st.text_input("KDJ_K", value=st.session_state.kdj_k, placeholder="例如: 75.2")
        kdj_d = st.text_input("KDJ_D", value=st.session_state.kdj_d, placeholder="例如: 72.5")
        kdj_j = st.text_input("KDJ_J", value=st.session_state.kdj_j, placeholder="例如: 80.6")
    
    # 如果有自動抓取的技術數據，自動填入
    if st.session_state.tech_data:
        tech = st.session_state.tech_data
        if not ma10:
            ma10 = str(round(tech.get('ma10', 0), 2))
        if not ma20:
            ma20 = str(round(tech.get('ma20', 0), 2))
        if not ma50:
            ma50 = str(round(tech.get('ma50', 0), 2))
        if not rsi14:
            rsi14 = str(round(tech.get('rsi14', 0), 1))
        if not macd_dif:
            macd_dif = str(round(tech.get('macd_dif', 0), 4))
        if not macd_dea:
            macd_dea = str(round(tech.get('macd_dea', 0), 4))
        if not kdj_k:
            kdj_k = str(round(tech.get('kdj_k', 0), 1))
        if not kdj_d:
            kdj_d = str(round(tech.get('kdj_d', 0), 1))
        if not kdj_j:
            kdj_j = str(round(tech.get('kdj_j', 0), 1))
    
    st.session_state.ma10 = ma10
    st.session_state.ma20 = ma20
    st.session_state.ma50 = ma50
    st.session_state.rsi14 = rsi14
    st.session_state.macd_dif = macd_dif
    st.session_state.macd_dea = macd_dea
    st.session_state.kdj_k = kdj_k
    st.session_state.kdj_d = kdj_d
    st.session_state.kdj_j = kdj_j
    
    p = st.session_state.hk_stock_price
    ma20_num = parse_number(ma20)
    r14 = parse_number(rsi14)
    dif = parse_number(macd_dif)
    dea = parse_number(macd_dea)
    to = st.session_state.hk_stock_turnover
    bias20 = (p - ma20_num) / ma20_num * 100 if ma20_num > 0 else 0
    kk = parse_number(kdj_k)
    dd = parse_number(kdj_d)
    
    st.divider()
    
    st.subheader("📉 MACD 狀態")
    status, _ = get_macd_status(dif, dea)
    if status == "金叉":
        st.markdown('<div style="background-color:#00aa00; color:white; padding:5px; border-radius:5px">✅ 金叉 (黃金交叉)</div>', unsafe_allow_html=True)
    elif status == "死叉":
        st.markdown('<div style="background-color:#aa0000; color:white; padding:5px; border-radius:5px">❌ 死叉 (死亡交叉)</div>', unsafe_allow_html=True)
    else:
        st.info(f"📊 {status}")
    
    st.subheader("🎯 交易信號")
    cond1 = p > ma20_num if ma20_num > 0 else False
    cond2 = r14 > 50 if r14 > 0 else False
    cond3 = dif > dea
    cond4 = to > 0.3 if to > 0 else False
    cond5 = -4 <= bias20 <= 5 if ma20_num > 0 else False
    
    total_score = sum([cond1, cond2, cond3, cond4, cond5])
    
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
    
    st.subheader("📊 大盤趨勢過濾")
    hsi_trend, hsi_change, hsi_bullish = get_hsi_trend()
    if hsi_bullish is True:
        st.success(f"✅ 大盤多頭趨勢 ({hsi_change:+.2f}%)")
    elif hsi_bullish is False:
        st.error(f"⚠️ 大盤空頭趨勢 ({hsi_change:+.2f}%)")
    else:
        st.warning(f"🟡 大盤盤整震盪 ({hsi_change:+.2f}%)")
    
    st.subheader("📊 風險報酬比計算")
    col1, col2, col3 = st.columns(3)
    with col1:
        target_price = st.number_input("目標價", value=None, step=0.1, format="%.2f", placeholder="目標價")
    with col2:
        stop_loss = st.number_input("止損價", value=None, step=0.1, format="%.2f", placeholder="止損價")
    with col3:
        entry_price = st.number_input("入場價", value=p if p > 0 else None, step=0.1, format="%.2f", placeholder="入場價")
    
    if target_price and target_price > 0 and stop_loss and stop_loss > 0 and entry_price and entry_price > 0:
        rr_ratio, risk_pct, reward_pct = calculate_risk_reward(entry_price, target_price, stop_loss)
        if rr_ratio:
            st.metric("風險報酬比", f"1 : {rr_ratio:.2f}")
            if rr_ratio >= 2:
                st.success("✅ 符合標準 (≥2)")
            elif rr_ratio >= 1:
                st.warning("🟡 尚可 (1~2)")
            else:
                st.error("❌ 風險過高 (<1)")
    
    st.subheader("🛡️ 止損建議")
    entry_price_input = st.number_input("你的買入價", value=None, step=0.1, format="%.2f", placeholder="留空則用 MA20")
    stop_loss, stop_loss_pct, distance_pct, method = get_stop_loss_suggestion(p, ma20_num, entry_price_input if entry_price_input else None)
    if stop_loss:
        st.metric("建議止損價", f"${stop_loss:.2f}")
        st.caption(f"📌 {method}")
    
    with st.expander("📋 5項條件詳細判斷"):
        st.write(f"① 股價 > 20天線: {p:.2f} > {ma20_num:.2f} → {'✅' if p > ma20_num else '❌'}")
        st.write(f"② RSI(14) > 50: {r14:.1f} > 50 → {'✅' if r14 > 50 else '❌'}")
        st.write(f"③ MACD 金叉: {dif:.4f} > {dea:.4f} → {'✅' if dif > dea else '❌'}")
        st.write(f"④ 成交額 > 0.3億: {to:.2f} > 0.3 → {'✅' if to > 0.3 else '❌'}")
        st.write(f"⑤ 乖離率 -4%~+5%: {bias20:.2f}% → {'✅' if -4 <= bias20 <= 5 else '❌'}")

# 2. 自選股頁面
elif st.session_state.page == "⭐ 自選股":
    st.markdown("# ⭐ 自選股")
    watchlist = load_watchlist()
    if not watchlist:
        st.info("暫無自選股")
    else:
        for code in watchlist:
            col1, col2 = st.columns([3, 1])
            with col1:
                st.write(f"📊 {code}")
            with col2:
                if st.button("分析", key=f"analyze_{code}"):
                    perform_search(code)
                    set_page("🔍 港股分析")
    
    with st.expander("➕ 添加自選股"):
        new_code = st.text_input("股票代碼")
        if st.button("添加"):
            if new_code:
                norm_code = normalize_code(new_code)
                wl = load_watchlist()
                if norm_code not in wl:
                    wl.append(norm_code)
                    save_watchlist(wl)
                    st.success(f"已添加 {norm_code}")
                    st.rerun()

# 3. 投資組合頁面
elif st.session_state.page == "📊 投資組合":
    st.markdown("# 📊 投資組合")
    pf = load_portfolio()
    with st.expander("➕ 新增交易"):
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            trade_code = st.text_input("股票代碼")
        with col2:
            trade_type = st.selectbox("類型", ["買入", "賣出"])
        with col3:
            trade_price = st.number_input("價格", value=0.0, step=0.1)
        with col4:
            trade_shares = st.number_input("股數", value=0, step=100)
        if st.button("儲存"):
            if trade_code and trade_price > 0 and trade_shares > 0:
                pf.append({'code': normalize_code(trade_code), 'type': trade_type, 'price': trade_price, 'shares': trade_shares, 'date': datetime.now().strftime('%Y-%m-%d')})
                save_portfolio(pf)
                st.rerun()
    if pf:
        st.dataframe(pd.DataFrame(pf))

# 4. 交易日誌頁面
elif st.session_state.page == "📝 交易日誌":
    st.markdown("# 📝 交易日誌")
    code = st.text_input("股票代碼")
    if code:
        notes = load_journal(code)
        with st.form("note"):
            title = st.text_input("標題")
            content = st.text_area("內容", height=150)
            if st.form_submit_button("儲存"):
                save_journal(code, {'title': title, 'content': content, 'date': datetime.now().strftime('%Y-%m-%d %H:%M')})
                st.rerun()
        for n in reversed(notes):
            st.markdown(f"**📌 {n.get('title', '無標題')}**")
            st.caption(n.get('date', ''))
            st.write(n.get('content', ''))
            st.divider()

# 5. 交易記錄與檢討頁面
elif st.session_state.page == "📊 交易記錄與檢討":
    st.markdown("# 📊 交易記錄與檢討")
    records = load_trade_records()
    
    with st.expander("➕ 新增記錄"):
        col1, col2 = st.columns(2)
        with col1:
            record_code = st.text_input("股票代碼")
            record_buy = st.number_input("買入價", value=0.0, step=0.1)
            record_shares = st.number_input("股數", value=0, step=100)
        with col2:
            record_sell = st.number_input("賣出價", value=0.0, step=0.1)
            record_date = st.date_input("日期", value=datetime.now().date())
        record_note = st.text_area("備註")
        if st.button("儲存記錄"):
            if record_code and record_buy > 0:
                profit = (record_sell - record_buy) * record_shares if record_sell > 0 else 0
                records.append({
                    'code': record_code, 'buy': record_buy, 'sell': record_sell,
                    'shares': record_shares, 'profit': profit, 'date': record_date.strftime('%Y-%m-%d'),
                    'note': record_note
                })
                save_trade_records(records)
                st.rerun()
    
    if records:
        st.dataframe(pd.DataFrame(records), use_container_width=True)
        
        total_profit = sum(r.get('profit', 0) for r in records if r.get('sell', 0) > 0)
        st.metric("總盈利", f"${total_profit:,.2f}")

# 6. 每日選股頁面
elif st.session_state.page == "🎯 每日選股":
    st.markdown("# 🎯 每日選股")
    if st.button("🚀 開始選股", type="primary"):
        with st.spinner("正在篩選股票..."):
            progress_bar = st.progress(0)
            status_text = st.empty()
            results_df = run_screening(progress_bar, status_text)
            if not results_df.empty:
                st.session_state.screening_results = results_df
                st.dataframe(results_df, use_container_width=True)
            else:
                st.warning("沒有符合條件的股票")
    
    if st.session_state.screening_results is not None:
        st.dataframe(st.session_state.screening_results, use_container_width=True)

# 7. 設定頁面
elif st.session_state.page == "⚙️ 設定":
    st.markdown("# ⚙️ 設定")
    st.info("設定功能")

# ==================== 啟動訊息 ====================
print("=" * 50)
print("📈 港股美股技術分析系統 (雲端版)")
print(f"🚀 啟動時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print("=" * 50)
