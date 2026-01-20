import streamlit as st
import math
import pandas as pd
import numpy as np

# =========================================================
# 유틸리티: CSV 다운로드 변환 함수
# =========================================================
def convert_df(df):
    return df.to_csv(index=False).encode('utf-8-sig') # 한글 깨짐 방지 utf-8-sig

# ... (기존 함수들: get_angle_correction, get_age_coefficient 등은 그대로 유지) ...
# (이전 코드의 get_angle_correction, get_age_coefficient 함수를 여기에 붙여넣으세요)
def get_angle_correction(R_val, angle):
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
            ratio = (days - d1) / (d2 - d1)
            return age_table[d1] + ratio * (age_table[d2] - age_table[d1])
    return 1.0

st.set_page_config(page_title="구조물 안전진단 통합 평가", page_icon="🏗️")
st.title("🏗️ 구조물 안전진단 통합 평가 (Pro)")

# 사이드바: 프로젝트 정보 (보고서용)
with st.sidebar:
    st.header("📝 프로젝트 정보")
    p_name = st.text_input("프로젝트명", "OO교량 정밀안전진단")
    p_user = st.text_input("작성자", "홍길동")
    st.info("결과 다운로드 시 파일명에 활용될 수 있습니다.")

main_tab1, main_tab2, main_tab3 = st.tabs(["🧪 1. 탄산화 평가", "🔨 2. 반발경도 평가", "📈 3. 강도 통계 분석"])

# [Tab 1] (기존 코드 유지 - 생략 가능하지만 실행을 위해 간략 포함)
with main_tab1:
    st.header("🧪 탄산화 평가")
    st.write("*(기존 코드와 동일합니다)*")
    # (여기에 기존 Tab 1 코드를 넣으시면 됩니다)

# =========================================================
# [Tab 2] 반발경도 평가 (업그레이드: 설계강도 비교 + 다운로드)
# =========================================================
with main_tab2:
    st.header("🔨 반발경도(슈미트해머) 강도 산정")
    
    # 입력 UI 개선 (3단 컬럼)
    with st.container():
        c1, c2, c3 = st.columns(3)
        with c1:
            angle_option = st.selectbox("타격 방향", [0, -90, -45, 45, 90], format_func=lambda x: f"{x}°")
        with c2:
            days_input = st.number_input("재령 (일수)", 10, 5000, 1000)
        with c3:
            # [추가] 설계기준강도 입력
            design_fck = st.number_input("설계기준강도 (MPa)", 15.0, 100.0, 24.0, step=1.0, help="구조물 도면에 명시된 설계 강도")

        input_text = st.text_area("측정값 입력 (20개)", "54 56 55 53 58 55 54 55 52 57 55 56 54 55 59 42 55 56 54 55", height=70)

    if st.button("🚀 강도 산정 및 등급 평가", type="primary", key="btn_rebound"):
        try:
            # 데이터 처리 로직 (기존과 동일)
            clean_text = input_text.replace(',', ' ').replace('\n', ' ')
            readings = [float(x) for x in clean_text.split() if x.strip()]
            
            if len(readings) < 5:
                st.error("데이터 부족")
            else:
                avg1 = sum(readings) / len(readings)
                lower, upper = avg1 * 0.8, avg1 * 1.2
                valid = [r for r in readings if lower <= r <= upper]
                R_final = sum(valid) / len(valid)
                angle_corr = get_angle_correction(R_final, angle_option)
                R0 = R_final + angle_corr 
                age_coeff = get_age_coefficient(days_input)
                
                # 5가지 공식 계산
                f_aij = (7.3 * R0 + 100) * 0.098 * age_coeff        
                f_jsms = (1.27 * R0 - 18.0) * age_coeff             
                f_mst = (15.2 * R0 - 112.8) * 0.098 * age_coeff     
                f_kwon = (2.304 * R0 - 38.80) * age_coeff           
                f_kalis = (1.3343 * R0 + 8.1977) * age_coeff 
                est_strengths = [max(0, x) for x in [f_aij, f_jsms, f_mst, f_kwon, f_kalis]]
                
                # [추가] 설계강도 대비 비율 및 판정
                # 대표값은 안전측인 '최소값' 혹은 통상적인 '평균값'을 사용 (여기선 평균 사용)
                s_mean = np.mean(est_strengths)
                safety_ratio = (s_mean / design_fck) * 100
                
                grade_emoji = "🟢"
                if safety_ratio >= 100: grade_eval = "A (충족)"
                elif safety_ratio >= 90: grade_eval = "B (보통)"
                elif safety_ratio >= 75: 
                    grade_eval = "C (미흡)"
                    grade_emoji = "🟠"
                else: 
                    grade_eval = "D/E (부족)"
                    grade_emoji = "🔴"

                st.divider()
                # 결과 요약 메트릭
                m1, m2, m3, m4 = st.columns(4)
                m1.metric("평균 추정강도", f"{s_mean:.2f} MPa")
                m2.metric("설계기준강도", f"{design_fck:.1f} MPa")
                m3.metric("강도비 (추정/설계)", f"{safety_ratio:.1f} %", delta=f"{safety_ratio-100:.1f}%")
                m4.metric("종합 판정", f"{grade_emoji} {grade_eval}")

                # 결과 데이터프레임 생성
                df_result = pd.DataFrame({
                    "공식 구분": ["일본건축", "일본재료", "과기부(고)", "권영웅", "KALIS"],
                    "추정강도(MPa)": est_strengths,
                    "설계대비비율(%)": [x/design_fck*100 for x in est_strengths]
                })

                st.subheader("📊 상세 분석 결과")
                st.dataframe(
                    df_result.style.format({"추정강도(MPa)": "{:.2f}", "설계대비비율(%)": "{:.1f}%"})
                    .highlight_between(left=0, right=99.9, subset=["설계대비비율(%)"], color="#ffcdd2"),
                    use_container_width=True
                )

                # [추가] CSV 다운로드 버튼
                csv = convert_df(df_result)
                st.download_button(
                    label="📥 결과 보고서 다운로드 (CSV)",
                    data=csv,
                    file_name=f'{p_name}_반발경도_결과.csv',
                    mime='text/csv',
                    key='download-btn'
                )

        except ValueError:
            st.error("입력 오류")

# [Tab 3] (기존 코드 유지)
with main_tab3:
    st.header("📈 강도 통계 분석 (직접 입력)")
    st.write("*(기존 코드와 동일합니다)*")
    # (여기에 기존 Tab 3 코드를 넣으시면 됩니다)
