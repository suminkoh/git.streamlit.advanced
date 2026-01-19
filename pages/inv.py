import streamlit as st
import FinanceDataReader as fdr
import plotly.graph_objects as go
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# --- 1. 페이지 설정 ---
st.set_page_config(page_title="주식 분석 및 미래 예측", layout="wide")

# --- 2. 데이터 로딩 함수 ---
@st.cache_data
def get_krx_list():
    return fdr.StockListing('KRX')

def get_stock_data(code, start, end):
    return fdr.DataReader(code, start, end)

# --- 3. 사이드바 설정 ---
with st.sidebar:
    st.header("📊 설정 및 시뮬레이션")
    
    df_listing = get_krx_list()
    company_names = df_listing['Name'].tolist()
    
    target_company = st.selectbox("종목 선택", company_names, index=company_names.index("삼성전자") if "삼성전자" in company_names else 0)
    stock_code = df_listing[df_listing['Name'] == target_company]['Code'].values[0]
    
    today = datetime.now()
    one_year_ago = today - timedelta(days=365)
    selected_dates = st.date_input("조회 기간", [one_year_ago, today])
    
    st.write("---")
    st.subheader("💰 과거 투자 시뮬레이션")
    budget = st.number_input("초기 투자 금액 (원)", value=1000000, step=100000)

# --- 4. 메인 로직 ---
if len(selected_dates) == 2:
    start_date, end_date = selected_dates
    price_df = get_stock_data(stock_code, start_date, end_date)
    
    if not price_df.empty:
        price_df = price_df.reset_index()
        current_price = price_df['Close'].iloc[-1]

        # [사이드바: 과거 시뮬레이션 계산]
        with st.sidebar:
            min_date = price_df['Date'].min().to_pydatetime()
            max_date = price_df['Date'].max().to_pydatetime()
            buy_date = st.date_input("매수 날짜 선택", value=min_date, min_value=min_date, max_value=max_date)
            
            buy_price_row = price_df.loc[price_df['Date'].dt.date <= buy_date].iloc[-1]
            buy_price = buy_price_row['Close']
            
            shares = budget / buy_price
            current_value = shares * current_price
            profit = current_value - budget
            roi = (profit / budget) * 100

            st.markdown(f"**현재 가치:** {int(current_value):,}원")
            color = "red" if profit > 0 else "blue"
            st.markdown(f"**수익:** <span style='color:{color}'>{int(profit):,}원 ({roi:.2f}%)</span>", unsafe_allow_html=True)

        # [미래 추세 예측 계산 (단순 선형 회귀)]
        # 날짜를 숫자로 변환하여 추세 계산
        x = np.arange(len(price_df))
        y = price_df['Close'].values
        z = np.polyfit(x, y, 1) # 1차원 추세선 생성
        p = np.poly1d(z)
        
        # 향후 30일 데이터 생성
        future_x = np.arange(len(price_df), len(price_df) + 30)
        future_y = p(future_x)
        future_dates = [price_df['Date'].iloc[-1] + timedelta(days=i) for i in range(1, 31)]

        # [메인 UI 화면]
        st.title(f"📈 {target_company} 분석 리포트")
        
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("현재가", f"{int(current_price):,}원", f"{int(current_price - price_df['Close'].iloc[-2]):,}원")
        col2.metric("기간 내 최고가", f"{int(price_df['Close'].max()):,}원")
        col3.metric("기간 내 최저가", f"{int(price_df['Close'].min()):,}원")
        col4.metric("30일 뒤 예상가", f"{int(future_y[-1]):,}원", f"{((future_y[-1]-current_price)/current_price)*100:.1f}%")

        tab1, tab2, tab3 = st.tabs(["주가 차트", "데이터 내역", "🚀 미래 추세 예측"])
        
        with tab1:
            fig = go.Figure(data=[go.Candlestick(
                x=price_df['Date'], open=price_df['Open'], high=price_df['High'],
                low=price_df['Low'], close=price_df['Close'], name="주가"
            )])
            fig.update_layout(plot_bgcolor='white', xaxis_rangeslider_visible=False)
            st.plotly_chart(fig, use_container_width=True)

        with tab2:
            st.dataframe(price_df.sort_values(by='Date', ascending=False), use_container_width=True)

        with tab3:
            st.subheader("🔮 향후 30일 추세 예측")
            st.write("최근 1년간의 주가 흐름을 바탕으로 계산된 산술적 추세선입니다. (투자 참고용)")
            
            fig_pred = go.Figure()
            # 과거 주가
            fig_pred.add_trace(go.Scatter(x=price_df['Date'], y=price_df['Close'], name="과거 종가", line=dict(color="gray")))
            # 추세선 (미래)
            fig_pred.add_trace(go.Scatter(x=future_dates, y=future_y, name="미래 추세 예측", line=dict(color="red", dash="dash")))
            
            fig_pred.update_layout(plot_bgcolor='white', hovermode='x unified')
            st.plotly_chart(fig_pred, use_container_width=True)
            
            # 예측 기반 매도 시뮬레이션
            sell_date_future = st.slider("미래 매도 시점 선택 (오늘부터 +N일)", 1, 30, 7)
            pred_price_at_date = future_y[sell_date_future-1]
            st.write(f"📅 오늘부터 **{sell_date_future}일 뒤** 예상 주가는 약 **{int(pred_price_at_date):,}원**입니다.")
            
            future_profit = (pred_price_at_date - current_price) * shares
            st.success(f"예상 수익금: {int(future_profit):,}원 (현재 보유량 기준)")

    else:
        st.error("데이터를 불러오지 못했습니다.")