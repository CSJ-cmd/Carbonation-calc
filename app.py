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

# 모바일 가독성 최적화 CSS
st.markdown("""
    <style>
    .stTabs [data-baseweb="tab-list"] { gap: 2px; }
    .stTabs [data-baseweb="tab"] {
        height: 50px; white-space: pre-wrap; background-color: #f0f2f6;
        border-radius: 4px 4px 0px 0px; gap: 1px; padding-top: 10px; padding-bottom: 10px;
    }
    [data-testid="stMetricValue"] { font-size: 1.2rem !important; }
    /* 통계 컨테이너 여백 조정 */
    [data-testid="stVerticalBlock"] > [style*="flex-direction: column;"] > [data-testid="stVerticalBlock"] {
        gap: 0.5rem;
    }
    </style>
""", unsafe_allow_html=True)

# =========================================================
# 2. 전역 함수 정의
# =========================================================

def get_angle_correction(R_val, angle):
    """ 타격 방향 보정값 반환 """
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
    """ 재령 보정계수 반환 """
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
    """ 
    강도 산정 로직 
    Returns: 모든 공식 결과값 + 설계강도 기준에 따른 평균값
    """
    if len(readings) < 5: return False, "데이터 부족 (5개 미만)"
    
    # 이상치 제거
    avg1 = sum(readings) / len(readings)
    valid = [r for r in readings if avg1*0.8 <= r <= avg1*1.2]
    discard_cnt = len(readings) - len(valid)
    
    if len(readings) >= 20 and discard_cnt > 4: return False, f"시험 무효 (기각 {discard_cnt}개)"
    if not valid: return False, "유효 데이터 없음"
        
    R_final = sum(valid) / len(valid)
    corr = get_angle_correction(R_final, angle)
    R0 = R_final + corr
    age_c = get_age_coefficient(days)
    
    # 5가지 추정식 모두 계산
    f_aij = max(0, (7.3 * R0 + 100) * 0.098 * age_c)        
    f_jsms = max(0, (1.27 * R0 - 18.0) * age_c)             
    f_mst = max(0, (15.2 * R0 - 112.8) * 0.098 * age_c)     
    f_kwon = max(0, (2.304 * R0 - 38.80) * age_c)           
    f_kalis = max(0, (1.3343 * R0 + 8.1977) * age_c)
    
    # 설계강도 기준 평균값 계산용 리스트
    target_values = []
    if design_fck < 40:
        target_values = [f_aij, f_jsms] # 일반강도
    else:
        target_values = [f_mst, f_kwon, f_kalis] # 고강도
    
    s_mean = np.mean(target_values) if target_values else 0
    
    # 모든 결과 반환
    return True, {
        "R_avg": R_final, "R0": R0, "Age_Coeff": age_c,
        "Discard": discard_cnt, 
        "Formulas": { # 딕셔너리로 전체 결과 반환
            "일본건축": f_aij,
            "일본재료": f_jsms,
            "과기부": f_mst,
            "권영웅": f_kwon,
            "KALIS": f_kalis
        },
        "Mean_Strength": s_mean
    }

def convert_df(df):
    """ CSV 다운로드 변환 """
    return df.to_csv(index=False).encode('utf-8-sig')

# =========================================================
# 3. 메인 화면 UI
# =========================================================

st.title("🏗️ 안전진단 Pro")

with st.sidebar:
    st.header("⚙️ 설정")
    project_name = st.text_input("프로젝트명", "OO교량")
    inspector = st.text_input("진단자", "홍길동")

tab1, tab2, tab3 = st.tabs(["🧪 탄산화", "🔨 반발경도", "📈 통계·비교"])

# ---------------------------------------------------------
# [Tab 1] 탄산화 평가
# ---------------------------------------------------------
with tab1:
    st.subheader("탄산화 깊이 평가")
    with st.container(border=True):
        c1, c2 = st.columns(2)
        with c1: measured_depth = st.number_input("측정 깊이(mm)", 0.0, 100.0, 12.0, 0.1, format="%.1f")
        with c2: design_cover = st.number_input("설계 피복(mm)", 10.0, 200.0, 40.0, 1.0)
        age_years = st.number_input("경과 년수(년)", 1, 100, 20)
            
    if st.button("평가 실행", type="primary", key="btn_carb", use_container_width=True):
        remaining = design_cover - measured_depth
        rate_coeff = measured_depth / math.sqrt(age_years) if age_years > 0 else 0
        life_str = "계산 불가"
        is_danger = False
        grade, color, desc = "판정 불가", "gray", ""

        if rate_coeff > 0:
            total_time = (design_cover / rate_coeff) ** 2
            life_years = total_time - age_years
            if remaining <= 0:
                life_str = "🚨 0년 (도달)"
                is_danger = True
            elif life_years > 0:
                life_str = f"{life_years:.1f} 년"
            else:
                life_str = "0년 (임박)"
        elif measured_depth == 0:
            life_str = "99년 이상"

        if remaining >= 30: grade, color, desc = "A", "green", "매우 양호"
        elif remaining >= 10: grade, color, desc = "B", "blue", "양호"
        elif remaining >= 0: grade, color, desc = "C", "orange", "보통"
        else: grade, color, desc = "D", "red", "불량"
        
        with st.container(border=True):
            st.markdown(f"### 결과: :{color}[{grade} 등급]")
            st.caption(desc)
            st.divider()
            m1, m2 = st.columns(2)
            m1.metric("잔여 깊이", f"{remaining:.1f} mm")
            m2.metric("예측 수명", life_str)
            if is_danger: st.error("경고: 철근 위치 도달!")

# ---------------------------------------------------------
# [Tab 2] 반발경도 평가
# ---------------------------------------------------------
with tab2:
    st.subheader("반발경도 강도 산정")
    
    mode = st.radio(
        "입력 방식", 
        ["단일 입력", "다중 입력 (Batch)", "파일 업로드"], 
        horizontal=True,
        label_visibility="collapsed"
    )

    # [Mode A] 단일 지점 입력
    if mode == "단일 입력":
        with st.container(border=True):
            c1, c2 = st.columns(2)
            with c1: angle_opt = st.selectbox("타격 방향", [0, -90, -45, 45, 90], format_func=lambda x: f"{x}°")
            with c2: days_inp = st.number_input("재령(일)", 10, 10000, 1000)
            design_fck = st.number_input("설계강도(MPa)", 15.0, 100.0, 24.0, help="40MPa 이상일 경우 고강도 공식이 적용됩니다.")
            input_txt = st.text_area("측정값 (20개)", "54 56 55 53 58 55 54 55 52 57 55 56 54 55 59 42 55 56 54 55", height=100)
            
        if st.button("계산 실행", type="primary", key="btn_single", use_container_width=True):
            clean = input_txt.replace(',', ' ').replace('\n', ' ')
            readings = [float(x) for x in clean.split() if x.strip()]
            
            success, res = calculate_strength(readings, angle_opt, days_inp, design_fck)
            
            if not success:
                st.error(res)
            else:
                s_mean = res["Mean_Strength"]
                ratio = (s_mean / design_fck) * 100
                grade_mk = "A" if ratio >= 100 else ("B" if ratio >= 90 else ("C" if ratio >= 75 else "D/E"))
                applied_type = "고강도(≥40MPa)" if design_fck >= 40 else "일반강도(<40MPa)"
                
                with st.container(border=True):
                    st.success(f"평균: **{s_mean:.2f} MPa** ({ratio:.0f}%) → **{grade_mk}**")
                    st.caption(f"ℹ️ 적용 기준: {applied_type} 공식 자동 선택됨")
                    
                    df_res = pd.DataFrame({
                        "공식": res["Formulas"].keys(),
                        "강도": res["Formulas"].values()
                    })
                    
                    base = alt.Chart(df_res).encode(x=alt.X('공식', sort=None), y='강도')
                    bars = base.mark_bar().encode(
                        color=alt.condition(
                            alt.datum.강도 >= design_fck,
                            alt.value('#4D96FF'), 
                            alt.value('#FF6B6B') 
                        )
                    )
                    rule = alt.Chart(pd.DataFrame({'y': [design_fck]})).mark_rule(
                        color='red', strokeDash=[5, 3], size=2
                    ).encode(y='y')
                    
                    st.altair_chart(bars + rule, use_container_width=True)

                    st.dataframe(
                        df_res.style.format({"강도": "{:.2f}"})
                        .highlight_max(subset=["강도"], color="#d6eaf8"),
                        use_container_width=True, hide_index=True
                    )

    # [Mode B] 다중 지점 직접 입력 (Batch)
    elif mode == "다중 입력 (Batch)":
        with st.expander("ℹ️ 사용법 및 데이터 붙여넣기", expanded=True):
            st.caption("엑셀 복사: `지점명` `각도` `재령` `설계강도` `측정값20개`")
            batch_input = st.text_area(
                "Raw Data", height=100, placeholder="P1 0 1000 24 55 56 ...", label_visibility="collapsed"
            )

        # 초기 데이터 파싱
        initial_data = []
        if batch_input.strip():
            lines = batch_input.strip().split('\n')
            for line in lines:
                if not line.strip(): continue
                if '\t' in line: parts = line.split('\t')
                elif ',' in line: parts = line.split(',')
                else: parts = line.split()
                parts = [p.strip() for p in parts if p.strip()]
                
                try:
                    loc_name = parts[0]
                    try: float(parts[1]) 
                    except: continue 
                    try: angle_val = int(float(parts[1]))
                    except: angle_val = 0
                    try: age_val = int(float(parts[2]))
                    except: age_val = 1000
                    try: fck_val = float(parts[3])
                    except: fck_val = 24.0
                    readings_str = " ".join(parts[4:])
                    initial_data.append({
                        "선택": True, "지점": loc_name, "각도": angle_val, 
                        "재령": age_val, "설계": fck_val, "데이터": readings_str
                    })
                except: continue

        if not initial_data:
            df_input = pd.DataFrame(columns=["선택", "지점", "각도", "재령", "설계", "데이터"])
        else:
            df_input = pd.DataFrame(initial_data)

        st.markdown("👇 **데이터 편집** (아래 표에서 수정 가능)")
        edited_df = st.data_editor(
            df_input,
            column_config={
                "선택": st.column_config.CheckboxColumn("V", width="small"),
                "지점": st.column_config.TextColumn("지점", width="small"),
                "각도": st.column_config.SelectboxColumn("각도", options=[-90, -45, 0, 45, 90], width="small", required=True),
                "재령": st.column_config.NumberColumn("재령", width="small"),
                "설계강도": st.column_config.NumberColumn("설계강도", width="small"),
                "데이터": st.column_config.TextColumn("측정값", width="large")
            },
            hide_index=True, num_rows="dynamic", use_container_width=True
        )

        if st.button("🚀 일괄 계산 실행", type="primary", key="btn_batch_edit", use_container_width=True):
            if edited_df.empty:
                st.warning("입력된 데이터가 없습니다.")
            else:
                results = []
                success_count = 0
                
                with st.status("분석 진행 중...", expanded=True) as status:
                    for idx, row in edited_df.iterrows():
                        if not row["선택"]: continue
                        raw_str = str(row["데이터"]).replace(',', ' ')
                        try: readings = [float(x) for x in raw_str.split() if x.replace('.','',1).isdigit()]
                        except: readings = []

                        success, res = calculate_strength(readings, row["각도"], row["재령"], row["설계"])
                        
                        entry = {
                            "지점": row["지점"], 
                            "설계": row["설계"], 
                            "결과": "실패", 
                            "평균강도": 0.0, 
                            "등급": "-",
                            "일본건축": 0.0, "일본재료": 0.0, "과기부": 0.0, "권영웅": 0.0, "KALIS": 0.0
                        }
                        
                        if success:
                            s_mean = res["Mean_Strength"]
                            ratio = (s_mean / row["설계"]) * 100 if row["설계"] > 0 else 0
                            grade_mk = "A" if ratio >= 100 else ("B" if ratio >= 90 else ("C" if ratio >= 75 else "D/E"))
                            
                            entry.update({
                                "결과": "성공", 
                                "평균강도": round(s_mean, 2), 
                                "등급": grade_mk,
                                "일본건축": round(res["Formulas"]["일본건축"], 1),
                                "일본재료": round(res["Formulas"]["일본재료"], 1),
                                "과기부": round(res["Formulas"]["과기부"], 1),
                                "권영웅": round(res["Formulas"]["권영웅"], 1),
                                "KALIS": round(res["Formulas"]["KALIS"], 1)
                            })
                            success_count += 1
                        results.append(entry)
                    status.update(label="분석 완료!", state="complete", expanded=False)
                
                if results:
                    df_final = pd.DataFrame(results)
                    
                    st.markdown("### 📊 분석 결과 그래프")
                    
                    base_b = alt.Chart(df_final).encode(x=alt.X('지점', sort=None))
                    
                    bars_b = base_b.mark_bar().encode(
                        y=alt.Y('평균강도', title='평균강도 (MPa)'),
                        color=alt.condition(
                            alt.datum.평균강도 >= alt.datum.설계,
                            alt.value('#4D96FF'),
                            alt.value('#FF6B6B')
                        ),
                        tooltip=['지점', '평균강도', '설계', '등급']
                    )
                    
                    ticks_b = base_b.mark_tick(
                        color='red', thickness=3, size=30
                    ).encode(
                        y='설계',
                        tooltip=['설계']
                    )
                    
                    st.altair_chart(bars_b + ticks_b, use_container_width=True)

                    cols = ["지점", "설계", "평균강도", "등급", "일본건축", "일본재료", "과기부", "권영웅", "KALIS"]
                    
                    st.dataframe(
                        df_final[cols].style.format({
                            "평균강도": "{:.2f}", 
                            "설계": "{:.1f}", 
                            "일본건축": "{:.1f}", 
                            "일본재료": "{:.1f}", 
                            "과기부": "{:.1f}", 
                            "권영웅": "{:.1f}", 
                            "KALIS": "{:.1f}"
                        })
                        .applymap(lambda v: 'color: red; font-weight: bold;' if v == '실패' or v == 'D/E' else None),
                        use_container_width=True, hide_index=True
                    )
                    st.download_button("CSV 저장", convert_df(df_final[cols]), f"{project_name}_Batch.csv", "text/csv", use_container_width=True)

    # [Mode C] 파일 업로드
    elif mode == "파일 업로드":
        with st.container(border=True):
            st.caption("양식: Location, Angle, Age, Design_Fck, Readings")
            uploaded_file = st.file_uploader("파일 선택", type=["csv", "xlsx"], label_visibility="collapsed")
        
        if uploaded_file:
            try:
                if uploaded_file.name.endswith('.csv'): df_upload = pd.read_csv(uploaded_file)
                else: df_upload = pd.read_excel(uploaded_file)
                st.success("파일 업로드 성공 (분석 로직은 Batch 모드 참조)")
            except Exception as e:
                st.error(f"오류: {e}")

# ---------------------------------------------------------
# [Tab 3] 강도 통계 및 비교 (모바일 최적화 및 통계 추가)
# ---------------------------------------------------------
with tab3:
    st.subheader("통계 및 안전성 평가")
    
    with st.container(border=True):
        c1, c2 = st.columns([1, 2])
        with c1: design_fck_stats = st.number_input("설계강도", 15.0, 100.0, 24.0)
        with c2: input_stats = st.text_area("강도 데이터 (MPa)", height=68, placeholder="21.5 22.1 ...")
        
    if st.button("분석 실행", key="btn_stat", use_container_width=True):
        try:
            data_s = [float(x) for x in input_stats.replace(',',' ').split() if x.strip()]
            if len(data_s) < 2:
                st.warning("데이터 2개 이상 필요")
            else:
                # 통계 계산
                st_mean = np.mean(data_s)
                st_std = np.std(data_s, ddof=1)
                st_cov = (st_std / st_mean * 100) if st_mean > 0 else 0
                st_max = np.max(data_s)
                st_min = np.min(data_s)

                ratio = (st_mean / design_fck_stats) * 100
                grade_mk = "A" if ratio >= 100 else ("B" if ratio >= 90 else ("C" if ratio >= 75 else "D/E"))
                
                # 1. 종합 판정 (카드형)
                with st.container(border=True):
                    st.markdown("#### 📊 종합 판정")
                    c1, c2 = st.columns(2)
                    c1.metric("평균 강도", f"{st_mean:.2f} MPa")
                    c2.metric("판정", f"{grade_mk}", delta=f"{ratio:.0f}%")

                # 2. 상세 통계 (2열 배치 - 모바일 최적화)
                with st.container(border=True):
                    st.markdown("#### 📈 상세 통계")
                    r1c1, r1c2 = st.columns(2)
                    r1c1.metric("최대값 (Max)", f"{st_max:.2f}")
                    r1c2.metric("최소값 (Min)", f"{st_min:.2f}")
                    
                    r2c1, r2c2 = st.columns(2)
                    r2c1.metric("표준편차", f"{st_std:.2f}")
                    r2c2.metric("변동계수", f"{st_cov:.1f}%")
                
                # 3. 차트 (Altair)
                chart_df = pd.DataFrame({"순번": range(1, len(data_s)+1), "강도": sorted(data_s)})
                
                bars = alt.Chart(chart_df).mark_bar().encode(
                    x=alt.X('순번:O'), y=alt.Y('강도:Q'),
                    color=alt.condition(alt.datum.강도 < design_fck_stats, alt.value('#FF6B6B'), alt.value('#4D96FF'))
                )
                
                rule = alt.Chart(pd.DataFrame({'y': [design_fck_stats]})).mark_rule(
                    color='red', strokeDash=[5, 3], size=2
                ).encode(y='y')
                
                st.altair_chart(bars + rule, use_container_width=True)
                
                with st.expander("상세 데이터 목록"):
                    st.dataframe(pd.DataFrame(data_s, columns=["강도"]), hide_index=True, use_container_width=True)

        except:
            st.error("입력 오류")

