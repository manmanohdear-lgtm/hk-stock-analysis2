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

# 增加遞迴限制
sys.setrecursionlimit(1000000)

# 嘗試導入數據庫套件
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

# ==================== 雲端部署：使用相對路徑 ====================
EXPORT_FOLDER = os.path.join(os.path.dirname(__file__), 'data')
os.makedirs(EXPORT_FOLDER, exist_ok=True)

WATCHLIST_FILE = os.path.join(EXPORT_FOLDER, 'watchlist.json')
PORTFOLIO_FILE = os.path.join(EXPORT_FOLDER, 'portfolio.json')
JOURNAL_FILE = os.path.join(EXPORT_FOLDER, 'journal.json')
TRADE_RECORDS_FILE = os.path.join(EXPORT_FOLDER, 'trade_records.json')

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
    SECTOR_KEYWORDS = {
        'AI/科技': ['AI', '人工智能', '騰訊', '阿里', '百度', '網易', '美團', '快手', '京東'],
        '半導體': ['半導體', '芯片', '中芯', '華虹'],
        '新能源/電動車': ['新能源', '電動車', '比亞迪', '理想', '蔚來', '小鵬', '特斯拉'],
        '醫藥/生物科技': ['醫藥', '生物科技', '藥明', '石藥'],
        '金融/保險': ['銀行', '保險', '證券', '匯豐', '友邦', '平保', '港交所'],
        '其他': []
    }
    name_lower = name.lower() if name else ""
    for sector, keywords in SECTOR_KEYWORDS.items():
        for kw in keywords:
            if kw.lower() in name_lower:
                return sector
    return "其他"

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

# ==================== 簡單的技術數據獲取（雲端優化版）====================
def get_simple_tech_data(code):
    """簡化的技術數據獲取，減少記憶體使用"""
    try:
        if not AKSHARE_AVAILABLE:
            return None
        df = ak.stock_hk_daily(symbol=code, adjust='qfq')
        if df is None or len(df) < 20:
            return None
        df = df.sort_values('date')
        closes = df['close'].values
        price = closes[-1]
        ma20 = np.mean(closes[-20:]) if len(closes) >= 20 else price
        rsi14 = 50
        if len(closes) >= 15:
            deltas = np.diff(closes[-15:])
            gains = np.where(deltas > 0, deltas, 0)
            losses = np.where(deltas < 0, -deltas, 0)
            avg_gain = np.mean(gains[-14:]) if len(gains) >= 14 else 0
            avg_loss = np.mean(losses[-14:]) if len(losses) >= 14 else 0
            rsi14 = 100 - (100 / (1 + avg_gain/avg_loss)) if avg_loss > 0 else 100
        bias20 = (price - ma20) / ma20 * 100 if ma20 > 0 else 0
        turnover = df['turnover'].values[-1] / 100000000 if 'turnover' in df.columns else 0
        return {
            'price': price, 'ma20': ma20, 'rsi14': rsi14,
            'bias20': bias20, 'turnover': turnover, 'success': True
        }
    except Exception as e:
        return None

# ==================== 每日選股函數（雲端優化版）====================
def run_screening(progress_bar, status_text):
    if not AKSHARE_AVAILABLE:
        status_text.text("請安裝 akshare: pip3 install akshare")
        return pd.DataFrame()
    
    status_text.text("獲取港股列表...")
    try:
        stocks = ak.stock_hk_spot()
    except Exception as e:
        status_text.text(f"失敗: {e}")
        return pd.DataFrame()
    
    if stocks is None or stocks.empty:
        status_text.text("無法獲取股票數據")
        return pd.DataFrame()
    
    stocks['成交额'] = pd.to_numeric(stocks['成交额'], errors='coerce')
    stocks['最新价'] = pd.to_numeric(stocks['最新价'], errors='coerce')
    stocks = stocks[(stocks['成交额'] > 50000000) & (stocks['最新价'] > 1)]
    
    # 雲端版：只分析 10 隻股票
    MAX_ANALYSIS = 10
    if len(stocks) > MAX_ANALYSIS:
        stocks = stocks.head(MAX_ANALYSIS)
        status_text.text(f"⚠️ 限制分析 {MAX_ANALYSIS} 隻股票")
    
    if stocks.empty:
        status_text.text("沒有符合基本條件的股票")
        return pd.DataFrame()
    
    progress_bar.progress(0.2)
    status_text.text(f"分析 {len(stocks)} 隻股票...")
    
    results = []
    total = len(stocks)
    
    for i, (_, row) in enumerate(stocks.iterrows()):
        code = row['代码']
        name = row.get('中文名称', code)
        
        pct = 0.2 + 0.7 * (i / total) if total > 0 else 0.9
        progress_bar.progress(min(pct, 0.99))
        status_text.text(f"[{i+1}/{total}] {code} {name[:12]}")
        
        tech = get_simple_tech_data(code)
        if not tech:
            continue
        
        cond1 = tech['price'] > tech['ma20']
        cond2 = tech['rsi14'] > 50
        cond3 = tech['turnover'] > 0.3
        cond4 = -4 <= tech['bias20'] <= 5
        tech_score = sum([cond1, cond2, cond3, cond4])
        
        if tech_score < 2:
            continue
        
        sector = get_stock_sector(name)
        total_score = tech_score * 10 + min(tech['turnover'], 10) * 2
        
        results.append({
            '代碼': code,
            '名稱': name[:20],
            '股價': round(tech['price'], 2),
            '成交額': round(tech['turnover'], 2),
            'RSI': round(tech['rsi14'], 1),
            '板塊': sector,
            '總分': round(total_score, 2)
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

# ==================== 初始化 Session State ====================
if 'page' not in st.session_state:
    st.session_state.page = "📋 每日工作流"
if 'screening_results' not in st.session_state:
    st.session_state.screening_results = None
if 'current_stock' not in st.session_state:
    st.session_state.current_stock = ""
if 'search_history' not in st.session_state:
    st.session_state.search_history = []

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

# 1. 港股分析頁面
elif st.session_state.page == "🔍 港股分析":
    st.markdown("# 📈 港股技術分析")
    st.info("港股分析功能正在恢復中...")
    code = st.text_input("股票代碼", placeholder="例如: 00700")
    if code and st.button("分析"):
        st.info(f"正在分析 {code}...")

# 2. 自選股頁面
elif st.session_state.page == "⭐ 自選股":
    st.markdown("# ⭐ 自選股")
    watchlist = load_watchlist()
    if not watchlist:
        st.info("暫無自選股")
    else:
        for code in watchlist:
            st.write(f"📊 {code}")

# 3. 投資組合頁面
elif st.session_state.page == "📊 投資組合":
    st.markdown("# 📊 投資組合")
    pf = load_portfolio()
    st.dataframe(pd.DataFrame(pf) if pf else pd.DataFrame())

# 4. 交易日誌頁面
elif st.session_state.page == "📝 交易日誌":
    st.markdown("# 📝 交易日誌")
    code = st.text_input("股票代碼")
    if code:
        notes = load_journal(code)
        for n in notes:
            st.write(f"📌 {n}")

# 5. 交易記錄與檢討頁面
elif st.session_state.page == "📊 交易記錄與檢討":
    st.markdown("# 📊 交易記錄與檢討")
    records = load_trade_records()
    st.dataframe(pd.DataFrame(records) if records else pd.DataFrame())

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

# 7. 設定頁面
elif st.session_state.page == "⚙️ 設定":
    st.markdown("# ⚙️ 設定")
    st.info("設定功能正在恢復中...")

# ==================== 啟動訊息 ====================
print("=" * 50)
print("📈 港股美股技術分析系統 (雲端版)")
print(f"🚀 啟動時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print("=" * 50)
