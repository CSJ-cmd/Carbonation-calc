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
    layout="wide"
)

# =========================================================
# 2. 전역 함수 정의 (계산 로직)
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

def calculate_strength(readings, angle, days):
    """ 
    단일 지점 강도 계산 함수 
    Returns: (성공여부, 결과Dict/에러메시지)
    """
    if len(readings) < 5:
        return False, "데이터 부족 (5개 미만)"
    
    # 이상치 제거
    avg1 = sum(readings) / len(readings)
    valid = [r for r in readings if avg1*0.8 <= r <= avg1*1.2]
    discard_cnt = len(readings) - len(valid)
    
    # 기각 판정 (20% 초과)
    if len(readings) >= 20 and discard_cnt > 4:
        return False, f"시험 무효 (기각 {discard_cnt}개)"
    
    if not valid:
        return False, "유효 데이터 없음"
        
    # 강도 계산
    R_final = sum(valid) / len(valid)
    corr = get_angle_correction(R_final, angle)
    R0 = R_final + corr
    age_c = get_age_coefficient(days)
    
    # 5개 공식
    f_aij = (7.3 * R0 + 100) * 0.098 * age_c        
    f_jsms = (1.27 * R0 - 18.0) * age_c             
    f_mst = (15.2 * R0 - 112.8) * 0.098 * age_c     
    f_kwon = (2.304 * R0 - 38.80) * age_c           
    f_kalis = (1.3343 * R0 + 8.1977) * age_c 
    
    est_list = [max(0, x) for x in [f_aij, f_jsms, f_mst, f_kwon, f_kalis]]
    s_mean = np.mean(est_list)
    
    return True, {
        "R_avg": R_final,
        "R0": R0,
        "Age_Coeff": age_c,
        "Discard": discard_cnt,
        "Est_Strengths": est_list,
        "Mean_Strength": s_mean
    }

def convert_df(df):
    return df.to_csv(index=False).encode('utf-8-sig')

# =========================================================
# 3. 메인 화면 UI
# =========================================================

st.title("🏗️ 구조물 안전진단 통합 평가 System")
st.markdown("정밀안전진단 기준에 따른 **탄산화**, **반발경도(일괄처리)**, **통계 및 안전성 평가** 도구입니다.")

# 사이드바
with st.sidebar:
    st.header("📝 프로젝트 설정")
    project_name = st.text_input("프로젝트명", "OO교량 안전진단")
    inspector = st.text_input("진단자", "홍길동")
    st.divider()
    st.markdown("### 💡 사용 팁")
    st.info("""
    **데이터 입력 방식**
    1. **단일 입력**: 1개 지점씩 상세 분석
    2. **다중 직접 입력**: 엑셀 데이터를 복사+붙여넣기
    3. **파일 업로드**: 대량의 CSV/Excel 파일 처리
    """)

tab1, tab2, tab3 = st.tabs(["🧪 1. 탄산화 평가", "🔨 2. 반발경도 평가", "📈 3. 강도 통계 및 비교"])

# ---------------------------------------------------------
# [Tab 1] 탄산화 평가
# ---------------------------------------------------------
with tab1:
    st.header("🧪 탄산화 깊이 및 등급 평가")
    with st.container():
        c1, c2, c3 = st.columns(3)
        with c1: measured_depth = st.number_input("측정 탄산화 깊이 (mm)", 0.0, 100.0, 12.0, 0.1, format="%.1f")
        with c2: design_cover = st.number_input("설계 피복 두께 (mm)", 10.0, 200.0, 40.0, 1.0)
        with c3: age_years = st.number_input("건물 경과 년수 (년)", 1, 100, 20)
            
    if st.button("탄산화 평가 실행", type="primary", key="btn_carb"):
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

        if remaining >= 30: grade, color, desc = "A 등급", "green", "매우 양호"
        elif remaining >= 10: grade, color, desc = "B 등급", "blue", "양호"
        elif remaining >= 0: grade, color, desc = "C 등급", "orange", "보통"
        else: grade, color, desc = "D 등급", "red", "불량"
        
        st.divider()
        m1, m2, m3 = st.columns(3)
        m1.metric("잔여 깊이", f"{remaining:.1f} mm")
        m2.metric("속도 계수", f"{rate_coeff:.4f}")
        m3.metric("예측 수명", life_str)
        if is_danger: st.error("경고: 철근 위치 도달")
        st.markdown(f"<h3 style='color:{color}'>{grade} ({desc})</h3>", unsafe_allow_html=True)

# ---------------------------------------------------------
# [Tab 2] 반발경도 평가 (3가지 모드)
# ---------------------------------------------------------
with tab2:
    st.header("🔨 반발경도 강도 산정")
    
    mode = st.radio(
        "작업 모드 선택", 
        ["📝 단일 지점 입력", "📋 다중 지점 직접 입력 (Batch)", "📂 파일 업로드 (Excel/CSV)"], 
        horizontal=True
    )
    st.divider()

    # [Mode A] 단일 지점 입력
    if mode == "📝 단일 지점 입력":
        with st.container():
            col1, col2, col3 = st.columns(3)
            with col1: angle_opt = st.selectbox("타격 방향", [0, -90, -45, 45, 90], format_func=lambda x: f"{x}°")
            with col2: days_inp = st.number_input("재령 (일수)", 10, 10000, 1000)
            with col3: design_fck = st.number_input("설계강도 (MPa)", 15.0, 100.0, 24.0)
            
            input_txt = st.text_area("측정값 (20개)", "54 56 55 53 58 55 54 55 52 57 55 56 54 55 59 42 55 56 54 55", height=70)
            
        if st.button("계산 실행", type="primary", key="btn_single"):
            clean = input_txt.replace(',', ' ').replace('\n', ' ')
            readings = [float(x) for x in clean.split() if x.strip()]
            
            success, res = calculate_strength(readings, angle_opt, days_inp)
            
            if not success:
                st.error(res)
            else:
                s_mean = res["Mean_Strength"]
                ratio = (s_mean / design_fck) * 100
                grade_mk = "A (우수)" if ratio >= 100 else ("B (양호)" if ratio >= 90 else ("C (미흡)" if ratio >= 75 else "D/E (부족)"))
                
                st.success(f"✅ 평균 추정강도: **{s_mean:.2f} MPa** (설계 대비 {ratio:.1f}%) → 등급: **{grade_mk}**")
                
                df_res = pd.DataFrame({
                    "공식": ["일본건축", "일본재료", "과기부", "권영웅", "KALIS"],
                    "강도(MPa)": res["Est_Strengths"]
                })
                
                # [수정] 딕셔너리 포맷팅 적용
                st.dataframe(
                    df_res.style.format({"강도(MPa)": "{:.2f}"})
                    .highlight_max(subset=["강도(MPa)"], color="#d6eaf8"),
                    use_container_width=True
                )

# =========================================================
    # [Mode B] 다중 지점 직접 입력 (Batch) - (Data Editor 적용)
    # =========================================================
    elif mode == "📋 다중 지점 직접 입력 (Batch)":
        st.info("💡 엑셀 데이터를 붙여넣은 후, 아래 표에서 **각도나 재령을 클릭하여 수정**할 수 있습니다.")
        
        # 1. 초기 데이터 입력을 위한 텍스트 영역
        with st.expander("📝 데이터 붙여넣기 (Excel 복사)", expanded=True):
            st.markdown("""
            **붙여넣기 요령**: `지점명` ... `측정값(20개)` 순서로 복사하세요.
            (각도, 재령, 설계강도는 비워두거나 0으로 넣어도 아래 표에서 수정 가능합니다.)
            """)
            batch_input = st.text_area(
                "Raw Data Input", 
                height=150, 
                placeholder="P1-Top  0  1000  24  55  56 ... (엑셀에서 복사해서 붙여넣기)",
                label_visibility="collapsed"
            )

        # 2. 텍스트 -> 데이터프레임 변환 (Pre-processing)
        initial_data = []
        if batch_input.strip():
            lines = batch_input.strip().split('\n')
            for line in lines:
                if not line.strip(): continue
                # 구분자 처리
                if '\t' in line: parts = line.split('\t')
                elif ',' in line: parts = line.split(',')
                else: parts = line.split()
                
                parts = [p.strip() for p in parts if p.strip()]
                
                # 헤더 건너뛰기용 (숫자 체크)
                try:
                    # 데이터 파싱 시도 (최소한 지점명은 있다고 가정)
                    loc_name = parts[0]
                    
                    # 각도/재령/강도가 텍스트에 있으면 가져오고, 없거나 오류나면 기본값 설정
                    try: angle_val = int(float(parts[1]))
                    except: angle_val = 0
                    
                    try: age_val = int(float(parts[2]))
                    except: age_val = 1000 # 기본값
                    
                    try: fck_val = float(parts[3])
                    except: fck_val = 24.0 # 기본값
                    
                    # 측정값만 추출 (나머지 부분)
                    readings_str = " ".join(parts[4:])
                    
                    initial_data.append({
                        "지점명": loc_name,
                        "타격방향": angle_val,
                        "재령(일)": age_val,
                        "설계강도": fck_val,
                        "측정값(20개)": readings_str,
                        "선택": True # 계산 포함 여부 체크박스
                    })
                except:
                    continue

        # 데이터가 없으면 빈 템플릿 표시
        if not initial_data:
            df_input = pd.DataFrame(columns=["선택", "지점명", "타격방향", "재령(일)", "설계강도", "측정값(20개)"])
        else:
            df_input = pd.DataFrame(initial_data)

        st.divider()
        st.markdown("#### 🛠️ 데이터 편집 및 설정 (개별 선택 가능)")
        
        # 3. Data Editor (핵심 기능: 여기서 수정 가능)
        edited_df = st.data_editor(
            df_input,
            column_config={
                "선택": st.column_config.CheckboxColumn(
                    "계산",
                    help="체크 해제 시 계산에서 제외됩니다.",
                    default=True,
                    width="small"
                ),
                "지점명": st.column_config.TextColumn("지점명", width="medium"),
                "타격방향": st.column_config.SelectboxColumn(
                    "타격방향(°)",
                    options=[-90, -45, 0, 45, 90], # 드롭다운 선택 가능!
                    help="0:수평, -90:하향, 90:상향",
                    width="small",
                    required=True
                ),
                "재령(일)": st.column_config.NumberColumn(
                    "재령(일)",
                    min_value=10, max_value=10000, step=10,
                    width="small"
                ),
                "설계강도": st.column_config.NumberColumn(
                    "설계강도(MPa)",
                    min_value=15.0, max_value=100.0, step=1.0, format="%.1f",
                    width="small"
                ),
                "측정값(20개)": st.column_config.TextColumn(
                    "측정값 (공백 구분)",
                    width="large",
                    help="20개의 반발경도 값을 공백으로 구분하여 입력하세요."
                )
            },
            hide_index=True,
            num_rows="dynamic", # 행 추가/삭제 가능
            use_container_width=True
        )

        # 4. 계산 실행 버튼
        if st.button("🚀 위 설정대로 일괄 계산 실행", type="primary", key="btn_batch_edit"):
            if edited_df.empty:
                st.warning("데이터가 없습니다.")
            else:
                results = []
                success_count = 0
                
                # 진행률 표시
                progress_bar = st.progress(0)
                total_rows = len(edited_df)

                for idx, row in edited_df.iterrows():
                    # 체크박스 해제된 행은 건너뜀
                    if not row["선택"]: 
                        progress_bar.progress((idx + 1) / total_rows)
                        continue

                    # 측정값 파싱
                    raw_str = str(row["측정값(20개)"]).replace(',', ' ')
                    try:
                        readings = [float(x) for x in raw_str.split() if x.replace('.','',1).isdigit()]
                    except:
                        readings = []

                    # 계산 함수 호출
                    success, res = calculate_strength(readings, row["타격방향"], row["재령(일)"])
                    
                    entry = {
                        "지점명": row["지점명"],
                        "타격방향": row["타격방향"], # 확인용
                        "설계강도": row["설계강도"],
                        "상태": "성공" if success else "실패",
                        "평균추정강도(MPa)": 0.0,
                        "판정": "-",
                        "비고": ""
                    }
                    
                    if success:
                        s_mean = res["Mean_Strength"]
                        design_fck = row["설계강도"]
                        if design_fck > 0:
                            ratio = (s_mean / design_fck) * 100
                            grade_mk = "A" if ratio >= 100 else ("B" if ratio >= 90 else ("C" if ratio >= 75 else "D/E"))
                        else:
                            ratio = 0
                            grade_mk = "-"
                        
                        entry["평균추정강도(MPa)"] = round(s_mean, 2)
                        entry["설계비(%)"] = round(ratio, 1)
                        entry["판정"] = grade_mk
                        entry["보정후R0"] = round(res["R0"], 1)
                        success_count += 1
                    else:
                        entry["비고"] = res
                        
                    results.append(entry)
                    progress_bar.progress((idx + 1) / total_rows)
                
                # 결과 출력
                if results:
                    st.success(f"✅ 선택된 {success_count}개 지점 분석 완료")
                    df_final = pd.DataFrame(results)
                    
                    # 결과 테이블 (스타일링)
                    st.dataframe(
                        df_final.style.format({"평균추정강도(MPa)": "{:.2f}", "설계비(%)": "{:.1f}"})
                        .applymap(lambda v: 'color: red; font-weight: bold;' if v == '실패' or v == 'D/E' else None),
                        use_container_width=True
                    )
                    
                    # 다운로드 버튼
                    st.download_button(
                        f"📥 결과 다운로드 (CSV)", 
                        convert_df(df_final), 
                        f"{project_name}_Batch_Result.csv", 
                        "text/csv"
                    )
                else:
                    st.warning("계산할 유효한 데이터가 없습니다. (데이터를 입력하거나 '선택' 체크박스를 확인하세요)")

    # [Mode C] 파일 업로드
    elif mode == "📂 파일 업로드 (Excel/CSV)":
        st.info("💡 대량의 데이터를 파일로 업로드하여 처리합니다.")
        with st.expander("📥 입력 양식 다운로드"):
            sample_data = pd.DataFrame({
                "Location": ["P1-Top", "P1-Bottom"],
                "Angle": [0, -90],
                "Age": [1000, 1000],
                "Design_Fck": [24, 24],
                "Readings": ["55 56 54 ...", "45 44 46 ..."]
            })
            st.download_button("양식(CSV) 다운로드", convert_df(sample_data), "반발경도_양식.csv", "text/csv")

        uploaded_file = st.file_uploader("파일 업로드", type=["csv", "xlsx"])
        
        if uploaded_file:
            try:
                if uploaded_file.name.endswith('.csv'): df_upload = pd.read_csv(uploaded_file)
                else: df_upload = pd.read_excel(uploaded_file)
                
                required_cols = ["Location", "Angle", "Age", "Design_Fck", "Readings"]
                if not all(col in df_upload.columns for col in required_cols):
                    st.error(f"❌ 양식이 맞지 않습니다. 필수 컬럼: {required_cols}")
                else:
                    results = []
                    for idx, row in df_upload.iterrows():
                        raw_str = str(row["Readings"]).replace(',', ' ')
                        try: readings = [float(x) for x in raw_str.split() if x.replace('.','',1).isdigit()]
                        except: readings = []
                        success, res = calculate_strength(readings, row["Angle"], row["Age"])
                        
                        entry = {
                            "지점명": row["Location"],
                            "설계강도": row["Design_Fck"],
                            "상태": "성공" if success else "실패",
                            "평균추정강도(MPa)": 0.0,
                            "판정": "-",
                            "비고": ""
                        }
                        if success:
                            s_mean = res["Mean_Strength"]
                            ratio = (s_mean / row["Design_Fck"]) * 100
                            grade_mk = "A" if ratio >= 100 else ("B" if ratio >= 90 else ("C" if ratio >= 75 else "D/E"))
                            entry["평균추정강도(MPa)"] = round(s_mean, 2)
                            entry["설계비(%)"] = round(ratio, 1)
                            entry["판정"] = grade_mk
                            entry["보정후R0"] = round(res["R0"], 1)
                        else:
                            entry["비고"] = res
                        results.append(entry)
                    
                    df_final = pd.DataFrame(results)
                    st.dataframe(df_final.style.format({"평균추정강도(MPa)": "{:.2f}"}), use_container_width=True)
                    st.download_button(f"📥 결과 다운로드", convert_df(df_final), f"{project_name}_파일분석결과.csv", "text/csv")
            except Exception as e:
                st.error(f"오류 발생: {e}")

# ---------------------------------------------------------
# [Tab 3] 강도 통계 및 비교 (설계강도 기준선 추가)
# ---------------------------------------------------------
with tab3:
    st.header("📈 강도 통계 및 안전성 평가")
    st.markdown("##### 📝 산정된 강도 값들을 입력하여 통계를 확인하고 **설계강도**와 비교하세요.")
    
    with st.container():
        c1, c2 = st.columns([1, 2])
        with c1:
            design_fck_stats = st.number_input("설계기준강도 (MPa)", min_value=15.0, max_value=100.0, value=24.0, step=1.0, key="fck_stats")
        with c2:
            input_stats = st.text_area("강도 데이터 입력 (MPa)", placeholder="예: 21.5 22.1 23.0 24.5 ... (공백/줄바꿈 구분)", height=100)
        
    if st.button("분석 실행", key="btn_stat"):
        try:
            data_s = [float(x) for x in input_stats.replace(',',' ').split() if x.strip()]
            if len(data_s) < 2:
                st.warning("데이터가 2개 이상 필요합니다.")
            else:
                st_mean = np.mean(data_s)
                st_std = np.std(data_s, ddof=1)
                st_cov = (st_std / st_mean * 100) if st_mean > 0 else 0
                st_max = np.max(data_s)
                st_min = np.min(data_s)
                
                ratio = (st_mean / design_fck_stats) * 100
                grade_mk = "A (우수)" if ratio >= 100 else ("B (양호)" if ratio >= 90 else ("C (미흡)" if ratio >= 75 else "D/E (부족)"))
                
                st.divider()
                st.success(f"✅ 총 {len(data_s)}개 데이터 분석 완료")
                
                col1, col2, col3, col4 = st.columns(4)
                col1.metric("평균 강도", f"{st_mean:.2f} MPa")
                col2.metric("설계기준강도", f"{design_fck_stats:.1f} MPa")
                col3.metric("강도비 (평균/설계)", f"{ratio:.1f} %", delta=f"{ratio-100:.1f}%")
                col4.metric("종합 판정", grade_mk)
                
                st.markdown("---")
                st.subheader("📊 상세 통계 지표")
                k1, k2, k3, k4 = st.columns(4)
                k1.metric("최대값 (Max)", f"{st_max:.2f} MPa")
                k2.metric("최소값 (Min)", f"{st_min:.2f} MPa")
                k3.metric("표준편차 (SD)", f"{st_std:.2f}")
                k4.metric("변동계수 (COV)", f"{st_cov:.1f} %")
                
                st.markdown("---")
                
                # =================================================
                # [Altair Chart] 시각화 (기준선 추가)
                # =================================================
                v1, v2 = st.columns([2, 1])
                with v1:
                    st.subheader("📉 데이터 분포 및 기준선")
                    
                    # 데이터프레임 생성
                    chart_df = pd.DataFrame({
                        "순번": range(1, len(data_s)+1),
                        "강도": sorted(data_s)
                    })
                    
                    # 1. 막대 그래프
                    bars = alt.Chart(chart_df).mark_bar().encode(
                        x=alt.X('순번:O', title='데이터 순번 (오름차순)'),
                        y=alt.Y('강도:Q', title='압축강도 (MPa)'),
                        color=alt.condition(
                            alt.datum.강도 < design_fck_stats,
                            alt.value('#FF6B6B'),  # 미달 (빨강)
                            alt.value('#4D96FF')   # 정상 (파랑)
                        ),
                        tooltip=['순번', '강도']
                    )
                    
                    # 2. 기준선 (설계강도, 빨간 실선)
                    rule = alt.Chart(pd.DataFrame({'y': [design_fck_stats]})).mark_rule(
                        color='red', strokeWidth=2, strokeDash=[4, 2]
                    ).encode(
                        y='y'
                    )
                    
                    # 3. 기준선 라벨 (텍스트)
                    text = alt.Chart(pd.DataFrame({
                        'y': [design_fck_stats], 
                        'label': [f'설계강도 {design_fck_stats}MPa']
                    })).mark_text(
                        align='left', baseline='bottom', dx=5, color='red', fontWeight='bold'
                    ).encode(
                        y='y', text='label'
                    )
                    
                    # 차트 합치기
                    st.altair_chart(bars + rule + text, use_container_width=True)
                    
                    # 미달 데이터 개수 확인
                    fail_cnt = sum(1 for x in data_s if x < design_fck_stats)
                    if fail_cnt > 0:
                        st.warning(f"⚠️ 설계강도({design_fck_stats} MPa) 미달 데이터가 {fail_cnt}개 있습니다.")
                    else:
                        st.success("✅ 모든 데이터가 설계강도 이상입니다.")

                with v2:
                    st.subheader("📋 데이터 목록")
                    df_list = pd.DataFrame(data_s, columns=["강도(MPa)"])
                    st.dataframe(
                        df_list.style.format({"강도(MPa)": "{:.2f}"})
                        .applymap(lambda v: 'color: red; font-weight: bold;' if v < design_fck_stats else None),
                        use_container_width=True,
                        height=400
                    )
        except:
            st.error("숫자만 입력해주세요.")

