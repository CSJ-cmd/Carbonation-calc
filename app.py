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
# 2. 전역 함수 정의 (전문 로직 유지)
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
    """ 재령 보정계수 (지침 기준, 기본값 3000일 적용) """
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
    return True, {"R_initial": avg1, "R_avg": R_avg, "Angle_Corr": corr, "R0": R0, "Age_Coeff": age_c, "Discard": len(excluded), "Excluded": excluded, "Formulas": {"일본건축": f_aij, "일본재료": f_jsms, "과기부": f_mst, "권영웅": f_kwon, "KALIS": f_kalis}, "Mean_Strength": s_mean}

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

tab1, tab2, tab3, tab4 = st.tabs(["📖 점검 매뉴얼", "🔨 반발경도", "🧪 탄산화", "📈 통계·비교"])

# ---------------------------------------------------------
# [Tab 1] 점검 매뉴얼 (기존 구성 유지)
# ---------------------------------------------------------
with tab1:
    st.subheader("💡 프로그램 사용 가이드")
    st.info("""
    **1. 반발경도 산정 시 설계기준강도를 입력해주세요.**
    * 설계기준강도를 바탕으로 압축강도 추정에 필요한 공식 적용 로직이 자동으로 변경됩니다.
    
    **2. 타격방향 보정 값을 매뉴얼을 참고해서 상향 타격인지 하향타격인지를 구분해서 선택해주세요.**
    
    **3. 재령 등 별도로 적용하지 않을 시 프로그램상에서 재령 3000일, 설계기준강도 24MPa가 적용됩니다.**
    
    **4. 통계ㆍ비교 탭 활용 안내**
    * 추정된 압축강도의 표준편차와 변동계수 등을 계산하여 해당 시설물에 가장 적합한 산정식을 확인하고 검토하기 위함입니다.
    * 설계기준강도 입력 및 압축강도 추정에 사용된 공식을 선택해주세요. 입력된 설계기준 강도 값을 바탕으로 프로그램상에서 평균강도 산정 공식을 선별합니다.
    """)
    st.divider()
    with st.expander("1. 반발경도 시험 상세 지침"):
        m_df = pd.DataFrame({"구분": ["상향 수직", "상향 경사", "수평 타격", "하향 경사", "하향 수직"], "각도 (α)": ["+90°", "+45°", "0°", "-45°", "-90°"], "부재 예시": ["슬래브 하부", "보 경사면", "벽체, 기둥", "교대 경사", "슬래브 상면"]})
        st.table(m_df)
    with st.expander("2. 탄산화 등급 판정"):
        st.write("- **A 등급**: $\ge 30mm$ / **B 등급**: $\ge 10mm$ / **C 등급**: $\ge 0mm$ / **D 등급**: $< 0mm$")

# ---------------------------------------------------------
# [Tab 2] 반발경도 평가 (원본 유지)
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
                chart = alt.Chart(df_f).mark_bar().encode(x=alt.X('공식', sort=None), y='강도', color=alt.condition(alt.datum.강도 >= fck, alt.value('#4D96FF'), alt.value('#FF6B6B'))).properties(height=350)
                st.altair_chart(chart + alt.Chart(pd.DataFrame({'y': [fck]})).mark_rule(color='red', strokeDash=[5, 3], size=2).encode(y='y'), use_container_width=True)
    else:
        uploaded_file = st.file_uploader("CSV 또는 Excel 파일 업로드", type=["csv", "xlsx"])
        init_data = []
        if uploaded_file:
            try:
                df_up = pd.read_csv(uploaded_file) if uploaded_file.name.endswith('.csv') else pd.read_excel(uploaded_file)
                for _, row in df_up.iterrows(): init_data.append({"선택": True, "지점": row.get("지점", "P"), "각도": int(row.get("각도", 0)), "재령": int(row.get("재령", 3000)), "설계": float(row.get("설계", 24.0)), "데이터": str(row.get("데이터", ""))})
            except: st.error("파일 파싱 실패")
        df_batch = pd.DataFrame(init_data) if init_data else pd.DataFrame(columns=["선택","지점","각도","재령","설계","데이터"])
        edited_df = st.data_editor(df_batch, column_config={"선택": st.column_config.CheckboxColumn("선택", default=True), "각도": st.column_config.SelectboxColumn("각도 (α)", options=[90, 45, 0, -45, -90], required=True), "재령": st.column_config.NumberColumn("재령", default=3000), "설계": st.column_config.NumberColumn("설계", default=24)}, use_container_width=True, hide_index=True, num_rows="dynamic")
        if st.button("🚀 일괄 계산 실행", type="primary", use_container_width=True):
            batch_res = []
            for _, row in edited_df.iterrows():
                if not row["선택"]: continue
                try:
                    rd_list = [float(x) for x in str(row["데이터"]).replace(',',' ').split() if x.replace('.','',1).isdigit()]
                    ang_v, age_v, fck_v = (0 if pd.isna(row["각도"]) else row["각도"]), (3000 if pd.isna(row["재령"]) else row["재령"]), (24 if pd.isna(row["설계"]) else row["설계"])
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
# [Tab 3] 탄산화 평가 (상세 데이터 지표를 상단으로 재정렬)
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
        
        # 1. 등급 결과 및 상세 계산 지표 (그래프 위로 이동)
        st.markdown(f"### 결과: :{color}[{grade} 등급]")
        with st.container(border=True):
            cc1, cc2, cc3 = st.columns(3)
            cc1.metric("잔여 피복량", f"{rem:.1f} mm")
            cc2.metric("속도 계수 (A)", f"{rate_a:.3f}")
            cc3.metric("예측 잔여수명", f"{max(0, res_life):.1f} 년")
            st.info(f"**계산 근거:** $A = {m_depth} / \\sqrt{{{a_years}}} = {rate_a:.3f}$, 잔여수명 $T = ({d_cover}/{rate_a:.3f})^2 - {a_years} = {res_life:.1f}$년")
        
        # 2. 탄산화 예측 그래프 (상세 지표 아래로 이동)
        year_steps = np.linspace(0, 100, 101)
        depth_steps = rate_a * np.sqrt(year_steps)
        df_plot = pd.DataFrame({'경과년수': year_steps, '탄산화깊이': depth_steps})
        
        line = alt.Chart(df_plot).mark_line(color='#1f77b4').encode(x=alt.X('경과년수:Q', title='경과년수 (년)'), y=alt.Y('탄산화깊이:Q', title='탄산화 깊이 (mm)'))
        rule = alt.Chart(pd.DataFrame({'y': [d_cover]})).mark_rule(color='red', strokeDash=[5,5], size=2).encode(y='y')
        point = alt.Chart(pd.DataFrame({'x': [a_years], 'y': [m_depth]})).mark_point(color='orange', size=100, filled=True).encode(x='x', y='y')
        st.altair_chart(line + rule + point, use_container_width=True)

# ---------------------------------------------------------
# [Tab 4] 통계 및 비교 (원본 유지)
# ---------------------------------------------------------
with tab4:
    st.subheader("📊 강도 통계 및 비교 분석")
    c1, c2 = st.columns([1, 2])
    with c1: st_fck = st.number_input("기준 설계강도(MPa)", 15.0, 100.0, 24.0, key="stat_fck")
    with c2: raw_txt = st.text_area("강도 데이터 목록", "24.5 26.2 23.1 21.8 25.5 27.0", height=68)
    parsed = [float(x) for x in raw_txt.replace(',',' ').split() if x.replace('.','',1).isdigit()]
    if parsed:
        df_stat = pd.DataFrame({"순번": range(1, len(parsed) + 1), "추정강도": parsed, "적용공식": ["전체평균(추천)"] * len(parsed)})
        label_df = st.data_editor(df_stat, column_config={"순번": st.column_config.NumberColumn("No.", disabled=True), "적용공식": st.column_config.SelectboxColumn("공식 선택", options=["일본건축", "일본재료", "과기부", "권영웅", "KALIS", "전체평균(추천)"], required=True)}, use_container_width=True, hide_index=True)
        if st.button("통계 분석 실행", type="primary", use_container_width=True):
            valid_f = ["일본건축", "일본재료", "전체평균(추천)"] if st_fck < 40 else ["과기부", "권영웅", "KALIS", "전체평균(추천)"]
            filtered = label_df[label_df["적용공식"].isin(valid_f)]
            data = sorted(filtered["추정강도"].tolist())
            if len(data) >= 2:
                avg_v, std_v = np.mean(data), np.std(data, ddof=1)
                with st.container(border=True):
                    m1, m2, m3 = st.columns(3)
                    m1.metric("평균", f"{avg_v:.2f} MPa", delta=f"{(avg_v/st_fck*100):.1f}%"); m2.metric("표준편차 (σ)", f"{std_v:.2f} MPa"); m3.metric("변동계수 (CV)", f"{(std_v/avg_v*100):.1f}%")
                st.altair_chart(alt.Chart(pd.DataFrame({"번호": range(1, len(data)+1), "강도": data})).mark_bar().encode(x='번호:O', y='강도:Q', color=alt.condition(alt.datum.강도 >= st_fck, alt.value('#4D96FF'), alt.value('#FF6B6B'))) + alt.Chart(pd.DataFrame({'y':[st_fck]})).mark_rule(color='red', strokeDash=[5,3], size=2).encode(y='y'), use_container_width=True)

