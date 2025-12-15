import streamlit as st
import math
import pandas as pd

# =========================================================
# 1. 페이지 기본 설정
# =========================================================
st.set_page_config(page_title="구조물 안전진단 통합 평가", page_icon="🏗️")

# =========================================================
# 2. 전역 함수 정의 (반발경도 보정 로직)
# =========================================================

def get_angle_correction(R_val, angle):
    """
    [타격 방향 보정]
    - R값 구간별 보정치를 Step 방식(계단식)으로 적용
    """
    correction_table = {
        -90: {20: +3.2, 30: +3.1, 40: +2.7, 50: +2.2, 60: +1.7}, # 하향
        -45: {20: +2.4, 30: +2.3, 40: +2.0, 50: +1.6, 60: +1.3}, # 사하향
        0:   {20: 0.0,  30: 0.0,  40: 0.0,  50: 0.0,  60: 0.0},  # 수평
        45:  {20: -3.5, 30: -3.1, 40: -2.0, 50: -2.7, 60: -1.6}, # 사상향
        90:  {20: -5.4, 30: -4.7, 40: -3.9, 50: -3.1, 60: -2.3}  # 상향
    }
    
    if angle not in correction_table:
        return 0.0
    
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
    """
    [재령 보정계수]
    - 표준 곡선(일본재료학회) + 장기 재령 통합
    """
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
# 3. 메인 화면 UI 구성
# =========================================================

st.title("🏗️ 구조물 안전진단 통합 평가")
st.markdown("**탄산화**와 **반발경도**를 모두 평가할 수 있습니다.")

tab1, tab2 = st.tabs(["🧪 1. 탄산화 평가", "🔨 2. 반발경도 평가"])

# =========================================================
# [Tab 1] 탄산화 평가 로직 (유지)
# =========================================================
with tab1:
    st.header("🧪 탄산화 깊이 및 등급 평가")
    with st.container():
        st.info("👇 탄산화 측정 데이터를 입력하세요.")
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
        life_years = 0.0
        
        if rate_coeff > 0:
            total_time_to_reach = (design_cover / rate_coeff) ** 2
            life_years = total_time_to_reach - age_years
            if life_years > 0:
                life_msg = f"{life_years:.1f} 년"
            else:
                life_msg = "0년 (이미 도달함)"
        elif measured_depth == 0:
             life_msg = "예측 불가 (진행 안됨)"
        else:
             life_msg = "계산 불가"

        if remaining_depth >= 30:
            grade = "A 등급"; color = "green"; desc = "매우 양호 (30mm 이상 여유)"
        elif remaining_depth >= 10:
            grade = "B 등급"; color = "blue"; desc = "양호 (10mm 이상 여유)"
        elif remaining_depth >= 0:
            grade = "C 등급"; color = "orange"; desc = "보통 (10mm 미만 여유)"
        else:
            grade = "D 등급"; color = "red"; desc = "미흡/불량 (철근 위치 초과)"

        st.divider()
        c1, c2, c3 = st.columns(3)
        c1.metric("잔여 깊이", f"{remaining_depth:.1f} mm")
        c2.metric("속도 계수", f"{rate_coeff:.4f}")
        c3.metric("예측 잔존 수명", life_msg)
        
        if color == "green": st.success(f"### {grade}\n{desc}")
        elif color == "blue": st.info(f"### {grade}\n{desc}")
        elif color == "orange": st.warning(f"### {grade}\n{desc}")
        else: st.error(f"### {grade}\n{desc}")
        
        st.caption("요약 테이블")
        df_res = pd.DataFrame({
            "항목": ["측정 깊이", "잔여 깊이", "속도 계수", "예측 잔존 수명", "판정"],
            "값": [f"{measured_depth}mm", f"{remaining_depth:.1f}mm", f"{rate_coeff:.4f}", life_msg, grade]
        })
        st.dataframe(df_res, use_container_width=True, hide_index=True)

# =========================================================
# [Tab 2] 반발경도 평가 로직 (KALIS 추가됨)
# =========================================================
with tab2:
    st.header("🔨 반발경도(슈미트해머) 강도 산정")
    st.markdown("##### 측정값 20개와 보정 조건을 입력하세요.")

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
            "측정값(Raw Data) 20개 입력 (숫자만 띄어쓰기로 구분)", 
            "54 56 55 53 58 55 54 55 52 57 55 56 54 55 59 42 55 56 54 55",
            height=80
        )

    if st.button("🚀 강도 산정하기", type="primary", use_container_width=True, key="btn_rebound"):
        try:
            clean_text = input_text.replace(',', ' ').replace('\n', ' ')
            readings = [float(x) for x in clean_text.split() if x.strip()]
            
            if len(readings) < 5:
                st.error("❗ 데이터가 너무 적습니다. 최소 5개 이상 입력해주세요.")
            else:
                avg1 = sum(readings) / len(readings)
                lower, upper = avg1 * 0.8, avg1 * 1.2
                valid = [r for r in readings if lower <= r <= upper]
                
                if not valid:
                    st.error("유효한 데이터가 없습니다.")
                else:
                    # R0 계산
                    R_final = sum(valid) / len(valid)
                    angle_corr = get_angle_correction(R_final, angle_option)
                    R0 = R_final + angle_corr 
                    age_coeff = get_age_coefficient(days_input)
                    
                    # === 3. 강도 산정 (KALIS 추가) ===
                    f_aij = (7.3 * R0 + 100) * 0.098 * age_coeff       # 건축학회(일반)
                    f_jsms = (1.27 * R0 - 18.0) * age_coeff            # 재료학회(일반)
                    f_mst = (15.2 * R0 - 112.8) * 0.098 * age_coeff    # 과기부(고강도)
                    f_kwon = (2.304 * R0 - 38.80) * age_coeff          # 권영웅(고강도)
                    
                    # [추가됨] KALIS 고강도 추정식 (Fc = 1.3343 Ro + 8.1977)
                    f_kalis = (1.3343 * R0 + 8.1977) * age_coeff 
                    
                    # 4. 결과 표시
                    st.divider()
                    st.success("✅ 산정 완료")
                    
                    c1, c2, c3, c4 = st.columns(4)
                    c1.metric("1차 평균 R", f"{R_final:.1f}")
                    c2.metric("타격 보정", f"{angle_corr:+.1f}")
                    c3.metric("최종 R0", f"{R0:.1f}")
                    c4.metric("재령 계수", f"{age_coeff:.3f}")

                    st.markdown("---")

                    st.subheader("📊 압축강도 산정 결과 비교")
                    result_data = {
                        "구분": [
                            "일본건축학회 (일반)", 
                            "일본재료학회 (일반)", 
                            "과학기술부 (고강도)", 
                            "권영웅 (고강도)",
                            "KALIS (고강도, 40MPa↑)" # 추가된 항목
                        ],
                        "추정 강도 (MPa)": [
                            f"{max(0, f_aij):.2f}",
                            f"{max(0, f_jsms):.2f}",
                            f"{max(0, f_mst):.2f}",
                            f"{max(0, f_kwon):.2f}",
                            f"{max(0, f_kalis):.2f}" # 추가된 값
                        ],
                        "적용 수식": [
                            "(7.3×Ro + 100) × 0.098", 
                            "1.27×Ro - 18.0", 
                            "(15.2×Ro - 112.8) × 0.098", 
                            "2.304×Ro - 38.80",
                            "1.3343×Ro + 8.1977"    # 추가된 수식 설명
                        ]
                    }
                    st.table(pd.DataFrame(result_data))
                    
                    with st.expander("ℹ️ 상세 분석 정보 (유효 데이터 등)"):
                        st.markdown("**1. 데이터 품질 분석**")
                        st.write(f"- 전체 입력: {len(readings)}개, 유효 데이터: {len(valid)}개")
                        if len(readings)-len(valid) > 0:
                            st.warning(f"제외된 이상치: {[r for r in readings if r not in valid]}")
                        
                        st.markdown("**2. KALIS 고강도 공식 적용**")
                        st.info("KALIS 식은 일반적으로 40MPa 이상의 고강도 콘크리트에서 신뢰도가 높습니다.")

        except ValueError:
            st.error("⚠️ 숫자만 입력해주세요.")

