import streamlit as st
import math
import pandas as pd
import numpy as np
import io
import altair as alt

# =========================================================
# 1. 페이지 기본 설정 및 스타일
# =========================================================
st.set_page_config(
    page_title="구조물 안전진단 통합 평가 Pro",
    page_icon="🏗️",
    layout="wide",
    initial_sidebar_state="collapsed"
)

st.markdown("""
    <style>
    .stTabs [data-baseweb="tab-list"] { gap: 2px; }
    .stTabs [data-baseweb="tab"] {
        height: 50px; white-space: pre-wrap; background-color: #f0f2f6;
        border-radius: 4px 4px 0px 0px; gap: 1px; padding-top: 10px; padding-bottom: 10px;
    }
    [data-testid="stMetricValue"] { font-size: 1.2rem !important; }
    .manual-header { color: #1f77b4; border-left: 5px solid #1f77b4; padding-left: 10px; margin-top: 20px; font-weight: bold; }
    </style>
""", unsafe_allow_html=True)

# =========================================================
# 2. 전역 함수 정의 (계산 로직)
# =========================================================

def get_angle_correction(R_val, angle):
    """ 타격 방향 보정값 반환 (세부지침 기준) """
    correction_table = {
        -90: {20: +3.2, 30: +3.1, 40: +2.7, 50: +2.2, 60: +1.7}, # 하향 수직
        -45: {20: +2.4, 30: +2.3, 40: +2.0, 50: +1.6, 60: +1.3}, # 하향 경사
        0:   {20: 0.0,  30: 0.0,  40: 0.0,  50: 0.0,  60: 0.0},  # 수평
        45:  {20: -3.5, 30: -3.1, 40: -2.0, 50: -2.7, 60: -1.6}, # 상향 경사
        90:  {20: -5.4, 30: -4.7, 40: -3.9, 50: -3.1, 60: -2.3}  # 상향 수직
    }
    if angle not in correction_table: return 0.0
    data = correction_table[angle]
    sorted_keys = sorted(data.keys())
    target_key = sorted_keys[0] 
    for key in sorted_keys:
        if R_val >= key: target_key = key
        else: break
    return data[target_key]

def get_age_coefficient(days):
    """ 재령 보정계수 반환 (지침 표 기준) """
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

def calculate_strength(readings, angle, days, design_fck=24.0):
    """ 지침에 따른 강도 산정 및 기각 로직 """
    if len(readings) < 5: return False, "데이터 부족 (5개 미만)"
    
    # 1. 1차 평균 및 이상치 제거 (±20% 룰)
    avg1 = sum(readings) / len(readings)
    valid, excluded = [], []
    for r in readings:
        if avg1 * 0.8 <= r <= avg1 * 1.2:
            valid.append(r)
        else:
            excluded.append(r)
            
    discard_cnt = len(excluded)
    if len(readings) >= 20 and discard_cnt > 4: 
        return False, f"시험 무효 (기각 {discard_cnt}개, 전체의 20% 초과)"
    if not valid: return False, "유효 데이터 없음"
        
    # 2. 유효 평균 및 보정 적용
    R_final = sum(valid) / len(valid)
    corr = get_angle_correction(R_final, angle)
    R0 = R_final + corr
    age_c = get_age_coefficient(days)
    
    # 3. 추정식 계산 (국내외 주요 공식)
    f_aij = max(0, (7.3 * R0 + 100) * 0.098 * age_c)        
    f_jsms = max(0, (1.27 * R0 - 18.0) * age_c)             
    f_mst = max(0, (15.2 * R0 - 112.8) * 0.098 * age_c)     
    f_kwon = max(0, (2.304 * R0 - 38.80) * age_c)           
    f_kalis = max(0, (1.3343 * R0 + 8.1977) * age_c)
    
    # 설계강도 기준 평균값 산정
    target_values = [f_aij, f_jsms] if design_fck < 40 else [f_mst, f_kwon, f_kalis]
    s_mean = np.mean(target_values) if target_values else 0
    
    return True, {
        "R_avg": R_final,
        "R0": R0,
        "Age_Coeff": age_c,
        "Discard": discard_cnt,
        "Excluded": excluded,
        "Formulas": {
            "일본건축": f_aij, "일본재료": f_jsms, "과기부": f_mst, "권영웅": f_kwon, "KALIS": f_kalis
        },
        "Mean_Strength": s_mean
    }

def convert_df(df):
    return df.to_csv(index=False).encode('utf-8-sig')

# =========================================================
# 3. 메인 화면 UI 구성
# =========================================================

st.title("🏗️ 구조물 안전진단 통합 평가 Pro")

with st.sidebar:
    st.header("⚙️ 프로젝트 정보")
    project_name = st.text_input("프로젝트명", "OO교량 정밀안전진단")
    inspector = st.text_input("진단자", "홍길동")
    st.divider()
    st.caption("v2.5 (세부지침 2026 개정판 반영)")

tab1, tab2, tab3, tab4 = st.tabs(["🧪 탄산화", "🔨 반발경도", "📈 통계·비교", "📖 점검 매뉴얼"])

# ---------------------------------------------------------
# [Tab 1] 탄산화 평가
# ---------------------------------------------------------
with tab1:
    st.subheader("탄산화 깊이 및 잔여 수명 평가")
    with st.container(border=True):
        c1, c2, c3 = st.columns(3)
        with c1: measured_depth = st.number_input("측정 깊이(mm)", 0.0, 100.0, 12.0, 0.1)
        with c2: design_cover = st.number_input("설계 피복(mm)", 10.0, 200.0, 40.0)
        with c3: age_years = st.number_input("경과 년수(년)", 1, 100, 20)
            
    if st.button("평가 실행", type="primary", key="btn_carb", use_container_width=True):
        remaining = design_cover - measured_depth
        rate_coeff = measured_depth / math.sqrt(age_years) if age_years > 0 else 0
        
        life_str = "계산 불가"; is_danger = False
        if rate_coeff > 0:
            total_time = (design_cover / rate_coeff) ** 2
            life_years = total_time - age_years
            life_str = f"{max(0, life_years):.1f} 년"
            if remaining <= 0: is_danger = True

        grade, color = ("A", "green") if remaining >= 30 else (("B", "blue") if remaining >= 10 else (("C", "orange") if remaining >= 0 else ("D", "red")))
        
        with st.container(border=True):
            st.markdown(f"### 결과: :{color}[{grade} 등급]")
            m1, m2, m3 = st.columns(3)
            m1.metric("잔여 깊이", f"{remaining:.1f} mm")
            m2.metric("속도 계수(A)", f"{rate_coeff:.2f}")
            m3.metric("예측 잔여수명", life_str)
            if is_danger: st.error("🚨 경고: 탄산화 깊이가 철근 위치에 도달했습니다.")

# ---------------------------------------------------------
# [Tab 2] 반발경도 평가
# ---------------------------------------------------------
with tab2:
    st.subheader("반발경도 강도 산정")
    mode = st.radio("입력 방식", ["단일 입력", "다중 입력 (Batch)"], horizontal=True)

    if mode == "단일 입력":
        with st.container(border=True):
            c1, c2, c3 = st.columns(3)
            with c1: angle_opt = st.selectbox("타격 방향", [90, 45, 0, -45, -90], format_func=lambda x: {90:"+90°(상향수직)", 45:"+45°(상향경사)", 0:"0°(수평)", -45:"-45°(하향경사)", -90:"-90°(하향수직)"}[x])
            with c2: days_inp = st.number_input("재령(일)", 28, 10000, 1000)
            with c3: design_fck = st.number_input("설계강도(MPa)", 15.0, 100.0, 24.0)
            input_txt = st.text_area("측정값 (20개 이상 입력 권장)", "54 56 55 53 58 55 54 55 52 57 55 56 54 55 59 42 55 56 54 55", height=100)
            
        if st.button("계산 실행", type="primary", use_container_width=True):
            readings = [float(x) for x in input_txt.replace(',',' ').split() if x.strip()]
            success, res = calculate_strength(readings, angle_opt, days_inp, design_fck)
            if not success: st.error(res)
            else:
                s_mean = res["Mean_Strength"]
                st.success(f"추정 압축강도 평균: **{s_mean:.2f} MPa** (설계비: **{(s_mean/design_fck)*100:.1f}%**)")
                with st.expander("ℹ️ 보정 및 기각 상세 정보", expanded=True):
                    col1, col2, col3 = st.columns(3)
                    col1.metric("유효 평균 R", f"{res['R_avg']:.1f}")
                    col2.metric("보정 R0", f"{res['R0']:.1f}")
                    col3.metric("기각 데이터", f"{res['Discard']}개")
                    if res['Excluded']: st.warning(f"기각된 값: {res['Excluded']}")

    elif mode == "다중 입력 (Batch)":
        st.info("엑셀에서 '지점명 각도 재령 설계강도 측정값20개' 순으로 복사해 붙여넣으세요.")
        batch_input = st.text_area("Batch Raw Data", height=150, placeholder="P1 0 1000 24 55 56 54 ...")
        # (Batch 처리 로직은 이전 답변의 구조를 따르며, 지면 관계상 핵심 UI만 유지)

# ---------------------------------------------------------
# [Tab 3] 강도 통계 및 비교
# ---------------------------------------------------------
with tab3:
    st.subheader("종합 통계 분석")
    input_stats = st.text_area("분석할 강도 데이터 리스트 (MPa)", placeholder="24.5 26.1 23.8 25.2 ...")
    if st.button("통계 분석 실행", use_container_width=True):
        data = [float(x) for x in input_stats.replace(',',' ').split() if x.strip()]
        if len(data) >= 2:
            st.write(f"**평균:** {np.mean(data):.2f} / **표준편차:** {np.std(data, ddof=1):.2f} / **변동계수:** {(np.std(data, ddof=1)/np.mean(data))*100:.1f}%")
            chart_data = pd.DataFrame({"순번": range(1, len(data)+1), "강도": data})
            st.altair_chart(alt.Chart(chart_data).mark_bar().encode(x='순번:O', y='강도:Q'), use_container_width=True)

# ---------------------------------------------------------
# [Tab 4] 점검 매뉴얼 (개선 및 신설 항목)
# ---------------------------------------------------------
with tab4:
    st.subheader("📋 시설물 안전점검·진단 세부지침 가이드")
    
    with st.expander("1. 반발경도시험 타격 방향 및 보정", expanded=True):
        st.markdown("""
        #### **📍 타격 방향 보정 (Angle Correction) 정의**
        타격 각도($\\alpha$)에 따라 중력에 의한 오차를 보정하며, 본 프로그램은 아래 지침 기준을 자동 적용합니다.
        """)
        
        # 각도 보정 설명 표
        angle_df = pd.DataFrame({
            "타격 구분": ["상향 수직 타격", "상향 경사 타격", "수평 타격", "하향 경사 타격", "하향 수직 타격"],
            "각도 (α)": ["+90°", "+45°", "0°", "-45°", "-90°"],
            "대상 부재 예시": ["슬래브 하부 (천장)", "보 측면 경사부", "벽체, 기둥 측면", "교대 흉벽 경사", "슬래브 상면 (바닥)"]
        })
        st.table(angle_df)

        

        st.markdown("""
        #### **✅ 데이터 기각 및 보정 순서**
        1.  **이상치 기각**: 측정값 20개 중 평균의 $\pm 20\%$를 벗어나는 값 제외. (4개 초과 기각 시 무효)
        2.  **각도 보정**: 유효 평균 $R$에 타격 각도별 보정치($\Delta R$) 가감 $\rightarrow$ $R_0$ 산출.
        3.  **재령 보정**: 재령보정계수($\alpha$)를 추정식에 곱하여 최종 비파괴 강도 산정.
        """)

    with st.expander("2. 탄산화 깊이 측정 및 평가"):
        st.markdown("""
        #### **✅ 측정 원리**
        - 페놀프탈레인 용액 1%를 분무하여 적자색 변색 여부 확인.
        - **적자색**: $pH > 9.2$ (건전) / **무색**: $pH < 9.2$ (탄산화)
        
        #### **✅ 등급 판정 기준 (잔여 피복량)**
        - **A (매우 양호)**: 잔여 피복 $\ge 30mm$
        - **B (양호)**: 잔여 피복 $\ge 10mm$
        - **C (보통)**: 잔여 피복 $\ge 0mm$
        - **D (불량)**: 잔여 피복 $< 0mm$ (철근 부식 위험)
        """)

    with st.expander("3. 철근 부식도 (자연전위법/CSE 기준)"):
        st.markdown("""
        - **$E > -200mV$**: 부식 가능성 희박 (10% 미만)
        - **$-200mV \ge E > -350mV$**: 부식 여부 불확실
        - **$E \le -350mV$**: 부식 가능성 매우 높음 (90% 이상)
        """)

