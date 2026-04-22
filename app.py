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
