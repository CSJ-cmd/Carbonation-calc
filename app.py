import streamlit as st
import math
import pandas as pd

# 페이지 기본 설정
st.set_page_config(page_title="구조물 안전진단 통합 평가", page_icon="🏗️")

# 제목
st.title("🏗️ 구조물 안전진단 통합 평가")
st.markdown("하나의 앱에서 **탄산화(수명예측 수정됨)**와 **반발경도**를 모두 평가할 수 있습니다.")

# 탭 생성
tab1, tab2 = st.tabs(["🧪 1. 탄산화 평가", "🔨 2. 반발경도 평가"])

# =========================================================
# [Tab 1] 탄산화 평가 로직 (수식 수정됨)
# =========================================================
with tab1:
    st.header("🧪 탄산화 깊이 및 등급 평가")
    
    # 입력 폼
    with st.container():
        st.info("👇 탄산화 측정 데이터를 입력하세요.")
        col1, col2 = st.columns(2)
        with col1:
            measured_depth = st.number_input("측정 탄산화 깊이 (mm)", min_value=0.0, value=12.0, step=0.1, format="%.1f")
            age_years = st.number_input("건물 경과 년수 (년)", min_value=1, value=20, step=1)
        with col2:
            design_cover = st.number_input("설계 피복 두께 (mm)", min_value=10.0, value=40.0, step=1.0)
    
    # 계산 실행 버튼
    if st.button("탄산화 계산 실행", type="primary", key="btn_carbon"):
        # 1. 잔여 깊이 (등급 판정용)
        remaining_depth = design_cover - measured_depth
        
        # 2. 속도 계수 (A = C / sqrt(t))
        rate_coeff = 0.0
        if age_years > 0:
            rate_coeff = measured_depth / math.sqrt(age_years)
            
        # 3. 수명 예측 (요청하신 수식 적용)
        # 공식: (설계피복 / 속도계수)^2 - 현재재령
        life_msg = ""
        life_years = 0.0
        
        if rate_coeff > 0:
            # 피복두께까지 도달하는 총 시간 예측
            total_time_to_reach = (design_cover / rate_coeff) ** 2
            
            # 잔존 수명 = 총 시간 - 현재 나이
            life_years = total_time_to_reach - age_years
            
            if life_years > 0:
                life_msg = f"{life_years:.1f} 년"
            else:
                life_msg = "0년 (이미 도달함)"
        elif measured_depth == 0:
             life_msg = "예측 불가 (진행 안됨)"
        else:
             life_msg = "계산 불가"

        # 4. 등급 판정 (잔여 깊이 기준)
        # IF(잔여>=30,"A", IF(잔여>=10,"B", IF(잔여>=0,"C", "D")))
        if remaining_depth >= 30:
            grade = "A 등급"
            color = "green"
            desc = "매우 양호 (30mm 이상 여유)"
        elif remaining_depth >= 10:
            grade = "B 등급"
            color = "blue"
            desc = "양호 (10mm 이상 여유)"
        elif remaining_depth >= 0:
            grade = "C 등급"
            color = "orange"
            desc = "보통 (10mm 미만 여유)"
        else:
            grade = "D 등급"
            color = "red"
            desc = "미흡/불량 (철근 위치 초과)"

        # 결과 표시
        st.divider()
        c1, c2, c3 = st.columns(3)
        c1.metric("잔여 깊이", f"{remaining_depth:.1f} mm")
        c2.metric("속도 계수", f"{rate_coeff:.4f}")
        c3.metric("예측 잔존 수명", life_msg)
        
        if color == "green": st.success(f"### {grade}\n{desc}")
        elif color == "blue": st.info(f"### {grade}\n{desc}")
        elif color == "orange": st.warning(f"### {grade}\n{desc}")
        else: st.error(f"### {grade}\n{desc}")
        
        # 상세 데이터 테이블
        st.caption("요약 테이블")
        df_res = pd.DataFrame({
            "항목": ["측정 깊이", "잔여 깊이", "속도 계수", "예측 잔존 수명", "판정"],
            "값": [f"{measured_depth}mm", f"{remaining_depth:.1f}mm", f"{rate_coeff:.4f}", life_msg, grade]
        })
        st.dataframe(df_res, use_container_width=True, hide_index=True)

# =========================================================
# [Tab 2] 반발경도 평가 로직 (기존 유지)
# =========================================================
with tab2:
    st.header("🔨 반발경도(슈미트해머) 강도 추정")
    
    st.info("👇 반발경도 측정값과 보정 계수를 입력하세요.")
    
    # 입력 데이터
    rebound_r = st.number_input("측정 반발경도 (R값 평균)", min_value=10.0, value=35.0, step=0.1, format="%.1f")
    
    # 고급 설정
    with st.expander("⚙️ 강도 환산식 설정 (필요시 수정)"):
        st.markdown("**환산식: $F_c = A \times R + B$** (기본값: 일본건축학회)")
        coeff_a = st.number_input("기울기 (A)", value=7.3)
        coeff_b = st.number_input("절편 (B)", value=100.0)
        
        st.markdown("**보정값 설정**")
        angle_correction = st.number_input("타격 각도 보정값 (없으면 0)", value=0.0, step=1.0)
        age_factor = st.number_input("재령 보정 계수 (일반적으로 1.0)", value=1.0, step=0.01)

    if st.button("압축강도 계산 실행", type="primary", key="btn_rebound"):
        # 1. 반발도 보정
        corrected_R = rebound_r + angle_correction
        
        # 2. 압축강도 추정 (kgf/cm2) -> MPa 변환
        strength_kgf = (coeff_a * corrected_R + coeff_b) * age_factor
        strength_mpa = strength_kgf * 0.0980665
        
        # 결과 표시
        st.divider()
        st.subheader("📊 강도 추정 결과")
        
        c1, c2 = st.columns(2)
        with c1:
            st.metric(label="추정 압축강도 (MPa)", value=f"{strength_mpa:.1f} MPa")
        with c2:
            st.metric(label="추정 압축강도 (kgf/cm²)", value=f"{strength_kgf:.0f} kgf/cm²")
            
        st.caption("--- 상세 계산 근거 ---")
        st.text(f"1. 보정 반발도(R) : {rebound_r} + {angle_correction} = {corrected_R}")
        st.text(f"2. 강도 환산식    : {coeff_a} × {corrected_R} + {coeff_b} = {coeff_a * corrected_R + coeff_b:.1f}")
        st.text(f"3. 재령 보정      : × {age_factor} = {strength_kgf:.1f} kgf/cm²")
        
        if strength_mpa >= 24:
            st.success("24MPa 이상 (양호)")
        else:
            st.warning("24MPa 미만 (주의)")
