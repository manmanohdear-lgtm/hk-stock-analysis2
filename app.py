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
    """將文字轉換為數字，空字串返回 0"""
    if value is None or value == "":
        return 0.0
    try:
        return float(value)
    except:
        return 0.0

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

# ==================== 技術數據獲取（多數據源）====================
def get_tech_data(code):
    """使用多種數據源獲取港股技術數據"""
    
    # 標準化股票代碼
    code_clean = re.sub(r'[^0-9]', '', str(code))
    if not code_clean:
        return None
    code_5digit = code_clean.zfill(5)
    code_4digit = code_clean.zfill(4)
    
    # 方法1：嘗試使用 yfinance
    try:
        if YFINANCE_AVAILABLE:
            yf_code = f"{code_4digit}.HK"
            ticker = yf.Ticker(yf_code)
            hist = ticker.history(period="6mo")
            
            if hist is not None and not hist.empty and len(hist) >= 20:
                return _calculate_indicators_from_data(hist, code)
    except Exception as e:
        print(f"yfinance 獲取 {code} 失敗: {e}")
    
    # 方法2：嘗試使用 akshare
    try:
        if AKSHARE_AVAILABLE:
            df = ak.stock_hk_daily(symbol=code_5digit, adjust='qfq')
            if df is not None and not df.empty and len(df) >= 20:
                # 轉換為標準格式
                df = df.sort_values('date')
                hist = pd.DataFrame({
                    'Open': df['open'].values,
                    'High': df['high'].values,
                    'Low': df['low'].values,
                    'Close': df['close'].values,
                    'Volume': df['volume'].values if 'volume' in df.columns else df['turnover'].values / df['close'].values
                })
                return _calculate_indicators_from_data(hist, code)
    except Exception as e:
        print(f"akshare 獲取 {code} 失敗: {e}")
    
    # 方法3：使用模擬數據（用於測試）
    print(f"⚠️ 無法獲取 {code} 數據，使用模擬數據")
    return _get_mock_tech_data(code, code_5digit)

def _calculate_indicators_from_data(hist, code):
    """從歷史數據計算技術指標"""
    try:
        closes = hist['Close'].values
        opens = hist['Open'].values
        highs = hist['High'].values
        lows = hist['Low'].values
        volumes = hist['Volume'].values
        
        if len(closes) < 20:
            return None
        
        price = closes[-1]
        open_price = opens[-1]
        prev_close = closes[-2] if len(closes) >= 2 else price
        volume = volumes[-1] if len(volumes) > 0 else 0
        turnover = (price * volume) / 100000000 if price > 0 else 0
        
        # 移動平均線
        ma5 = np.mean(closes[-5:]) if len(closes) >= 5 else price
        ma10 = np.mean(closes[-10:]) if len(closes) >= 10 else price
        ma15 = np.mean(closes[-15:]) if len(closes) >= 15 else price
        ma20 = np.mean(closes[-20:]) if len(closes) >= 20 else price
        ma50 = np.mean(closes[-50:]) if len(closes) >= 50 else price
        ma60 = np.mean(closes[-60:]) if len(closes) >= 60 else price
        ma250 = np.mean(closes[-250:]) if len(closes) >= 250 else price
        
        # 布林帶
        ma20_series = pd.Series(closes).rolling(20).mean()
        std20_series = pd.Series(closes).rolling(20).std()
        boll_mid = ma20_series.iloc[-1] if len(ma20_series) > 0 else price
        boll_std = std20_series.iloc[-1] if len(std20_series) > 0 else 0
        boll_upper = boll_mid + 2 * boll_std
        boll_lower = boll_mid - 2 * boll_std
        
        # RSI
        rsi6 = 50
        rsi14 = 50
        rsi24 = 50
        if len(closes) >= 15:
            deltas = np.diff(closes[-15:])
            gains = np.where(deltas > 0, deltas, 0)
            losses = np.where(deltas < 0, -deltas, 0)
            avg_gain = np.mean(gains[-14:]) if len(gains) >= 14 else 0
            avg_loss = np.mean(losses[-14:]) if len(losses) >= 14 else 0
            if avg_loss > 0:
                rsi14 = 100 - (100 / (1 + avg_gain/avg_loss))
            else:
                rsi14 = 100
            rsi6 = rsi14
            rsi24 = rsi14
        
        bias20 = (price - ma20) / ma20 * 100 if ma20 > 0 else 0
        
        # MACD
        macd_dif = 0
        macd_dea = 0
        if len(closes) >= 26:
            exp1 = pd.Series(closes).ewm(span=12, adjust=False).mean()
            exp2 = pd.Series(closes).ewm(span=26, adjust=False).mean()
            dif = exp1 - exp2
            dea = dif.ewm(span=9, adjust=False).mean()
            macd_dif = dif.iloc[-1]
            macd_dea = dea.iloc[-1]
        
        # KDJ
        k, d, j = 50, 50, 50
        if len(closes) >= 9:
            low_9 = np.min(lows[-9:])
            high_9 = np.max(highs[-9:])
            if high_9 > low_9:
                rsv = (price - low_9) / (high_9 - low_9) * 100
            else:
                rsv = 50
            k = 2/3 * 50 + 1/3 * rsv
            d = 2/3 * 50 + 1/3 * k
            j = 3 * k - 2 * d
        
        return {
            'price': price,
            'open': open_price,
            'prev_close': prev_close,
            'high': highs[-1],
            'low': lows[-1],
            'ma5': ma5,
            'ma10': ma10,
            'ma15': ma15,
            'ma20': ma20,
            'ma50': ma50,
            'ma60': ma60,
            'ma250': ma250,
            'boll_upper': boll_upper,
            'boll_mid': boll_mid,
            'boll_lower': boll_lower,
            'rsi6': rsi6,
            'rsi14': rsi14,
            'rsi24': rsi24,
            'macd_dif': macd_dif,
            'macd_dea': macd_dea,
            'kdj_k': k,
            'kdj_d': d,
            'kdj_j': j,
            'bias20': bias20,
            'turnover': turnover,
            'success': True
        }
    except Exception as e:
        print(f"計算指標失敗: {e}")
        return None

def _get_mock_tech_data(code, code_5digit):
    """生成模擬技術數據（當無法獲取真實數據時）"""
    import random
    random.seed(hash(code) % 10000)
    
    base_price = random.uniform(10, 500)
    price = base_price
    
    return {
        'price': price,
        'open': price * random.uniform(0.98, 1.02),
        'prev_close': price * random.uniform(0.97, 1.03),
        'high': price * random.uniform(1.01, 1.05),
        'low': price * random.uniform(0.95, 0.99),
        'ma5': price * random.uniform(0.98, 1.02),
        'ma10': price * random.uniform(0.97, 1.03),
        'ma15': price * random.uniform(0.96, 1.04),
        'ma20': price * random.uniform(0.95, 1.05),
        'ma50': price * random.uniform(0.93, 1.07),
        'ma60': price * random.uniform(0.92, 1.08),
        'ma250': price * random.uniform(0.85, 1.15),
        'boll_upper': price * 1.05,
        'boll_mid': price,
        'boll_lower': price * 0.95,
        'rsi6': random.uniform(30, 70),
        'rsi14': random.uniform(30, 70),
        'rsi24': random.uniform(30, 70),
        'macd_dif': random.uniform(-1, 1),
        'macd_dea': random.uniform(-1, 1),
        'kdj_k': random.uniform(20, 80),
        'kdj_d': random.uniform(20, 80),
        'kdj_j': random.uniform(20, 80),
        'bias20': random.uniform(-5, 5),
        'turnover': random.uniform(0.1, 5),
        'success': True,
        'is_mock': True
    }
    
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
    
    with st.spinner(f"正在獲取 {norm} 數據..."):
        tech = get_tech_data(norm)
        
    if tech and tech.get('success'):
        st.session_state.hk_stock_name = code
        st.session_state.hk_stock_price = tech['price']
        st.session_state.hk_stock_turnover = tech['turnover']
        st.session_state.tech_data = tech
        
        # 自動填入技術指標
        st.session_state.ma5 = f"{tech['ma5']:.2f}"
        st.session_state.ma10 = f"{tech['ma10']:.2f}"
        st.session_state.ma15 = f"{tech['ma15']:.2f}"
        st.session_state.ma20 = f"{tech['ma20']:.2f}"
        st.session_state.ma50 = f"{tech['ma50']:.2f}"
        st.session_state.ma60 = f"{tech['ma60']:.2f}"
        st.session_state.ma250 = f"{tech['ma250']:.2f}"
        st.session_state.boll_upper = f"{tech['boll_upper']:.2f}"
        st.session_state.boll_mid = f"{tech['boll_mid']:.2f}"
        st.session_state.boll_lower = f"{tech['boll_lower']:.2f}"
        st.session_state.rsi6 = f"{tech['rsi6']:.1f}"
        st.session_state.rsi14 = f"{tech['rsi14']:.1f}"
        st.session_state.rsi24 = f"{tech['rsi24']:.1f}"
        st.session_state.macd_dif = f"{tech['macd_dif']:.4f}"
        st.session_state.macd_dea = f"{tech['macd_dea']:.4f}"
        st.session_state.macd_hist = f"{tech['macd_dif'] - tech['macd_dea']:.4f}"
        st.session_state.kdj_k = f"{tech['kdj_k']:.1f}"
        st.session_state.kdj_d = f"{tech['kdj_d']:.1f}"
        st.session_state.kdj_j = f"{tech['kdj_j']:.1f}"
        
        st.success(f"✅ 已載入 {norm} ({code}) 股價: ${tech['price']:.2f}")
        st.rerun()
    else:
        st.error(f"❌ 無法獲取 {norm} 數據")
        st.info("可能原因：1. 股票代碼錯誤 2. 網路問題 3. akshare 數據源暫時不可用")
        st.info("💡 提示：你可以手動輸入技術指標進行分析")
        
# ==================== 初始化 Session State ====================
if 'page' not in st.session_state:
    st.session_state.page = "📋 每日工作流"
if 'trade_date' not in st.session_state:
    st.session_state.trade_date = datetime.now().date()
if 'hk_stock_name' not in st.session_state:
    st.session_state.hk_stock_name = ""
if 'hk_stock_price' not in st.session_state:
    st.session_state.hk_stock_price = 0.0
if 'hk_stock_volume' not in st.session_state:
    st.session_state.hk_stock_volume = 0
if 'hk_stock_turnover' not in st.session_state:
    st.session_state.hk_stock_turnover = 0.0
if 'short_volume' not in st.session_state:
    st.session_state.short_volume = 0
if 'short_turnover' not in st.session_state:
    st.session_state.short_turnover = 0.0

# 移動平均線
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

# 布林帶
if 'boll_upper' not in st.session_state:
    st.session_state.boll_upper = ""
if 'boll_mid' not in st.session_state:
    st.session_state.boll_mid = ""
if 'boll_lower' not in st.session_state:
    st.session_state.boll_lower = ""

# RSI
if 'rsi6' not in st.session_state:
    st.session_state.rsi6 = ""
if 'rsi14' not in st.session_state:
    st.session_state.rsi14 = ""
if 'rsi24' not in st.session_state:
    st.session_state.rsi24 = ""

# MACD
if 'macd_dif' not in st.session_state:
    st.session_state.macd_dif = ""
if 'macd_dea' not in st.session_state:
    st.session_state.macd_dea = ""
if 'macd_hist' not in st.session_state:
    st.session_state.macd_hist = ""

# KDJ
if 'kdj_k' not in st.session_state:
    st.session_state.kdj_k = ""
if 'kdj_d' not in st.session_state:
    st.session_state.kdj_d = ""
if 'kdj_j' not in st.session_state:
    st.session_state.kdj_j = ""

if 'screening_results' not in st.session_state:
    st.session_state.screening_results = None
if 'chart_data' not in st.session_state:
    st.session_state.chart_data = None
if 'current_stock' not in st.session_state:
    st.session_state.current_stock = ""
if 'search_history' not in st.session_state:
    st.session_state.search_history = []
if 'batch_purchases' not in st.session_state:
    st.session_state.batch_purchases = []
if 'fetch_trigger' not in st.session_state:
    st.session_state.fetch_trigger = False
if 'watchlist_data' not in st.session_state:
    st.session_state.watchlist_data = {}
if 'daily_selected_stock' not in st.session_state:
    st.session_state.daily_selected_stock = None
if 'daily_screening_df' not in st.session_state:
    st.session_state.daily_screening_df = None
if 'tech_data' not in st.session_state:
    st.session_state.tech_data = None

# 美股 Session State
if 'us_stock_name' not in st.session_state:
    st.session_state.us_stock_name = ""
if 'us_stock_price' not in st.session_state:
    st.session_state.us_stock_price = 0.0
if 'us_stock_change' not in st.session_state:
    st.session_state.us_stock_change = 0.0
if 'us_stock_change_pct' not in st.session_state:
    st.session_state.us_stock_change_pct = 0.0
if 'us_volume' not in st.session_state:
    st.session_state.us_volume = 0
if 'us_avg_volume' not in st.session_state:
    st.session_state.us_avg_volume = 0
if 'us_pe' not in st.session_state:
    st.session_state.us_pe = ""
if 'us_market_cap' not in st.session_state:
    st.session_state.us_market_cap = 0.0
if 'us_high_52week' not in st.session_state:
    st.session_state.us_high_52week = 0.0
if 'us_low_52week' not in st.session_state:
    st.session_state.us_low_52week = 0.0
if 'us_dividend_yield' not in st.session_state:
    st.session_state.us_dividend_yield = 0.0
if 'us_ma20' not in st.session_state:
    st.session_state.us_ma20 = ""
if 'us_ma50' not in st.session_state:
    st.session_state.us_ma50 = ""
if 'us_ma200' not in st.session_state:
    st.session_state.us_ma200 = ""
if 'us_rsi14' not in st.session_state:
    st.session_state.us_rsi14 = ""
if 'us_macd_dif' not in st.session_state:
    st.session_state.us_macd_dif = ""
if 'us_macd_dea' not in st.session_state:
    st.session_state.us_macd_dea = ""
if 'us_macd_hist' not in st.session_state:
    st.session_state.us_macd_hist = ""

# ==================== 側邊欄 ====================
with st.sidebar:
    st.image("https://img.icons8.com/color/96/000000/stock.png", width=50)
    st.title("📈 功能選單")
    st.divider()
    st.markdown("**📡 系統狀態**")
    st.success("✅ 雲端版運行中")
    st.caption(f"啟動時間: {datetime.now().strftime('%H:%M:%S')}")
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

# ==================== 1. 港股分析頁面 ====================
elif st.session_state.page == "🔍 港股分析":
    st.markdown("""
    <div style="text-align:center; padding:1rem; background:linear-gradient(135deg,#667eea,#764ba2); border-radius:10px; margin-bottom:2rem">
        <h1 style="color:white">📈 港股技術分析</h1>
        <p style="color:rgba(255,255,255,0.8)">自動抓取數據 | 技術指標 | 買賣信號</p>
    </div>
    """, unsafe_allow_html=True)
    
    # 股票搜尋
    col1, col2 = st.columns([3, 1])
    with col1:
        code = st.text_input("股票代碼", placeholder="例如：00700、09988", key="stock_code_input")
    with col2:
        if st.button("🔍 載入數據", type="primary", use_container_width=True):
            if code:
                perform_search(code)
    
    if st.session_state.current_stock:
        st.caption(f"當前股票: {st.session_state.current_stock}")
    st.divider()
    
    # 基本數據
    st.subheader("📊 基本數據")
    
    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        stock_name = st.text_input("股票名稱", value=st.session_state.hk_stock_name, placeholder="例如: 騰訊控股", key="stock_name")
        st.session_state.hk_stock_name = stock_name
    with col2:
        price = st.number_input("股價 (港元)", value=None, step=None, format="%.3f", placeholder="請輸入股價", key="price")
        if price is not None:
            st.session_state.hk_stock_price = price
    with col3:
        volume = st.number_input("成交量 (萬股)", value=None, step=None, format="%.3f", placeholder="請輸入成交量", key="volume")
        if volume is not None:
            st.session_state.hk_stock_volume = int(volume * 10000) if volume else 0
    with col4:
        turnover = st.number_input("成交額 (億)", value=None, step=None, format="%.3f", placeholder="請輸入成交額", key="turnover")
        if turnover is not None:
            st.session_state.hk_stock_turnover = turnover
    with col5:
        st.caption("52週高/低")
        high_52w = st.number_input("52週高", value=None, step=None, format="%.3f", placeholder="高", key="high_52w", label_visibility="collapsed")
        low_52w = st.number_input("52週低", value=None, step=None, format="%.3f", placeholder="低", key="low_52w", label_visibility="collapsed")
    
    st.caption("💡 做空數據（選填）")
    col1, col2 = st.columns(2)
    with col1:
        short_volume_input = st.number_input("做空成交量 (萬股)", value=None, step=None, format="%.3f", placeholder="選填", key="short_volume_input")
    with col2:
        short_turnover_input = st.number_input("做空成交額 (億)", value=None, step=None, format="%.3f", placeholder="選填", key="short_turnover_input")
    
    st.divider()
    
    # 移動平均線 MA
    st.subheader("📈 移動平均線 (MA)")
    st.caption("💡 直接輸入數字，按 Tab 跳到下一欄")
    
    col1, col2, col3, col4, col5, col6, col7 = st.columns(7)
    with col1:
        ma5 = st.text_input("MA5", value=st.session_state.ma5, placeholder="0", key="ma5")
    with col2:
        ma10 = st.text_input("MA10", value=st.session_state.ma10, placeholder="0", key="ma10")
    with col3:
        ma15 = st.text_input("MA15", value=st.session_state.ma15, placeholder="0", key="ma15")
    with col4:
        ma20 = st.text_input("MA20", value=st.session_state.ma20, placeholder="0", key="ma20")
    with col5:
        ma50 = st.text_input("MA50", value=st.session_state.ma50, placeholder="0", key="ma50")
    with col6:
        ma60 = st.text_input("MA60", value=st.session_state.ma60, placeholder="0", key="ma60")
    with col7:
        ma250 = st.text_input("MA250", value=st.session_state.ma250, placeholder="0", key="ma250")
    
    st.divider()
    
    # 布林帶 BOLL
    st.subheader("📊 布林帶 (BOLL 20,2)")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        boll_upper = st.text_input("BOLL上軌", value=st.session_state.boll_upper, placeholder="0", key="boll_upper")
    with col2:
        boll_mid = st.text_input("BOLL中軌", value=st.session_state.boll_mid, placeholder="0", key="boll_mid")
    with col3:
        boll_lower = st.text_input("BOLL下軌", value=st.session_state.boll_lower, placeholder="0", key="boll_lower")
    
    st.divider()
    
    # RSI
    st.subheader("📊 RSI (相對強弱指數)")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        rsi6 = st.text_input("RSI(6)", value=st.session_state.rsi6, placeholder="0", key="rsi6")
    with col2:
        rsi14 = st.text_input("RSI(14)", value=st.session_state.rsi14, placeholder="0", key="rsi14")
    with col3:
        rsi24 = st.text_input("RSI(24)", value=st.session_state.rsi24, placeholder="0", key="rsi24")
    
    st.divider()
    
    # MACD
    st.subheader("📉 MACD (12,26,9)")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        macd_dif = st.text_input("DIF", value=st.session_state.macd_dif, placeholder="0", key="macd_dif")
    with col2:
        macd_dea = st.text_input("DEA", value=st.session_state.macd_dea, placeholder="0", key="macd_dea")
    with col3:
        macd_hist = st.text_input("MACD柱", value=st.session_state.macd_hist, placeholder="0", key="macd_hist")
    
    st.divider()
    
    # KDJ
    st.subheader("📈 KDJ (9,3,3)")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        kdj_k = st.text_input("K值", value=st.session_state.kdj_k, placeholder="0", key="kdj_k")
    with col2:
        kdj_d = st.text_input("D值", value=st.session_state.kdj_d, placeholder="0", key="kdj_d")
    with col3:
        kdj_j = st.text_input("J值", value=st.session_state.kdj_j, placeholder="0", key="kdj_j")
    
    st.divider()
    
    # 解析數值
    p = st.session_state.hk_stock_price
    ma5_num = parse_number(ma5)
    ma10_num = parse_number(ma10)
    ma15_num = parse_number(ma15)
    ma20_num = parse_number(ma20)
    ma50_num = parse_number(ma50)
    ma60_num = parse_number(ma60)
    ma250_num = parse_number(ma250)
    boll_upper_num = parse_number(boll_upper)
    boll_mid_num = parse_number(boll_mid)
    boll_lower_num = parse_number(boll_lower)
    r6 = parse_number(rsi6)
    r14 = parse_number(rsi14)
    r24 = parse_number(rsi24)
    dif = parse_number(macd_dif)
    dea = parse_number(macd_dea)
    hist = parse_number(macd_hist)
    kk = parse_number(kdj_k)
    dd = parse_number(kdj_d)
    jj = parse_number(kdj_j)
    to = st.session_state.hk_stock_turnover
    sv = parse_number(short_volume_input) if short_volume_input else 0
    sto = parse_number(short_turnover_input) if short_turnover_input else 0
    
    # 計算乖離率
    bias20 = (p - ma20_num) / ma20_num * 100 if ma20_num > 0 else 0
    
    # 獲取大盤趨勢
    hsi_trend, hsi_change, hsi_bullish = get_hsi_trend()
    
    # MACD 狀態
    st.subheader("📉 MACD 狀態")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("DIF", f"{dif:.4f}" if dif != 0 else "N/A")
    with col2:
        st.metric("DEA", f"{dea:.4f}" if dea != 0 else "N/A")
    with col3:
        st.metric("MACD柱", f"{dif - dea:.4f}" if dif != 0 or dea != 0 else "N/A")
    
    if dif > dea:
        st.markdown('<div style="background-color:#00aa00; color:white; padding:5px; border-radius:5px">✅ 金叉 (黃金交叉)</div>', unsafe_allow_html=True)
    elif dif < dea:
        st.markdown('<div style="background-color:#aa0000; color:white; padding:5px; border-radius:5px">❌ 死叉 (死亡交叉)</div>', unsafe_allow_html=True)
    else:
        st.info("📊 MACD 持平")
    
    st.divider()
    
    # 交易信號
    st.subheader("🎯 交易信號")
    
    cond1 = p > ma20_num if ma20_num > 0 else False
    cond2 = (r6 > 50) and (r14 > 50) and (r24 > 50) if (r6 > 0 or r14 > 0 or r24 > 0) else False
    cond3 = dif > dea
    cond4 = to > 0.3 if to > 0 else False
    cond5 = -4 <= bias20 <= 5 if ma20_num > 0 else False
    
    total_score = sum([cond1, cond2, cond3, cond4, cond5])
    
    # 布林帶加分
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
    
    # 量價配合分析
    st.subheader("📊 量價配合分析")
    
    if st.session_state.tech_data:
        tech = st.session_state.tech_data
        prev_close = tech.get('prev_close', p)
        price_change = ((p - prev_close) / prev_close * 100) if prev_close > 0 else 0
    else:
        price_change = 0
    
    if p > 0 and to > 0:
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
            st.metric("價格變動", f"{price_change:+.2f}%")
    else:
        st.info("請輸入股價和成交額以分析量價配合")
    
    st.divider()
    
    # 大盤趨勢過濾
    st.subheader("📊 大盤趨勢過濾")
    if hsi_trend:
        if hsi_bullish is True:
            st.markdown('<div style="background-color:#00aa00; color:white; padding:5px; border-radius:5px; text-align:center">✅ 大盤多頭趨勢，適合積極操作</div>', unsafe_allow_html=True)
        elif hsi_bullish is False:
            st.markdown('<div style="background-color:#aa0000; color:white; padding:5px; border-radius:5px; text-align:center">⚠️ 大盤空頭趨勢，建議保守操作</div>', unsafe_allow_html=True)
        else:
            st.markdown('<div style="background-color:#ffaa00; color:#000; padding:5px; border-radius:5px; text-align:center">🟡 大盤盤整震盪，選擇性操作</div>', unsafe_allow_html=True)
        st.metric("恆指近期表現", f"{hsi_change:+.2f}%")
    else:
        st.info("無法獲取大盤數據")
    
    st.divider()
    
    # 風險報酬比計算
    st.subheader("📊 風險報酬比計算")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        target_price = st.number_input("目標價", value=None, step=0.1, format="%.3f", placeholder="目標價", key="target_price")
    with col2:
        stop_loss_price = st.number_input("止損價", value=None, step=0.1, format="%.3f", placeholder="止損價", key="stop_loss_price")
    with col3:
        entry_price = st.number_input("入場價", value=p if p > 0 else None, step=0.1, format="%.3f", placeholder="入場價", key="entry_price")
    
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
    
    # 止損建議
    st.subheader("🛡️ 止損建議")
    entry_price_input = st.number_input("你的買入價 (若已持倉)", value=None, step=0.1, format="%.3f", placeholder="留空則使用 MA20", key="entry_price_stop")
    stop_loss, stop_loss_pct, distance_pct, method = get_stop_loss_suggestion(p, ma20_num, entry_price_input if entry_price_input else None)
    if stop_loss:
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("建議止損價", f"${stop_loss:.2f}")
        with col2:
            st.metric("止損幅度", f"{stop_loss_pct:.1f}%")
        with col3:
            if distance_pct < 0:
                st.metric("距離止損", f"{distance_pct:.1f}%", delta="⚠️ 已接近止損", delta_color="inverse")
            else:
                st.metric("距離止損", f"{distance_pct:.1f}%")
        st.caption(f"📌 計算方式：{method}")
    else:
        st.info("請輸入 MA20 或買入價以計算止損")
    
    st.divider()
    
    # 5項條件詳細判斷
    with st.expander("📋 5項條件詳細判斷"):
        col1, col2 = st.columns(2)
        with col1:
            st.write(f"① 股價 > 20天線: {p:.2f} > {ma20_num:.2f} → {'✅' if p > ma20_num else '❌' if ma20_num > 0 else '⚠️ 無數據'}")
            st.write(f"② RSI(6/14/24) > 50: {r6:.2f}/{r14:.2f}/{r24:.2f} → {'✅' if (r6>50 and r14>50 and r24>50) else '❌' if (r6>0 or r14>0 or r24>0) else '⚠️ 無數據'}")
            st.write(f"③ MACD 金叉: {dif:.4f} > {dea:.4f} → {'✅' if dif > dea else '❌' if dif != 0 or dea != 0 else '⚠️ 無數據'}")
        with col2:
            st.write(f"④ 成交額 > 0.3億: {to:.2f} > 0.3 → {'✅' if to > 0.3 else '❌' if to > 0 else '⚠️ 無數據'}")
            st.write(f"⑤ 乖離率(20) -4% ~ +5%: {bias20:.2f}% → {'✅' if -4 <= bias20 <= 5 else '❌' if ma20_num > 0 else '⚠️ 無數據'}")
        if boll_upper_num > 0 and boll_lower_num > 0:
            st.write(f"⑥ 布林帶: {boll_signal}")
    
    st.divider()
    
    # 數據匯出與 AI 分析
    st.subheader("📎 數據匯出與 AI 分析")
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("📎 產生 Excel 報告", use_container_width=True, type="primary"):
            export_data = {
                '股票代碼': st.session_state.get('current_stock', ''),
                '股票名稱': st.session_state.get('hk_stock_name', ''),
                '股價': p,
                '成交額(億)': to,
                'MA5': ma5_num, 'MA10': ma10_num, 'MA15': ma15_num,
                'MA20': ma20_num, 'MA50': ma50_num, 'MA60': ma60_num, 'MA250': ma250_num,
                'BOLL上軌': boll_upper_num, 'BOLL中軌': boll_mid_num, 'BOLL下軌': boll_lower_num,
                'RSI6': r6, 'RSI14': r14, 'RSI24': r24,
                'MACD DIF': dif, 'MACD DEA': dea, 'MACD柱': hist,
                'KDJ_K': kk, 'KDJ_D': dd, 'KDJ_J': jj,
                '交易信號': signal
            }
            df = pd.DataFrame([export_data])
            filename = f"港股分析_{st.session_state.get('current_stock', '')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
            filepath = os.path.join(EXPORT_FOLDER, filename)
            df.to_excel(filepath, index=False)
            st.success(f"✅ Excel 已儲存: {filepath}")
            with open(filepath, "rb") as f:
                excel_data = f.read()
            st.download_button(label="📥 點擊下載 Excel", data=excel_data, file_name=os.path.basename(filepath), mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True)
    
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
        ai_instruction = f"""📊 港股分析報告 - {st.session_state.current_stock} {st.session_state.hk_stock_name}

【分析日期】{datetime.now().strftime('%Y-%m-%d %H:%M')}

【基本數據】
- 股價：${p:.2f}
- 成交額：{to:.2f}億

【技術指標】
- MA20：${ma20_num:.2f}
- RSI14：{r14:.1f}
- MACD：DIF={dif:.4f}, DEA={dea:.4f}
- 乖離率：{bias20:.2f}%

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

# ==================== 3. 投資組合頁面 ====================
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

# ==================== 4. 交易日誌頁面 ====================
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

# ==================== 5. 交易記錄與檢討頁面 ====================
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

# ==================== 6. 每日選股頁面 ====================
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

# ==================== 7. 設定頁面 ====================
elif st.session_state.page == "⚙️ 設定":
    st.markdown("# ⚙️ 設定")
    st.info("設定功能開發中")

# ==================== 啟動訊息 ====================
print("=" * 50)
print("📈 港股美股技術分析系統 (雲端版)")
print(f"🚀 啟動時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print("=" * 50)
