import streamlit as st
import math
import pandas as pd
import numpy as np
import io

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
st.markdown("정밀안전진단 기준에 따른 **탄산화**, **반발경도(일괄처리)**, **통계 분석** 도구입니다.")

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

tab1, tab2, tab3 = st.tabs(["🧪 1. 탄산화 평가", "🔨 2. 반발경도 평가", "📈 3. 강도 통계 (직접 입력)"])

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
    
    # 모드 선택 라디오 버튼 (가로형)
    mode = st.radio(
        "작업 모드 선택", 
        ["📝 단일 지점 입력", "📋 다중 지점 직접 입력 (Batch)", "📂 파일 업로드 (Excel/CSV)"], 
        horizontal=True
    )
    st.divider()

    # =========================================================
    # [Mode A] 단일 지점 입력
    # =========================================================
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
                grade_mk = "A" if ratio >= 100 else ("B" if ratio >= 90 else ("C" if ratio >= 75 else "D/E"))
                
                st.success(f"✅ 평균 추정강도: **{s_mean:.2f} MPa** (설계 대비 {ratio:.1f}%) → 등급: **{grade_mk}**")
                
                # 상세 표
                df_res = pd.DataFrame({
                    "공식": ["일본건축", "일본재료", "과기부", "권영웅", "KALIS"],
                    "강도(MPa)": res["Est_Strengths"]
                })
                st.dataframe(df_res.style.format("{:.2f}").highlight_max(color="#d6eaf8"), use_container_width=True)

    # =========================================================
    # [Mode B] 다중 지점 직접 입력 (Batch) - NEW
    # =========================================================
    elif mode == "📋 다중 지점 직접 입력 (Batch)":
        st.info("💡 엑셀 등에서 데이터를 복사(Ctrl+C)하여 아래에 붙여넣으세요. (탭 또는 콤마로 구분)")
        
        with st.expander("📝 입력 형식 예시 (클릭하여 확인)", expanded=True):
            st.markdown("""
            **형식**: `지점명` | `각도` | `재령` | `설계강도` | `측정값 1` ... `측정값 20`
            (각 항목은 탭(Tab) 또는 콤마(,)로 구분되어야 합니다. 엑셀에서 복사하면 자동으로 탭 구분됩니다.)
            
            **예시 데이터**:
            ```text
            P1-Top	0	1000	24	54	56	55	53	58	55	54	55	52	57	55	56	54	55	59	42	55	56	54	55
            P1-Bot	-90	1000	24	45	46	44	48	45	46	47	44	45	46	45	44	47	48	46	45	44	45	46	47
            ```
            """)

        batch_input = st.text_area("데이터 붙여넣기", height=200, placeholder="여기에 데이터를 붙여넣으세요...")
        
        if st.button("일괄 계산 실행", type="primary", key="btn_batch"):
            if not batch_input.strip():
                st.warning("데이터를 입력해주세요.")
            else:
                results = []
                lines = batch_input.strip().split('\n')
                
                for i, line in enumerate(lines):
                    if not line.strip(): continue
                    
                    # 구분자 처리 (탭 우선, 없으면 콤마)
                    if '\t' in line:
                        parts = line.split('\t')
                    else:
                        parts = line.split(',')
                    
                    # 빈 값 제거
                    parts = [p.strip() for p in parts if p.strip()]
                    
                    if len(parts) < 5:
                        st.error(f"Line {i+1}: 데이터 형식이 올바르지 않습니다. (최소 5개 항목 필요)")
                        continue
                        
                    try:
                        loc_name = parts[0]
                        angle_val = float(parts[1])
                        age_val = float(parts[2])
                        fck_val = float(parts[3])
                        # 나머지 부분은 측정값
                        readings = [float(x) for x in parts[4:]]
                        
                        # 계산 수행
                        success, res = calculate_strength(readings, angle_val, age_val)
                        
                        entry = {
                            "지점명": loc_name,
                            "설계강도": fck_val,
                            "상태": "성공" if success else "실패",
                            "평균추정강도(MPa)": 0.0,
                            "판정": "-",
                            "입력값수": len(readings),
                            "비고": ""
                        }
                        
                        if success:
                            s_mean = res["Mean_Strength"]
                            ratio = (s_mean / fck_val) * 100
                            grade_mk = "A" if ratio >= 100 else ("B" if ratio >= 90 else ("C" if ratio >= 75 else "D/E"))
                            
                            entry["평균추정강도(MPa)"] = round(s_mean, 2)
                            entry["설계비(%)"] = round(ratio, 1)
                            entry["판정"] = grade_mk
                            entry["보정후R0"] = round(res["R0"], 1)
                            entry["기각수"] = res["Discard"]
                        else:
                            entry["비고"] = res
                            
                        results.append(entry)
                        
                    except ValueError:
                        st.error(f"Line {i+1}: 숫자 변환 오류. 입력 형식을 확인하세요.")
                
                if results:
                    st.success(f"✅ 총 {len(results)}개 지점 분석 완료")
                    df_final = pd.DataFrame(results)
                    
                    st.dataframe(
                        df_final.style.format({"평균추정강도(MPa)": "{:.2f}"})
                        .applymap(lambda v: 'color: red; font-weight: bold;' if v == '실패' or v == 'D/E' else None),
                        use_container_width=True
                    )
                    
                    st.download_button(
                        f"📥 결과 다운로드 (CSV)", 
                        convert_df(df_final), 
                        f"{project_name}_Batch결과.csv", 
                        "text/csv"
                    )

    # =========================================================
    # [Mode C] 파일 업로드 (Excel/CSV)
    # =========================================================
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
                if uploaded_file.name.endswith('.csv'):
                    df_upload = pd.read_csv(uploaded_file)
                else:
                    df_upload = pd.read_excel(uploaded_file)
                
                required_cols = ["Location", "Angle", "Age", "Design_Fck", "Readings"]
                if not all(col in df_upload.columns for col in required_cols):
                    st.error(f"❌ 양식이 맞지 않습니다. 필수 컬럼: {required_cols}")
                else:
                    results = []
                    progress_bar = st.progress(0)
                    
                    for idx, row in df_upload.iterrows():
                        raw_str = str(row["Readings"]).replace(',', ' ')
                        try:
                            readings = [float(x) for x in raw_str.split() if x.replace('.','',1).isdigit()]
                        except:
                            readings = []
                            
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
                            entry["기각수"] = res["Discard"]
                        else:
                            entry["비고"] = res
                        results.append(entry)
                        progress_bar.progress((idx + 1) / len(df_upload))
                    
                    st.success("✅ 분석 완료!")
                    df_final = pd.DataFrame(results)
                    st.dataframe(df_final.style.format({"평균추정강도(MPa)": "{:.2f}"}), use_container_width=True)
                    st.download_button(f"📥 결과 다운로드", convert_df(df_final), f"{project_name}_파일분석결과.csv", "text/csv")
                    
            except Exception as e:
                st.error(f"오류 발생: {e}")

# ---------------------------------------------------------
# [Tab 3] 통계 분석 (유지)
# ---------------------------------------------------------
with tab3:
    st.header("📈 강도 데이터 통계 분석")
    input_stats = st.text_area("강도 데이터 입력 (MPa)", placeholder="예: 21.5 22.1 23.0 ...", height=100)
        
    if st.button("분석 실행", key="btn_stat"):
        try:
            data_s = [float(x) for x in input_stats.replace(',',' ').split() if x.strip()]
            if len(data_s) < 2:
                st.warning("데이터가 2개 이상 필요합니다.")
            else:
                st_mean = np.mean(data_s)
                st_std = np.std(data_s, ddof=1)
                st_cov = (st_std / st_mean * 100) if st_mean > 0 else 0
                
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("평균", f"{st_mean:.2f} MPa")
                c2.metric("최대", f"{max(data_s):.2f} MPa")
                c3.metric("최소", f"{min(data_s):.2f} MPa")
                c4.metric("변동계수", f"{st_cov:.1f} %")
                
                st.bar_chart(sorted(data_s))
        except:
            st.error("숫자만 입력해주세요.")
