import streamlit as st
import math
import pandas as pd

# 페이지 기본 설정 (모바일 친화적)
st.set_page_config(page_title="탄산화 평가 프로그램", page_icon="🏗️")

# 제목 및 설명
st.title("🏗️ 콘크리트 탄산화 평가")
st.markdown("정밀안전진단 기준에 따른 **탄산화 잔여 깊이, 속도계수, 등급**을 판정합니다.")

# --- 사이드바 (입력창) ---
# 모바일에서는 상단에 접이식 메뉴로 표시됩니다.
with st.sidebar:
    st.header("📝 데이터 입력")
    measured_depth = st.number_input("1. 측정 탄산화 깊이 (mm)", min_value=0.0, value=12.0, step=0.1, format="%.1f")
    age_years = st.number_input("2. 건물 경과 년수 (년)", min_value=1, value=20, step=1)
    design_cover = st.number_input("3. 설계 피복 두께 (mm)", min_value=10.0, value=40.0, step=1.0)
    
    calc_button = st.button("계산 실행", type="primary")

# --- 계산 로직 ---
if calc_button:
    # 1. 잔여 깊이
    remaining_depth = design_cover - measured_depth
    
    # 2. 속도 계수 (A = C / sqrt(t))
    rate_coeff = 0.0
    if age_years > 0:
        rate_coeff = measured_depth / math.sqrt(age_years)
    
    # 3. 등급 판정 (조건식)
    grade = ""
    status_color = ""  # 결과창 색상 (green, orange, red)
    desc = ""

    if measured_depth <= 5:
        grade = "A 등급"
        desc = "매우 양호 (우수)"
        status_color = "green"
    elif (measured_depth <= design_cover / 3) or (measured_depth <= 10):
        grade = "B 등급"
        desc = "양호"
        status_color = "blue"
    elif (measured_depth <= design_cover / 2) or (measured_depth <= 15):
        grade = "C 등급"
        desc = "보통 (탄산화 진행)"
        status_color = "orange"
    elif (measured_depth <= design_cover) or (measured_depth <= 30):
        grade = "D 등급"
        desc = "미흡 (철근 인근 도달)"
        status_color = "red"
    else:
        grade = "E 등급"
        desc = "불량 (철근 위치 초과)"
        status_color = "red"

    # --- 결과 출력 화면 ---
    st.divider()
    st.subheader("📊 분석 결과")

    # 주요 지표 (큰 글씨)
    col1, col2 = st.columns(2)
    with col1:
        st.metric(label="잔여 깊이", value=f"{remaining_depth:.1f} mm")
    with col2:
        st.metric(label="속도 계수", value=f"{rate_coeff:.4f}")

    # 판정 결과 박스
    if status_color == "green":
        st.success(f"### {grade}\n{desc}")
    elif status_color == "blue":
        st.info(f"### {grade}\n{desc}")
    elif status_color == "orange":
        st.warning(f"### {grade}\n{desc}")
    else:
        st.error(f"### {grade}\n{desc}")

    # 상세 데이터 표 (엑셀처럼 보기)
    st.markdown("---")
    st.caption("요약 테이블")
    df = pd.DataFrame({
        "항목": ["측정 깊이", "경과 년수", "설계 피복", "잔여 깊이", "속도 계수"],
        "값": [f"{measured_depth}mm", f"{age_years}년", f"{design_cover}mm", f"{remaining_depth}mm", f"{rate_coeff:.4f}"]
    })
    st.dataframe(df, use_container_width=True, hide_index=True)

else:
    st.info("👈 왼쪽(모바일은 상단 화살표)에서 값을 입력하고 '계산 실행'을 눌러주세요.")
