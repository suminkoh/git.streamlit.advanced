import streamlit as st
import FinanceDataReader as fdr
import plotly.graph_objects as go
import pandas as pd
from datetime import datetime, timedelta

# --- 1. 페이지 설정 ---
st.set_page_config(page_title="주가 조회 및 시뮬레이션", layout="wide")

# --- 2. 데이터 로딩 함수 (캐싱 처리로 속도 향상) ---
@st.cache_data
def get_krx_list():
    """KRX 상장사 리스트 가져오기"""
    return fdr.StockListing('KRX')

def get_stock_data(code, start, end):
    """주가 데이터 가져오기"""
    df = fdr.DataReader(code, start, end)
    return df

# --- 3. 사이드바 구성 ---
with st.sidebar:
    st.header("📊 설정")
    
    # 상장사 리스트 로드
    df_listing = get_krx_list()
    company_names = df_listing['Name'].tolist()
    
    # 종목 선택
    target_company = st.selectbox("종목 선택", company_names, index=company_names.index("삼성전자") if "삼성전자" in company_names else 0)
    stock_code = df_listing[df_listing['Name'] == target_company]['Code'].values[0]
    
    # 날짜 선택
    today = datetime.now()
    one_year_ago = today - timedelta(days=365)
    selected_dates = st.date_input("조회 기간", [one_year_ago, today])
    
    st.write("---")
    st.subheader("💰 투자 시뮬레이션")
    budget = st.number_input("투자 금액 (원)", value=1000000, step=100000)
    
    st.info(f"선택된 종목: {target_company} ({stock_code})")

# --- 4. 메인 로직 ---
if len(selected_dates) == 2:
    start_date, end_date = selected_dates
    
    # 데이터 불러오기
    price_df = get_stock_data(stock_code, start_date, end_date)
    
    if not price_df.empty:
        # 인덱스 초기화 (차트 및 계산용)
        price_df = price_df.reset_index()
        
        # [수익률 계산 로직]
        latest_data = price_df.iloc[-1]
        current_price = latest_data['Close']
        
        # 사이드바에서 시뮬레이션용 날짜 입력
        with st.sidebar:
            min_date = price_df['Date'].min().to_pydatetime()
            max_date = price_df['Date'].max().to_pydatetime()
            buy_date = st.date_input("매수 날짜 선택", value=min_date, min_value=min_date, max_value=max_date)
            
            # 선택한 날짜의 종가 찾기 (영업일 고려)
            buy_price_row = price_df.loc[price_df['Date'].dt.date <= buy_date].iloc[-1]
            buy_price = buy_price_row['Close']
            
            shares = budget / buy_price
            current_value = shares * current_price
            profit = current_value - budget
            roi = (profit / budget) * 100

            # 결과 표시 (사이드바)
            color = "red" if profit > 0 else "blue"
            st.markdown(f"**현재 가치:** {int(current_value):,}원")
            st.markdown(f"**수익금:** <span style='color:{color}'>{int(profit):,}원 ({roi:.2f}%)</span>", unsafe_allow_html=True)

        # [메인 화면 UI]
        st.title(f"📈 {target_company} 주가 분석 리포트")
        
        # 주요 지표 (Metrics)
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("현재가", f"{int(current_price):,}원", f"{int(current_price - price_df['Close'].iloc[-2]):,}원")
        m2.metric("최고가 (기간내)", f"{int(price_df['Close'].max()):,}원")
        m3.metric("최저가 (기간내)", f"{int(price_df['Close'].min()):,}원")
        m4.metric("시뮬레이션 수익률", f"{roi:.2f}%")

        # 탭 구성
        tab1, tab2 = st.tabs(["주가 차트", "데이터 내역"])
        
        with tab1:
            # 캔들차트 생성
            fig = go.Figure(data=[go.Candlestick(
                x=price_df['Date'],
                open=price_df['Open'],
                high=price_df['High'],
                low=price_df['Low'],
                close=price_df['Close'],
                increasing_line_color='#FF3333',
                decreasing_line_color='#3333FF',
                name="주가"
            )])
            
            # 이동평균선 추가
            price_df['MA20'] = price_df['Close'].rolling(window=20).mean()
            fig.add_trace(go.Scatter(x=price_df['Date'], y=price_df['MA20'], name='20일선', line=dict(color='orange', width=1)))
            
            fig.update_layout(
                plot_bgcolor='white',
                xaxis_rangeslider_visible=False,
                margin=dict(l=10, r=10, t=30, b=10),
                hovermode='x unified'
            )
            st.plotly_chart(fig, use_container_width=True)

        with tab2:
            st.dataframe(price_df.sort_values(by='Date', ascending=False), use_container_width=True)

    else:
        st.error("데이터를 불러오지 못했습니다. 종목코드나 기간을 확인해주세요.")
else:
    st.info("조회 시작일과 종료일을 선택해주세요.")