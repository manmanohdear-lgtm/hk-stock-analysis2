#!/usr/bin/env python3
# ==================== 🚀 自動使用 streamlit run 啟動 ====================
import sys
import os
import subprocess

def restart_with_streamlit():
    if os.environ.get('STREAMLIT_RUNNING') == '1':
        return
    if not hasattr(sys, '_called_from_streamlit'):
        print("=" * 60)
        print("⚠️ 檢測到使用 python3 直接執行")
        print("=" * 60)
        print("這個應用是 Streamlit 應用，需要用以下命令啟動：")
        print("")
        print("    streamlit run app.py")
        print("")
        print("正在自動為你重新啟動...")
        print("=" * 60)
        script_path = os.path.abspath(__file__)
        try:
            env = os.environ.copy()
            env['STREAMLIT_RUNNING'] = '1'
            subprocess.run(['streamlit', 'run', script_path], env=env)
            sys.exit(0)
        except FileNotFoundError:
            print("❌ 找不到 streamlit 命令")
            print("")
            print("請先安裝 streamlit：")
            print("    pip3 install streamlit")
            sys.exit(1)
        except Exception as e:
            print(f"❌ 自動重新啟動失敗: {e}")
            print("")
            print("請手動執行：")
            print(f"    streamlit run {script_path}")
            sys.exit(1)

if __name__ == "__main__":
    restart_with_streamlit()
# ==================== 檢測程式碼結束 ====================

import streamlit as st
import sys
sys.setrecursionlimit(1000000)
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
warnings.filterwarnings('ignore')

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

try:
    from futu import *
    FUTU_AVAILABLE = True
except:
    FUTU_AVAILABLE = False

st.set_page_config(page_title="港股美股技術分析系統", page_icon="📈", layout="wide")

EXPORT_FOLDER = os.path.join(os.path.dirname(__file__), 'data')
os.makedirs(EXPORT_FOLDER, exist_ok=True)

WATCHLIST_FILE = os.path.join(EXPORT_FOLDER, 'watchlist.json')
WATCHLIST_DATA_FILE = os.path.join(EXPORT_FOLDER, 'watchlist_data.json')
PORTFOLIO_FILE = os.path.join(EXPORT_FOLDER, 'portfolio.json')
JOURNAL_FILE = os.path.join(EXPORT_FOLDER, 'journal.json')
PRICE_ALERT_FILE = os.path.join(EXPORT_FOLDER, 'alerts.json')
TRADE_RECORDS_FILE = os.path.join(EXPORT_FOLDER, 'trade_records.json')
CHECKLIST_FILE = os.path.join(EXPORT_FOLDER, 'checklist_status.json')

SECTOR_KEYWORDS = {
    'AI/科技': ['AI', '人工智能', '智譜', 'MINIMAX', '軟件', '雲端', '大數據', '騰訊', '阿里', '百度', '網易', '美團', '快手', '京東'],
    '半導體': ['半導體', '芯片', '晶片', '中芯', '華虹', 'ASM', '先進半導體'],
    '新能源/電動車': ['新能源', '電動車', '鋰電', '光伏', '比亞迪', '理想', '蔚來', '小鵬', '特斯拉', '寧德', '贛鋒', '天齊'],
    '醫藥/生物科技': ['醫藥', '生物科技', '創新藥', '藥明', '石藥', '中國生物製藥', '百濟', '信達', '金斯瑞'],
    '金融/保險': ['銀行', '保險', '證券', '匯豐', '友邦', '平保', '港交所', '中銀', '恒生', '渣打', '建行', '工行', '中行', '招行'],
    '地產/物業': ['地產', '物業', '恆地', '新地', '長實', '新世界', '信和', '碧桂園', '萬科', '華潤置地', '龍湖'],
    '消費/零售': ['消費', '零售', '餐飲', '體育', '安踏', '李寧', '蒙牛', '海底撈', '百勝', '周大福', '六福'],
    '電訊/基建': ['電訊', '移動', '聯通', '電信', '鐵塔', '中通訊', '基建', '中鐵', '中交建'],
    '能源/資源': ['石油', '煤炭', '中石油', '中石化', '中海油', '神華', '兗礦', '中煤', '礦業', '黃金', '紫金', '招金'],
    '工業/製造': ['工業', '製造', '創科', '舜宇', '瑞聲', '比亞迪電子', '鴻騰', '耐世特'],
    '公用事業': ['公用', '電力', '煤氣', '港燈', '中電', '電能', '水務', '燃氣'],
    '運輸/物流': ['運輸', '物流', '航空', '國泰', '南航', '東航', '國航', '中遠', '嘉里', '順豐'],
    'REITs/信託': ['REIT', '信託', '領展', '置富', '陽光', '冠君'],
    '其他': []
}

SCREENING_CONFIG = {
    'turnover_threshold': 0.3,
    'bias_lower': -4,
    'bias_upper': 5,
    'rsi_threshold': 50,
    'volume_surge_ratio': 1.5,
    'north_flow_days': 3,
}

# ==================== 股票名稱對照表 ====================
STOCK_NAME_MAP = {
    '00700': '騰訊控股', '09988': '阿里巴巴', '01810': '小米集團', '03690': '美團',
    '01024': '快手', '09999': '網易', '09618': '京東集團', '09888': '百度集團',
    '00005': '匯豐控股', '02318': '中國平安', '01299': '友邦保險', '00388': '香港交易所',
    '00941': '中國移動', '00883': '中國海洋石油', '03317': '智譜', '03318': 'MINIMAX-W',
    '01211': '比亞迪股份', '00981': '中芯國際', '01347': '華虹半導體', '02269': '藥明生物',
    'AAPL': '蘋果', 'NVDA': '英偉達', 'TSLA': '特斯拉', 'MSFT': '微軟',
    'GOOGL': '谷歌', 'AMZN': '亞馬遜', 'META': 'Meta', 'AMD': '超微半導體',
    'INTC': '英特爾', 'NFLX': '奈飛', 'DIS': '迪士尼', 'PYPL': 'PayPal',
    'ADBE': 'Adobe', 'CRM': 'Salesforce', 'DOCN': 'DigitalOcean',
}

quote_ctx = None
_current_data_source = "未知"

# ==================== 多數據源管理器 ====================
class DataSourceManager:
    def __init__(self):
        self.primary_source = "futu"
        self.fallback_sources = ["yfinance", "akshare"]
        self.current_source = None
        self.source_status = {
            "futu": {"available": False, "last_error": None},
            "yfinance": {"available": False, "last_error": None},
            "akshare": {"available": False, "last_error": None}
        }
        self._check_all_sources()
    
    def _check_all_sources(self):
        if FUTU_AVAILABLE:
            try:
                ctx = self._get_futu_context()
                if ctx:
                    self.source_status["futu"]["available"] = True
            except:
                pass
        if YFINANCE_AVAILABLE:
            try:
                test = yf.Ticker("00700.HK")
                hist = test.history(period="1d")
                self.source_status["yfinance"]["available"] = len(hist) > 0
            except:
                pass
        if AKSHARE_AVAILABLE:
            self.source_status["akshare"]["available"] = True
        self._set_current_source()
    
    def _set_current_source(self):
        for source in [self.primary_source] + self.fallback_sources:
            if self.source_status.get(source, {}).get("available", False):
                self.current_source = source
                global _current_data_source
                _current_data_source = source
                return
        self.current_source = None
    
    def _get_futu_context(self):
        global quote_ctx
        if quote_ctx is not None:
            try:
                ret, _ = quote_ctx.get_market_snapshot(['HK.00700'])
                if ret == RET_OK:
                    return quote_ctx
                else:
                    quote_ctx.close()
                    quote_ctx = None
            except:
                quote_ctx = None
        if quote_ctx is None and FUTU_AVAILABLE:
            try:
                quote_ctx = OpenQuoteContext(host='127.0.0.1', port=11111)
                return quote_ctx
            except:
                return None
        return quote_ctx
    
    def get_hk_stock_data(self, code):
        if self.current_source == "futu":
            result = self._get_from_futu(code)
            if result[0]:
                return result
            self.source_status["futu"]["available"] = False
            self._set_current_source()
        if self.current_source == "yfinance":
            result = self._get_from_yfinance_hk(code)
            if result[0]:
                return result
            self.source_status["yfinance"]["available"] = False
            self._set_current_source()
        if self.current_source == "akshare":
            result = self._get_from_akshare(code)
            if result[0]:
                return result
        return False, None, None, None, None
    
    def _get_from_futu(self, code):
        try:
            ctx = self._get_futu_context()
            if not ctx:
                return False, None, None, None, None
            code_clean = re.sub(r'[^0-9]', '', str(code))
            if not code_clean:
                return False, None, None, None, None
            code_5digit = code_clean.zfill(5)
            futu_code = f"HK.{code_5digit}"
            ret, snap = ctx.get_market_snapshot([futu_code])
            if ret == RET_OK and not snap.empty:
                name = snap['name'].iloc[0]
                price = float(snap['last_price'].iloc[0])
                volume = int(snap['volume'].iloc[0])
                turnover = float(snap['turnover'].iloc[0]) / 100000000
                return True, name, price, volume / 10000, turnover
            return False, None, None, None, None
        except:
            return False, None, None, None, None
    
    def _get_from_yfinance_hk(self, code):
        try:
            code_clean = re.sub(r'[^0-9]', '', str(code))
            if not code_clean:
                return False, None, None, None, None
            yf_code = f"{code_clean.zfill(4)}.HK"
            ticker = yf.Ticker(yf_code)
            info = ticker.info
            name = info.get('longName', info.get('shortName', code))
            price = info.get('currentPrice', info.get('regularMarketPrice', 0))
            if price == 0:
                hist = ticker.history(period="1d")
                if not hist.empty:
                    price = hist['Close'].iloc[-1]
            volume = info.get('volume', 0)
            turnover = (price * volume) / 100000000 if price > 0 and volume > 0 else 0
            if price > 0:
                return True, name, price, volume / 10000, turnover
            return False, None, None, None, None
        except:
            return False, None, None, None, None
    
    def _get_from_akshare(self, code):
        try:
            code_clean = re.sub(r'[^0-9]', '', str(code))
            if not code_clean:
                return False, None, None, None, None
            code_5digit = code_clean.zfill(5)
            df = ak.stock_hk_spot()
            row = df[df['代码'] == code_5digit]
            if not row.empty:
                name = row.iloc[0].get('中文名称', code)
                price = float(row.iloc[0]['最新价'])
                volume = float(row.iloc[0].get('成交量', 0))
                turnover = float(row.iloc[0].get('成交额', 0)) / 100000000
                return True, name, price, volume / 10000, turnover
            return False, None, None, None, None
        except:
            return False, None, None, None, None
    
    def get_hk_chart_data(self, code, days=180):
        if self.source_status["futu"]["available"]:
            result = self._get_chart_from_futu(code, days)
            if result is not None:
                return result
        if self.source_status["yfinance"]["available"]:
            result = self._get_chart_from_yfinance(code, days)
            if result is not None:
                return result
        return None
    
    def _get_chart_from_futu(self, code, days):
        try:
            ctx = self._get_futu_context()
            if not ctx:
                return None
            code_clean = re.sub(r'[^0-9]', '', str(code))
            code_5digit = code_clean.zfill(5)
            futu_code = f"HK.{code_5digit}"
            ret, hist = ctx.get_history_kline(futu_code, start=(datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d'), end=datetime.now().strftime('%Y-%m-%d'))
            if ret != RET_OK or hist.empty:
                return None
            df = hist.copy()
            df['date'] = pd.to_datetime(df['time_key'])
            df = df.sort_values('date')
            return self._calculate_indicators(df)
        except:
            return None
    
    def _get_chart_from_yfinance(self, code, days):
        try:
            code_clean = re.sub(r'[^0-9]', '', str(code))
            yf_code = f"{code_clean.zfill(4)}.HK"
            ticker = yf.Ticker(yf_code)
            hist = ticker.history(period=f"{days+30}d")
            if hist.empty:
                return None
            df = hist.reset_index()
            df = df.rename(columns={'Date': 'date', 'Open': 'open', 'High': 'high', 'Low': 'low', 'Close': 'close', 'Volume': 'volume'})
            df['date'] = pd.to_datetime(df['date'])
            df = df.sort_values('date')
            return self._calculate_indicators(df)
        except:
            return None
    
    def _calculate_indicators(self, df):
        if df is None or df.empty:
            return None
        df['MA5'] = df['close'].rolling(5).mean()
        df['MA10'] = df['close'].rolling(10).mean()
        df['MA20'] = df['close'].rolling(20).mean()
        df['MA30'] = df['close'].rolling(30).mean()
        df['MA50'] = df['close'].rolling(50).mean()
        df['MA60'] = df['close'].rolling(60).mean()
        df['MA120'] = df['close'].rolling(120).mean()
        df['MA250'] = df['close'].rolling(250).mean()
        df['BOLL_MID'] = df['close'].rolling(20).mean()
        df['BOLL_STD'] = df['close'].rolling(20).std()
        df['BOLL_UPPER'] = df['BOLL_MID'] + 2 * df['BOLL_STD']
        df['BOLL_LOWER'] = df['BOLL_MID'] - 2 * df['BOLL_STD']
        exp1 = df['close'].ewm(span=12, adjust=False).mean()
        exp2 = df['close'].ewm(span=26, adjust=False).mean()
        df['MACD_DIF'] = exp1 - exp2
        df['MACD_DEA'] = df['MACD_DIF'].ewm(span=9, adjust=False).mean()
        df['MACD_HIST'] = df['MACD_DIF'] - df['MACD_DEA']
        low_min = df['low'].rolling(9).min()
        high_max = df['high'].rolling(9).max()
        df['RSV'] = (df['close'] - low_min) / (high_max - low_min) * 100
        df['KDJ_K'] = df['RSV'].ewm(com=2, adjust=False).mean()
        df['KDJ_D'] = df['KDJ_K'].ewm(com=2, adjust=False).mean()
        df['KDJ_J'] = 3 * df['KDJ_K'] - 2 * df['KDJ_D']
        delta = df['close'].diff()
        gain = delta.where(delta > 0, 0)
        loss = -delta.where(delta < 0, 0)
        df['RSI14'] = 100 - (100 / (1 + gain.rolling(14).mean() / loss.rolling(14).mean()))
        return df
    
    def get_current_source(self):
        return self.current_source
    
    def get_source_status(self):
        return self.source_status

data_source_manager = DataSourceManager()

# ==================== 多新聞 API 管理器 ====================
class NewsAPIManager:
    def __init__(self):
        self.api_keys = {
            'gnews': '',  # 請填入你的 GNews API Key
            'newsapi': '',
            'mediastack': '',
            'guardian': '',
        }
        self.api_status = {
            'gnews': {'available': True, 'daily_used': 0, 'last_reset': datetime.now().date()},
            'newsapi': {'available': True, 'daily_used': 0, 'last_reset': datetime.now().date()},
            'mediastack': {'available': True, 'monthly_used': 0, 'last_reset': datetime.now().month},
            'guardian': {'available': True, 'daily_used': 0, 'last_reset': datetime.now().date()},
        }
        self.priority_order = ['gnews', 'newsapi', 'mediastack', 'guardian']
        self.current_source = None
    
    def _reset_counts_if_needed(self):
        today = datetime.now().date()
        for api, status in self.api_status.items():
            if api in ['gnews', 'newsapi', 'guardian']:
                if status.get('last_reset') != today:
                    status['daily_used'] = 0
                    status['last_reset'] = today
            elif api == 'mediastack':
                if status.get('last_reset') != datetime.now().month:
                    status['monthly_used'] = 0
                    status['last_reset'] = datetime.now().month
    
    def _get_gnews(self, keyword, limit=10):
        if not self.api_keys.get('gnews'):
            return None
        import requests
        url = "https://gnews.io/api/v4/search"
        params = {'q': keyword, 'lang': 'zh', 'max': limit, 'apikey': self.api_keys['gnews']}
        try:
            response = requests.get(url, params=params, timeout=10)
            if response.status_code == 200:
                data = response.json()
                articles = data.get('articles', [])
                self.api_status['gnews']['daily_used'] += 1
                return self._format_articles(articles, 'gnews')
            elif response.status_code == 429:
                self.api_status['gnews']['available'] = False
                return None
            else:
                return None
        except:
            self.api_status['gnews']['available'] = False
            return None
    
    def _get_newsapi(self, keyword, limit=10):
        if not self.api_keys.get('newsapi'):
            return None
        import requests
        url = "https://newsapi.org/v2/everything"
        params = {'q': keyword, 'language': 'zh', 'pageSize': limit, 'apiKey': self.api_keys['newsapi']}
        try:
            response = requests.get(url, params=params, timeout=10)
            if response.status_code == 200:
                data = response.json()
                articles = data.get('articles', [])
                self.api_status['newsapi']['daily_used'] += 1
                return self._format_articles(articles, 'newsapi')
            elif response.status_code == 429:
                self.api_status['newsapi']['available'] = False
                return None
            else:
                return None
        except:
            self.api_status['newsapi']['available'] = False
            return None
    
    def _get_mediastack(self, keyword, limit=10):
        if not self.api_keys.get('mediastack'):
            return None
        import requests
        url = "http://api.mediastack.com/v1/news"
        params = {'access_key': self.api_keys['mediastack'], 'keywords': keyword, 'languages': 'zh,en', 'limit': limit, 'sort': 'published_desc'}
        try:
            response = requests.get(url, params=params, timeout=10)
            if response.status_code == 200:
                data = response.json()
                articles = data.get('data', [])
                self.api_status['mediastack']['monthly_used'] += 1
                return self._format_articles(articles, 'mediastack')
            else:
                return None
        except:
            self.api_status['mediastack']['available'] = False
            return None
    
    def _get_guardian(self, keyword, limit=10):
        if not self.api_keys.get('guardian'):
            return None
        import requests
        url = "https://content.guardianapis.com/search"
        params = {'q': keyword, 'api-key': self.api_keys['guardian'], 'page-size': limit, 'show-fields': 'headline,trailText', 'lang': 'zh'}
        try:
            response = requests.get(url, params=params, timeout=10)
            if response.status_code == 200:
                data = response.json()
                articles = data.get('response', {}).get('results', [])
                self.api_status['guardian']['daily_used'] += 1
                return self._format_articles(articles, 'guardian')
            else:
                return None
        except:
            self.api_status['guardian']['available'] = False
            return None
    
    def _format_articles(self, articles, source):
        formatted = []
        for article in articles:
            if source == 'gnews':
                formatted.append({
                    'title': article.get('title', ''),
                    'source': article.get('source', {}).get('name', 'GNews'),
                    'time': article.get('publishedAt', ''),
                    'url': article.get('url', ''),
                    'description': article.get('description', ''),
                    'api_source': 'gnews'
                })
            elif source == 'newsapi':
                formatted.append({
                    'title': article.get('title', ''),
                    'source': article.get('source', {}).get('name', 'NewsAPI'),
                    'time': article.get('publishedAt', ''),
                    'url': article.get('url', ''),
                    'description': article.get('description', ''),
                    'api_source': 'newsapi'
                })
            elif source == 'mediastack':
                formatted.append({
                    'title': article.get('title', ''),
                    'source': article.get('source', 'Mediastack'),
                    'time': article.get('published_at', ''),
                    'url': article.get('url', ''),
                    'description': article.get('description', ''),
                    'api_source': 'mediastack'
                })
            elif source == 'guardian':
                fields = article.get('fields', {})
                formatted.append({
                    'title': fields.get('headline', article.get('webTitle', '')),
                    'source': 'The Guardian',
                    'time': article.get('webPublicationDate', ''),
                    'url': article.get('webUrl', ''),
                    'description': fields.get('trailText', ''),
                    'api_source': 'guardian'
                })
        return formatted
    
    def search_news(self, keyword, limit=10):
        self._reset_counts_if_needed()
        for api_name in self.priority_order:
            if not self.api_status.get(api_name, {}).get('available', False):
                continue
            if api_name in ['gnews', 'newsapi', 'guardian']:
                if self.api_status[api_name]['daily_used'] >= 100:
                    continue
            elif api_name == 'mediastack':
                if self.api_status[api_name]['monthly_used'] >= 500:
                    continue
            method = getattr(self, f'_get_{api_name}', None)
            if method:
                result = method(keyword, limit)
                if result:
                    self.current_source = api_name
                    return result
        self.current_source = 'mock'
        return self._get_mock_news(keyword, limit)
    
    def _get_mock_news(self, keyword, limit=10):
        import random
        random.seed(hash(keyword) % 10000)
        sentiments = ['positive', 'neutral', 'negative']
        weights = [0.4, 0.4, 0.2]
        news_list = []
        for i in range(min(limit, 10)):
            sentiment = random.choices(sentiments, weights=weights)[0]
            news_list.append({
                'title': f"{keyword} 相關新聞 {i+1}（模擬數據）",
                'source': ['香港經濟日報', '信報', '明報', '東方日報'][random.randint(0, 3)],
                'time': (datetime.now() - timedelta(hours=random.randint(1, 72))).strftime('%Y-%m-%d %H:%M'),
                'sentiment': sentiment,
                'url': '#',
                'description': '這是模擬新聞數據。請在設定中填入真實的 API Key 以獲取真實新聞。',
                'api_source': 'mock'
            })
        return news_list
    
    def get_current_source(self):
        return self.current_source or 'unknown'

news_api_manager = NewsAPIManager()

# ==================== 技術數據獲取函數 ====================
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
        high_price = highs[-1]
        low_price = lows[-1]
        
        ma5 = np.mean(closes[-5:]) if len(closes) >= 5 else price
        ma10 = np.mean(closes[-10:]) if len(closes) >= 10 else price
        ma20 = np.mean(closes[-20:]) if len(closes) >= 20 else price
        ma50 = np.mean(closes[-50:]) if len(closes) >= 50 else price
        
        if len(closes) >= 10:
            ma5_5days_ago = np.mean(closes[-10:-5]) if len(closes) >= 10 else ma5
            ma10_5days_ago = np.mean(closes[-15:-10]) if len(closes) >= 15 else ma10
            ma5_slope = (ma5 - ma5_5days_ago) / ma5_5days_ago * 100 if ma5_5days_ago > 0 else 0
            ma10_slope = (ma10 - ma10_5days_ago) / ma10_5days_ago * 100 if ma10_5days_ago > 0 else 0
        else:
            ma5_slope = 0
            ma10_slope = 0
        
        both_ma_up = (ma5_slope > 0.5) and (ma10_slope > 0.5)
        is_red_candle = price > open_price
        
        if len(turnovers) >= 6:
            avg_volume_5d = np.mean(turnovers[-6:-1])
            volume_ratio = turnovers[-1] / avg_volume_5d if avg_volume_5d > 0 else 1
        else:
            volume_ratio = 1
        is_volume_surge = volume_ratio > 1.5
        
        recent_high = np.max(highs[-20:]) if len(highs) >= 20 else high_price
        is_breakout = price > recent_high and is_red_candle and is_volume_surge
        
        pullback_to_ma10 = abs(price - ma10) / ma10 * 100 < 3 if ma10 > 0 else False
        pullback_to_ma20 = abs(price - ma20) / ma20 * 100 < 3 if ma20 > 0 else False
        is_pullback = pullback_to_ma10 or pullback_to_ma20
        
        is_stop_red = False
        if len(closes) >= 2:
            prev_close = closes[-2]
            prev_open = opens[-2]
            prev_is_down = prev_close < prev_open
            if prev_is_down and is_red_candle:
                is_stop_red = True
        
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
        
        prev = turnovers[-6:-1] if len(turnovers) >= 6 else turnovers
        avg_prev = np.mean(prev) if len(prev) > 0 else current_turnover
        surge_ratio = current_turnover / avg_prev if avg_prev > 0 else 1
        volume_surge = surge_ratio >= SCREENING_CONFIG['volume_surge_ratio']
        
        if len(closes) >= 9:
            low_9 = np.min(lows[-9:])
            high_9 = np.max(highs[-9:])
            rsv = (price - low_9) / (high_9 - low_9) * 100 if high_9 > low_9 else 50
            k = 2/3 * 50 + 1/3 * rsv
            is_kdj_oversold = k < 20
            is_bottom_buy = is_kdj_oversold and is_red_candle and price > ma5
        else:
            is_bottom_buy = False
        
        return {
            'code': code, 'price': price, 'ma5': ma5, 'ma10': ma10, 'ma20': ma20, 'ma50': ma50,
            'both_ma_up': both_ma_up, 'is_red_candle': is_red_candle, 'is_volume_surge': is_volume_surge,
            'volume_ratio': volume_ratio, 'is_breakout': is_breakout, 'is_pullback': is_pullback,
            'is_stop_red': is_stop_red, 'is_bottom_buy': is_bottom_buy, 'rsi14': rsi14,
            'bias20': bias20, 'turnover': current_turnover, 'volume_surge': volume_surge,
            'surge_ratio': surge_ratio, 'success': True
        }
    except Exception as e:
        return None
    # ==================== 輔助函數 ====================
def get_stock_sector(name):
    name_lower = name.lower() if name else ""
    for sector, keywords in SECTOR_KEYWORDS.items():
        for kw in keywords:
            if kw.lower() in name_lower:
                return sector
    return "其他"

def get_north_flow_data(code):
    import random
    random.seed(hash(code) % 10000)
    days = random.randint(0, 7)
    return days >= SCREENING_CONFIG['north_flow_days'], days

def normalize_code(code):
    if code is None:
        return ""
    code_raw = re.sub(r'[^0-9]', '', str(code).strip())
    if code_raw:
        return code_raw.zfill(5)
    return str(code).strip()

def parse_number(value):
    return float(value) if value and value != "" else 0.0

def get_macd_status(dif, dea):
    return ("金叉", "golden") if dif > dea else ("死叉", "death") if dif < dea else ("持平", "neutral")

def check_volume_price(price_change_pct, volume_ratio):
    if price_change_pct > 0:
        if volume_ratio > 1.5:
            return "✅ 價漲量增（健康上漲，動能充足）", "bullish"
        elif volume_ratio > 1.0:
            return "🟡 價漲量平（上漲動能一般）", "neutral"
        else:
            return "⚠️ 價漲量縮（上漲乏力，可能反轉）", "bearish"
    elif price_change_pct < 0:
        if volume_ratio > 1.5:
            return "❌ 價跌量增（下跌動能強，風險較大）", "bearish"
        elif volume_ratio > 1.0:
            return "🟡 價跌量平（下跌動能一般）", "neutral"
        else:
            return "✅ 價跌量縮（下跌動能減弱，可能止跌）", "bullish"
    else:
        return "⚪ 價格持平，量能參考意義有限", "neutral"

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

def auto_fetch_and_fill(code):
    success, name, price, volume, turnover = data_source_manager.get_hk_stock_data(code)
    if success:
        return success, name, price, volume, turnover
    return False, None, None, None, None

def perform_search(code):
    if not code:
        return
    norm = normalize_code(code)
    st.session_state.current_stock = norm
    if norm not in [h['code'] for h in st.session_state.search_history]:
        st.session_state.search_history.append({'code': norm, 'name': code, 'time': datetime.now().strftime('%H:%M:%S')})
    success, name, price, volume, turnover = auto_fetch_and_fill(code)
    if success:
        st.session_state.hk_stock_name = name
        st.session_state.hk_stock_price = price
        st.session_state.hk_stock_volume = int(volume * 10000)
        st.session_state.hk_stock_turnover = turnover
        st.session_state.fetch_trigger = not st.session_state.fetch_trigger
        st.success(f"✅ 已抓取 {norm} ({name}) 股價: ${price}")
        st.info(f"📡 數據來源: {data_source_manager.get_current_source()}")
    else:
        st.warning(f"無法獲取 {norm} 數據，請手動輸入")
    st.session_state.chart_data = data_source_manager.get_hk_chart_data(norm)
    st.rerun()

def export_to_excel_hk():
    data = {
        '股票代碼': st.session_state.get('current_stock', ''),
        '股票名稱': st.session_state.get('hk_stock_name', ''),
        '股價': st.session_state.get('hk_stock_price', 0),
        '成交量(萬股)': st.session_state.get('hk_stock_volume', 0) / 10000,
        '成交額(億)': st.session_state.get('hk_stock_turnover', 0),
        'MA10': st.session_state.get('ma10', ''),
        'MA20': st.session_state.get('ma20', ''),
        'MA50': st.session_state.get('ma50', ''),
        'MA60': st.session_state.get('ma60', ''),
        'MA250': st.session_state.get('ma250', ''),
        'BOLL中軌': st.session_state.get('boll_mid', ''),
        'BOLL上軌': st.session_state.get('boll_upper', ''),
        'BOLL下軌': st.session_state.get('boll_lower', ''),
        'RSI6': st.session_state.get('rsi6', ''),
        'RSI14': st.session_state.get('rsi14', ''),
        'RSI24': st.session_state.get('rsi24', ''),
        'MACD DIF': st.session_state.get('macd_dif', ''),
        'MACD DEA': st.session_state.get('macd_dea', ''),
        'MACD柱': st.session_state.get('macd_hist', ''),
        'KDJ_K': st.session_state.get('kdj_k', ''),
        'KDJ_D': st.session_state.get('kdj_d', ''),
        'KDJ_J': st.session_state.get('kdj_j', ''),
        '做空成交量(萬股)': st.session_state.get('short_volume', 0) / 10000,
        '做空成交額(億)': st.session_state.get('short_turnover', 0),
    }
    df = pd.DataFrame([data])
    filename = f"港股分析_{st.session_state.get('current_stock', '')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    filepath = os.path.join(EXPORT_FOLDER, filename)
    df.to_excel(filepath, index=False)
    return filepath

def set_page(p):
    st.session_state.page = p
    st.rerun()

# ==================== 市場寬度計算 ====================
def calculate_market_breadth():
    try:
        if not AKSHARE_AVAILABLE:
            return None
        stocks = ak.stock_hk_spot()
        if stocks is None or stocks.empty:
            return None
        stocks['成交额'] = pd.to_numeric(stocks['成交额'], errors='coerce')
        stocks = stocks[stocks['成交额'] > 10000000]
        if stocks.empty:
            return None
        
        above_ma20_count = 0
        above_ma50_count = 0
        total = 0
        sample_stocks = stocks.head(300)
        
        for _, row in sample_stocks.iterrows():
            code = row['代码']
            tech = get_tech_data(code)
            if tech and tech.get('success'):
                total += 1
                if tech['price'] > tech['ma20']:
                    above_ma20_count += 1
                if tech['price'] > tech['ma50']:
                    above_ma50_count += 1
        
        if total == 0:
            return None
        
        ma20_breadth = (above_ma20_count / total) * 100
        ma50_breadth = (above_ma50_count / total) * 100
        
        if ma20_breadth >= 70:
            status = "🔴 強勢市場"
            suggestion = "可積極選股，倉位可達 70-100%"
            level = "strong"
        elif ma20_breadth >= 50:
            status = "🟡 正常市場"
            suggestion = "選擇性選股，倉位 40-60%"
            level = "normal"
        elif ma20_breadth >= 30:
            status = "🟠 弱勢市場"
            suggestion = "只選最強勢股，倉位 20-40%"
            level = "weak"
        else:
            status = "⚫ 熊市"
            suggestion = "暫停選股，或極輕倉 (0-20%)"
            level = "bear"
        
        return {
            'ma20_breadth': round(ma20_breadth, 1),
            'ma50_breadth': round(ma50_breadth, 1),
            'status': status,
            'suggestion': suggestion,
            'level': level,
            'total_analyzed': total
        }
    except Exception as e:
        print(f"市場寬度計算失敗: {e}")
        return None

# ==================== 每日選股函數 ====================
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
    stocks = stocks[(stocks['成交额'] > 30000000) & (stocks['最新价'] > 1)]
    
    # 雲端版：限制分析數量，避免記憶體不足
    MAX_ANALYSIS = 10
    if len(stocks) > MAX_ANALYSIS:
        stocks = stocks.head(MAX_ANALYSIS)
        status_text.text(f"⚠️ 限制分析 {MAX_ANALYSIS} 隻股票")
    
    if stocks.empty:
        status_text.text("沒有符合基本條件的股票")
        return pd.DataFrame()
    
    progress_bar.progress(0.1)
    status_text.text(f"分析 {len(stocks)} 隻股票...")
    
    results = []
    total = len(stocks)
    
    for i, (_, row) in enumerate(stocks.iterrows()):
        code = row['代码']
        name = row.get('中文名称', code)
        
        pct = 0.1 + 0.8 * (i / total) if total > 0 else 0.9
        progress_bar.progress(min(pct, 0.99))
        status_text.text(f"[{i+1}/{total}] {code} {name[:12]}")
        
        tech = get_tech_data(code)
        if not tech:
            continue
        
        cond1 = tech['price'] > tech['ma20']
        cond2 = tech['rsi14'] > SCREENING_CONFIG['rsi_threshold']
        cond3 = tech['turnover'] > SCREENING_CONFIG['turnover_threshold']
        cond4 = SCREENING_CONFIG['bias_lower'] <= tech['bias20'] <= SCREENING_CONFIG['bias_upper']
        tech_score = sum([cond1, cond2, cond3, cond4])
        
        cond5 = tech['price'] > tech['ma5']
        cond6 = tech.get('both_ma_up', False)
        cond7 = tech.get('is_red_candle', False)
        cond8 = tech.get('is_breakout', False)
        cond9 = tech.get('is_pullback', False) and tech.get('is_stop_red', False)
        cond10 = tech.get('is_bottom_buy', False)
        
        new_score = 0
        if cond5: new_score += 2
        if cond6: new_score += 2
        if cond7: new_score += 1
        if cond8: new_score += 3
        if cond9: new_score += 3
        if cond10: new_score += 3
        
        if tech_score < 2 and new_score < 3:
            continue
        
        sector = get_stock_sector(name)
        is_hot = sector in ['AI/科技', '半導體', '新能源/電動車']
        north_flow, north_days = get_north_flow_data(code)
        
        extra = 0
        if tech.get('volume_surge', False): extra += 2
        if north_flow: extra += 3
        if is_hot: extra += 2
        
        total_score = tech_score * 5 + new_score + extra + max(0, tech['rsi14'] - 50) * 0.5 + min(tech['turnover'], 10) * 2
        
        results.append({
            '代碼': code,
            '名稱': name[:20],
            '股價': round(tech['price'], 2),
            '成交額': round(tech['turnover'], 2),
            '乖離%': round(tech['bias20'], 1),
            'RSI': round(tech['rsi14'], 1),
            'MA5站穩': '✅' if cond5 else '❌',
            '均線向上': '✅' if cond6 else '❌',
            '收紅K': '✅' if cond7 else '❌',
            '突破買': '🔥' if cond8 else '-',
            '拉回買': '📉' if cond9 else '-',
            '底部買': '🌱' if cond10 else '-',
            '板塊': sector,
            '熱門': '🔥' if is_hot else '',
            '總分': round(total_score, 2)
        })
    
    results.sort(key=lambda x: x['總分'], reverse=True)
    progress_bar.progress(1.0)
    status_text.text(f"完成! 找到 {len(results)} 隻")
    
    return pd.DataFrame(results[:200])
    
# ==================== 載入/儲存函數 ====================
def load_watchlist():
    if os.path.exists(WATCHLIST_FILE):
        with open(WATCHLIST_FILE, 'r') as f:
            return json.load(f)
    return []

def save_watchlist(wl):
    with open(WATCHLIST_FILE, 'w') as f:
        json.dump(wl, f, indent=2)

def load_watchlist_data():
    if os.path.exists(WATCHLIST_DATA_FILE):
        with open(WATCHLIST_DATA_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def save_watchlist_data(data):
    with open(WATCHLIST_DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

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

def load_portfolio_positions():
    if os.path.exists(PORTFOLIO_FILE):
        with open(PORTFOLIO_FILE, 'r') as f:
            return json.load(f)
    return []

def calculate_portfolio_summary(positions):
    summary = {}
    for pos in positions:
        code = pos['code']
        if code not in summary:
            summary[code] = {'total_shares': 0, 'total_cost': 0}
        summary[code]['total_shares'] += pos['shares'] if pos['type'] == '買入' else -pos['shares']
        summary[code]['total_cost'] += pos['price'] * pos['shares'] if pos['type'] == '買入' else -pos['price'] * pos['shares']
    for code, data in summary.items():
        if data['total_shares'] > 0:
            data['avg_cost'] = data['total_cost'] / data['total_shares']
        else:
            data['avg_cost'] = 0
        success, _, price, _, _ = data_source_manager.get_hk_stock_data(code)
        data['current_price'] = price if success else 0
        data['current_value'] = data['total_shares'] * data['current_price']
        data['profit_loss'] = data['current_value'] - data['total_cost']
        data['profit_loss_pct'] = (data['profit_loss'] / data['total_cost'] * 100) if data['total_cost'] > 0 else 0
    return summary

def load_trade_records():
    if os.path.exists(TRADE_RECORDS_FILE):
        with open(TRADE_RECORDS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return []

def save_trade_records(records):
    with open(TRADE_RECORDS_FILE, 'w', encoding='utf-8') as f:
        json.dump(records, f, ensure_ascii=False, indent=2)

# ==================== 股價提醒功能 ====================
def load_alerts():
    if os.path.exists(PRICE_ALERT_FILE):
        with open(PRICE_ALERT_FILE, 'r') as f:
            return json.load(f)
    return []

def save_alerts(alerts):
    with open(PRICE_ALERT_FILE, 'w') as f:
        json.dump(alerts, f, indent=2)

def check_price_alerts():
    alerts = load_alerts()
    triggered = []
    new_alerts = []
    for alert in alerts:
        if alert.get('triggered', False):
            new_alerts.append(alert)
            continue
        success, _, price, _, _ = data_source_manager.get_hk_stock_data(alert['code'])
        if success and price > 0:
            if alert['type'] == 'above' and price >= alert['target_price']:
                alert['triggered'] = True
                alert['trigger_time'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                alert['current_price'] = price
                triggered.append(alert)
            elif alert['type'] == 'below' and price <= alert['target_price']:
                alert['triggered'] = True
                alert['trigger_time'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                alert['current_price'] = price
                triggered.append(alert)
        new_alerts.append(alert)
    save_alerts(new_alerts)
    return triggered

def add_alert(code, name, alert_type, target_price):
    alerts = load_alerts()
    alerts.append({'code': code, 'name': name, 'type': alert_type, 'target_price': target_price, 'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'), 'triggered': False})
    save_alerts(alerts)

def remove_alert(index):
    alerts = load_alerts()
    if 0 <= index < len(alerts):
        alerts.pop(index)
        save_alerts(alerts)

# ==================== 歷史回測功能 ====================
def run_backtest(code, buy_conditions, start_date, end_date, initial_capital=100000):
    try:
        df = data_source_manager.get_hk_chart_data(code, days=(datetime.strptime(end_date, '%Y-%m-%d') - datetime.strptime(start_date, '%Y-%m-%d')).days + 50)
        if df is None:
            return None, None, None
        df = df[(df['date'] >= start_date) & (df['date'] <= end_date)]
        if df.empty:
            return None, None, None
        cash = initial_capital
        position = 0
        trades = []
        for i in range(20, len(df)):
            row = df.iloc[i]
            price = row['close']
            ma20 = row['MA20']
            rsi14 = row['RSI14']
            macd_dif = row['MACD_DIF']
            macd_dea = row['MACD_DEA']
            turnover = row['volume'] * price / 100000000
            cond1 = price > ma20
            cond2 = rsi14 > buy_conditions.get('rsi_threshold', 50)
            cond3 = macd_dif > macd_dea
            cond4 = turnover > buy_conditions.get('turnover_threshold', 0.3)
            bias20 = (price - ma20) / ma20 * 100
            cond5 = buy_conditions.get('bias_lower', -4) <= bias20 <= buy_conditions.get('bias_upper', 5)
            buy_signal = cond1 and cond2 and cond3 and cond4 and cond5
            sell_signal = price < ma20 and position > 0
            if buy_signal and cash > 0:
                shares = int(cash / price)
                if shares > 0:
                    cash -= shares * price
                    position += shares
                    trades.append({'date': row['date'], 'type': '買入', 'price': price, 'shares': shares})
            elif sell_signal and position > 0:
                cash += position * price
                trades.append({'date': row['date'], 'type': '賣出', 'price': price, 'shares': position})
                position = 0
        if position > 0:
            cash += position * df.iloc[-1]['close']
        total_return = cash - initial_capital
        total_return_pct = (total_return / initial_capital) * 100
        return {'trades': trades, 'total_return': total_return, 'total_return_pct': total_return_pct, 'final_capital': cash, 'num_trades': len(trades)}, df, None
    except:
        return None, None, None

# ==================== 板塊資金流向 ====================
def get_sector_flow():
    try:
        if not AKSHARE_AVAILABLE:
            return None
        stocks = ak.stock_hk_spot()
        stocks['成交额'] = pd.to_numeric(stocks['成交额'], errors='coerce')
        stocks['漲跌幅'] = pd.to_numeric(stocks['涨跌幅'], errors='coerce')
        from collections import defaultdict
        sector_flow = defaultdict(lambda: {'turnover': 0, 'change_sum': 0, 'count': 0, 'stocks': []})
        for _, row in stocks.iterrows():
            name = row.get('中文名称', '')
            if not name:
                continue
            turnover = row['成交额'] / 100000000 if pd.notna(row['成交额']) else 0
            change_pct = row['漲跌幅'] if pd.notna(row['漲跌幅']) else 0
            sector = get_stock_sector(name)
            sector_flow[sector]['turnover'] += turnover
            sector_flow[sector]['change_sum'] += change_pct
            sector_flow[sector]['count'] += 1
            if len(sector_flow[sector]['stocks']) < 5:
                sector_flow[sector]['stocks'].append({'code': row['代码'], 'name': name[:10], 'change': change_pct})
        for sector in sector_flow:
            if sector_flow[sector]['count'] > 0:
                sector_flow[sector]['avg_change'] = sector_flow[sector]['change_sum'] / sector_flow[sector]['count']
        return dict(sector_flow)
    except:
        return None

# ==================== 新聞情緒分析 ====================
def get_news_sentiment(keyword, limit=10):
    articles = news_api_manager.search_news(keyword, limit)
    if not articles:
        return None
    positive_words = ['升', '漲', '好', '增', '突破', '新高', '利好', '正面', '樂觀', '增長']
    negative_words = ['跌', '降', '差', '減', '跌破', '新低', '利空', '負面', '悲觀', '下滑']
    positive_count = negative_count = neutral_count = 0
    for article in articles:
        text = f"{article.get('title', '')} {article.get('description', '')}".lower()
        pos = sum(1 for w in positive_words if w in text)
        neg = sum(1 for w in negative_words if w in text)
        if pos > neg:
            article['sentiment'] = 'positive'
            positive_count += 1
        elif neg > pos:
            article['sentiment'] = 'negative'
            negative_count += 1
        else:
            article['sentiment'] = 'neutral'
            neutral_count += 1
    total = len(articles)
    sentiment_score = (positive_count - negative_count) / total if total > 0 else 0
    return {
        'news': articles,
        'sentiment_score': sentiment_score,
        'sentiment_label': '正面' if sentiment_score > 0.2 else '負面' if sentiment_score < -0.2 else '中性',
        'positive_count': positive_count,
        'neutral_count': neutral_count,
        'negative_count': negative_count,
        'api_source': news_api_manager.get_current_source()
    }

# ==================== 手續費計算函數 ====================
def calculate_hk_fees_auto(buy_price, sell_price, shares):
    buy_amount = buy_price * shares
    sell_amount = sell_price * shares
    buy_commission = max(3, buy_amount * 0.0003)
    sell_commission = max(3, sell_amount * 0.0003)
    buy_platform = 15.0
    sell_platform = 15.0
    stamp_duty = sell_amount * 0.0013
    buy_trading_fee = buy_amount * 0.000027
    sell_trading_fee = sell_amount * 0.000027
    buy_transaction_fee = buy_amount * 0.0000565
    sell_transaction_fee = sell_amount * 0.0000565
    buy_settlement = max(2, min(100, buy_amount * 0.00002))
    sell_settlement = max(2, min(100, sell_amount * 0.00002))
    total_fees = (buy_commission + sell_commission + buy_platform + sell_platform + 
                  stamp_duty + buy_trading_fee + sell_trading_fee + 
                  buy_transaction_fee + sell_transaction_fee + 
                  buy_settlement + sell_settlement)
    gross_profit = sell_amount - buy_amount
    net_profit = gross_profit - total_fees
    return {
        'buy_amount': round(buy_amount, 2), 'sell_amount': round(sell_amount, 2),
        'gross_profit': round(gross_profit, 2), 'total_fees': round(total_fees, 2),
        'net_profit': round(net_profit, 2), 'currency': 'HKD', 'currency_symbol': 'HK$',
        'fee_breakdown': {
            '買入佣金': round(buy_commission, 2), '賣出佣金': round(sell_commission, 2),
            '買入平台費': buy_platform, '賣出平台費': sell_platform,
            '印花稅': round(stamp_duty, 2), '交易徵費': round(buy_trading_fee + sell_trading_fee, 2),
            '交易費': round(buy_transaction_fee + sell_transaction_fee, 2),
            '結算費': round(buy_settlement + sell_settlement, 2)
        }
    }

def calculate_us_fees_auto(buy_price, sell_price, shares, show_hkd=True, exchange_rate=7.8):
    buy_amount = buy_price * shares
    sell_amount = sell_price * shares
    buy_commission = max(0.99, shares * 0.0049)
    sell_commission = max(0.99, shares * 0.0049)
    buy_platform = max(1.0, shares * 0.005)
    sell_platform = max(1.0, shares * 0.005)
    buy_settlement = shares * 0.003
    sell_settlement = shares * 0.003
    sec_fee = sell_amount * 0.0000278
    taf = max(0.01, shares * 0.000166)
    total_fees_usd = (buy_commission + sell_commission + buy_platform + sell_platform + 
                      buy_settlement + sell_settlement + sec_fee + taf)
    gross_profit_usd = sell_amount - buy_amount
    net_profit_usd = gross_profit_usd - total_fees_usd
    result = {
        'buy_amount_usd': round(buy_amount, 2), 'sell_amount_usd': round(sell_amount, 2),
        'gross_profit_usd': round(gross_profit_usd, 2), 'total_fees_usd': round(total_fees_usd, 2),
        'net_profit_usd': round(net_profit_usd, 2), 'currency': 'USD', 'currency_symbol': '$',
        'fee_breakdown_usd': {
            '買入佣金': round(buy_commission, 2), '賣出佣金': round(sell_commission, 2),
            '買入平台費': round(buy_platform, 2), '賣出平台費': round(sell_platform, 2),
            '買入交收費': round(buy_settlement, 2), '賣出交收費': round(sell_settlement, 2),
            'SEC規費': round(sec_fee, 4), 'TAF': round(taf, 2)
        }
    }
    if show_hkd:
        result['net_profit_hkd'] = round(net_profit_usd * exchange_rate, 2)
    return result

# ==================== 12項檢查清單 ====================
checklist_items = [
    {"id": 1, "name": "股價位置", "standard": "股價 > 20天線"},
    {"id": 2, "name": "均線排列", "standard": "10天線 > 20天線（多頭排列）"},
    {"id": 3, "name": "RSI(14)", "standard": "RSI > 50（強勢區）"},
    {"id": 4, "name": "MACD金叉", "standard": "DIF > DEA 且 MACD柱 > 0"},
    {"id": 5, "name": "MACD強度", "standard": "MACD柱 > 0.1"},
    {"id": 6, "name": "成交額", "standard": "> 3000萬港元"},
    {"id": 7, "name": "BIAS1(10日)", "standard": "-5% ~ +8%"},
    {"id": 8, "name": "BIAS2(20日)", "standard": "-4% ~ +5%"},
    {"id": 9, "name": "BIAS3(60日)", "standard": "-3% ~ +3%"},
    {"id": 10, "name": "KDJ J值", "standard": "J < 80"},
    {"id": 11, "name": "股價與52週高位", "standard": "不是處於歷史最高位"},
    {"id": 12, "name": "成交量配合", "standard": "價升量增，價跌量縮"}
]

def load_checklist_status():
    if os.path.exists(CHECKLIST_FILE):
        with open(CHECKLIST_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def save_checklist_status(status):
    with open(CHECKLIST_FILE, 'w', encoding='utf-8') as f:
        json.dump(status, f, ensure_ascii=False, indent=2)

# ==================== 移動平均線買入賣出信號 ====================
def calculate_ma_signals(price, ma10, ma20, ma50, ma60, ma250):
    above_ma10 = price > ma10 if ma10 > 0 else None
    above_ma20 = price > ma20 if ma20 > 0 else None
    above_ma50 = price > ma50 if ma50 > 0 else None
    above_ma60 = price > ma60 if ma60 > 0 else None
    above_ma250 = price > ma250 if ma250 > 0 else None
    
    above_count = sum([above_ma10 is True, above_ma20 is True, above_ma50 is True, above_ma60 is True, above_ma250 is True])
    
    bullish_arrange = False
    bearish_arrange = False
    if all([ma10 > ma20, ma20 > ma50, ma50 > ma60, ma60 > ma250]) and ma10 > 0:
        bullish_arrange = True
    elif all([ma10 < ma20, ma20 < ma50, ma50 < ma60, ma60 < ma250]) and ma10 > 0:
        bearish_arrange = True
    
    score = above_count
    if bullish_arrange:
        score += 2
    if bearish_arrange:
        score -= 2
    
    max_score = 7
    if score >= 6:
        signal = "🔴 強烈買入（均線多頭排列）"
        signal_type = "strong_buy"
    elif score >= 5:
        signal = "🟢 買入（趨勢向好）"
        signal_type = "buy"
    elif score >= 3:
        signal = "🟡 持有 / 觀望"
        signal_type = "hold"
    elif score >= 2:
        signal = "⚪ 謹慎"
        signal_type = "cautious"
    else:
        signal = "⚫ 賣出 / 迴避"
        signal_type = "sell"
    
    details = {'above_count': above_count, 'total_ma': 5, 'bullish_arrange': bullish_arrange, 'bearish_arrange': bearish_arrange, 'score': score, 'max_score': max_score}
    return signal, signal_type, details

def generate_signals(price, ma20, rsi6, rsi14, rsi24, macd_dif, macd_dea, turnover, bias20, kdj_k, kdj_d, short_volume, short_turnover, boll_upper=None, boll_lower=None, volume_ratio=None, price_change_pct=None, ma10=None, ma50=None, ma60=None, ma250=None):
    cond1 = price > ma20 if ma20 > 0 else False
    cond2 = (rsi6 > 50) and (rsi14 > 50) and (rsi24 > 50)
    cond3 = macd_dif > macd_dea
    cond4 = turnover > 0.3
    cond5 = -4 <= bias20 <= 5
    
    boll_status = ""
    if boll_upper and boll_lower and boll_upper > 0 and boll_lower > 0:
        if price > boll_upper:
            boll_status = "overbought"
        elif price < boll_lower:
            boll_status = "oversold"
    
    total_score = sum([cond1, cond2, cond3, cond4, cond5])
    if boll_status == "oversold":
        total_score += 1
    elif boll_status == "overbought":
        total_score -= 1
    
    if total_score >= 5:
        final_signal = "🔴 強烈買入"
    elif total_score >= 4:
        final_signal = "🟢 買入"
    elif total_score >= 3:
        final_signal = "🟡 持有 / 觀望"
    elif total_score >= 2:
        final_signal = "⚪ 謹慎"
    else:
        final_signal = "⚫ 賣出 / 迴避"
    
    return final_signal, "normal", {'score': total_score, 'max_score': 7}
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
if 'ma10' not in st.session_state:
    st.session_state.ma10 = ""
if 'ma20' not in st.session_state:
    st.session_state.ma20 = ""
if 'ma50' not in st.session_state:
    st.session_state.ma50 = ""
if 'ma60' not in st.session_state:
    st.session_state.ma60 = ""
if 'ma250' not in st.session_state:
    st.session_state.ma250 = ""
if 'boll_mid' not in st.session_state:
    st.session_state.boll_mid = ""
if 'boll_upper' not in st.session_state:
    st.session_state.boll_upper = ""
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
    st.markdown("**📡 數據源狀態**")
    status = data_source_manager.get_source_status()
    for src, info in status.items():
        icon = "🟢" if info["available"] else "🔴"
        st.caption(f"{icon} {src}: {'可用' if info['available'] else '不可用'}")
    st.caption(f"當前使用: **{data_source_manager.get_current_source()}**")
    st.divider()
    pages = ["📋 每日工作流", "🔍 港股分析", "🇺🇸 美股分析", "⭐ 自選股", "📊 投資組合", "📝 交易日誌", "📊 交易記錄與檢討", "🔔 股價提醒", "📈 歷史回測", "💰 板塊資金流向", "📰 新聞情緒", "📜 搜索歷史", "📎 數據匯入", "📊 圖表分析", "🎯 每日選股", "🧮 交易計算器", "⚙️ 設定"]
    for p in pages:
        if st.button(p, use_container_width=True):
            set_page(p)

# ==================== 頁面內容 ====================

# 0. 每日工作流儀表板（主頁面）
if st.session_state.page == "📋 每日工作流":
    st.markdown("""
    <div style="text-align:center; padding:1rem; background:linear-gradient(135deg,#667eea,#764ba2); border-radius:10px; margin-bottom:2rem">
        <h1 style="color:white">📋 每日工作流</h1>
        <p style="color:rgba(255,255,255,0.8)">市場走勢 → 選股 → 分析 → 計算 → 記錄</p>
    </div>
    """, unsafe_allow_html=True)
    
    # ========== 步驟 1：市場走勢 ==========
    with st.expander("📊 步驟 1：市場走勢（每日必看）", expanded=True):
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.subheader("🇭🇰 大盤趨勢")
            hsi_trend, hsi_change, hsi_bullish = get_hsi_trend()
            if hsi_bullish is True:
                st.success(f"✅ 多頭趨勢")
                st.metric("恆指變動", f"{hsi_change:+.2f}%")
            elif hsi_bullish is False:
                st.error(f"⚠️ 空頭趨勢")
                st.metric("恆指變動", f"{hsi_change:+.2f}%")
            else:
                st.warning(f"🟡 盤整震盪")
                st.metric("恆指變動", f"{hsi_change:+.2f}%")
        
        with col2:
            st.subheader("📈 市場寬度")
            breadth = calculate_market_breadth()
            if breadth:
                st.metric("MA20 寬度", f"{breadth['ma20_breadth']}%", 
                         delta="強勢" if breadth['ma20_breadth'] >= 70 else "正常" if breadth['ma20_breadth'] >= 50 else "弱勢")
                if breadth['level'] == 'strong':
                    st.success(f"💡 {breadth['suggestion'][:30]}")
                elif breadth['level'] == 'normal':
                    st.info(f"💡 {breadth['suggestion'][:30]}")
                elif breadth['level'] == 'weak':
                    st.warning(f"💡 {breadth['suggestion'][:30]}")
                else:
                    st.error(f"💡 {breadth['suggestion'][:30]}")
            else:
                st.info("無法獲取數據")
        
        with col3:
            st.subheader("💰 板塊資金流向")
            sector_flow = get_sector_flow()
            if sector_flow:
                sorted_sectors = sorted(sector_flow.items(), key=lambda x: x[1]['turnover'], reverse=True)[:5]
                for sector, data in sorted_sectors:
                    change_color = "🟢" if data.get('avg_change', 0) > 0 else "🔴" if data.get('avg_change', 0) < 0 else "⚪"
                    st.write(f"{change_color} **{sector}**")
                    st.caption(f"成交額 {data['turnover']:.1f}億 | {data.get('avg_change', 0):+.2f}%")
            else:
                st.info("無法獲取數據")
    
    # ========== 步驟 2：選股 ==========
    with st.expander("🎯 步驟 2：今日可留意股票", expanded=True):
        col1, col2 = st.columns([3, 1])
        with col1:
            st.markdown("**符合技術條件的股票（按總分排序）**")
        with col2:
            if st.button("🔄 開始篩選", type="primary", use_container_width=True):
                with st.spinner("正在篩選股票，請稍候..."):
                    progress_bar = st.progress(0)
                    status_text = st.empty()
                    results_df = run_screening(progress_bar, status_text)
                    if not results_df.empty:
                        st.session_state.daily_screening_df = results_df
                        st.success(f"✅ 找到 {len(results_df)} 隻股票")
                        st.rerun()
                    else:
                        st.warning("沒有符合條件的股票")
                        st.session_state.daily_screening_df = None
        
        if st.session_state.daily_screening_df is not None:
            df = st.session_state.daily_screening_df
            display_cols = ['代碼', '名稱', '股價', '突破買', '拉回買', '底部買', '總分']
            available_cols = [c for c in display_cols if c in df.columns]
            st.dataframe(df[available_cols].head(30), use_container_width=True)
            
            stock_options = df['代碼'].tolist()
            selected_code = st.selectbox("選擇股票進行分析", stock_options, key="daily_stock_select")
            
            if st.button("📊 分析所選股票", use_container_width=True):
                st.session_state.daily_selected_stock = selected_code
                st.rerun()
        else:
            st.info("點擊「開始篩選」獲取今日可留意股票")
    
    # ========== 步驟 3：股票分析 ==========
    with st.expander("📈 步驟 3：股票技術分析", expanded=st.session_state.daily_selected_stock is not None):
        if st.session_state.daily_selected_stock:
            code = st.session_state.daily_selected_stock
            st.subheader(f"📊 分析 {code}")
            
            success, name, price, volume, turnover = auto_fetch_and_fill(code)
            
            if success:
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("股票名稱", name)
                with col2:
                    st.metric("當前股價", f"${price:.2f}")
                with col3:
                    st.metric("成交額", f"{turnover:.2f}億")
                
                if st.button("🔍 進入完整分析頁面", use_container_width=True):
                    perform_search(code)
                    set_page("🔍 港股分析")
                
                st.markdown("---")
                st.markdown("**📊 快速技術判斷**")
                
                tech = get_tech_data(normalize_code(code))
                if tech:
                    col1, col2 = st.columns(2)
                    with col1:
                        st.write(f"MA20: ${tech.get('ma20', 0):.2f}")
                        st.write(f"乖離率: {tech.get('bias20', 0):+.2f}%")
                        st.write(f"RSI14: {tech.get('rsi14', 0):.1f}")
                    with col2:
                        st.write(f"均線向上: {'✅' if tech.get('both_ma_up') else '❌'}")
                        st.write(f"收紅K: {'✅' if tech.get('is_red_candle') else '❌'}")
                        st.write(f"突破買: {'🔥' if tech.get('is_breakout') else '-'}")
            else:
                st.warning("無法獲取股票數據，請檢查股票代碼")
        else:
            st.info("請先在「步驟 2」選擇股票")
    
    # ========== 步驟 4：快速計算 ==========
    with st.expander("🧮 步驟 4：快速利潤計算", expanded=False):
        st.markdown("**富途費用快速計算（港股）**")
        col1, col2, col3 = st.columns(3)
        with col1:
            calc_buy = st.number_input("買入價", value=0.0, step=0.1, format="%.2f", key="calc_buy")
        with col2:
            calc_sell = st.number_input("賣出價", value=0.0, step=0.1, format="%.2f", key="calc_sell")
        with col3:
            calc_shares = st.number_input("股數", value=100, step=100, key="calc_shares")
        
        if calc_buy > 0 and calc_sell > 0 and calc_shares > 0:
            buy_amount = calc_buy * calc_shares
            sell_amount = calc_sell * calc_shares
            commission = max(3, buy_amount * 0.0003) + max(3, sell_amount * 0.0003)
            stamp_duty = sell_amount * 0.0013
            platform_fee = 30
            total_fees = commission + stamp_duty + platform_fee
            profit = sell_amount - buy_amount - total_fees
            
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("買入金額", f"${buy_amount:,.2f}")
            with col2:
                st.metric("賣出金額", f"${sell_amount:,.2f}")
            with col3:
                st.metric("總費用", f"${total_fees:.2f}")
            with col4:
                profit_color = "🟢" if profit > 0 else "🔴"
                st.metric(f"{profit_color} 淨利潤", f"${profit:.2f}")
    
    # ========== 步驟 5：操作記錄 ==========
    with st.expander("📝 步驟 5：今日操作記錄與檢討", expanded=False):
        today = datetime.now().strftime('%Y-%m-%d')
        st.subheader(f"📅 {today} 的操作記錄")
        
        today_journal = load_journal(today)
        if today_journal:
            st.markdown("**已有記錄：**")
            for entry in today_journal:
                st.write(f"• {entry.get('timestamp', '')} - {entry.get('stock', '')} - {entry.get('action', '')} @ ${entry.get('price', 0):.2f}")
            st.divider()
        
        with st.form("daily_journal_form"):
            col1, col2 = st.columns(2)
            with col1:
                trade_stock = st.text_input("股票代碼", placeholder="例如: 00700", key="journal_stock")
                trade_action = st.selectbox("操作", ["買入", "賣出", "觀望", "加倉", "減倉"], key="journal_action")
            with col2:
                trade_price = st.number_input("價格", value=0.0, step=0.1, format="%.2f", key="journal_price")
                trade_shares = st.number_input("股數", value=0, step=100, key="journal_shares")
            
            review = st.text_area("檢討 / 心得", height=80, placeholder="記錄你的操作反思、學到什麼、下次如何改進...", key="journal_review")
            
            col1, col2 = st.columns(2)
            with col1:
                submitted = st.form_submit_button("💾 儲存記錄", use_container_width=True)
            with col2:
                if st.form_submit_button("🗑️ 清空今日記錄", use_container_width=True):
                    all_journals = load_journal()
                    if today in all_journals:
                        del all_journals[today]
                        with open(JOURNAL_FILE, 'w', encoding='utf-8') as f:
                            json.dump(all_journals, f, ensure_ascii=False, indent=2)
                    st.rerun()
            
            if submitted:
                if trade_stock:
                    entry = {
                        'stock': trade_stock,
                        'action': trade_action,
                        'price': trade_price,
                        'shares': trade_shares,
                        'review': review,
                        'timestamp': datetime.now().strftime('%H:%M')
                    }
                    save_journal(today, entry)
                    st.success("✅ 已儲存！")
                    st.rerun()
                else:
                    st.warning("請填寫股票代碼")
    
    st.divider()
    st.caption("💡 提示：完成所有步驟後，明天再回來重新開始新的一天！")

# 1. 港股分析頁面（完整版）
elif st.session_state.page == "🔍 港股分析":
    st.markdown("""
    <div style="text-align:center; padding:1rem; background:linear-gradient(135deg,#667eea,#764ba2); border-radius:10px; margin-bottom:2rem">
        <h1 style="color:white">📈 港股技術分析</h1>
        <p style="color:rgba(255,255,255,0.8)">自動抓取基本數據 | 手動輸入技術指標 | 匯出 Excel 給 AI 分析</p>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2 = st.columns([3, 1])
    with col1:
        code = st.text_input("股票代碼", placeholder="例如：00700、09988、03317", key="stock_code_input")
    with col2:
        if st.button("🔍 載入/新增", type="primary", use_container_width=True):
            if code:
                perform_search(code)
    
    if st.session_state.current_stock:
        st.caption(f"當前股票: {st.session_state.current_stock}")
    st.divider()
    
    st.subheader("📊 基本數據")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        stock_name = st.text_input("股票名稱", value=st.session_state.hk_stock_name, placeholder="例如: 騰訊控股", key=f"stock_name_{st.session_state.fetch_trigger}")
        st.session_state.hk_stock_name = stock_name
    with col2:
        price_value = st.session_state.hk_stock_price if st.session_state.hk_stock_price != 0 else None
        price = st.number_input("股價 (港元)", value=price_value, step=0.1, format="%.3f", placeholder="請輸入股價", key=f"price_{st.session_state.fetch_trigger}")
        if price is not None:
            st.session_state.hk_stock_price = price
    with col3:
        volume_display = st.session_state.hk_stock_volume / 10000 if st.session_state.hk_stock_volume > 0 else None
        volume = st.number_input("成交量 (萬股)", value=volume_display, step=1.0, format="%.0f", placeholder="請輸入成交量", key=f"volume_{st.session_state.fetch_trigger}")
        if volume is not None:
            st.session_state.hk_stock_volume = int(volume * 10000)
    with col4:
        turnover_value = st.session_state.hk_stock_turnover if st.session_state.hk_stock_turnover != 0 else None
        turnover = st.number_input("成交額 (億)", value=turnover_value, step=0.1, format="%.2f", placeholder="請輸入成交額", key=f"turnover_{st.session_state.fetch_trigger}")
        if turnover is not None:
            st.session_state.hk_stock_turnover = turnover
    
    st.subheader("📉 做空數據（選填）")
    col1, col2 = st.columns(2)
    with col1:
        short_volume_val = st.number_input("做空成交量 (萬股)", value=None, step=1.0, format="%.0f", placeholder="選填", key="short_volume_input")
        st.session_state.short_volume = int(short_volume_val * 10000) if short_volume_val else 0
    with col2:
        short_turnover_val = st.number_input("做空成交額 (億)", value=None, step=0.1, format="%.2f", placeholder="選填", key="short_turnover_input")
        st.session_state.short_turnover = short_turnover_val if short_turnover_val else 0.0
    
    st.divider()
    
    st.subheader("📊 技術指標（從手機App輸入）")
    st.caption("💡 直接輸入數字，無需刪除預設值")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("**📈 移動平均線**")
        ma10 = st.text_input("MA10", value=st.session_state.ma10, placeholder="例如: 510.200", key="ma10_input")
        ma20 = st.text_input("MA20", value=st.session_state.ma20, placeholder="例如: 502.700", key="ma20_input")
        ma50 = st.text_input("MA50", value=st.session_state.ma50, placeholder="例如: 495.300", key="ma50_input")
        ma60 = st.text_input("MA60", value=st.session_state.ma60, placeholder="例如: 493.100", key="ma60_input")
        ma250 = st.text_input("MA250", value=st.session_state.ma250, placeholder="例如: 450.200", key="ma250_input")
        
        st.markdown("**📊 布林帶**")
        boll_mid = st.text_input("BOLL中軌", value=st.session_state.boll_mid, placeholder="例如: 502.700", key="boll_mid_input")
        boll_upper = st.text_input("BOLL上軌", value=st.session_state.boll_upper, placeholder="例如: 525.600", key="boll_upper_input")
        boll_lower = st.text_input("BOLL下軌", value=st.session_state.boll_lower, placeholder="例如: 479.800", key="boll_lower_input")
    
    with col2:
        st.markdown("**📊 RSI（三個週期）**")
        rsi6 = st.text_input("RSI(6)", value=st.session_state.rsi6, placeholder="例如: 62.300", key="rsi6_input")
        rsi14 = st.text_input("RSI(14)", value=st.session_state.rsi14, placeholder="例如: 62.300", key="rsi14_input")
        rsi24 = st.text_input("RSI(24)", value=st.session_state.rsi24, placeholder="例如: 62.300", key="rsi24_input")
        
        st.markdown("**📉 MACD**")
        macd_dif = st.text_input("MACD DIF", value=st.session_state.macd_dif, placeholder="例如: 1.234", key="macd_dif_input")
        macd_dea = st.text_input("MACD DEA", value=st.session_state.macd_dea, placeholder="例如: 1.123", key="macd_dea_input")
        macd_hist = st.text_input("MACD 柱", value=st.session_state.macd_hist, placeholder="自動計算", key="macd_hist_input")
    
    with col3:
        st.markdown("**📈 KDJ (9,3,3)**")
        kdj_k = st.text_input("KDJ_K", value=st.session_state.kdj_k, placeholder="例如: 75.200", key="kdj_k_input")
        kdj_d = st.text_input("KDJ_D", value=st.session_state.kdj_d, placeholder="例如: 72.500", key="kdj_d_input")
        kdj_j = st.text_input("KDJ_J", value=st.session_state.kdj_j, placeholder="例如: 80.600", key="kdj_j_input")
    
    st.session_state.ma10 = ma10
    st.session_state.ma20 = ma20
    st.session_state.ma50 = ma50
    st.session_state.ma60 = ma60
    st.session_state.ma250 = ma250
    st.session_state.boll_mid = boll_mid
    st.session_state.boll_upper = boll_upper
    st.session_state.boll_lower = boll_lower
    st.session_state.rsi6 = rsi6
    st.session_state.rsi14 = rsi14
    st.session_state.rsi24 = rsi24
    st.session_state.macd_dif = macd_dif
    st.session_state.macd_dea = macd_dea
    st.session_state.macd_hist = macd_hist
    st.session_state.kdj_k = kdj_k
    st.session_state.kdj_d = kdj_d
    st.session_state.kdj_j = kdj_j
    
    p = st.session_state.hk_stock_price
    ma10_num = parse_number(ma10)
    ma20_num = parse_number(ma20)
    ma50_num = parse_number(ma50)
    ma60_num = parse_number(ma60)
    ma250_num = parse_number(ma250)
    r6 = parse_number(rsi6)
    r14 = parse_number(rsi14)
    r24 = parse_number(rsi24)
    dif = parse_number(macd_dif)
    dea = parse_number(macd_dea)
    to = st.session_state.hk_stock_turnover
    bias20 = (p - ma20_num) / ma20_num * 100 if ma20_num > 0 else 0
    kk = parse_number(kdj_k)
    dd = parse_number(kdj_d)
    sv = st.session_state.short_volume
    sto = st.session_state.short_turnover
    boll_upper_num = parse_number(boll_upper)
    boll_lower_num = parse_number(boll_lower)
    volume_val = st.session_state.hk_stock_volume / 10000
    avg_volume = volume_val * 0.8
    volume_ratio = volume_val / avg_volume if avg_volume > 0 else 1
    price_change_pct = 0
    hsi_trend, hsi_change, hsi_bullish = get_hsi_trend()
    
    st.divider()
    
    st.subheader("📉 MACD 狀態")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("MACD DIF", f"{dif:.4f}" if dif != 0 else "N/A")
    with col2:
        st.metric("MACD DEA", f"{dea:.4f}" if dea != 0 else "N/A")
    with col3:
        st.metric("MACD 柱", f"{dif - dea:.4f}" if dif != 0 or dea != 0 else "N/A")
    
    status, _ = get_macd_status(dif, dea)
    if status == "金叉":
        st.markdown('<div style="background-color:#00aa00; color:white; padding:5px; border-radius:5px">✅ 金叉 (黃金交叉)</div>', unsafe_allow_html=True)
    elif status == "死叉":
        st.markdown('<div style="background-color:#aa0000; color:white; padding:5px; border-radius:5px">❌ 死叉 (死亡交叉)</div>', unsafe_allow_html=True)
    elif dif != 0 or dea != 0:
        st.info(f"📊 {status}")
    
    st.subheader("🎯 交易信號")
    cond1 = p > ma20_num if ma20_num > 0 else False
    cond2 = (r6 > 50) and (r14 > 50) and (r24 > 50)
    cond3 = dif > dea
    cond4 = to > 0.3
    cond5 = -4 <= bias20 <= 5
    
    total_score = sum([cond1, cond2, cond3, cond4, cond5])
    if boll_upper_num > 0 and boll_lower_num > 0:
        if p < boll_lower_num:
            total_score += 1
        elif p > boll_upper_num:
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
    
    st.subheader("📊 大盤趨勢過濾")
    if hsi_trend:
        col1, col2 = st.columns(2)
        with col1:
            if hsi_bullish is True:
                st.markdown('<div style="background-color:#00aa00; color:white; padding:5px; border-radius:5px; text-align:center">✅ 大盤多頭趨勢，適合積極操作</div>', unsafe_allow_html=True)
            elif hsi_bullish is False:
                st.markdown('<div style="background-color:#aa0000; color:white; padding:5px; border-radius:5px; text-align:center">⚠️ 大盤空頭趨勢，建議保守操作</div>', unsafe_allow_html=True)
            else:
                st.markdown('<div style="background-color:#ffaa00; color:#000; padding:5px; border-radius:5px; text-align:center">🟡 大盤盤整震盪，選擇性操作</div>', unsafe_allow_html=True)
        with col2:
            st.metric("恆指近期表現", f"{hsi_change:+.2f}%" if hsi_change != 0 else "N/A")
    else:
        st.info("無法獲取大盤數據")
    
    st.subheader("📊 量價配合分析")
    if volume_val > 0:
        if price_change_pct > 0 and volume_ratio > 1.5:
            vp_text = "✅ 價漲量增（健康上漲，動能充足）"
        elif price_change_pct < 0 and volume_ratio < 0.8:
            vp_text = "✅ 價跌量縮（下跌動能減弱，可能止跌）"
        elif price_change_pct > 0 and volume_ratio < 0.8:
            vp_text = "⚠️ 價漲量縮（上漲乏力，可能反轉）"
        elif price_change_pct < 0 and volume_ratio > 1.5:
            vp_text = "❌ 價跌量增（下跌動能強，風險較大）"
        else:
            vp_text = "🟡 量價配合一般"
        st.info(vp_text)
    else:
        st.info("請輸入成交量數據")
    
    st.subheader("📊 風險報酬比計算")
    col1, col2, col3 = st.columns(3)
    with col1:
        target_price_input = st.number_input("目標價 (港元)", value=None, step=0.1, format="%.3f", placeholder="請輸入目標價", key="target_price")
    with col2:
        stop_loss_input = st.number_input("止損價 (港元)", value=None, step=0.1, format="%.3f", placeholder="請輸入止損價", key="stop_loss_price")
    with col3:
        entry_price_input_rr = st.number_input("入場價 (港元)", value=p if p > 0 else None, step=0.1, format="%.3f", placeholder="請輸入入場價", key="entry_price_rr")
    
    if target_price_input and target_price_input > 0 and stop_loss_input and stop_loss_input > 0 and entry_price_input_rr and entry_price_input_rr > 0:
        rr_ratio, risk_pct, reward_pct = calculate_risk_reward(entry_price_input_rr, target_price_input, stop_loss_input)
        if rr_ratio is not None:
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("風險報酬比", f"1 : {rr_ratio:.2f}")
            with col2:
                st.metric("潛在虧損", f"{risk_pct:.2f}%")
            with col3:
                st.metric("潛在獲利", f"{reward_pct:.2f}%")
            with col4:
                if rr_ratio >= 2:
                    st.markdown('<div style="background-color:#00aa00; color:white; padding:5px; border-radius:5px; text-align:center">✅ 符合標準 (≥2)</div>', unsafe_allow_html=True)
                elif rr_ratio >= 1:
                    st.markdown('<div style="background-color:#ffaa00; color:#000; padding:5px; border-radius:5px; text-align:center">🟡 尚可 (1~2)</div>', unsafe_allow_html=True)
                else:
                    st.markdown('<div style="background-color:#aa0000; color:white; padding:5px; border-radius:5px; text-align:center">❌ 風險過高 (<1)</div>', unsafe_allow_html=True)
    else:
        st.info("請輸入目標價、止損價和入場價以計算風險報酬比")
    
    st.subheader("🛡️ 止損建議")
    entry_price_input = st.number_input("你的買入價 (若已持倉)", value=None, step=0.1, format="%.3f", placeholder="留空則使用 MA20 計算", key="entry_price_input")
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
    
    with st.expander("📋 5項條件詳細判斷"):
        col1, col2 = st.columns(2)
        with col1:
            st.write(f"① 股價 > 20天線: {p:.2f} > {ma20_num:.2f} → {'✅' if p > ma20_num else '❌' if ma20_num > 0 else '⚠️ 無數據'}")
            st.write(f"② RSI(6/14/24) > 50: {r6:.2f}/{r14:.2f}/{r24:.2f} → {'✅' if (r6>50 and r14>50 and r24>50) else '❌' if (r6>0 or r14>0 or r24>0) else '⚠️ 無數據'}")
            st.write(f"③ MACD 金叉: {dif:.2f} > {dea:.2f} → {'✅' if dif > dea else '❌' if dif != 0 or dea != 0 else '⚠️ 無數據'}")
        with col2:
            st.write(f"④ 成交額 > 0.3億: {to:.2f} > 0.3 → {'✅' if to > 0.3 else '❌' if to > 0 else '⚠️ 無數據'}")
            st.write(f"⑤ 乖離率(20) -4% ~ +5%: {bias20:.2f}% → {'✅' if -4 <= bias20 <= 5 else '❌' if ma20_num > 0 else '⚠️ 無數據'}")
        if boll_upper_num > 0 and boll_lower_num > 0:
            if p > boll_upper_num:
                st.write(f"⑥ 布林帶: 股價 {p:.2f} > 上軌 {boll_upper_num:.2f} → 🔴 已突破上軌，可能過熱")
            elif p < boll_lower_num:
                st.write(f"⑥ 布林帶: 股價 {p:.2f} < 下軌 {boll_lower_num:.2f} → 🟢 跌破下軌，反彈機會")
            else:
                st.write(f"⑥ 布林帶: 股價在通道內 ({boll_lower_num:.2f} ~ {boll_upper_num:.2f}) → 🟡 正常區間")
    
    st.subheader("📎 數據匯出與 AI 分析")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("📎 產生 Excel 報告", use_container_width=True, type="primary"):
            filepath = export_to_excel_hk()
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
【基本數據】股價：${p:.2f}，成交額：{to:.2f}億
【技術指標】MA20：${ma20_num:.2f}，RSI14：{r14:.1f}，MACD：DIF={dif:.4f}，DEA={dea:.4f}
【交易信號】{signal}
請根據以上數據提供專業分析建議。"""
        st.code(ai_instruction, language="markdown", line_numbers=False)
        # 2. 美股分析頁面（完整版）
elif st.session_state.page == "🇺🇸 美股分析":
    st.markdown("""
    <div style="text-align:center; padding:1rem; background:linear-gradient(135deg,#667eea,#764ba2); border-radius:10px; margin-bottom:2rem">
        <h1 style="color:white">🇺🇸 美股技術分析</h1>
        <p style="color:rgba(255,255,255,0.8)">自動抓取美股數據 | 技術指標 | 匯出 Excel 給 AI 分析</p>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2 = st.columns([3, 1])
    with col1:
        us_code = st.text_input("美股代碼", placeholder="例如：AAPL、NVDA、TSLA、MSFT", key="us_code_input").upper().strip()
    with col2:
        if st.button("🔍 載入", type="primary", use_container_width=True):
            if us_code:
                with st.spinner(f"正在獲取 {us_code} 數據..."):
                    try:
                        if not YFINANCE_AVAILABLE:
                            st.error("請安裝 yfinance: pip3 install yfinance")
                        else:
                            ticker = yf.Ticker(us_code)
                            info = ticker.info
                            
                            st.session_state.us_stock_name = info.get('longName', us_code)
                            st.session_state.us_stock_price = info.get('regularMarketPrice', info.get('currentPrice', 0))
                            st.session_state.us_stock_change = info.get('regularMarketChange', 0)
                            st.session_state.us_stock_change_pct = info.get('regularMarketChangePercent', 0)
                            st.session_state.us_volume = info.get('volume', 0)
                            st.session_state.us_avg_volume = info.get('averageVolume', 0)
                            st.session_state.us_pe = info.get('trailingPE', 'N/A')
                            st.session_state.us_market_cap = info.get('marketCap', 0)
                            st.session_state.us_high_52week = info.get('fiftyTwoWeekHigh', 0)
                            st.session_state.us_low_52week = info.get('fiftyTwoWeekLow', 0)
                            st.session_state.us_dividend_yield = info.get('dividendYield', 0)
                            
                            hist = ticker.history(period="6mo")
                            if len(hist) >= 50:
                                closes = hist['Close'].values
                                st.session_state.us_ma20 = round(np.mean(closes[-20:]), 2) if len(closes) >= 20 else "N/A"
                                st.session_state.us_ma50 = round(np.mean(closes[-50:]), 2) if len(closes) >= 50 else "N/A"
                                st.session_state.us_ma200 = round(np.mean(closes[-200:]), 2) if len(closes) >= 200 else "N/A"
                                
                                if len(closes) >= 15:
                                    deltas = np.diff(closes[-15:])
                                    gains = np.where(deltas > 0, deltas, 0)
                                    losses = np.where(deltas < 0, -deltas, 0)
                                    avg_gain = np.mean(gains[-14:]) if len(gains) >= 14 else 0
                                    avg_loss = np.mean(losses[-14:]) if len(losses) >= 14 else 0
                                    st.session_state.us_rsi14 = round(100 - (100 / (1 + avg_gain/avg_loss)) if avg_loss > 0 else 100, 1)
                                else:
                                    st.session_state.us_rsi14 = "N/A"
                                
                                if len(closes) >= 26:
                                    exp1 = pd.Series(closes).ewm(span=12, adjust=False).mean()
                                    exp2 = pd.Series(closes).ewm(span=26, adjust=False).mean()
                                    dif = exp1 - exp2
                                    dea = dif.ewm(span=9, adjust=False).mean()
                                    st.session_state.us_macd_dif = round(dif.iloc[-1], 4)
                                    st.session_state.us_macd_dea = round(dea.iloc[-1], 4)
                                    st.session_state.us_macd_hist = round((dif - dea).iloc[-1], 4)
                                
                                st.success(f"✅ 已載入 {us_code} ({st.session_state.us_stock_name})")
                            else:
                                st.warning(f"數據不足，無法計算技術指標")
                            
                    except Exception as e:
                        st.error(f"獲取數據失敗: {e}")
                        st.info("請檢查美股代碼是否正確（例如：AAPL、NVDA、TSLA、MSFT、GOOGL）")
    
    if st.session_state.us_stock_price > 0:
        st.caption(f"當前股票: {us_code} - {st.session_state.us_stock_name}")
    st.divider()
    
    st.subheader("📊 基本數據")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("股價 (USD)", f"${st.session_state.us_stock_price:.2f}" if st.session_state.us_stock_price else "N/A", 
                 delta=f"{st.session_state.us_stock_change:+.2f} ({st.session_state.us_stock_change_pct:+.2f}%)" if st.session_state.us_stock_change else None)
    with col2:
        st.metric("成交量", f"{st.session_state.us_volume:,}" if st.session_state.us_volume else "N/A")
    with col3:
        avg_vol = st.session_state.us_avg_volume
        st.metric("平均成交量", f"{avg_vol:,}" if avg_vol else "N/A")
    with col4:
        pe = st.session_state.us_pe
        st.metric("市盈率 (PE)", f"{pe:.2f}" if isinstance(pe, (int, float)) and pe > 0 else str(pe))
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        if st.session_state.us_market_cap > 0:
            market_cap_bn = st.session_state.us_market_cap / 1e9
            st.metric("市值", f"${market_cap_bn:.1f} 億")
    with col2:
        if st.session_state.us_high_52week > 0:
            st.metric("52週高", f"${st.session_state.us_high_52week:.2f}")
    with col3:
        if st.session_state.us_low_52week > 0:
            st.metric("52週低", f"${st.session_state.us_low_52week:.2f}")
    with col4:
        if st.session_state.us_dividend_yield > 0:
            st.metric("股息率", f"{st.session_state.us_dividend_yield * 100:.2f}%")
    
    st.divider()
    
    st.subheader("📊 技術指標")
    st.caption("💡 以下數據已自動計算，也可手動修改")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown("**📈 移動平均線**")
        us_ma20 = st.text_input("MA20", value=str(st.session_state.us_ma20) if st.session_state.us_ma20 != "N/A" else "", placeholder="例如: 175.50", key="us_ma20_input")
        us_ma50 = st.text_input("MA50", value=str(st.session_state.us_ma50) if st.session_state.us_ma50 != "N/A" else "", placeholder="例如: 170.00", key="us_ma50_input")
        us_ma200 = st.text_input("MA200", value=str(st.session_state.us_ma200) if st.session_state.us_ma200 != "N/A" else "", placeholder="例如: 150.00", key="us_ma200_input")
    with col2:
        st.markdown("**📊 RSI / MACD**")
        us_rsi14 = st.text_input("RSI(14)", value=str(st.session_state.us_rsi14) if st.session_state.us_rsi14 != "N/A" else "", placeholder="例如: 65.5", key="us_rsi14_input")
        us_macd_dif = st.text_input("MACD DIF", value=str(st.session_state.us_macd_dif) if st.session_state.us_macd_dif else "", placeholder="例如: 1.234", key="us_macd_dif_input")
        us_macd_dea = st.text_input("MACD DEA", value=str(st.session_state.us_macd_dea) if st.session_state.us_macd_dea else "", placeholder="例如: 1.123", key="us_macd_dea_input")
    with col3:
        st.markdown("**📊 手動輸入**")
        us_rsi14_manual = st.number_input("手動輸入 RSI14", value=None, step=0.5, format="%.1f", placeholder="或手動輸入", key="us_rsi14_manual")
        us_macd_dif_manual = st.number_input("手動輸入 DIF", value=None, step=0.1, format="%.4f", placeholder="或手動輸入", key="us_macd_dif_manual")
        us_macd_dea_manual = st.number_input("手動輸入 DEA", value=None, step=0.1, format="%.4f", placeholder="或手動輸入", key="us_macd_dea_manual")
    
    final_rsi = us_rsi14_manual if us_rsi14_manual is not None else (parse_number(us_rsi14) if us_rsi14 else 0)
    final_dif = us_macd_dif_manual if us_macd_dif_manual is not None else (parse_number(us_macd_dif) if us_macd_dif else 0)
    final_dea = us_macd_dea_manual if us_macd_dea_manual is not None else (parse_number(us_macd_dea) if us_macd_dea else 0)
    
    p = st.session_state.us_stock_price
    ma20_num = parse_number(us_ma20)
    ma50_num = parse_number(us_ma50)
    ma200_num = parse_number(us_ma200)
    rsi = final_rsi
    dif = final_dif
    dea = final_dea
    volume = st.session_state.us_volume
    avg_volume = st.session_state.us_avg_volume
    
    st.divider()
    
    st.subheader("📈 技術分析")
    
    if ma20_num > 0 and ma50_num > 0 and ma200_num > 0:
        if ma20_num > ma50_num > ma200_num:
            ma_status = "✅ 多頭排列 (MA20 > MA50 > MA200)"
            ma_color = "green"
        elif ma20_num < ma50_num < ma200_num:
            ma_status = "❌ 空頭排列 (MA20 < MA50 < MA200)"
            ma_color = "red"
        else:
            ma_status = "🟡 均線糾結，方向不明"
            ma_color = "yellow"
        st.markdown(f'<div style="color:{ma_color}; font-weight:bold">{ma_status}</div>', unsafe_allow_html=True)
    else:
        st.info("請輸入 MA 數據")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("股價 vs MA20", f"${p:.2f} vs ${ma20_num:.2f}" if ma20_num > 0 else "N/A", delta=f"{((p - ma20_num)/ma20_num*100):+.2f}%" if ma20_num > 0 else None)
    with col2:
        st.metric("股價 vs MA50", f"${p:.2f} vs ${ma50_num:.2f}" if ma50_num > 0 else "N/A", delta=f"{((p - ma50_num)/ma50_num*100):+.2f}%" if ma50_num > 0 else None)
    with col3:
        st.metric("股價 vs MA200", f"${p:.2f} vs ${ma200_num:.2f}" if ma200_num > 0 else "N/A", delta=f"{((p - ma200_num)/ma200_num*100):+.2f}%" if ma200_num > 0 else None)
    
    if volume > 0 and avg_volume > 0:
        volume_ratio = volume / avg_volume
        if volume_ratio > 1.5:
            volume_status = "📊 成交量明顯放大 (比平均多50%以上)"
        elif volume_ratio < 0.5:
            volume_status = "📊 成交量萎縮"
        else:
            volume_status = "📊 成交量正常"
        st.info(volume_status)
    
    if rsi > 0:
        if rsi > 70:
            rsi_status = "🔴 超買區 (RSI > 70)，可能回調"
            rsi_color = "red"
        elif rsi < 30:
            rsi_status = "🟢 超賣區 (RSI < 30)，可能反彈"
            rsi_color = "green"
        elif rsi > 50:
            rsi_status = "🟡 強勢區 (RSI > 50)"
            rsi_color = "yellow"
        else:
            rsi_status = "⚪ 弱勢區 (RSI < 50)"
            rsi_color = "gray"
        st.markdown(f'<div style="color:{rsi_color}">{rsi_status} (RSI: {rsi:.1f})</div>', unsafe_allow_html=True)
    
    if dif != 0 or dea != 0:
        if dif > dea:
            macd_status = "✅ MACD 金叉 (DIF > DEA)，看漲信號"
            macd_color = "green"
        elif dif < dea:
            macd_status = "❌ MACD 死叉 (DIF < DEA)，看跌信號"
            macd_color = "red"
        else:
            macd_status = "🟡 MACD 持平"
            macd_color = "yellow"
        st.markdown(f'<div style="color:{macd_color}">{macd_status}</div>', unsafe_allow_html=True)
    
    st.divider()
    
    st.subheader("🎯 綜合交易信號")
    
    score = 0
    reasons = []
    
    if p > ma20_num and ma20_num > 0:
        score += 1
        reasons.append("股價站穩 MA20")
    if p > ma50_num and ma50_num > 0:
        score += 1
        reasons.append("股價站穩 MA50")
    if p > ma200_num and ma200_num > 0:
        score += 1
        reasons.append("股價站穩 MA200")
    if 30 < rsi < 70 and rsi > 0:
        score += 1
        reasons.append("RSI 健康區間")
    elif rsi < 30 and rsi > 0:
        reasons.append("RSI 超賣，留意反彈機會")
    elif rsi > 70 and rsi > 0:
        reasons.append("RSI 超買，注意風險")
    if dif > dea and dif != 0:
        score += 1
        reasons.append("MACD 金叉")
    if volume > avg_volume * 1.5 and avg_volume > 0:
        score += 1
        reasons.append("成交量放大，資金關注")
    
    if score >= 5:
        signal = "🔴 強烈買入"
        signal_color = "#00ff00"
    elif score >= 4:
        signal = "🟢 買入"
        signal_color = "#00cc00"
    elif score >= 3:
        signal = "🟡 持有 / 觀望"
        signal_color = "#ffaa00"
    elif score >= 2:
        signal = "⚪ 謹慎"
        signal_color = "#ff8800"
    else:
        signal = "⚫ 賣出 / 迴避"
        signal_color = "#ff4444"
    
    st.markdown(f'<div style="background-color:{signal_color}; color:#000; padding:10px; border-radius:5px; font-weight:bold; text-align:center">{signal}</div>', unsafe_allow_html=True)
    
    with st.expander("📋 信號詳細分析"):
        for r in reasons:
            st.write(f"✅ {r}")
        st.write(f"綜合評分: {score}/7")
    
    st.divider()
    
    st.subheader("📎 數據匯出與 AI 分析")
    st.caption("匯出完整 Excel 檔案，然後上傳到 DeepSeek 或 ChatGPT 進行深度分析")
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("📎 匯出完整 Excel 報告", use_container_width=True, type="primary"):
            market_cap_val = st.session_state.us_market_cap if isinstance(st.session_state.us_market_cap, (int, float)) else 0
            us_export_data = {
                '股票代碼': us_code,
                '股票名稱': st.session_state.us_stock_name,
                '分析日期': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                '股價 (USD)': st.session_state.us_stock_price,
                '漲跌': st.session_state.us_stock_change,
                '漲跌幅 (%)': st.session_state.us_stock_change_pct,
                '成交量': st.session_state.us_volume,
                '平均成交量': st.session_state.us_avg_volume,
                '市盈率 (PE)': st.session_state.us_pe,
                '市值 (億 USD)': market_cap_val / 1e9 if market_cap_val > 0 else 'N/A',
                '52週高': st.session_state.us_high_52week,
                '52週低': st.session_state.us_low_52week,
                '股息率 (%)': st.session_state.us_dividend_yield * 100 if st.session_state.us_dividend_yield else 0,
                'MA20': ma20_num,
                'MA50': ma50_num,
                'MA200': ma200_num,
                'RSI(14)': rsi,
                'MACD DIF': dif,
                'MACD DEA': dea,
                'MACD柱': dif - dea,
                '交易信號': signal,
                '綜合評分': f"{score}/7"
            }
            df_us_export = pd.DataFrame([us_export_data])
            filename = f"美股分析_{us_code}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
            filepath = os.path.join(EXPORT_FOLDER, filename)
            df_us_export.to_excel(filepath, index=False)
            st.success(f"✅ Excel 已儲存: {filepath}")
            st.info("📌 請將此 Excel 檔案上傳到 DeepSeek 或 ChatGPT 進行分析")
    
    with col2:
        wl = load_watchlist()
        us_code_full = f"US_{us_code}"
        if us_code_full in wl:
            st.button("⭐ 已加入自選股", disabled=True, use_container_width=True)
        else:
            if st.button("➕ 加入自選股", use_container_width=True):
                wl.append(us_code_full)
                save_watchlist(wl)
                st.success("✅ 已加入自選股")
                st.rerun()
    
    with st.expander("📋 點擊展開 AI 分析指令（複製後貼到 DeepSeek/ChatGPT）"):
        ai_instruction = f"""請分析以下美股，提供投資建議：
【股票資訊】股票代碼：{us_code}，名稱：{st.session_state.us_stock_name}，股價：${st.session_state.us_stock_price:.2f}，漲跌幅：{st.session_state.us_stock_change_pct:+.2f}%
【技術指標】MA20：${ma20_num:.2f}，MA50：${ma50_num:.2f}，MA200：${ma200_num:.2f}，RSI(14)：{rsi:.1f}，MACD：DIF={dif:.4f}，DEA={dea:.4f}
【技術信號】{signal}
請提供專業分析建議。"""
        st.code(ai_instruction, language="markdown", line_numbers=False)
        st.caption("💡 提示：複製指令 → 上傳 Excel → 貼上指令 → 獲得 AI 分析")

# 3. 自選股頁面（完整版）
elif st.session_state.page == "⭐ 自選股":
    st.markdown("""
    <div style="text-align:center; padding:1rem; background:linear-gradient(135deg,#667eea,#764ba2); border-radius:10px; margin-bottom:2rem">
        <h1 style="color:white">⭐ 自選股列表</h1>
        <p style="color:rgba(255,255,255,0.8)">追蹤股票 | 五項條件 | 個人備註</p>
    </div>
    """, unsafe_allow_html=True)
    
    watchlist_codes = load_watchlist()
    
    for code in watchlist_codes:
        if code not in st.session_state.watchlist_data:
            st.session_state.watchlist_data[code] = {
                'name': '', 'sector': '', 'price': None, 'ma20': None, 'rsi14': None,
                'macd_dif': None, 'macd_dea': None, 'turnover': None, 'bias20': None,
                'cond1': '⚠️ 無數據', 'cond2': '⚠️ 無數據', 'cond3': '⚠️ 無數據',
                'cond4': '⚠️ 無數據', 'cond5': '⚠️ 無數據', 'notes': '', 'last_update': ''
            }
    
    with st.expander("➕ 添加新股票到自選股", expanded=False):
        col1, col2, col3 = st.columns([2, 1, 1])
        with col1:
            new_code = st.text_input("股票代碼", placeholder="例如: 00700", key="new_watchlist_code")
        with col2:
            if st.button("🔍 自動獲取數據", use_container_width=True):
                if new_code:
                    norm_code = normalize_code(new_code)
                    success, name, price, volume, turnover = auto_fetch_and_fill(new_code)
                    if success:
                        st.session_state.watchlist_data[norm_code]['name'] = name
                        st.session_state.watchlist_data[norm_code]['price'] = price
                        st.session_state.watchlist_data[norm_code]['turnover'] = turnover
                        st.session_state.watchlist_data[norm_code]['sector'] = get_stock_sector(name)
                        st.success(f"✅ 已獲取 {norm_code} 基本數據")
                    else:
                        st.info("請手動輸入股票資料")
        with col3:
            if st.button("➕ 加入自選股", use_container_width=True, type="primary"):
                if new_code:
                    norm_code = normalize_code(new_code)
                    if norm_code not in watchlist_codes:
                        watchlist_codes.append(norm_code)
                        save_watchlist(watchlist_codes)
                        st.success(f"✅ 已加入 {norm_code}")
                        st.rerun()
                    else:
                        st.warning("股票已在自選股中")
    
    if not watchlist_codes:
        st.info("暫無自選股。點擊上方「添加新股票」開始加入。")
    else:
        st.subheader(f"📋 自選股列表 ({len(watchlist_codes)} 隻)")
        
        for idx, code in enumerate(watchlist_codes):
            data = st.session_state.watchlist_data.get(code, {})
            
            with st.expander(f"📊 {code} - {data.get('name', '未命名')}", expanded=False):
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    new_name = st.text_input("股票名稱", value=data.get('name', ''), placeholder="例如: 騰訊控股", key=f"name_{code}_{idx}")
                    data['name'] = new_name
                with col2:
                    new_sector = st.text_input("所屬板塊", value=data.get('sector', ''), placeholder="例如: AI/科技", key=f"sector_{code}_{idx}")
                    data['sector'] = new_sector
                with col3:
                    new_price = st.number_input("股價 (港元)", value=data.get('price'), step=0.1, format="%.3f", placeholder="請輸入股價", key=f"price_{code}_{idx}")
                    data['price'] = new_price if new_price else None
                with col4:
                    new_turnover = st.number_input("成交額 (億)", value=data.get('turnover'), step=0.1, format="%.2f", placeholder="請輸入成交額", key=f"turnover_{code}_{idx}")
                    data['turnover'] = new_turnover if new_turnover else None
                
                st.markdown("---")
                st.markdown("**📊 技術指標**")
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    new_ma20 = st.number_input("MA20", value=data.get('ma20'), step=0.1, format="%.3f", placeholder="例如: 502.700", key=f"ma20_{code}_{idx}")
                    data['ma20'] = new_ma20 if new_ma20 else None
                with col2:
                    new_rsi14 = st.number_input("RSI(14)", value=data.get('rsi14'), step=0.5, format="%.1f", placeholder="例如: 62.5", key=f"rsi14_{code}_{idx}")
                    data['rsi14'] = new_rsi14 if new_rsi14 else None
                with col3:
                    new_macd_dif = st.number_input("MACD DIF", value=data.get('macd_dif'), step=0.1, format="%.4f", placeholder="例如: 1.234", key=f"macd_dif_{code}_{idx}")
                    data['macd_dif'] = new_macd_dif if new_macd_dif else None
                with col4:
                    new_macd_dea = st.number_input("MACD DEA", value=data.get('macd_dea'), step=0.1, format="%.4f", placeholder="例如: 1.123", key=f"macd_dea_{code}_{idx}")
                    data['macd_dea'] = new_macd_dea if new_macd_dea else None
                
                st.markdown("---")
                st.markdown("**📋 五項條件判斷**")
                
                price_val = data.get('price', 0)
                ma20_val = data.get('ma20', 0)
                rsi14_val = data.get('rsi14', 0)
                macd_dif_val = data.get('macd_dif', 0)
                macd_dea_val = data.get('macd_dea', 0)
                turnover_val = data.get('turnover', 0)
                
                if ma20_val and ma20_val > 0 and price_val:
                    bias20 = (price_val - ma20_val) / ma20_val * 100
                else:
                    bias20 = 0
                
                cond1_result = price_val > ma20_val if ma20_val else None
                cond2_result = rsi14_val > 50 if rsi14_val else None
                cond3_result = macd_dif_val > macd_dea_val if (macd_dif_val and macd_dea_val) else None
                cond4_result = turnover_val > 0.3 if turnover_val else None
                cond5_result = -4 <= bias20 <= 5 if ma20_val else None
                
                col1, col2, col3, col4, col5 = st.columns(5)
                with col1:
                    cond1_manual = st.selectbox("① 股價 > 20天線", options=["✅ 是", "❌ 否", "⚠️ 無數據"], index=0 if cond1_result == True else 1 if cond1_result == False else 2, key=f"cond1_{code}_{idx}")
                    data['cond1'] = cond1_manual
                with col2:
                    cond2_manual = st.selectbox("② RSI(14) > 50", options=["✅ 是", "❌ 否", "⚠️ 無數據"], index=0 if cond2_result == True else 1 if cond2_result == False else 2, key=f"cond2_{code}_{idx}")
                    data['cond2'] = cond2_manual
                with col3:
                    cond3_manual = st.selectbox("③ MACD 金叉", options=["✅ 是", "❌ 否", "⚠️ 無數據"], index=0 if cond3_result == True else 1 if cond3_result == False else 2, key=f"cond3_{code}_{idx}")
                    data['cond3'] = cond3_manual
                with col4:
                    cond4_manual = st.selectbox("④ 成交額 > 0.3億", options=["✅ 是", "❌ 否", "⚠️ 無數據"], index=0 if cond4_result == True else 1 if cond4_result == False else 2, key=f"cond4_{code}_{idx}")
                    data['cond4'] = cond4_manual
                with col5:
                    cond5_manual = st.selectbox("⑤ 乖離率 -4%~+5%", options=["✅ 是", "❌ 否", "⚠️ 無數據"], index=0 if cond5_result == True else 1 if cond5_result == False else 2, key=f"cond5_{code}_{idx}")
                    data['cond5'] = cond5_manual
                
                score = sum([1 for c in [cond1_manual, cond2_manual, cond3_manual, cond4_manual, cond5_manual] if c == "✅ 是"])
                st.markdown(f"**綜合評分: {score}/5**")
                
                if score >= 4:
                    st.markdown('<div style="background-color:#00ff00; color:#000; padding:5px; border-radius:5px; text-align:center">🔴 強烈買入信號</div>', unsafe_allow_html=True)
                elif score >= 3:
                    st.markdown('<div style="background-color:#00cc00; color:#fff; padding:5px; border-radius:5px; text-align:center">🟢 買入信號</div>', unsafe_allow_html=True)
                elif score >= 2:
                    st.markdown('<div style="background-color:#ffaa00; color:#000; padding:5px; border-radius:5px; text-align:center">🟡 持有/觀望</div>', unsafe_allow_html=True)
                elif score >= 1:
                    st.markdown('<div style="background-color:#ff8800; color:#fff; padding:5px; border-radius:5px; text-align:center">⚪ 謹慎</div>', unsafe_allow_html=True)
                else:
                    st.markdown('<div style="background-color:#ff4444; color:#fff; padding:5px; border-radius:5px; text-align:center">⚫ 賣出/迴避</div>', unsafe_allow_html=True)
                
                st.markdown("---")
                st.markdown("**📝 個人備註 / 筆記**")
                new_notes = st.text_area("備註", value=data.get('notes', ''), height=80, placeholder="記錄你的分析想法、買入理由、目標價等...", key=f"notes_{code}_{idx}")
                data['notes'] = new_notes
                data['last_update'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    if st.button(f"💾 儲存更改", key=f"save_{code}_{idx}", use_container_width=True):
                        st.session_state.watchlist_data[code] = data
                        save_watchlist_data(st.session_state.watchlist_data)
                        st.success(f"✅ 已儲存 {code} 的更改")
                        st.rerun()
                with col2:
                    if st.button(f"📊 詳細分析", key=f"analyze_{code}_{idx}", use_container_width=True):
                        perform_search(code)
                        set_page("🔍 港股分析")
                with col3:
                    if st.button(f"🗑️ 移除自選股", key=f"remove_{code}_{idx}", use_container_width=True):
                        watchlist_codes.remove(code)
                        save_watchlist(watchlist_codes)
                        if code in st.session_state.watchlist_data:
                            del st.session_state.watchlist_data[code]
                        save_watchlist_data(st.session_state.watchlist_data)
                        st.success(f"✅ 已移除 {code}")
                        st.rerun()
            
            with st.container():
                col1, col2, col3, col4, col5 = st.columns([1, 2, 1, 1, 1])
                data = st.session_state.watchlist_data.get(code, {})
                cond1 = data.get('cond1', '⚠️')
                cond2 = data.get('cond2', '⚠️')
                cond3 = data.get('cond3', '⚠️')
                cond4 = data.get('cond4', '⚠️')
                cond5 = data.get('cond5', '⚠️')
                score = sum([1 for c in [cond1, cond2, cond3, cond4, cond5] if c == "✅ 是"])
                signal_emoji = "🔴" if score >= 4 else "🟢" if score >= 3 else "🟡" if score >= 2 else "⚪" if score >= 1 else "⚫"
                with col1:
                    st.write(f"**{code}**")
                with col2:
                    st.write(data.get('name', '未命名'))
                with col3:
                    price = data.get('price')
                    st.write(f"${price:.2f}" if price else "N/A")
                with col4:
                    st.write(f"{signal_emoji} {score}/5")
                with col5:
                    pass

# 4. 投資組合頁面（完整版）
elif st.session_state.page == "📊 投資組合":
    st.markdown("# 📊 投資組合")
    pf = load_portfolio()
    with st.expander("➕ 新增交易"):
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            trade_code = st.text_input("股票代碼", placeholder="例如: 00700", key="tc")
        with col2:
            trade_type = st.selectbox("類型", ["買入", "賣出"], key="tt")
        with col3:
            trade_price = st.number_input("價格 (港元)", value=None, step=0.1, format="%.3f", placeholder="請輸入價格", key="tp")
        with col4:
            trade_shares = st.number_input("股數", value=None, step=100, placeholder="請輸入股數", key="ts")
        
        st.markdown("**📅 交易日期**")
        date_col1, date_col2, date_col3, date_col4 = st.columns([1, 2, 1, 2])
        with date_col1:
            if st.button("◀ 前一天", key="date_minus", use_container_width=True):
                st.session_state.trade_date -= timedelta(days=1)
                st.rerun()
        with date_col2:
            trade_date = st.date_input("日期", value=st.session_state.trade_date, key="trade_date_input", label_visibility="collapsed")
            st.session_state.trade_date = trade_date
        with date_col3:
            if st.button("後一天 ▶", key="date_plus", use_container_width=True):
                st.session_state.trade_date += timedelta(days=1)
                st.rerun()
        with date_col4:
            if st.button("📅 今天", key="date_today", use_container_width=True):
                st.session_state.trade_date = datetime.now().date()
                st.rerun()
        
        if st.button("💾 儲存"):
            if trade_code and trade_price and trade_price > 0 and trade_shares and trade_shares > 0:
                pf.append({'code': normalize_code(trade_code), 'type': trade_type, 'price': trade_price, 'shares': trade_shares, 'date': st.session_state.trade_date.strftime('%Y-%m-%d')})
                save_portfolio(pf)
                st.rerun()
            else:
                st.warning("請填寫完整資料")
    if pf:
        st.dataframe(pd.DataFrame(pf))
    
    st.subheader("📊 持倉成本追蹤")
    positions = load_portfolio_positions()
    if positions:
        summary = calculate_portfolio_summary(positions)
        summary_data = []
        for code, data in summary.items():
            if data['total_shares'] != 0:
                summary_data.append({
                    '股票代碼': code,
                    '持股數量': data['total_shares'],
                    '平均成本': f"${data['avg_cost']:.2f}" if data['avg_cost'] > 0 else "N/A",
                    '當前股價': f"${data['current_price']:.2f}" if data['current_price'] > 0 else "N/A",
                    '當前市值': f"${data['current_value']:,.2f}",
                    '盈虧': f"${data['profit_loss']:+,.2f}",
                    '盈虧%': f"{data['profit_loss_pct']:+.2f}%"
                })
        if summary_data:
            st.dataframe(pd.DataFrame(summary_data), use_container_width=True)
        else:
            st.info("暫無有效持倉")
    else:
        st.info("暫無交易記錄，請先添加交易")

# 5. 交易日誌頁面（完整版）
elif st.session_state.page == "📝 交易日誌":
    st.markdown("# 📝 交易日誌")
    code = st.text_input("股票代碼", placeholder="例如: 00700")
    if code:
        notes = load_journal(code)
        with st.form("note"):
            title = st.text_input("標題", placeholder="例如: 買入理由")
            content = st.text_area("內容", height=150, placeholder="記錄你的分析想法...")
            tags = st.text_input("標籤", placeholder="例如: 買入,技術分析")
            if st.form_submit_button("💾 儲存"):
                if title or content:
                    save_journal(code, {'title': title, 'content': content, 'tags': tags.split(',') if tags else [], 'date': datetime.now().strftime('%Y-%m-%d %H:%M')})
                    st.rerun()
        for n in reversed(notes):
            st.markdown(f"**📌 {n['title']}**")
            st.caption(f"{n['date']} | 標籤: {', '.join(n['tags'])}")
            st.write(n['content'])
            st.divider()

# 6. 交易記錄與檢討頁面（完整版）
elif st.session_state.page == "📊 交易記錄與檢討":
    st.markdown("""
    <div style="text-align:center; padding:1rem; background:linear-gradient(135deg,#667eea,#764ba2); border-radius:10px; margin-bottom:2rem">
        <h1 style="color:white">📊 交易記錄與檢討</h1>
        <p style="color:rgba(255,255,255,0.8)">記錄每筆交易 | 自動計算手續費 | 買入前檢查清單 | 操作檢討</p>
    </div>
    """, unsafe_allow_html=True)
    
    tab1, tab2, tab3, tab4 = st.tabs(["📝 新增交易記錄", "📋 交易記錄列表", "✅ 買入前檢查清單", "📈 績效統計"])
    
    # Tab 1: 新增交易記錄
    with tab1:
        st.subheader("➕ 新增交易記錄")
        
        col1, col2 = st.columns(2)
        with col1:
            market = st.selectbox("市場", ["🇭🇰 港股", "🇺🇸 美股"], key="trade_market")
            stock_code = st.text_input("股票代碼", placeholder="例如: 00700 / AAPL", key="trade_code")
            
            auto_name = ""
            if stock_code:
                code_upper = stock_code.upper().strip()
                if code_upper in STOCK_NAME_MAP:
                    auto_name = STOCK_NAME_MAP[code_upper]
                elif len(code_upper) == 5 and code_upper.isdigit():
                    if code_upper in STOCK_NAME_MAP:
                        auto_name = STOCK_NAME_MAP[code_upper]
                elif code_upper.isalpha() and len(code_upper) <= 5:
                    if code_upper in STOCK_NAME_MAP:
                        auto_name = STOCK_NAME_MAP[code_upper]
            
            if auto_name:
                st.success(f"📌 股票名稱: {auto_name}")
            
            stock_name = st.text_input("股票名稱", value=auto_name, placeholder="可手動修改", key="trade_name")
        
        with col2:
            trade_date = st.date_input("交易日期", value=datetime.now().date(), key="trade_date")
            buy_price = st.number_input("買入價", value=None, step=0.001, format="%.3f", placeholder="請輸入買入價", key="buy_price")
            sell_price = st.number_input("賣出價（未賣出可留空）", value=None, step=0.001, format="%.3f", placeholder="請輸入賣出價", key="sell_price")
            shares = st.number_input("股數", value=None, step=100, placeholder="請輸入股數", key="shares")
        
        show_hkd = False
        if market == "🇺🇸 美股":
            show_hkd = st.checkbox("同時顯示港幣換算（匯率 7.8）", value=True, key="show_hkd")
            exchange_rate = 7.8
        
        if buy_price is not None and buy_price > 0 and shares is not None and shares > 0:
            st.markdown("---")
            st.subheader("💰 費用預覽（自動計算）")
            
            if market == "🇭🇰 港股":
                preview_buy_amount = buy_price * shares
                preview_commission = max(3, preview_buy_amount * 0.0003)
                preview_platform = 15.0
                
                col_a, col_b, col_c = st.columns(3)
                with col_a:
                    st.metric("買入金額", f"HK${preview_buy_amount:,.2f}")
                with col_b:
                    st.metric("預估佣金", f"HK${preview_commission:.2f}")
                with col_c:
                    st.metric("平台費", f"HK${preview_platform:.2f}")
                
                if sell_price is not None and sell_price > 0:
                    preview_result = calculate_hk_fees_auto(buy_price, sell_price, shares)
                    col_a, col_b, col_c = st.columns(3)
                    with col_a:
                        st.metric("總費用", f"HK${preview_result['total_fees']:.2f}")
                    with col_b:
                        st.metric("毛利", f"HK${preview_result['gross_profit']:.2f}")
                    with col_c:
                        profit_color = "🟢" if preview_result['net_profit'] > 0 else "🔴"
                        st.metric(f"{profit_color} 淨利潤", f"HK${preview_result['net_profit']:.2f}")
                    
                    with st.expander("📋 費用明細"):
                        for name, amount in preview_result['fee_breakdown'].items():
                            st.write(f"{name}: HK${amount:.2f}")
                else:
                    st.info("輸入賣出價後將自動計算完整費用和利潤")
            
            else:
                preview_buy_amount_usd = buy_price * shares
                preview_commission_usd = max(0.99, shares * 0.0049)
                preview_platform_usd = max(1.0, shares * 0.005)
                
                col_a, col_b, col_c = st.columns(3)
                with col_a:
                    st.metric("買入金額", f"${preview_buy_amount_usd:,.2f}")
                    if show_hkd:
                        st.caption(f"≈ HK${preview_buy_amount_usd * exchange_rate:,.2f}")
                with col_b:
                    st.metric("預估佣金", f"${preview_commission_usd:.2f}")
                with col_c:
                    st.metric("平台費", f"${preview_platform_usd:.2f}")
                
                if sell_price is not None and sell_price > 0:
                    preview_result = calculate_us_fees_auto(buy_price, sell_price, shares, show_hkd, exchange_rate)
                    col_a, col_b, col_c = st.columns(3)
                    with col_a:
                        st.metric("總費用", f"${preview_result['total_fees_usd']:.2f}")
                        if show_hkd:
                            st.caption(f"≈ HK${preview_result['total_fees_hkd']:.2f}")
                    with col_b:
                        st.metric("毛利", f"${preview_result['gross_profit_usd']:.2f}")
                        if show_hkd:
                            st.caption(f"≈ HK${preview_result['gross_profit_hkd']:.2f}")
                    with col_c:
                        profit = preview_result['net_profit_usd']
                        profit_color = "🟢" if profit > 0 else "🔴"
                        st.metric(f"{profit_color} 淨利潤", f"${profit:.2f}")
                        if show_hkd:
                            st.caption(f"≈ HK${preview_result['net_profit_hkd']:.2f}")
                    
                    with st.expander("📋 費用明細（美元）"):
                        for name, amount in preview_result['fee_breakdown_usd'].items():
                            st.write(f"{name}: ${amount:.2f}")
                else:
                    st.info("輸入賣出價後將自動計算完整費用和利潤")
        
        st.markdown("---")
        st.subheader("📝 操作檢討")
        review_text = st.text_area("檢討內容", height=100, placeholder="記錄你的操作反思、學到什麼、下次如何改進...", key="review_text")
        
        col1, col2 = st.columns(2)
        with col1:
            rating = st.select_slider("操作評分", options=["⭐", "⭐⭐", "⭐⭐⭐", "⭐⭐⭐⭐", "⭐⭐⭐⭐⭐"], value="⭐⭐⭐", key="rating")
        with col2:
            lesson = st.text_input("學到的教訓", placeholder="例如: 不應追高、要設定止損...", key="lesson")
        
        if st.button("💾 儲存交易記錄", type="primary", use_container_width=True):
            if stock_code and buy_price is not None and buy_price > 0 and shares is not None and shares > 0:
                try:
                    if market == "🇭🇰 港股":
                        if sell_price is not None and sell_price > 0:
                            fee_result = calculate_hk_fees_auto(buy_price, sell_price, shares)
                        else:
                            fee_result = {
                                'buy_amount': buy_price * shares, 'sell_amount': 0,
                                'gross_profit': 0, 'total_fees': 0, 'net_profit': 0,
                                'currency': 'HKD', 'currency_symbol': 'HK$', 'fee_breakdown': {}
                            }
                    else:
                        if sell_price is not None and sell_price > 0:
                            fee_result = calculate_us_fees_auto(buy_price, sell_price, shares, show_hkd, 7.8)
                        else:
                            fee_result = {
                                'buy_amount_usd': buy_price * shares, 'sell_amount_usd': 0,
                                'gross_profit_usd': 0, 'total_fees_usd': 0, 'net_profit_usd': 0,
                                'currency': 'USD', 'currency_symbol': '$', 'fee_breakdown_usd': {}
                            }
                            if show_hkd:
                                fee_result['net_profit_hkd'] = 0
                    
                    new_record = {
                        "id": str(datetime.now().timestamp()),
                        "market": market,
                        "stock_code": stock_code,
                        "stock_name": stock_name,
                        "trade_date": trade_date.strftime('%Y-%m-%d'),
                        "buy_price": round(buy_price, 3),
                        "sell_price": round(sell_price, 3) if sell_price is not None and sell_price > 0 else None,
                        "shares": shares,
                        "fee_result": fee_result,
                        "show_hkd": show_hkd if market == "🇺🇸 美股" else False,
                        "review": review_text,
                        "rating": rating,
                        "lesson": lesson,
                        "created_at": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    }
                    
                    records = load_trade_records()
                    records.append(new_record)
                    save_trade_records(records)
                    st.success("✅ 交易記錄已儲存！")
                    st.rerun()
                except Exception as e:
                    st.error(f"儲存失敗: {e}")
            else:
                st.warning("請填寫股票代碼、買入價和股數")
    
    # Tab 2: 交易記錄列表
    with tab2:
        st.subheader("📋 交易記錄列表")
        
        records = load_trade_records()
        
        if not records:
            st.info("暫無交易記錄，請在「新增交易記錄」頁面添加")
        else:
            col1, col2, col3 = st.columns(3)
            with col1:
                filter_market = st.selectbox("篩選市場", ["全部", "🇭🇰 港股", "🇺🇸 美股"], key="filter_market")
            with col2:
                filter_code = st.text_input("篩選股票代碼", placeholder="例如: 00700", key="filter_code")
            with col3:
                sort_by = st.selectbox("排序方式", ["日期（新到舊）", "日期（舊到新）"], key="sort_by")
            
            filtered = records
            if filter_market != "全部":
                filtered = [r for r in filtered if r.get('market') == filter_market]
            if filter_code:
                filtered = [r for r in filtered if filter_code.upper() in r.get('stock_code', '').upper()]
            
            if sort_by == "日期（新到舊）":
                filtered.sort(key=lambda x: x.get('trade_date', ''), reverse=True)
            else:
                filtered.sort(key=lambda x: x.get('trade_date', ''))
            
            total_profit = 0
            win_count = 0
            total_trades = 0
            
            for r in filtered:
                if r.get('sell_price') is not None:
                    total_trades += 1
                    if r.get('market') == '🇭🇰 港股':
                        profit = r.get('fee_result', {}).get('net_profit', 0)
                    else:
                        profit = r.get('fee_result', {}).get('net_profit_usd', 0)
                    total_profit += profit
                    if profit > 0:
                        win_count += 1
            
            win_rate = win_count / total_trades * 100 if total_trades > 0 else 0
            
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("📊 篩選後交易數", len(filtered))
            with col2:
                st.metric("💰 總利潤", f"${total_profit:,.2f}")
            with col3:
                st.metric("📈 勝率", f"{win_rate:.1f}%")
            with col4:
                st.metric("🏆 獲利交易", f"{win_count}/{total_trades}")
            
            st.divider()
            
            for i, record in enumerate(filtered):
                market = record.get('market', '🇭🇰 港股')
                fee = record.get('fee_result', {})
                
                if market == '🇭🇰 港股':
                    profit = fee.get('net_profit', 0)
                    currency_symbol = "HK$"
                else:
                    profit = fee.get('net_profit_usd', 0)
                    currency_symbol = "$"
                
                profit_color = "🟢" if profit > 0 else "🔴" if profit < 0 else "⚪"
                
                with st.expander(f"📊 {record.get('trade_date', '')} - {record.get('stock_code', '')} {record.get('stock_name', '')} ({market})"):
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.write(f"**買入價**: ${record.get('buy_price', 0):.3f}")
                        if record.get('sell_price'):
                            st.write(f"**賣出價**: ${record.get('sell_price', 0):.3f}")
                        else:
                            st.write("**賣出價**: 未賣出")
                        st.write(f"**股數**: {record.get('shares', 0):,}")
                    
                    with col2:
                        if market == '🇭🇰 港股':
                            st.write(f"**買入金額**: {currency_symbol}{fee.get('buy_amount', 0):,.2f}")
                            if record.get('sell_price'):
                                st.write(f"**賣出金額**: {currency_symbol}{fee.get('sell_amount', 0):,.2f}")
                                st.write(f"**總費用**: {currency_symbol}{fee.get('total_fees', 0):.2f}")
                        else:
                            st.write(f"**買入金額**: {currency_symbol}{fee.get('buy_amount_usd', 0):,.2f}")
                            if record.get('sell_price'):
                                st.write(f"**賣出金額**: {currency_symbol}{fee.get('sell_amount_usd', 0):,.2f}")
                                st.write(f"**總費用**: {currency_symbol}{fee.get('total_fees_usd', 0):.2f}")
                    
                    with col3:
                        st.write(f"**毛利**: {currency_symbol}{fee.get('gross_profit_usd' if market == '🇺🇸 美股' else 'gross_profit', 0):,.2f}")
                        st.write(f"**{profit_color} 淨利潤**: {currency_symbol}{profit:,.2f}")
                        st.write(f"**評分**: {record.get('rating', '⭐⭐⭐')}")
                    
                    if record.get('review'):
                        st.markdown("**📝 檢討內容**")
                        st.info(record.get('review'))
                    if record.get('lesson'):
                        st.markdown(f"**💡 學到的教訓**: {record.get('lesson')}")
                    
                    if st.button("🗑️ 刪除", key=f"del_{record.get('id')}"):
                        records = [r for r in records if r.get('id') != record.get('id')]
                        save_trade_records(records)
                        st.rerun()
    
    # Tab 3: 買入前檢查清單
    with tab3:
        st.subheader("✅ 12項買入前檢查清單")
        st.caption("買入股票前，逐項確認，確保符合條件")
        
        checklist_stock = st.text_input("股票代碼", placeholder="例如: 00700", key="checklist_stock")
        
        checklist_status = load_checklist_status()
        
        for item in checklist_items:
            col1, col2, col3 = st.columns([3, 2, 1])
            with col1:
                st.write(f"**{item['id']}. {item['name']}**")
                st.caption(item['standard'])
            with col2:
                status_key = f"{checklist_stock}_{item['id']}" if checklist_stock else str(item['id'])
                current_status = checklist_status.get(status_key, False)
                new_status = st.checkbox("✅ 符合", value=current_status, key=f"check_{item['id']}_{checklist_stock}")
                if new_status != current_status:
                    checklist_status[status_key] = new_status
                    save_checklist_status(checklist_status)
            with col3:
                if new_status:
                    st.markdown("✅ 通過")
                else:
                    st.markdown("❌ 未確認")
        
        checked_count = sum(1 for k, v in checklist_status.items() if v and (checklist_stock in k or not checklist_stock))
        total_items = len(checklist_items)
        
        st.divider()
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("✅ 通過項目", f"{checked_count}/{total_items}")
        with col2:
            if checked_count == total_items:
                st.success("🔴 強烈買入 - 12項全部滿足")
            elif checked_count >= total_items - 1:
                st.warning("🟡 可考慮買入 - 缺1項，小注試單")
            else:
                st.error("🟢 觀望 - 10項或以下滿足，不買入")
        with col3:
            if checked_count == total_items:
                st.info("💰 建議倉位: 15-20% 本金")
            elif checked_count >= total_items - 1:
                st.info("💰 建議倉位: 5-10% 本金")
            else:
                st.info("💰 建議倉位: 0%")
        
        if st.button("🔄 重置所有檢查項目", use_container_width=True):
            save_checklist_status({})
            st.rerun()
    
    # Tab 4: 績效統計
    with tab4:
        st.subheader("📈 交易績效統計")
        
        records = load_trade_records()
        closed_trades = [r for r in records if r.get('sell_price') is not None and r.get('sell_price') > 0]
        
        if not closed_trades:
            st.info("暫無已完成交易記錄")
        else:
            hkd_trades = [r for r in closed_trades if r.get('market') == '🇭🇰 港股']
            usd_trades = [r for r in closed_trades if r.get('market') == '🇺🇸 美股']
            
            hkd_profit = sum(r.get('fee_result', {}).get('net_profit', 0) for r in hkd_trades)
            usd_profit = sum(r.get('fee_result', {}).get('net_profit_usd', 0) for r in usd_trades)
            
            hkd_wins = len([r for r in hkd_trades if r.get('fee_result', {}).get('net_profit', 0) > 0])
            usd_wins = len([r for r in usd_trades if r.get('fee_result', {}).get('net_profit_usd', 0) > 0])
            
            col1, col2 = st.columns(2)
            with col1:
                st.subheader("🇭🇰 港股績效")
                st.metric("總交易次數", len(hkd_trades))
                st.metric("總利潤", f"HK${hkd_profit:,.2f}")
                st.metric("獲利交易", f"{hkd_wins}/{len(hkd_trades)}")
            
            with col2:
                st.subheader("🇺🇸 美股績效")
                st.metric("總交易次數", len(usd_trades))
                st.metric("總利潤", f"${usd_profit:,.2f}")
                st.metric("獲利交易", f"{usd_wins}/{len(usd_trades)}")
            
            st.divider()
            
            total_profit_hkd = hkd_profit + (usd_profit * 7.8)
            st.subheader("📊 總體績效（港幣計價）")
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("總交易次數", len(closed_trades))
            with col2:
                st.metric("總利潤", f"HK${total_profit_hkd:,.2f}")
            with col3:
                st.metric("總獲利交易", f"{hkd_wins + usd_wins}/{len(closed_trades)}")
            with col4:
                st.metric("總勝率", f"{(hkd_wins + usd_wins) / len(closed_trades) * 100:.1f}%")

# 7. 股價提醒頁面（完整版）
elif st.session_state.page == "🔔 股價提醒":
    st.markdown("""
    <div style="text-align:center; padding:1rem; background:linear-gradient(135deg,#667eea,#764ba2); border-radius:10px; margin-bottom:2rem">
        <h1 style="color:white">🔔 股價提醒</h1>
        <p style="color:rgba(255,255,255,0.8)">設定目標價，當股價觸發時自動通知</p>
    </div>
    """, unsafe_allow_html=True)
    
    triggered_alerts = check_price_alerts()
    if triggered_alerts:
        for alert in triggered_alerts:
            st.warning(f"🔔 {alert['name']} ({alert['code']}) 已觸發！當前股價 ${alert['current_price']:.2f}，目標價 ${alert['target_price']:.2f}")
    else:
        st.info("暫無觸發的提醒")
    
    st.divider()
    
    st.subheader("➕ 新增提醒")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        alert_code = st.text_input("股票代碼", placeholder="例如: 00700", key="alert_code")
    with col2:
        alert_type = st.selectbox("提醒類型", ["above", "below"], format_func=lambda x: "高於目標價" if x == "above" else "低於目標價", key="alert_type")
    with col3:
        alert_price = st.number_input("目標價 (港元)", value=None, step=0.1, format="%.2f", placeholder="請輸入目標價", key="alert_price")
    with col4:
        if st.button("➕ 添加提醒", use_container_width=True, type="primary"):
            if alert_code and alert_price and alert_price > 0:
                success, name, _, _, _ = auto_fetch_and_fill(alert_code)
                if success:
                    add_alert(normalize_code(alert_code), name, alert_type, alert_price)
                    st.success(f"✅ 已添加 {name} 的股價提醒")
                    st.rerun()
                else:
                    add_alert(normalize_code(alert_code), alert_code, alert_type, alert_price)
                    st.success(f"✅ 已添加 {alert_code} 的股價提醒")
                    st.rerun()
            else:
                st.warning("請填寫完整資料")
    
    st.divider()
    
    st.subheader("📋 當前提醒列表")
    alerts = load_alerts()
    if alerts:
        for i, alert in enumerate(alerts):
            col1, col2, col3, col4, col5 = st.columns([2, 2, 2, 2, 1])
            with col1:
                st.write(f"**{alert['code']}**")
            with col2:
                st.write(alert.get('name', alert['code']))
            with col3:
                type_text = "高於" if alert['type'] == 'above' else "低於"
                st.write(f"{type_text} ${alert['target_price']:.2f}")
            with col4:
                status = "✅ 已觸發" if alert.get('triggered', False) else "⏳ 監控中"
                st.write(status)
            with col5:
                if st.button("🗑️", key=f"del_alert_{i}"):
                    remove_alert(i)
                    st.rerun()
    else:
        st.info("暫無股價提醒")

# 8. 歷史回測頁面（完整版）
elif st.session_state.page == "📈 歷史回測":
    st.markdown("""
    <div style="text-align:center; padding:1rem; background:linear-gradient(135deg,#667eea,#764ba2); border-radius:10px; margin-bottom:2rem">
        <h1 style="color:white">📈 歷史回測</h1>
        <p style="color:rgba(255,255,255,0.8)">驗證你的 5 項條件策略在過去的表現</p>
    </div>
    """, unsafe_allow_html=True)
    
    st.info("""
    **回測邏輯說明：**
    - **買入條件**：5 項條件全部滿足（股價 > MA20 + RSI14 > 50 + MACD 金叉 + 成交額 > 0.3億 + 乖離率 -4%~+5%）
    - **賣出條件**：股價跌破 MA20
    - **初始資金**：100,000 港元（全倉買入/賣出）
    """)
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        backtest_code = st.text_input("股票代碼", placeholder="例如: 00700", key="backtest_code")
    with col2:
        start_date = st.date_input("開始日期", value=datetime.now() - timedelta(days=365), key="start_date")
    with col3:
        end_date = st.date_input("結束日期", value=datetime.now(), key="end_date")
    with col4:
        if st.button("🚀 開始回測", type="primary", use_container_width=True):
            if backtest_code:
                with st.spinner("正在進行回測..."):
                    buy_conditions = SCREENING_CONFIG.copy()
                    result, df, signals = run_backtest(
                        normalize_code(backtest_code), 
                        buy_conditions, 
                        start_date.strftime('%Y-%m-%d'), 
                        end_date.strftime('%Y-%m-%d')
                    )
                    if result:
                        st.success(f"✅ 回測完成！")
                        col1, col2, col3, col4, col5 = st.columns(5)
                        with col1:
                            st.metric("總回報", f"${result['total_return']:+,.2f}")
                        with col2:
                            st.metric("總回報率", f"{result['total_return_pct']:+.2f}%")
                        with col3:
                            st.metric("勝率", f"{result['win_rate']:.1f}%")
                        with col4:
                            st.metric("交易次數", result['num_trades'])
                        with col5:
                            st.metric("最終資金", f"${result['final_capital']:,.2f}")
                        
                        if result['trades']:
                            st.subheader("📋 交易記錄")
                            trades_df = pd.DataFrame(result['trades'])
                            st.dataframe(trades_df, use_container_width=True)
                    else:
                        st.warning("回測失敗，請檢查股票代碼或日期範圍")
            else:
                st.warning("請輸入股票代碼")

# 9. 板塊資金流向頁面（完整版）
elif st.session_state.page == "💰 板塊資金流向":
    st.markdown("""
    <div style="text-align:center; padding:1rem; background:linear-gradient(135deg,#667eea,#764ba2); border-radius:10px; margin-bottom:2rem">
        <h1 style="color:white">💰 板塊資金流向</h1>
        <p style="color:rgba(255,255,255,0.8)">找出市場熱點板塊</p>
    </div>
    """, unsafe_allow_html=True)
    
    if st.button("🔄 更新數據", use_container_width=True):
        with st.spinner("正在獲取板塊資金流向..."):
            sector_flow = get_sector_flow()
            if sector_flow:
                st.session_state.sector_flow = sector_flow
                st.success("✅ 數據已更新")
            else:
                st.error("獲取數據失敗")
    
    if 'sector_flow' in st.session_state and st.session_state.sector_flow:
        sector_flow = st.session_state.sector_flow
        sorted_sectors = sorted(sector_flow.items(), key=lambda x: x[1]['turnover'], reverse=True)
        
        st.subheader("📊 板塊成交額排名")
        sector_data = []
        for sector, data in sorted_sectors:
            sector_data.append({
                '板塊': sector,
                '成交額(億)': round(data['turnover'], 2),
                '平均漲跌幅': f"{data['avg_change']:+.2f}%",
                '股票數量': data['count']
            })
        df_sector = pd.DataFrame(sector_data)
        st.dataframe(df_sector, use_container_width=True, hide_index=True)
        
        fig = px.bar(df_sector, x='板塊', y='成交額(億)', title='板塊成交額分佈', color='平均漲跌幅', color_continuous_scale='RdYlGn')
        st.plotly_chart(fig, use_container_width=True)
        
        st.subheader("📈 各板塊領漲股")
        for sector, data in sorted_sectors[:5]:
            with st.expander(f"🔥 {sector} - 成交額 {data['turnover']:.2f}億 | 平均漲跌 {data['avg_change']:+.2f}%"):
                for stock in data['stocks']:
                    color = "🟢" if stock['change'] > 0 else "🔴" if stock['change'] < 0 else "⚪"
                    st.write(f"{color} {stock['code']} - {stock['name']} ({stock['change']:+.2f}%)")
    else:
        st.info("點擊「更新數據」查看板塊資金流向")

# 10. 新聞情緒頁面（完整版）
elif st.session_state.page == "📰 新聞情緒":
    st.markdown("""
    <div style="text-align:center; padding:1rem; background:linear-gradient(135deg,#667eea,#764ba2); border-radius:10px; margin-bottom:2rem">
        <h1 style="color:white">📰 新聞情緒分析</h1>
        <p style="color:rgba(255,255,255,0.8)">分析市場對股票的看法（支援多新聞 API）</p>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2 = st.columns([3, 1])
    with col1:
        news_keyword = st.text_input("股票代碼或名稱", placeholder="例如: 00700 或 騰訊", key="news_keyword")
    with col2:
        if st.button("🔍 分析情緒", type="primary", use_container_width=True):
            if news_keyword:
                with st.spinner("正在分析新聞情緒..."):
                    sentiment_result = get_news_sentiment(news_keyword)
                    if sentiment_result:
                        st.session_state.sentiment_result = sentiment_result
                        st.session_state.sentiment_keyword = news_keyword
                        st.success("✅ 分析完成")
                    else:
                        st.error("分析失敗")
            else:
                st.warning("請輸入股票代碼或名稱")
    
    if 'sentiment_result' in st.session_state:
        result = st.session_state.sentiment_result
        keyword = st.session_state.sentiment_keyword
        
        st.subheader(f"📊 {keyword} 情緒分析結果")
        st.caption(f"📡 新聞來源: {result.get('api_source', 'unknown')}")
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            sentiment_color = "🟢" if result['sentiment_label'] == "正面" else "🔴" if result['sentiment_label'] == "負面" else "🟡"
            st.metric("整體情緒", f"{sentiment_color} {result['sentiment_label']}")
        with col2:
            st.metric("正面新聞", result['positive_count'])
        with col3:
            st.metric("中性新聞", result['neutral_count'])
        with col4:
            st.metric("負面新聞", result['negative_count'])
        
        st.subheader("📰 相關新聞")
        for news in result['news']:
            sentiment_icon = "🟢" if news['sentiment'] == 'positive' else "🔴" if news['sentiment'] == 'negative' else "🟡"
            with st.expander(f"{sentiment_icon} {news['title']} - {news['source']} ({news['time']})"):
                if news.get('description'):
                    st.write(f"摘要: {news['description']}")
                st.write(f"情緒: {news['sentiment']}")
                st.write(f"來源: {news['source']}")
                st.caption(f"時間: {news['time']}")
                if news.get('url') and news['url'] != '#':
                    st.write(f"連結: {news['url']}")
    else:
        st.info("輸入股票代碼或名稱，點擊「分析情緒」查看新聞情緒")

# 11. 搜索歷史頁面
elif st.session_state.page == "📜 搜索歷史":
    st.markdown("# 📜 搜索歷史")
    if not st.session_state.search_history:
        st.info("暫無搜索記錄")
    else:
        for h in st.session_state.search_history[-20:]:
            st.write(f"{h['code']} - {h['time']}")

# 12. 數據匯入頁面
elif st.session_state.page == "📎 數據匯入":
    st.markdown("# 📎 數據匯入")
    with st.expander("📥 下載 Excel 模板"):
        template_data = {
            '股票代碼': ['00700'],
            '股票名稱': ['騰訊控股'],
            '股價': [508.50],
            '成交量(萬股)': [2932.12],
            '成交額(億)': [14.92],
            'MA10': [505.20], 'MA20': [502.80], 'MA50': [495.30], 'MA60': [493.10], 'MA250': [450.20],
            'BOLL中軌': [502.80], 'BOLL上軌': [525.60], 'BOLL下軌': [480.00],
            'RSI(6)': [62.5], 'RSI(14)': [58.3], 'RSI(24)': [55.2],
            'MACD DIF': [1.234], 'MACD DEA': [1.123],
            'KDJ_K': [75.2], 'KDJ_D': [72.5], 'KDJ_J': [80.6],
        }
        template_df = pd.DataFrame(template_data)
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            template_df.to_excel(writer, sheet_name='股票分析', index=False)
        st.download_button("📎 下載模板", data=output.getvalue(), file_name="港股分析模板.xlsx")
    
    f = st.file_uploader("上傳 Excel", type=["xlsx", "csv"])
    if f:
        df = pd.read_excel(f)
        st.success(f"✅ 成功讀取 {len(df)} 行數據")
        st.dataframe(df)
        if st.button("📥 自動填入數據"):
            row = df.iloc[0]
            st.session_state.hk_stock_name = str(row.get('股票名稱', ''))
            st.session_state.hk_stock_price = float(row.get('股價', 0))
            st.session_state.hk_stock_volume = int(float(row.get('成交量(萬股)', 0)) * 10000)
            st.session_state.hk_stock_turnover = float(row.get('成交額(億)', 0))
            st.session_state.ma10 = str(row.get('MA10', ''))
            st.session_state.ma20 = str(row.get('MA20', ''))
            st.session_state.ma50 = str(row.get('MA50', ''))
            st.session_state.ma60 = str(row.get('MA60', ''))
            st.session_state.ma250 = str(row.get('MA250', ''))
            st.session_state.boll_mid = str(row.get('BOLL中軌', ''))
            st.session_state.boll_upper = str(row.get('BOLL上軌', ''))
            st.session_state.boll_lower = str(row.get('BOLL下軌', ''))
            st.session_state.rsi6 = str(row.get('RSI(6)', ''))
            st.session_state.rsi14 = str(row.get('RSI(14)', ''))
            st.session_state.rsi24 = str(row.get('RSI(24)', ''))
            st.session_state.macd_dif = str(row.get('MACD DIF', ''))
            st.session_state.macd_dea = str(row.get('MACD DEA', ''))
            st.session_state.kdj_k = str(row.get('KDJ_K', ''))
            st.session_state.kdj_d = str(row.get('KDJ_D', ''))
            st.session_state.kdj_j = str(row.get('KDJ_J', ''))
            st.success("✅ 已自動填入數據！")
            st.rerun()

# 13. 圖表分析頁面
elif st.session_state.page == "📊 圖表分析":
    st.markdown("# 📊 圖表分析")
    if not st.session_state.current_stock:
        st.info("請先到「港股分析」頁面查詢股票")
    elif st.session_state.chart_data is None:
        st.info("正在加載圖表數據，請稍後...")
        if st.button("🔄 重新加載"):
            with st.spinner("正在加載圖表數據..."):
                st.session_state.chart_data = data_source_manager.get_hk_chart_data(st.session_state.current_stock)
                st.rerun()
    else:
        df = st.session_state.chart_data
        stock_name = st.session_state.hk_stock_name or st.session_state.current_stock
        fig = make_subplots(rows=4, cols=1, shared_xaxes=True, vertical_spacing=0.05, row_heights=[0.5, 0.2, 0.15, 0.15],
                           subplot_titles=("K線圖 + MA + BOLL", "成交量", "MACD", "KDJ"))
        fig.add_trace(go.Candlestick(x=df['date'], open=df['open'], high=df['high'], low=df['low'], close=df['close'], name='K線'), row=1, col=1)
        fig.add_trace(go.Scatter(x=df['date'], y=df['MA10'], name='MA10', line=dict(color='orange', width=1)), row=1, col=1)
        fig.add_trace(go.Scatter(x=df['date'], y=df['MA20'], name='MA20', line=dict(color='red', width=1)), row=1, col=1)
        fig.add_trace(go.Scatter(x=df['date'], y=df['MA50'], name='MA50', line=dict(color='purple', width=1)), row=1, col=1)
        fig.add_trace(go.Scatter(x=df['date'], y=df['MA60'], name='MA60', line=dict(color='brown', width=1)), row=1, col=1)
        fig.add_trace(go.Scatter(x=df['date'], y=df['MA250'], name='MA250', line=dict(color='gray', width=1)), row=1, col=1)
        fig.add_trace(go.Scatter(x=df['date'], y=df['BOLL_UPPER'], name='BOLL上軌', line=dict(color='gray', width=1, dash='dash')), row=1, col=1)
        fig.add_trace(go.Scatter(x=df['date'], y=df['BOLL_MID'], name='BOLL中軌', line=dict(color='blue', width=1)), row=1, col=1)
        fig.add_trace(go.Scatter(x=df['date'], y=df['BOLL_LOWER'], name='BOLL下軌', line=dict(color='gray', width=1, dash='dash')), row=1, col=1)
        colors = ['red' if close < open else 'green' for close, open in zip(df['close'], df['open'])]
        fig.add_trace(go.Bar(x=df['date'], y=df['volume'], name='成交量', marker_color=colors), row=2, col=1)
        fig.add_trace(go.Bar(x=df['date'], y=df['MACD_HIST'], name='MACD柱', marker_color='gray'), row=3, col=1)
        fig.add_trace(go.Scatter(x=df['date'], y=df['MACD_DIF'], name='DIF', line=dict(color='blue', width=1)), row=3, col=1)
        fig.add_trace(go.Scatter(x=df['date'], y=df['MACD_DEA'], name='DEA', line=dict(color='red', width=1)), row=3, col=1)
        fig.add_trace(go.Scatter(x=df['date'], y=df['KDJ_K'], name='K', line=dict(color='blue', width=1)), row=4, col=1)
        fig.add_trace(go.Scatter(x=df['date'], y=df['KDJ_D'], name='D', line=dict(color='orange', width=1)), row=4, col=1)
        fig.add_trace(go.Scatter(x=df['date'], y=df['KDJ_J'], name='J', line=dict(color='purple', width=1)), row=4, col=1)
        fig.add_hline(y=80, line_dash="dash", line_color="red", row=4, col=1, annotation_text="超買")
        fig.add_hline(y=20, line_dash="dash", line_color="green", row=4, col=1, annotation_text="超賣")
        fig.update_layout(title=f"{stock_name} - 技術分析圖表", template="plotly_dark", height=900, showlegend=True)
        st.plotly_chart(fig, use_container_width=True)

# 14. 每日選股頁面（完整版）
elif st.session_state.page == "🎯 每日選股":
    st.markdown("""
    <div style="text-align:center; padding:1rem; background:linear-gradient(135deg,#667eea,#764ba2); border-radius:10px; margin-bottom:2rem">
        <h1 style="color:white">🎯 每日選股系統</h1>
        <p style="color:rgba(255,255,255,0.8)">技術面 + 成交額放大 + 北水資金 + 主流板塊 + 市場寬度過濾</p>
    </div>
    """, unsafe_allow_html=True)
    
    st.subheader("📊 當前市場寬度")
    
    @st.cache_data(ttl=3600)
    def get_cached_breadth():
        return calculate_market_breadth()
    
    breadth = get_cached_breadth()
    
    if breadth:
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("MA20 市場寬度", f"{breadth['ma20_breadth']}%")
        with col2:
            st.metric("MA50 市場寬度", f"{breadth['ma50_breadth']}%")
        with col3:
            st.metric("市場狀態", breadth['status'])
        
        if breadth['level'] == 'strong':
            st.success(f"💡 操作建議: {breadth['suggestion']}")
        elif breadth['level'] == 'normal':
            st.info(f"💡 操作建議: {breadth['suggestion']}")
        elif breadth['level'] == 'weak':
            st.warning(f"💡 操作建議: {breadth['suggestion']}")
        else:
            st.error(f"💡 操作建議: {breadth['suggestion']}")
        
        st.caption(f"📊 分析樣本: {breadth['total_analyzed']} 隻有流動性股票")
        
        if breadth['level'] == 'bear':
            st.warning("⚠️ 市場處於熊市，系統已暫停選股功能")
            st.info("建議：保持現金，等待市場轉強後再進行選股")
            st.stop()
    else:
        st.info("無法獲取市場寬度數據，將直接進行選股")
    
    st.divider()
    
    if st.button("🚀 開始每日選股", type="primary", use_container_width=True):
        progress_bar = st.progress(0)
        status_text = st.empty()
        results_df = run_screening(progress_bar, status_text)
        if not results_df.empty:
            st.session_state.screening_results = results_df
            st.success(f"✅ 從全市場篩選出 {len(results_df)} 隻精選股票")
        else:
            st.warning("今日沒有符合條件的股票")
    
    if st.session_state.screening_results is not None and not st.session_state.screening_results.empty:
        df = st.session_state.screening_results
        
        st.subheader("🔍 二次篩選")
        col_f1, col_f2, col_f3 = st.columns(3)
        with col_f1:
            filter_breakout = st.checkbox("只顯示「突破買🔥」信號")
        with col_f2:
            min_score = st.slider("最低總分", min_value=0, max_value=50, value=10)
        with col_f3:
            if '板塊' in df.columns:
                sectors = df['板塊'].unique().tolist()
                filter_sector = st.multiselect("選擇板塊", options=sectors)
        
        filtered_df = df.copy()
        if filter_breakout and '突破買' in filtered_df.columns:
            filtered_df = filtered_df[filtered_df['突破買'] == '🔥']
        filtered_df = filtered_df[filtered_df['總分'] >= min_score]
        if filter_sector and '板塊' in df.columns:
            filtered_df = filtered_df[filtered_df['板塊'].isin(filter_sector)]
        
        st.subheader(f"📋 選股結果 (共 {len(filtered_df)} 隻)")
        st.dataframe(filtered_df, use_container_width=True)
        
        csv = filtered_df.to_csv(index=False).encode('utf-8-sig')
        st.download_button("📎 下載 CSV", data=csv, file_name=f"每日選股_{datetime.now().strftime('%Y%m%d_%H%M')}.csv", mime="text/csv")

# 15. 交易計算器頁面（完整版）
elif st.session_state.page == "🧮 交易計算器":
    st.markdown("""
    <div style="text-align:center; padding:1rem; background:linear-gradient(135deg,#667eea,#764ba2); border-radius:10px; margin-bottom:2rem">
        <h1 style="color:white">🧮 交易計算器</h1>
        <p style="color:rgba(255,255,255,0.8)">富途標準費用 | 港股 + 美股 | 單筆交易 | 分批買入平均成本</p>
    </div>
    """, unsafe_allow_html=True)
    
    market = st.radio("選擇市場", ["🇭🇰 港股", "🇺🇸 美股"], horizontal=True)
    tab1, tab2 = st.tabs(["📊 單筆交易計算", "📋 分批買入平均成本"])
    
    with tab1:
        st.subheader("📊 富途費用設定")
        
        if market == "🇭🇰 港股":
            col1, col2, col3 = st.columns(3)
            with col1:
                commission_rate = st.number_input("佣金率 (%)", value=0.03, step=0.01, format="%.2f")
                min_commission = st.number_input("最低佣金 (港元)", value=3.0, step=0.5, format="%.2f")
            with col2:
                stamp_duty_rate = st.number_input("印花稅率 (%)", value=0.13, step=0.01, format="%.2f")
                trading_fee_rate = st.number_input("交易徵費率 (%)", value=0.0027, step=0.0001, format="%.4f")
            with col3:
                settlement_fee = st.number_input("結算費 (港元)", value=2.0, step=0.5, format="%.2f")
                platform_fee = st.number_input("平台使用費 (港元)", value=15.0, step=1.0, format="%.2f")
            st.caption("💡 富途港股交易費用：佣金 0.03% (最低 3 港元) + 平台費 15 港元 + 印花稅 0.13% + 交易徵費 0.0027% + 結算費 2 港元")
            currency = "港元"
            currency_symbol = "$"
        else:
            col1, col2, col3 = st.columns(3)
            with col1:
                commission_per_share = st.number_input("佣金 (每股美元)", value=0.0049, step=0.0001, format="%.4f")
                min_commission = st.number_input("最低佣金 (美元)", value=0.99, step=0.01, format="%.2f")
            with col2:
                platform_per_share = st.number_input("平台使用費 (每股美元)", value=0.005, step=0.0001, format="%.4f")
                min_platform = st.number_input("最低平台費 (美元)", value=1.0, step=0.1, format="%.2f")
            with col3:
                settlement_per_share = st.number_input("交收費 (每股美元)", value=0.003, step=0.0001, format="%.4f")
                st.info("💡 美股賣出時另收 SEC 規費 (0.0000278%) 及 TAF (0.000166/股，最低0.01)")
            st.caption("💡 富途美股交易費用：佣金 0.0049/股 (最低0.99) + 平台費 0.005/股 (最低1) + 交收費 0.003/股")
            currency = "美元"
            currency_symbol = "$"
        
        st.divider()
        st.subheader("📝 基本交易資料")
        
        if market == "🇭🇰 港股":
            col1, col2 = st.columns(2)
            with col1:
                buy_price = st.number_input(f"買入價 ({currency})", value=None, step=0.1, format="%.3f", placeholder="請輸入買入價")
                shares = st.number_input("股數", value=None, step=100, placeholder="請輸入股數")
            with col2:
                sell_price = st.number_input(f"賣出價 ({currency})", value=None, step=0.1, format="%.3f", placeholder="請輸入賣出價")
        else:
            col1, col2 = st.columns(2)
            with col1:
                buy_price = st.number_input(f"買入價 (美元)", value=None, step=0.1, format="%.3f", placeholder="請輸入買入價")
                shares = st.number_input("股數", value=None, step=1, placeholder="請輸入股數")
            with col2:
                sell_price = st.number_input(f"賣出價 (美元)", value=None, step=0.1, format="%.3f", placeholder="請輸入賣出價")
        
        if buy_price and buy_price > 0 and shares and shares > 0:
            if market == "🇭🇰 港股":
                buy_amount = buy_price * shares
                buy_commission = max(buy_amount * commission_rate / 100, min_commission)
                buy_stamp_duty = buy_amount * stamp_duty_rate / 100
                buy_trading_fee = buy_amount * trading_fee_rate / 100
                buy_total = buy_amount + buy_commission + buy_stamp_duty + buy_trading_fee + settlement_fee + platform_fee
                
                def calc_breakeven(sell_price):
                    sell_amount = sell_price * shares
                    sell_commission = max(sell_amount * commission_rate / 100, min_commission)
                    sell_stamp_duty = sell_amount * stamp_duty_rate / 100
                    sell_trading_fee = sell_amount * trading_fee_rate / 100
                    sell_net = sell_amount - sell_commission - sell_stamp_duty - sell_trading_fee - settlement_fee - platform_fee
                    return sell_net - buy_total
                
                low, high = buy_price * 0.9, buy_price * 1.2
                for _ in range(50):
                    mid = (low + high) / 2
                    if calc_breakeven(mid) < 0:
                        low = mid
                    else:
                        high = mid
                breakeven_price = (low + high) / 2
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("平手價 (打和點)", f"{currency_symbol}{breakeven_price:.3f}")
                    st.caption(f"需賣出高於此價格才能獲利")
                with col2:
                    with st.expander("📋 買入成本詳細"):
                        st.write(f"買入金額: {currency_symbol}{buy_amount:,.2f}")
                        st.write(f"佣金: {currency_symbol}{buy_commission:.2f}")
                        st.write(f"平台費: {currency_symbol}{platform_fee:.2f}")
                        st.write(f"印花稅: {currency_symbol}{buy_stamp_duty:.2f}")
                        st.write(f"交易徵費: {currency_symbol}{buy_trading_fee:.4f}")
                        st.write(f"結算費: {currency_symbol}{settlement_fee:.2f}")
                        st.write(f"**總成本: {currency_symbol}{buy_total:,.2f}**")
            else:
                buy_amount = buy_price * shares
                buy_commission = max(shares * commission_per_share, min_commission)
                buy_platform = max(shares * platform_per_share, min_platform)
                buy_settlement = shares * settlement_per_share
                buy_total = buy_amount + buy_commission + buy_platform + buy_settlement
                
                def calc_breakeven_us(sell_price):
                    sell_amount = sell_price * shares
                    sell_commission = max(shares * commission_per_share, min_commission)
                    sell_platform = max(shares * platform_per_share, min_platform)
                    sell_settlement = shares * settlement_per_share
                    sell_sec_fee = sell_amount * 0.0000278
                    sell_taf = max(shares * 0.000166, 0.01)
                    sell_net = sell_amount - sell_commission - sell_platform - sell_settlement - sell_sec_fee - sell_taf
                    return sell_net - buy_total
                
                low, high = buy_price * 0.9, buy_price * 1.2
                for _ in range(50):
                    mid = (low + high) / 2
                    if calc_breakeven_us(mid) < 0:
                        low = mid
                    else:
                        high = mid
                breakeven_price = (low + high) / 2
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("平手價 (打和點)", f"{currency_symbol}{breakeven_price:.3f}")
                    st.caption(f"需賣出高於此價格才能獲利")
                with col2:
                    with st.expander("📋 買入成本詳細"):
                        st.write(f"買入金額: {currency_symbol}{buy_amount:,.2f}")
                        st.write(f"佣金: {currency_symbol}{buy_commission:.2f}")
                        st.write(f"平台費: {currency_symbol}{buy_platform:.2f}")
                        st.write(f"交收費: {currency_symbol}{buy_settlement:.2f}")
                        st.write(f"**總成本: {currency_symbol}{buy_total:,.2f}**")
        else:
            st.info("請輸入買入價和股數")
        
        st.divider()
        st.subheader("📈 不同賣出價的利潤分析")
        st.caption("設定賣出價範圍，系統會自動計算每個價格的淨利潤")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            sell_price_min = st.number_input(f"最低賣出價 ({currency_symbol})", value=None, step=0.1, format="%.3f", placeholder="例如: 300")
        with col2:
            sell_price_max = st.number_input(f"最高賣出價 ({currency_symbol})", value=None, step=0.1, format="%.3f", placeholder="例如: 350")
        with col3:
            sell_price_step = st.number_input(f"價格間隔 ({currency_symbol})", value=1.0, step=0.5, format="%.1f", placeholder="例如: 5")
        
        if (buy_price and buy_price > 0 and shares and shares > 0 and 
            sell_price_min and sell_price_min > 0 and 
            sell_price_max and sell_price_max > 0 and 
            sell_price_step and sell_price_step > 0):
            
            sell_prices = np.arange(sell_price_min, sell_price_max + sell_price_step, sell_price_step)
            results = []
            
            for sp in sell_prices:
                if market == "🇭🇰 港股":
                    sell_amount = sp * shares
                    sell_commission = max(sell_amount * commission_rate / 100, min_commission)
                    sell_stamp_duty = sell_amount * stamp_duty_rate / 100
                    sell_trading_fee = sell_amount * trading_fee_rate / 100
                    sell_net = sell_amount - sell_commission - sell_stamp_duty - sell_trading_fee - settlement_fee - platform_fee
                    
                    buy_amount = buy_price * shares
                    buy_commission = max(buy_amount * commission_rate / 100, min_commission)
                    buy_stamp_duty = buy_amount * stamp_duty_rate / 100
                    buy_trading_fee = buy_amount * trading_fee_rate / 100
                    buy_total = buy_amount + buy_commission + buy_stamp_duty + buy_trading_fee + settlement_fee + platform_fee
                    
                    profit = sell_net - buy_total
                    profit_pct = (profit / buy_total) * 100 if buy_total > 0 else 0
                    results.append({
                        '賣出價': round(sp, 3), '賣出金額': round(sell_amount, 2),
                        '佣金': round(sell_commission, 2), '印花稅': round(sell_stamp_duty, 2),
                        '淨利潤': round(profit, 2), '回報率(%)': round(profit_pct, 2)
                    })
                else:
                    sell_amount = sp * shares
                    sell_commission = max(shares * commission_per_share, min_commission)
                    sell_platform = max(shares * platform_per_share, min_platform)
                    sell_settlement = shares * settlement_per_share
                    sell_sec_fee = sell_amount * 0.0000278
                    sell_taf = max(shares * 0.000166, 0.01)
                    sell_net = sell_amount - sell_commission - sell_platform - sell_settlement - sell_sec_fee - sell_taf
                    
                    buy_amount = buy_price * shares
                    buy_commission = max(shares * commission_per_share, min_commission)
                    buy_platform = max(shares * platform_per_share, min_platform)
                    buy_settlement = shares * settlement_per_share
                    buy_total = buy_amount + buy_commission + buy_platform + buy_settlement
                    
                    profit = sell_net - buy_total
                    profit_pct = (profit / buy_total) * 100 if buy_total > 0 else 0
                    results.append({
                        '賣出價': round(sp, 3), '賣出金額': round(sell_amount, 2),
                        '佣金': round(sell_commission, 2), '平台費': round(sell_platform, 2),
                        '交收費': round(sell_settlement, 2), 'SEC規費': round(sell_sec_fee, 4),
                        'TAF': round(sell_taf, 4), '淨利潤': round(profit, 2), '回報率(%)': round(profit_pct, 2)
                    })
            
            df_results = pd.DataFrame(results)
            if market == "🇭🇰 港股":
                st.dataframe(df_results.style.format({'賣出價':'{:.3f}','賣出金額':'{:,.2f}','佣金':'{:.2f}','印花稅':'{:.2f}','淨利潤':'${:.2f}','回報率(%)':'{:.2f}%'}), use_container_width=True, height=400)
            else:
                st.dataframe(df_results.style.format({'賣出價':'{:.3f}','賣出金額':'{:,.2f}','佣金':'{:.2f}','平台費':'{:.2f}','交收費':'{:.2f}','SEC規費':'{:.4f}','TAF':'{:.4f}','淨利潤':'${:.2f}','回報率(%)':'{:.2f}%'}), use_container_width=True, height=400)
            
            col1, col2 = st.columns(2)
            with col1:
                fig1 = px.line(df_results, x='賣出價', y='淨利潤', title='賣出價 vs 淨利潤')
                fig1.add_hline(y=0, line_dash="dash", line_color="red", annotation_text="盈虧平衡")
                fig1.add_vline(x=breakeven_price, line_dash="dash", line_color="green", annotation_text="平手價")
                st.plotly_chart(fig1, use_container_width=True)
            with col2:
                fig2 = px.bar(df_results, x='賣出價', y='回報率(%)', title='賣出價 vs 回報率', color='回報率(%)', color_continuous_scale='RdYlGn')
                fig2.add_hline(y=0, line_dash="dash", line_color="red")
                st.plotly_chart(fig2, use_container_width=True)
            
            st.subheader("📊 總結")
            best = df_results.loc[df_results['淨利潤'].idxmax()]
            worst = df_results.loc[df_results['淨利潤'].idxmin()]
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("最大淨利潤", f"{currency_symbol}{best['淨利潤']:,.2f}", delta=f"@{best['賣出價']:.3f}")
            with col2:
                st.metric("最大虧損", f"{currency_symbol}{worst['淨利潤']:,.2f}", delta=f"@{worst['賣出價']:.3f}", delta_color="inverse")
            with col3:
                st.metric("最高回報率", f"{best['回報率(%)']:.2f}%", delta=f"@{best['賣出價']:.3f}")
            with col4:
                st.metric("最低回報率", f"{worst['回報率(%)']:.2f}%", delta=f"@{worst['賣出價']:.3f}", delta_color="inverse")
            
            csv = df_results.to_csv(index=False).encode('utf-8-sig')
            st.download_button("📎 下載利潤分析 (CSV)", data=csv, file_name=f"利潤分析_{market.replace('🇭🇰 ','').replace('🇺🇸 ','')}_{datetime.now().strftime('%Y%m%d_%H%M')}.csv", mime="text/csv")
    
    with tab2:
        st.subheader("📋 分批買入平均成本計算")
        st.caption("記錄多次買入，自動計算平均成本、總持股、總成本")
        batch_currency = "港元" if market == "🇭🇰 港股" else "美元"
        batch_symbol = "$"
        
        if 'batch_purchases' not in st.session_state:
            st.session_state.batch_purchases = []
        
        with st.expander("➕ 添加買入記錄", expanded=True):
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                batch_price = st.number_input(f"買入價 ({batch_currency})", value=None, step=0.1, format="%.3f", key="batch_price", placeholder=f"請輸入買入價")
            with col2:
                batch_shares = st.number_input("股數", value=None, step=100, key="batch_shares", placeholder="請輸入股數")
            with col3:
                batch_date = st.date_input("日期", value=datetime.now().date(), key="batch_date")
            with col4:
                batch_note = st.text_input("備註", placeholder="例如: 第一筆", key="batch_note")
            
            col1, col2 = st.columns(2)
            with col1:
                if st.button("➕ 加入列表", use_container_width=True):
                    if batch_price and batch_price > 0 and batch_shares and batch_shares > 0:
                        st.session_state.batch_purchases.append({
                            'price': batch_price, 'shares': batch_shares,
                            'date': batch_date.strftime('%Y-%m-%d'),
                            'note': batch_note if batch_note else f"買入 {len(st.session_state.batch_purchases)+1}"
                        })
                        st.success("✅ 已加入")
                        st.rerun()
                    else:
                        st.warning("請輸入買入價和股數")
            with col2:
                if st.button("🗑️ 清空列表", use_container_width=True):
                    st.session_state.batch_purchases = []
                    st.rerun()
        
        if st.session_state.batch_purchases:
            st.subheader("📋 買入記錄")
            df_batch = pd.DataFrame(st.session_state.batch_purchases)
            df_batch['金額'] = df_batch['price'] * df_batch['shares']
            df_batch['序號'] = range(1, len(df_batch) + 1)
            df_batch_display = df_batch[['序號', 'date', 'note', 'price', 'shares', '金額']]
            df_batch_display.columns = ['序號', '日期', '備註', f'買入價({batch_currency})', '股數', '金額']
            st.dataframe(df_batch_display, use_container_width=True)
            
            total_shares = sum(item['shares'] for item in st.session_state.batch_purchases)
            total_cost = sum(item['price'] * item['shares'] for item in st.session_state.batch_purchases)
            avg_price = total_cost / total_shares if total_shares > 0 else 0
            
            st.subheader("📊 平均成本計算結果")
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("總股數", f"{total_shares:,}")
            with col2:
                st.metric("總成本", f"{batch_symbol}{total_cost:,.2f}")
            with col3:
                st.metric("平均成本價", f"{batch_symbol}{avg_price:.3f}")
            with col4:
                current_price_input = st.number_input(f"當前股價 ({batch_currency})", value=None, step=0.1, format="%.3f", key="current_price_input", placeholder="輸入查看盈虧")
            
            if current_price_input and current_price_input > 0:
                current_value = current_price_input * total_shares
                profit = current_value - total_cost
                profit_pct = (profit / total_cost) * 100 if total_cost > 0 else 0
                st.subheader("📈 盈虧分析")
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("當前市值", f"{batch_symbol}{current_value:,.2f}")
                with col2:
                    st.metric("浮動盈虧", f"{batch_symbol}{profit:,.2f}")
                with col3:
                    st.metric("回報率", f"{profit_pct:.2f}%")
            
            st.subheader("🗑️ 刪除記錄")
            col1, col2 = st.columns([2, 1])
            with col1:
                delete_options = [f"{i+1}. {item['date']} - {item['note']} - {batch_symbol}{item['price']} x {item['shares']}股" for i, item in enumerate(st.session_state.batch_purchases)]
                if delete_options:
                    selected_to_delete = st.selectbox("選擇要刪除的記錄", options=range(len(delete_options)), format_func=lambda i: delete_options[i], key="delete_select")
            with col2:
                if st.button("❌ 刪除所選記錄", use_container_width=True):
                    st.session_state.batch_purchases.pop(selected_to_delete)
                    st.success("✅ 已刪除")
                    st.rerun()
            
            col1, col2 = st.columns(2)
            with col1:
                if st.button("📎 導出買入記錄 (CSV)", use_container_width=True):
                    export_df = pd.DataFrame(st.session_state.batch_purchases)
                    export_df['金額'] = export_df['price'] * export_df['shares']
                    csv = export_df.to_csv(index=False).encode('utf-8-sig')
                    st.download_button("下載 CSV", data=csv, file_name=f"買入記錄_{datetime.now().strftime('%Y%m%d')}.csv", mime="text/csv")
            with col2:
                if st.button("🔄 重置所有記錄", use_container_width=True):
                    st.session_state.batch_purchases = []
                    st.rerun()
        else:
            st.info("暫無買入記錄。點擊「添加買入記錄」開始計算平均成本。")

# 16. 設定頁面
elif st.session_state.page == "⚙️ 設定":
    st.markdown("# ⚙️ 設定")
    new_rsi = st.slider("RSI 閾值", 30, 70, SCREENING_CONFIG['rsi_threshold'])
    new_ratio = st.slider("放量倍數", 1.1, 3.0, SCREENING_CONFIG['volume_surge_ratio'], 0.1)
    if st.button("儲存"):
        SCREENING_CONFIG['rsi_threshold'] = new_rsi
        SCREENING_CONFIG['volume_surge_ratio'] = new_ratio
        st.success("已儲存")

# ==================== 🚀 啟動時自動執行每日選股 ====================
def auto_run_screening_on_start():
    try:
        if st.session_state.get('auto_screening_done', False):
            return
        with st.spinner("🤖 正在自動執行每日選股，請稍候..."):
            progress_bar = st.progress(0)
            status_text = st.empty()
            results_df = run_screening(progress_bar, status_text)
            if not results_df.empty:
                st.session_state.screening_results = results_df
                print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] ✅ 自動選股完成，找到 {len(results_df)} 隻股票")
            progress_bar.empty()
            status_text.empty()
            st.session_state.auto_screening_done = True
    except Exception as e:
        print(f"自動選股失敗: {e}")

def show_startup_info():
    print("=" * 60)
    print("📈 港股美股技術分析系統")
    print(f"🚀 啟動時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"📡 當前數據源: {data_source_manager.get_current_source()}")
    print("=" * 60)

def init_app():
    show_startup_info()
    if 'auto_screening_done' not in st.session_state:
        st.session_state.auto_screening_done = False
    if not st.session_state.auto_screening_done:
        import threading
        def delayed():
            import time
            time.sleep(2)
            auto_run_screening_on_start()
        threading.Thread(target=delayed, daemon=True).start()

if 'app_initialized' not in st.session_state:
    st.session_state.app_initialized = True
    init_app()
