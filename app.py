# 표준 라이브러리
import datetime
from io import BytesIO

# 서드파티 라이브러리
import datetime
from io import BytesIO
import streamlit as st
import pandas as pd
import FinanceDataReader as fdr
import matplotlib.pyplot as plt
import koreanize_matplotlib
import os
import plotly.graph_objects as go
import yfinance as yf
from dotenv import load_dotenv


hidden_value = os.getenv('MY_NAME')
st.header(hidden_value)


@st.cache_data # 캐싱 
def get_krx_company_list() -> pd.DataFrame:
    try:
        # 파이썬 및 인터넷의 기본 문자열 인코딩 방식- UTF-8
        url = 'http://kind.krx.co.kr/corpgeneral/corpList.do?method=download&searchType=13'
        # MS 프로그램들은 cp949 / 구 몇몇 파일들의 인코딩 방식: EUC-KR
        df_listing = pd.read_html(url, header=0, flavor='bs4', encoding='EUC-KR')[0]
        
        # 필요한 컬럼만 추출 및 종목코드 6자리 포맷 맞추기
        df_listing = df_listing[['회사명', '종목코드']].copy()
        df_listing['종목코드'] = df_listing['종목코드'].apply(lambda x: f'{x:06}')
        return df_listing
    except Exception as e:
        st.error(f"상장사 명단을 불러오는 데 실패했습니다: {e}")
        return pd.DataFrame(columns=['회사명', '종목코드'])

st.sidebar.header("📈상장주식 주가 조회 서비스")
st.header("📈상장주식 주가 조회 서비스")


def get_stock_code_by_company(company_name: str) -> str:
    # 만약 입력값이 숫자 6자리라면 그대로 반환
    if company_name.isdigit() and len(company_name) == 6:
        return company_name
    
    company_df = get_krx_company_list()
    codes = company_df[company_df['회사명'] == company_name]['종목코드'].values
    ticker_symbol = f"{codes}.KS"
    if len(codes) > 0:
        return codes[0]
    else:
        raise ValueError(f"'{company_name}'을 찾을 수 없습니다. 종목코드 6자리를 직접 입력해보세요.")

company_name = st.sidebar.text_input('조회할 회사를 입력하세요')
# https://docs.streamlit.io/develop/api-reference/widgets/st.date_input

today = datetime.datetime.now()
jan_1 = datetime.date(today.year, 1, 1)

selected_dates = st.sidebar.date_input(
    '조회할 날짜를 입력하세요',
    (jan_1, today),
    format="MM.DD.YYYY",
)

# st.write(selected_dates)

confirm_btn = st.sidebar.button('조회하기') # 클릭하면 True

# --- 메인 로직 ---
if confirm_btn:
    if not company_name: # '' 이면
        st.warning("조회할 회사 이름을 입력하세요.")
    else:
        try:
            with st.spinner('데이터를 수집하는 중...'):
                stock_code = get_stock_code_by_company(company_name)
                start_date = selected_dates[0].strftime("%Y%m%d")
                end_date = selected_dates[1].strftime("%Y%m%d")
                
                price_df = fdr.DataReader(stock_code, selected_dates[0], selected_dates[1])
                price_df.reset_index(inplace=True)
                
            if price_df.empty:
                st.info("해당 기간의 주가 데이터가 없습니다.")
            else:
                tab1, tab2 = st.tabs(["📈 주가 차트", "📋 데이터 상세 내역"])

                with tab1:
                    # (기존 차트 코드 그대로 사용)
                    fig = go.Figure(data=[go.Candlestick(
                        x=price_df['Date'],
                        open=price_df['Open'],
                        high=price_df['High'],
                        low=price_df['Low'],
                        close=price_df['Close'],
                        increasing_line_color='#FF3333',
                        decreasing_line_color='#3333FF'
                    )])
                    st.plotly_chart(fig, use_container_width=True)

                with tab2:
                    st.subheader(f"최근 {company_name} 데이터 내역")
                    st.dataframe(price_df.sort_values(by='Date', ascending=False), use_container_width=True)
                
                with st.sidebar:
                    st.write("---")
                    st.subheader("📌 종목 요약 정보")
                    st.write(f"**종목명:** {company_name}")
                    st.write(f"**종목코드:** {stock_code}")
                    st.write(f"**최고가 (종가):** {int(price_df['Close'].max()):,}원")
                    st.write(f"**최저가 (종가):** {int(price_df['Close'].min()):,}원")
                    st.write(f"**평균 거래량:** {int(price_df['Volume'].mean()):,}주")
                    st.success(f"조회 기간: {selected_dates[0]} ~ {selected_dates[1]}")
                    
                                
                # 엑셀 다운로드 기능
                output = BytesIO()
                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                    price_df.to_excel(writer, index=True, sheet_name='Sheet1')
                st.download_button(
                    label="📥 엑셀 파일 다운로드",
                    data=output.getvalue(),
                    file_name=f"{company_name}_주가.xlsx",
                    mime="application/vnd.ms-excel"
                )
        except Exception as e:
            st.error(f"오류가 발생했습니다: {e}")
