import streamlit as st
import math
import pandas as pd
import numpy as np

# =========================================================
# 1. 페이지 기본 설정 및 스타일
# =========================================================
st.set_page_config(
    page_title="구조물 안전진단 통합 평가 Pro",
    page_icon="🏗️",
    layout="wide"
)

# =========================================================
# 2. 전역 함수 정의 (보정계수 및 유틸리티)
# =========================================================

def get_angle_correction(R_val, angle):
    """ [타격 방향 보정] Step 방식 """
    correction_table = {
        -90: {20: +3.2, 30: +3.1, 40: +2.7, 50: +2.2, 60: +1.7},
        -45: {20: +2.4, 30: +2.3, 40: +2.0, 50: +1.6, 60: +1.3},
        0:   {20: 0.0,  30: 0.0,  40: 0.0,  50: 0.0,  60: 0.0},
        45:  {20: -3.5, 30: -3.1, 40: -2.0, 50: -2.7, 60: -1.6},
        90:  {20: -5.4, 30: -4.7, 40: -3.9, 50: -3.1, 60: -2.3}
    }
    
    if angle not in correction_table: return 0.0
    
    data = correction_table[angle]
    sorted_keys = sorted(data.keys())
    target_key = sorted_keys[0] 
    
    for key in sorted_keys:
        if R_val >= key:
            target_key = key
        else:
            break
            
    return data[target_key]

def get_age_coefficient(days):
    """ [재령 보정계수] 보간법 적용 """
    age_table = {
        10: 1.55, 20: 1.12, 28: 1.00, 50: 0.87,
        100: 0.78, 150: 0.74, 200: 0.72, 300: 0.70,
        500: 0.67, 1000: 0.65, 3000: 0.63
    }
    
    sorted_days = sorted(age_table.keys())
    
    if days >= sorted_days[-1]: return age_table[sorted_days[-1]]
    if days <= sorted_days[0]: return age_table[sorted_days[0]]
    
    for i in range(len(sorted_days) - 1):
        d1 = sorted_days[i]
        d2 = sorted_days[i+1]
        if d1 <= days <= d2:
            c1 = age_table[d1]
            c2 = age_table[d2]
            ratio = (days - d1) / (d2 - d1)
            return c1 + ratio * (c2 - c1)
            
    return 1.0

def convert_df(df):
    """ DataFrame을 CSV 다운로드용 바이트로 변환 (UTF-8-SIG) """
    return df.to_csv(index=False).encode('utf-8-sig')

# =========================================================
# 3. 메인 화면 UI 구성
# =========================================================

st.title("🏗️ 구조물 안전진단 통합 평가 System")
st.markdown("""
정밀안전진단 기준에 따른 **탄산화**, **반발경도**, **강도 통계** 분석을 수행하는 전문가용 도구입니다.
""")

# 사이드바: 프로젝트 정보 입력
with st.sidebar:
    st.header("📝 프로젝트 설정")
    project_name = st.text_input("프로젝트명", value="OO교량 정밀안전진단")
    inspector_name = st.text_input("진단자", value="홍길동")
    st.caption("※ 다운로드 파일명에 반영됩니다.")
    st.divider()
    st.info("💡 **사용 가이드**\n\n1. 탄산화 깊이 측정\n2. 반발경도(R) 측정 (20점)\n3. 통계 분석 및 보고서 다운로드")

# 메인 탭 구성 (3개)
tab1, tab2, tab3 = st.tabs(["🧪 1. 탄산화 평가", "🔨 2. 반발경도 평가", "📈 3. 강도 통계 (직접 입력)"])

# =========================================================
# [Tab 1] 탄산화 평가
# =========================================================
with tab1:
    st.header("🧪 탄산화 깊이 및 등급 평가")
    
    with st.container():
        c1, c2, c3 = st.columns(3)
        with c1:
            measured_depth = st.number_input("측정 탄산화 깊이 (mm)", 0.0, 100.0, 12.0, 0.1, format="%.1f")
        with c2:
            design_cover = st.number_input("설계 피복 두께 (mm)", 10.0, 200.0, 40.0, 1.0)
        with c3:
            age_years = st.number_input("건물 경과 년수 (년)", 1, 100, 20)
            
    if st.button("탄산화 평가 실행", type="primary", key="btn_carb"):
        remaining = design_cover - measured_depth
        rate_coeff = measured_depth / math.sqrt(age_years) if age_years > 0 else 0
        
        # 수명 예측
        life_str = ""
        is_danger = False
        if rate_coeff > 0:
            total_time = (design_cover / rate_coeff) ** 2
            life_years = total_time - age_years
            if remaining <= 0:
                life_str = "🚨 0년 (이미 도달함)"
                is_danger = True
            elif life_years > 0
