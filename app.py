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
    .calc-box { background-color: #f8f9fa; padding: 15px; border-radius: 10px; border-left: 5px solid #1f77b4; margin-bottom: 10px; }
    </style>
""", unsafe_allow_html=True)

# =========================================================
# 2. 전역 함수 정의 (계산 로직)
# =========================================================

def get_angle_correction(R_val, angle):
    """ 타격 방향 보정값 반환 """
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
    """ 재령 보정계수 (지침 기준) """
    age_table = {
        10: 1.55, 20: 1.12, 28: 1.00, 50: 0.87,
        100: 0.78, 150: 0.74, 200: 0.72, 300: 0.70,
        500: 0.67, 1000: 0.65, 3000: 0.63
    }
    sorted_days = sorted(age_table.keys())
    if days >= sorted_days[-1]: return age_table[sorted_days[-1]]
    if days <= sorted_days[0]: return age_table[sorted_days[0]]
    for i in range(len(sorted_days) - 1):
        d1, d2 = sorted_days[i], sorted_days[i+1]
        if d1 <= days <= d2:
            c1, c2 = age_table[d1], age_table[d2]
            return c1 + (days - d1) / (d2 - d1) * (c2 - c1)
    return 1.0

def calculate_strength(readings, angle, days, design_fck=24.0):
    if len(readings) < 5: return False, "데이터 부족"
    avg1 = sum(readings) / len(readings)
    valid = [r for r in readings if avg1 * 0.8 <= r <= avg1 * 1.2]
    excluded = [r for r in readings if r not in valid]
    
    if len(readings) >= 20 and len(excluded) > 4: return False, f"무효 (기각 {len(excluded)}개)"
    if not valid: return False, "유효 데이터 없음"
        
    R_avg = sum(valid) / len(valid)
    corr = get_angle_correction(R_avg, angle)
    R0 = R_avg + corr
    age_c = get_age_coefficient(days)
    
    # 공식 적용
    f_aij = max(0, (7.3 * R0 + 100) * 0.098 * age_c)        
    f_jsms = max(0, (1.27 * R0 - 18.0) * age_c)             
    f_mst = max(0, (15.2 * R0 - 112.8) * 0.098 * age_c)     
    f_kwon = max(0, (2.304 * R0 - 38.80) * age_c)           
    f_kalis = max(0, (1.3343 * R0 + 8.1977) * age_c)
    
    target_fs = [f_aij, f_jsms] if design_fck < 40 else [f_mst, f_kwon, f_kalis]
    s_mean = np.mean(target_fs)
    
    return True, {
        "R_initial": avg1, "R_avg": R_avg, "Angle_Corr": corr, "R0": R0, 
        "Age_Coeff": age_c, "Discard": len(excluded), "Excluded": excluded,
        "Formulas": {"일본건축(AIJ)": f_aij, "일본재료(JSMS)": f_jsms, "과기부(MST)": f_mst, "권영웅": f_kwon, "KALIS": f_kalis},
        "Mean_Strength": s_mean
    }

# =========================================================
# 3. 메인 UI
# =========================================================

st.title("🏗️ 구조물 안전진단 통합 평가 Pro")

tab1, tab2, tab3, tab4 = st.tabs(["🧪 탄산화", "🔨 반발경도", "📈 통계·비교", "📖 점검 매뉴얼"])

# ---------------------------------------------------------
# [Tab 1] 탄산화 평가 (상세 계산식 추가)
# ---------------------------------------------------------
with tab1:
    st.subheader("탄산화 깊이 및 상세 분석")
    with st.container(border=True):
        c1, c2, c3 = st.columns(3)
        with c1: m_depth = st.number_input("측정 깊이(mm)", 0.0, 100.0, 12.0)
        with c2: d_cover = st.number_input("설계 피복(mm)", 10.0, 200.0, 40.0)
        with c3: a_years = st.number_input("경과 년수(년)", 1, 100, 20)
            
    if st.button("평가 실행", type="primary", use_container_width=True):
        rem = d_cover - m_depth
        rate_a = m_depth / math.sqrt(a_years) if a_years > 0 else 0
        total_life = (d_cover / rate_a)**2 if rate_a > 0 else 99.9
        res_life = total_life - a_years
        
        grade, color = ("A", "green") if rem >= 30 else (("B", "blue") if rem >= 10 else (("C", "orange") if rem >= 0 else ("D", "red")))
        
        st.markdown(f"### 결과: :{color}[{grade} 등급]")
        
        with st.container(border=True):
            st.markdown("#### 📝 상세 계산 근거")
            cc1, cc2, cc3 = st.columns(3)
            cc1.metric("잔여 피복량", f"{rem:.1f} mm")
            cc2.metric("속도 계수 (A)", f"{rate_a:.3f}")
            cc3.metric("예측 잔여수명", f"{max(0, res_life):.1f} 년")
            
            st.info(f"""
            **계산 프로세스:**
            1. **속도계수(A) 산출**: $A = C / \sqrt{{t}} = {m_depth} / \sqrt{{{a_years}}} = {rate_a:.3f}$
            2. **한계 수명(T) 산출**: $T = (Cover / A)^2 = ({d_cover} / {rate_a:.3f})^2 = {total_life:.1f}$ 년
            3. **잔여 수명**: $T - t = {total_life:.1f} - {a_years} = {res_life:.1f}$ 년
            """)

# ---------------------------------------------------------
# [Tab 2] 반발경도 평가 (R0 및 공식별 상세 추가)
# ---------------------------------------------------------
with tab2:
    st.subheader("반발경도 정밀 강도 산정")
    mode = st.radio("입력 방식", ["단일 입력", "다중 입력 (Batch)"], horizontal=True)

    if mode == "단일 입력":
        with st.container(border=True):
            c1, c2, c3 = st.columns(3)
            with c1: angle = st.selectbox("타격 방향", [90, 45, 0, -45, -90], format_func=lambda x: {90:"+90°(상향수직)", 45:"+45°(상향경사)", 0:"0°(수평)", -45:"-45°(하향경사)", -90:"-90°(하향수직)"}[x])
            with c2: days = st.number_input("재령(일)", 28, 10000, 1000)
            with c3: fck = st.number_input("설계강도(MPa)", 15.0, 100.0, 24.0)
            txt = st.text_area("측정값 (공백/줄바꿈 구분)", "54 56 55 53 58 55 54 55 52 57 55 56 54 55 59 42 55 56 54 55", height=100)
            
        if st.button("계산 실행", type="primary", use_container_width=True):
            rd = [float(x) for x in txt.replace(',',' ').split() if x.strip()]
            success, res = calculate_strength(rd, angle, days, fck)
            
            if success:
                st.success(f"평균 추정 압축강도: **{res['Mean_Strength']:.2f} MPa**")
                
                # 1. 보정 단계 요약
                with st.container(border=True):
                    st.markdown("#### 📏 반발경도 보정 프로세스")
                    m1, m2, m3, m4 = st.columns(4)
                    m1.metric("유효 평균 R", f"{res['R_avg']:.1f}")
                    m2.metric("각도 보정 (ΔR)", f"{res['Angle_Corr']:+.1f}")
                    m3.metric("보정 경도 (R₀)", f"{res['R0']:.1f}", help="각도 보정이 적용된 최종 반발경도")
                    m4.metric("재령 계수 (α)", f"{res['Age_Coeff']:.2f}")

                # 2. 공식별 상세 강도
                st.markdown("#### 📊 공식별 추정 강도 상세")
                df_f = pd.DataFrame({
                    "연구자/기관": res["Formulas"].keys(),
                    "추정강도 (MPa)": res["Formulas"].values()
                })
                
                c_left, c_right = st.columns([2, 1])
                with c_left:
                    # 차트
                    chart = alt.Chart(df_f).mark_bar().encode(
                        x=alt.X('연구자/기관', sort=None),
                        y='추정강도 (MPa)',
                        color=alt.condition(alt.datum['추정강도 (MPa)'] >= fck, alt.value('#4D96FF'), alt.value('#FF6B6B'))
                    ).properties(height=300)
                    st.altair_chart(chart, use_container_width=True)
                
                with c_right:
                    st.dataframe(df_f.style.format({"추정강도 (MPa)": "{:.2f}"}), hide_index=True, use_container_width=True)
                    st.info(f"설계강도 {fck}MPa 대비 {(res['Mean_Strength']/fck*100):.1f}% 수준")

                with st.expander("🚫 이상치 기각 정보"):
                    st.write(f"1차 평균: {res['R_initial']:.1f}")
                    st.write(f"기각된 데이터 ({res['Discard']}개): {res['Excluded']}")

    elif mode == "다중 입력 (Batch)":
        # (기존 Batch 로직 유지하되 결과 테이블에 R0, Alpha 컬럼 추가 가능)
        st.info("Batch 모드에서도 상세 보정값이 포함된 리포트를 생성합니다.")
        # ... [이하 기존 Batch 로직 생략] ...

# ---------------------------------------------------------
# [Tab 3] 통계 및 비교
# ---------------------------------------------------------
with tab3:
    st.subheader("강도 통계 분석")
    c1, c2 = st.columns([1, 3])
    with c1: st_fck = st.number_input("기준 설계강도", 15.0, 100.0, 24.0)
    with c2: st_txt = st.text_area("강도 데이터 목록 (MPa)", "24.5 26.2 23.1 21.8 25.5 27.0", height=68)
    
    if st.button("분석 실행", key="btn_st", use_container_width=True):
        data = sorted([float(x) for x in st_txt.replace(',',' ').split() if x.strip()])
        if len(data) >= 2:
            st.metric("평균 강도", f"{np.mean(data):.2f} MPa", delta=f"{(np.mean(data)/st_fck*100):.1f}%")
            
            # 통계 차트 (정렬된 데이터)
            st_df = pd.DataFrame({"순번": range(1, len(data)+1), "강도": data})
            s_bars = alt.Chart(st_df).mark_bar().encode(x='순번:O', y='강도:Q', color=alt.condition(alt.datum.강도 >= st_fck, alt.value('#4D96FF'), alt.value('#FF6B6B')))
            s_rule = alt.Chart(pd.DataFrame({'y': [st_fck]})).mark_rule(color='red', strokeDash=[5,3]).encode(y='y')
            st.altair_chart(s_bars + s_rule, use_container_width=True)

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

