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
    .calc-box { background-color: #f8f9fa; padding: 15px; border-radius: 10px; border-left: 5px solid #1f77b4; margin-bottom: 15px; }
    </style>
""", unsafe_allow_html=True)

# =========================================================
# 2. 전역 함수 정의
# =========================================================

def get_angle_correction(R_val, angle):
    """ 타격 방향 보정값 (세부지침 기준) """
    try: angle = int(angle)
    except: angle = 0
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
        if R_val >= key: target_key = key
        else: break
    return data[target_key]

def get_age_coefficient(days):
    """ 재령 보정계수 (지침 기준) """
    try: days = float(days)
    except: days = 3000.0
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
    """ 반발경도 강도 산정 메인 로직 """
    if not readings or len(readings) < 5: return False, "데이터 부족"
    avg1 = sum(readings) / len(readings)
    valid = [r for r in readings if avg1 * 0.8 <= r <= avg1 * 1.2]
    excluded = [r for r in readings if r not in valid]
    if len(readings) >= 20 and len(excluded) > 4: return False, f"시험 무효 (기각 {len(excluded)}개)"
    if not valid: return False, "유효 데이터 없음"
    R_avg = sum(valid) / len(valid)
    corr = get_angle_correction(R_avg, angle)
    R0 = R_avg + corr
    age_c = get_age_coefficient(days)
    
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
        "Formulas": {"일본건축": f_aij, "일본재료": f_jsms, "과기부": f_mst, "권영웅": f_kwon, "KALIS": f_kalis},
        "Mean_Strength": s_mean
    }

def convert_df(df):
    return df.to_csv(index=False).encode('utf-8-sig')

# =========================================================
# 3. 메인 UI 구성
# =========================================================

st.title("🏗️ 구조물 안전진단 통합 평가 Pro")

with st.sidebar:
    st.header("⚙️ 프로젝트 정보")
    p_name = st.text_input("프로젝트명", "OO시설물 정밀점검")
    st.divider()
    st.caption("시설물안전법 및 세부지침 준수")

# 탭 순서: 1. 매뉴얼, 2. 반발경도, 3. 탄산화, 4. 통계
tab1, tab2, tab3, tab4 = st.tabs(["📖 점검 매뉴얼", "🔨 반발경도", "🧪 탄산화", "📈 통계·비교"])

# ---------------------------------------------------------
# [Tab 1] 점검 매뉴얼 (내용 보강)
# ---------------------------------------------------------
with tab1:
    st.subheader("💡 프로그램 사용 가이드")
    st.info("""
    **1. 반발경도 산정 시 설계기준강도를 입력해주세요.**
    * 설계기준강도를 바탕으로 압축강도 추정에 필요한 공식 적용 로직이 자동으로 변경됩니다.

    **2. 타격방향 보정 값을 매뉴얼을 참고해서 상향 타격인지 하향타격인지를 구분해서 선택해주세요.**

    **3. 재령 등 별도로 적용하지 않을 시 프로그램상에서 재령 3000일, 설계기준강도 24MPa가 적용됩니다.**
    """)
    
    st.divider()
    
    st.subheader("📋 시설물 안전점검·진단 세부지침 매뉴얼")

    with st.expander("1. 반발경도 시험 (Rebound Hardness Test) 상세 지침", expanded=False):
        st.markdown("""
        #### **✅ 개요 및 원리**
        * 콘크리트 표면을 슈미트 해머로 타격하여 반발되는 거리($R$)를 측정하고, 이와 압축강도 사이의 상관관계를 통해 비파괴 강도를 추정합니다.
        
        #### **✅ 측정 장소 선정 (지침 기준)**
        * **부재 두께**: 최소 10cm 이상인 부위를 선정합니다.
        * **이격 거리**: 부재의 모서리나 끝부분으로부터 3~6cm 이상 떨어진 곳을 타격합니다.
        * **표면 처리**: 도장재, 요철, 이물질 등을 제거하고 평탄한 콘크리트 면을 노출시킨 후 측정합니다.

        #### **✅ 측정 및 기각 룰**
        1. **타격 점수**: 1개소당 **20점 이상** 측정을 원칙으로 합니다 (가로·세로 3cm 간격 격자망).
        2. **이상치 기각**: 전체 측정값의 산술평균을 낸 후, 평균값에서 **±20%를 벗어나는 데이터는 무효**로 처리합니다.
        3. **시험 무효**: 기각된 데이터가 **5개 이상(20% 초과)**인 경우 해당 측정 지점의 시험은 무효로 보고 재시험을 실시합니다.

        #### **📍 타격 방향 보정 (Angle Correction)**
        """)
        
        m_df = pd.DataFrame({
            "구분": ["상향 수직 (+90°)", "상향 경사 (+45°)", "수평 타격 (0°)", "하향 경사 (-45°)", "하향 수직 (-90°)"],
            "대상 부재 예시": ["슬래브 하부 (천장)", "보 경사면", "벽체, 기둥 측면", "교대/교각 경사부", "슬래브 상면 (바닥)"]
        })
        st.table(m_df)
        st.info("※ 본 프로그램은 위 각도 선택 시 세부지침의 보정표 값을 자동으로 가감($R_0$)합니다.")

    with st.expander("2. 탄산화 깊이 측정 (Carbonation Test) 상세 지침", expanded=False):
        st.markdown("""
        #### **✅ 개요 및 측정 방법**
        * 공기 중의 탄산가스가 콘크리트 내부로 침투하여 알칼리성을 저하시키는 현상을 측정합니다.
        * **시약**: 1% 페놀프탈레인 용액을 사용합니다.
        * **측정**: 신선한 콘크리트 파쇄면에 시약을 분무한 후, **적자색으로 변하지 않는 구간(무색)**의 깊이를 0.5mm 단위로 측정합니다.

        #### **✅ 탄산화 속도 및 수명 산식**
        * **$C = A\sqrt{t}$**
          - $C$: 탄산화 깊이($mm$)
          - $A$: 탄산화 속도계수
          - $t$: 경과 년수(년)
        * 예측 수명은 설계 피복 두께에 도달하는 시점으로 계산됩니다.

        #### **✅ 등급 판정 기준 (잔여 피복 두께 기반)**
        * **A (매우 양호)**: 잔여 피복 두께 30mm 이상
        * **B (양호)**: 잔여 피복 두께 10mm ~ 30mm 미만
        * **C (보통)**: 잔여 피복 두께 0mm ~ 10mm 미만
        * **D (불량)**: 탄산화 깊이가 철근 위치를 초과 (잔여 피복 < 0)
        """)
        

    with st.expander("3. 철근 부식도 및 기타 비파괴 시험 지침"):
        st.markdown("""
        #### **✅ 자연전위법 (철근 부식도)**
        * **-350mV 이하**: 부식 발생 확률 90% 이상 (매우 높음)
        * **-200mV ~ -350mV**: 부식 발생 여부 불확실
        * **-200mV 이상**: 부식 확률 10% 미만 (희박)
        * 측정 전 콘크리트 표면을 충분히 습윤시켜 전기적 저항을 낮추어야 합니다.
        """)

# ---------------------------------------------------------
# [Tab 2] 반발경도 평가 (기존 기능 유지)
# ---------------------------------------------------------
with tab2:
    st.subheader("🔨 반발경도 정밀 강도 산정")
    mode = st.radio("입력 방식", ["단일 지점", "다중 지점 (Batch/File)"], horizontal=True)

    if mode == "단일 지점":
        with st.container(border=True):
            c1, c2, c3 = st.columns(3)
            with c1: angle = st.selectbox("타격 방향", [90, 45, 0, -45, -90], format_func=lambda x: {90:"+90°(상향수직)", 45:"+45°(상향경사)", 0:"0°(수평)", -45:"-45°(하향경사)", -90:"-90°(하향수직)"}[x])
            with c2: days = st.number_input("재령(일)", 10, 10000, 3000)
            with c3: fck = st.number_input("설계강도(MPa)", 15.0, 100.0, 24.0)
            txt = st.text_area("측정값 (공백/줄바꿈 구분)", "54 56 55 53 58 55 54 55 52 57 55 56 54 55 59 42 55 56 54 55", height=80)
            
        if st.button("계산 실행", type="primary", use_container_width=True):
            rd = [float(x) for x in txt.replace(',',' ').split() if x.strip()]
            ok, res = calculate_strength(rd, angle, days, fck)
            if ok:
                st.success(f"평균 추정 압축강도: **{res['Mean_Strength']:.2f} MPa**")
                with st.container(border=True):
                    m1, m2, m3, m4 = st.columns(4)
                    m1.metric("유효 평균 R", f"{res['R_avg']:.1f}"); m2.metric("각도 보정", f"{res['Angle_Corr']:+.1f}"); m3.metric("최종 R₀", f"{res['R0']:.1f}"); m4.metric("재령 계수 α", f"{res['Age_Coeff']:.2f}")
                
                df_f = pd.DataFrame({"공식": res["Formulas"].keys(), "강도": res["Formulas"].values()})
                chart = alt.Chart(df_f).mark_bar().encode(
                    x=alt.X('공식', sort=None), y='강도',
                    color=alt.condition(alt.datum.강도 >= fck, alt.value('#4D96FF'), alt.value('#FF6B6B'))
                ).properties(height=350)
                rule = alt.Chart(pd.DataFrame({'y': [fck]})).mark_rule(color='red', strokeDash=[5, 3], size=2).encode(y='y')
                st.altair_chart(chart + rule, use_container_width=True)

    else:
        uploaded_file = st.file_uploader("CSV 또는 Excel 파일 업로드", type=["csv", "xlsx"])
        init_data = []
        if uploaded_file:
            try:
                df_up = pd.read_csv(uploaded_file) if uploaded_file.name.endswith('.csv') else pd.read_excel(uploaded_file)
                for _, row in df_up.iterrows():
                    init_data.append({"선택": True, "지점": row.get("지점", "P"), "각도": int(row.get("각도", 0)), "재령": int(row.get("재령", 3000)), "설계": float(row.get("설계", 24.0)), "데이터": str(row.get("데이터", ""))})
            except: st.error("파일 파싱 실패")

        df_batch = pd.DataFrame(init_data) if init_data else pd.DataFrame(columns=["선택","지점","각도","재령","설계","데이터"])
        edited_df = st.data_editor(df_batch, column_config={"선택": st.column_config.CheckboxColumn("선택", default=True), "각도": st.column_config.SelectboxColumn("각도 (α)", options=[90, 45, 0, -45, -90], required=True)}, use_container_width=True, hide_index=True, num_rows="dynamic")
        
        if st.button("🚀 일괄 계산 실행", type="primary", use_container_width=True):
            batch_res = []
            for _, row in edited_df.iterrows():
                if not row["선택"]: continue
                try:
                    rd_list = [float(x) for x in str(row["데이터"]).replace(',',' ').split() if x.replace('.','',1).isdigit()]
                    ang_v = 0 if pd.isna(row["각도"]) else row["각도"]
                    age_v = 3000 if pd.isna(row["재령"]) else row["재령"]
                    fck_v = 24 if pd.isna(row["설계"]) else row["설계"]
                    ok, res = calculate_strength(rd_list, ang_v, age_v, fck_v)
                    if ok:
                        data_entry = {"지점": row["지점"], "설계": fck_v, "추정강도": round(res["Mean_Strength"], 2), "강도비(%)": round((res["Mean_Strength"]/fck_v)*100, 1), "유효평균R": round(res["R_avg"], 1), "보정R0": round(res["R0"], 1), "재령계수": round(res["Age_Coeff"], 2), "기각수": res["Discard"], "기각데이터": str(res["Excluded"])}
                        for f_name, f_val in res["Formulas"].items(): data_entry[f_name] = round(f_val, 1)
                        batch_res.append(data_entry)
                except: continue
            if batch_res:
                final_df = pd.DataFrame(batch_res)
                res_tab1, res_tab2 = st.tabs(["📋 요약", "🔍 세부 데이터"])
                with res_tab1: st.dataframe(final_df[["지점", "설계", "추정강도", "강도비(%)"]], use_container_width=True, hide_index=True)
                with res_tab2: st.dataframe(final_df, use_container_width=True, hide_index=True)

# ---------------------------------------------------------
# [Tab 3] 탄산화 평가 (기존 기능 및 그래프 유지)
# ---------------------------------------------------------
with tab3:
    st.subheader("🧪 탄산화 깊이 및 상세 분석")
    with st.container(border=True):
        c1, c2, c3 = st.columns(3)
        with c1: m_depth = st.number_input("측정 깊이(mm)", 0.0, 100.0, 12.0)
        with c2: d_cover = st.number_input("설계 피복(mm)", 10.0, 200.0, 40.0)
        with c3: a_years = st.number_input("경과 년수(년)", 1, 100, 20)
            
    if st.button("평가 실행", type="primary", key="btn_carb_run", use_container_width=True):
        rem = d_cover - m_depth
        rate_a = m_depth / math.sqrt(a_years) if a_years > 0 else 0
        total_life = (d_cover / rate_a)**2 if rate_a > 0 else 99.9
        res_life = total_life - a_years
        grade, color = ("A", "green") if rem >= 30 else (("B", "blue") if rem >= 10 else (("C", "orange") if rem >= 0 else ("D", "red")))
        
        st.markdown(f"### 결과: :{color}[{grade} 등급]")
        
        # 탄산화 진행 곡선 그래프
        y_steps = np.linspace(0, 100, 101)
        d_steps = rate_a * np.sqrt(y_steps)
        df_plot = pd.DataFrame({'경과년수': y_steps, '탄산화깊이': d_steps})
        
        line = alt.Chart(df_plot).mark_line(color='#1f77b4').encode(x=alt.X('경과년수:Q', title='경과년수 (년)'), y=alt.Y('탄산화깊이:Q', title='탄산화 깊이 (mm)'))
        rule = alt.Chart(pd.DataFrame({'y': [d_cover]})).mark_rule(color='red', strokeDash=[5,5], size=2).encode(y='y')
        point = alt.Chart(pd.DataFrame({'x': [a_years], 'y': [m_depth]})).mark_point(color='orange', size=100, filled=True).encode(x='x', y='y')
        
        st.altair_chart(line + rule + point, use_container_width=True)

        with st.container(border=True):
            cc1, cc2, cc3 = st.columns(3)
            cc1.metric("잔여 피복량", f"{rem:.1f} mm"); cc2.metric("속도 계수 (A)", f"{rate_a:.3f}"); cc3.metric("예측 잔여수명", f"{max(0, res_life):.1f} 년")

# ---------------------------------------------------------
# [Tab 4] 통계 및 비교 (기존 기능 유지)
# ---------------------------------------------------------
with tab4:
    st.subheader("📈 통계 및 비교 분석")
    c1, c2 = st.columns([1, 3])
    with c1: st_fck = st.number_input("기준 설계강도(MPa)", 15.0, 100.0, 24.0, key="st_fck")
    with c2: st_txt = st.text_area("강도 데이터 목록", "24.5 26.2 23.1 21.8 25.5 27.0", key="st_txt")
    if st.button("통계 실행", use_container_width=True):
        data = sorted([float(x) for x in st_txt.replace(',',' ').split() if x.strip()])
        if len(data) >= 2:
            avg_v = np.mean(data); std_v = np.std(data, ddof=1); cv_v = (std_v / avg_v * 100) if avg_v > 0 else 0
            with st.container(border=True):
                m1, m2, m3 = st.columns(3)
                m1.metric("평균", f"{avg_v:.2f}"); m2.metric("표준편차 (σ)", f"{std_v:.2f}"); m3.metric("변동계수 (CV)", f"{cv_v:.1f}%")
            st_df = pd.DataFrame({"번호": range(1, len(data)+1), "강도": data})
            s_chart = alt.Chart(st_df).mark_bar().encode(x='번호:O', y='강도:Q', color=alt.condition(alt.datum.강도 >= st_fck, alt.value('#4D96FF'), alt.value('#FF6B6B')))
            st.altair_chart(s_chart + alt.Chart(pd.DataFrame({'y':[st_fck]})).mark_rule(color='red', strokeDash=[5,3], size=2).encode(y='y'), use_container_width=True)
