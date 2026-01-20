import streamlit as st
import math
import pandas as pd
import numpy as np

# =========================================================
# 1. 페이지 기본 설정
# =========================================================
st.set_page_config(page_title="구조물 안전진단 통합 평가", page_icon="🏗️")

# =========================================================
# 2. 전역 함수 정의
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

# =========================================================
# 3. 메인 화면 UI
# =========================================================

st.title("🏗️ 구조물 안전진단 통합 평가")
st.markdown("정밀안전진단 기준에 따른 **탄산화**, **반발경도**, **강도 통계** 분석 도구입니다.")

# 탭을 3개로 확장
main_tab1, main_tab2, main_tab3 = st.tabs(["🧪 1. 탄산화 평가", "🔨 2. 반발경도 평가", "📈 3. 강도 통계 분석 (직접 입력)"])

# =========================================================
# [Tab 1] 탄산화 평가
# =========================================================
with main_tab1:
    st.header("🧪 탄산화 깊이 및 등급 평가")
    with st.container():
        st.info("👇 측정 데이터를 입력하세요.")
        col1, col2 = st.columns(2)
        with col1:
            measured_depth = st.number_input("측정 탄산화 깊이 (mm)", min_value=0.0, value=12.0, step=0.1, format="%.1f")
            age_years = st.number_input("건물 경과 년수 (년)", min_value=1, value=20, step=1)
        with col2:
            design_cover = st.number_input("설계 피복 두께 (mm)", min_value=10.0, value=40.0, step=1.0)
    
    if st.button("탄산화 계산 실행", type="primary", key="btn_carbon"):
        remaining_depth = design_cover - measured_depth
        rate_coeff = 0.0
        if age_years > 0:
            rate_coeff = measured_depth / math.sqrt(age_years)
            
        life_msg = ""
        is_danger = False

        if rate_coeff > 0:
            total_time = (design_cover / rate_coeff) ** 2
            life_years = total_time - age_years
            
            if remaining_depth <= 0:
                life_msg = "🚨 0년 (이미 도달함)"
                is_danger = True
            elif life_years > 0:
                life_msg = f"{life_years:.1f} 년"
            else:
                life_msg = "0년 (도달 임박)"
        elif measured_depth == 0:
             life_msg = "99년 이상 (진행 안됨)"
        else:
             life_msg = "계산 불가"

        if remaining_depth >= 30:
            grade = "A 등급"; color = "green"; desc = "매우 양호 (30mm 이상 여유)"
        elif remaining_depth >= 10:
            grade = "B 등급"; color = "blue"; desc = "양호 (10mm 이상 여유)"
        elif remaining_depth >= 0:
            grade = "C 등급"; color = "orange"; desc = "보통 (10mm 미만 여유)"
        else:
            grade = "D 등급"; color = "red"; desc = "불량 (철근 위치 초과 - 부식 위험)"

        st.divider()
        c1, c2, c3 = st.columns(3)
        c1.metric("잔여 깊이", f"{remaining_depth:.1f} mm", delta_color="off")
        c2.metric("속도 계수", f"{rate_coeff:.4f} mm/√yr")
        c3.metric("예측 잔존 수명", life_msg)
        
        if is_danger:
            st.error("🚨 **경고**: 탄산화가 이미 철근 위치까지 진행되었습니다. 철근 부식 가능성이 높으므로 정밀 점검이 필요합니다.")
        
        if color == "green": st.success(f"### {grade}\n{desc}")
        elif color == "blue": st.info(f"### {grade}\n{desc}")
        elif color == "orange": st.warning(f"### {grade}\n{desc}")
        else: st.error(f"### {grade}\n{desc}")
        
        st.caption("요약 데이터")
        df_res = pd.DataFrame({
            "항목": ["측정 깊이", "잔여 깊이", "속도 계수", "예측 잔존 수명", "판정"],
            "값": [f"{measured_depth}mm", f"{remaining_depth:.1f}mm", f"{rate_coeff:.4f}", life_msg, grade]
        })
        st.dataframe(df_res, use_container_width=True, hide_index=True)

# =========================================================
# [Tab 2] 반발경도 평가
# =========================================================
with main_tab2:
    st.header("🔨 반발경도(슈미트해머) 강도 산정")
    st.markdown("##### 📝 측정값 20개를 입력하세요 (KS F 2730)")

    with st.container():
        col1, col2 = st.columns(2)
        with col1:
            angle_option = st.selectbox(
                "타격 방향 (각도)", 
                options=[0, -90, -45, 45, 90],
                format_func=lambda x: f"{x}° (수평)" if x==0 else (f"{x}° (하향/바닥)" if x<0 else f"+{x}° (상향/천장)")
            )
        with col2:
            days_input = st.number_input("재령 (일수)", min_value=10, value=1000, step=10)

        input_text = st.text_area(
            "측정값 입력 (공백 또는 줄바꿈으로 구분)", 
            "54 56 55 53 58 55 54 55 52 57 55 56 54 55 59 42 55 56 54 55",
            height=80
        )

    if st.button("🚀 강도 산정하기", type="primary", use_container_width=True, key="btn_rebound"):
        try:
            clean_text = input_text.replace(',', ' ').replace('\n', ' ')
            readings = [float(x) for x in clean_text.split() if x.strip()]
            
            # 1. 데이터 검증
            if len(readings) < 5:
                st.error("❗ 데이터가 너무 적습니다. 최소 5개 이상 입력해주세요.")
            else:
                avg1 = sum(readings) / len(readings)
                lower, upper = avg1 * 0.8, avg1 * 1.2
                valid = [r for r in readings if lower <= r <= upper]
                discard_count = len(readings) - len(valid)
                
                is_invalid_test = (len(readings) >= 20 and discard_count > 4)
                
                if not valid:
                    st.error("❌ 유효한 데이터가 없습니다.")
                elif is_invalid_test:
                    st.error(f"❌ **시험 무효**: 20% 이상의 데이터({discard_count}개)가 기각되었습니다.")
                else:
                    R_final = sum(valid) / len(valid)
                    angle_corr = get_angle_correction(R_final, angle_option)
                    R0 = R_final + angle_corr 
                    age_coeff = get_age_coefficient(days_input)
                    
                    # 2. 강도 산정 (5가지 공식)
                    f_aij = (7.3 * R0 + 100) * 0.098 * age_coeff        
                    f_jsms = (1.27 * R0 - 18.0) * age_coeff             
                    f_mst = (15.2 * R0 - 112.8) * 0.098 * age_coeff     
                    f_kwon = (2.304 * R0 - 38.80) * age_coeff           
                    f_kalis = (1.3343 * R0 + 8.1977) * age_coeff 

                    est_strengths = [max(0, x) for x in [f_aij, f_jsms, f_mst, f_kwon, f_kalis]]
                    
                    # 3. 결과 표시
                    st.divider()
                    st.success("✅ 산정 완료")
                    
                    # 탭 분리
                    res_tab1, res_tab2 = st.tabs(["📊 1. 강도 추정 결과", "📈 2. 강도 통계 분석"])
                    
                    # [Sub Tab 1] 강도 추정 결과
                    with res_tab1:
                        st.subheader("📋 압축강도 추정값 목록")
                        
                        result_data = {
                            "구분": [
                                "일본건축학회 (일반)", 
                                "일본재료학회 (일반)", 
                                "과학기술부 (고강도)", 
                                "권영웅 (고강도)",
                                "KALIS (고강도, 40MPa↑)"
                            ],
                            "추정 강도 (MPa)": est_strengths,
                            "적용 수식": [
                                "(7.3×Ro + 100) × 0.098", 
                                "1.27×Ro - 18.0", 
                                "(15.2×Ro - 112.8) × 0.098", 
                                "2.304×Ro - 38.80",
                                "1.3343×Ro + 8.1977"
                            ]
                        }
                        df_result = pd.DataFrame(result_data)
                        st.dataframe(
                            df_result.style.format({"추정 강도 (MPa)": "{:.2f}"})
                            .highlight_max(subset=["추정 강도 (MPa)"], color="#d6eaf8", axis=0),
                            use_container_width=True,
                            hide_index=True
                        )
                        
                        st.markdown("---")
                        st.caption("ℹ️ 산정 기초 데이터 (반발경도)")
                        c1, c2, c3, c4 = st.columns(4)
                        c1.metric("1차 평균 R", f"{R_final:.1f}")
                        c2.metric("타격 보정", f"{angle_corr:+.1f}")
                        c3.metric("최종 R0", f"{R0:.1f}")
                        c4.metric("재령 계수", f"{age_coeff:.3f}")
                        if discard_count > 0:
                            st.warning(f"⚠️ 이상치 {discard_count}개가 제외되었습니다.")

                    # [Sub Tab 2] 강도 통계 분석 (5가지 강도값 기준)
                    with res_tab2:
                        st.subheader("📈 산정된 압축강도 통계")
                        st.info("💡 위 5가지 제안식으로 계산된 **압축강도 값들의 분포 특성**입니다.")
                        
                        s_mean = np.mean(est_strengths)
                        s_std = np.std(est_strengths, ddof=1)
                        s_max = np.max(est_strengths)
                        s_min = np.min(est_strengths)
                        s_cov = (s_std / s_mean * 100) if s_mean > 0 else 0
                        
                        col_s1, col_s2, col_s3 = st.columns(3)
                        col_s1.metric("평균 강도", f"{s_mean:.2f} MPa")
                        col_s2.metric("최대 강도", f"{s_max:.2f} MPa")
                        col_s3.metric("최소 강도", f"{s_min:.2f} MPa")
                        
                        col_s4, col_s5, col_s6 = st.columns(3)
                        col_s4.metric("표준편차", f"{s_std:.2f}")
                        col_s5.metric("변동계수 (COV)", f"{s_cov:.1f} %")
                        col_s6.metric("데이터 수", "5 개 (공식 수)")
                        
                        st.markdown("---")
                        with st.expander("📊 분포 시각화 (간이 차트)"):
                            chart_data = pd.DataFrame({
                                "공식": df_result["구분"],
                                "강도": est_strengths
                            }).set_index("공식")
                            st.bar_chart(chart_data)

        except ValueError:
            st.error("⚠️ 숫자만 입력해주세요.")

# =========================================================
# [Tab 3] 강도 통계 분석
# =========================================================
with main_tab3:
    st.header("📈 압축강도 데이터 통계 분석")
    st.markdown("##### 📝 이미 산정된 압축강도 값들을 입력하여 통계를 확인하세요.")
    
    with st.container():
        input_strength_text = st.text_area(
            "압축강도 데이터 입력 (MPa)",
            placeholder="예: 24.5 25.1 23.8 26.0 ... (공백 또는 줄바꿈으로 구분)",
            height=100,
            key="input_strength"
        )
        
    if st.button("📊 통계 분석 실행", type="primary", key="btn_stat"):
        if not input_strength_text.strip():
            st.warning("⚠️ 데이터를 입력해주세요.")
        else:
            try:
                # 데이터 파싱
                clean_str = input_strength_text.replace(',', ' ').replace('\n', ' ')
                data_list = [float(x) for x in clean_str.split() if x.strip()]
                
                if len(data_list) < 2:
                    st.error("❗ 통계 분석을 위해 최소 2개 이상의 데이터가 필요합니다.")
                else:
                    # 통계 계산
                    stat_mean = np.mean(data_list)
                    stat_std = np.std(data_list, ddof=1) # 표본표준편차
                    stat_max = np.max(data_list)
                    stat_min = np.min(data_list)
                    stat_cov = (stat_std / stat_mean * 100) if stat_mean > 0 else 0
                    
                    st.divider()
                    st.success(f"✅ 총 {len(data_list)}개의 데이터 분석 완료")
                    
                    # 메트릭 표시
                    c1, c2, c3, c4, c5 = st.columns(5)
                    c1.metric("평균 (Mean)", f"{stat_mean:.2f} MPa")
                    c2.metric("최대 (Max)", f"{stat_max:.2f} MPa")
                    c3.metric("최소 (Min)", f"{stat_min:.2f} MPa")
                    c4.metric("표준편차 (SD)", f"{stat_std:.2f}")
                    c5.metric("변동계수 (COV)", f"{stat_cov:.1f} %")
                    
                    st.markdown("---")
                    
                    # 시각화 및 데이터 표
                    col_viz1, col_viz2 = st.columns([2, 1])
                    
                    with col_viz1:
                        st.subheader("📊 데이터 분포")
                        # 간단한 히스토그램 역할을 하는 바 차트 (구간별 빈도 대신 값 자체 표시 or 정렬)
                        # 여기서는 값의 크기 비교를 위해 정렬 후 Bar Chart 표시
                        sorted_data = sorted(data_list)
                        st.bar_chart(pd.DataFrame({"압축강도": sorted_data}), use_container_width=True)
                        st.caption("*X축: 데이터 순번 (오름차순 정렬), Y축: 압축강도(MPa)")

                    with col_viz2:
                        st.subheader("📋 입력 데이터 목록")
                        df_input = pd.DataFrame(data_list, columns=["압축강도(MPa)"])
                        st.dataframe(df_input.style.format("{:.2f}"), use_container_width=True, height=300)

            except ValueError:
                st.error("⚠️ 숫자만 입력해주세요 (문자 포함 불가).")

