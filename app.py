import streamlit as st
import math
import pandas as pd

# 페이지 기본 설정
st.set_page_config(page_title="탄산화 평가 프로그램", page_icon="🏗️")

# 제목 및 설명
st.title("🏗️ 콘크리트 탄산화 평가")
st.markdown("측정된 탄산화 깊이에 따른 **탄산화 등급 및 잔존 수명**을 판정합니다.")

# --- 사이드바 (입력창) ---
with st.sidebar:
    st.header("📝 데이터 입력")
    measured_depth = st.number_input("1. 측정 탄산화 깊이 (mm)", min_value=0.0, value=12.0, step=0.1, format="%.1f")
    age_years = st.number_input("2. 구조물 경과 년수 (년)", min_value=1, value=20, step=1)
    design_cover = st.number_input("3. 설계 피복 두께 (mm)", min_value=10.0, value=40.0, step=1.0)
    
    calc_button = st.button("계산 실행", type="primary")

# --- 계산 로직 ---
if calc_button:
    # 1. 잔여 깊이 계산
    remaining_depth = design_cover - measured_depth
    
    # 2. 속도 계수 계산 (A = C / sqrt(t))
    rate_coeff = 0.0
    if age_years > 0:
        rate_coeff = measured_depth / math.sqrt(age_years)
    
    # 3. 수명 예측 (잔여깊이 / 속도계수)^2
    life_expectancy = 0.0
    life_msg = "" 

    if rate_coeff > 0:
        if remaining_depth > 0:
            life_expectancy = (remaining_depth / rate_coeff) ** 2
            life_msg = f"{life_expectancy:.1f} 년"
        else:
            life_msg = "0년 (이미 도달)"
    else:
        life_msg = "예측 불가 (진행 안됨)"

    # 4. 등급 판정 (요청하신 수식 적용)
    # =IF(잔여>=30,"a", IF(잔여>=10,"b", IF(잔여>=0,"c", "d")))
    
    grade = ""
    status_color = ""
    desc = ""

    if remaining_depth >= 30:
        grade = "A 등급"
        desc = "매우 양호 (30mm 이상 여유)"
        status_color = "green"
    elif remaining_depth >= 10:
        grade = "B 등급"
        desc = "양호 (10mm 이상 여유)"
        status_color = "blue"
    elif remaining_depth >= 0:
        grade = "C 등급"
        desc = "보통 (10mm 미만 여유)"
        status_color = "orange"
    else:
        grade = "D 등급"
        desc = "미흡/불량 (철근 위치 초과)"
        status_color = "red"

    # --- 결과 출력 화면 ---
    st.divider()
    st.subheader("📊 분석 결과")

    # 주요 지표 3개
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric(label="잔여 깊이", value=f"{remaining_depth:.1f} mm")
    with col2:
        st.metric(label="속도 계수", value=f"{rate_coeff:.4f}")
    with col3:
        st.metric(label="예측 잔존 수명", value=life_msg)

    # 판정 결과 메시지 박스
    if status_color == "green":
        st.success(f"### {grade}\n{desc}")
    elif status_color == "blue":
        st.info(f"### {grade}\n{desc}")
    elif status_color == "orange":
        st.warning(f"### {grade}\n{desc}")
    else:
        st.error(f"### {grade}\n{desc}")

    # 요약 테이블
    st.markdown("---")
    st.caption("요약 테이블")
    df = pd.DataFrame({
        "항목": ["측정 깊이", "경과 년수", "설계 피복", "잔여 깊이", "속도 계수", "예측 잔존 수명", "최종 등급"],
        "값": [
            f"{measured_depth}mm", 
            f"{age_years}년", 
            f"{design_cover}mm", 
            f"{remaining_depth:.1f}mm", 
            f"{rate_coeff:.4f}",
            life_msg,
            grade
        ]
    })
    st.dataframe(df, use_container_width=True, hide_index=True)
    
else:
    st.info("👈 왼쪽(모바일은 상단 화살표)에서 값을 입력하고 '계산 실행'을 눌러주세요.")

