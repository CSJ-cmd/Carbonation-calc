import streamlit as st
import math
import pandas as pd
import numpy as np

# =========================================================
# 1. 페이지 기본 설정 및 스타일
# =========================================================
st.set_page_config(
    page_title="구조물 안전진단 통합 평가 Pro",
    page_icon="🏗️",
    layout="wide"
)

# =========================================================
# 2. 전역 함수 정의 (보정계수 및 유틸리티)
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

def convert_df(df):
    """ DataFrame을 CSV 다운로드용 바이트로 변환 (UTF-8-SIG) """
    return df.to_csv(index=False).encode('utf-8-sig')

# =========================================================
# 3. 메인 화면 UI 구성
# =========================================================

st.title("🏗️ 구조물 안전진단 통합 평가 System")
st.markdown("""
정밀안전진단 기준에 따른 **탄산화**, **반발경도**, **강도 통계** 분석을 수행하는 전문가용 도구입니다.
""")

# 사이드바: 프로젝트 정보 입력
with st.sidebar:
    st.header("📝 프로젝트 설정")
    project_name = st.text_input("프로젝트명", value="OO교량 정밀안전진단")
    inspector_name = st.text_input("진단자", value="홍길동")
    st.caption("※ 다운로드 파일명에 반영됩니다.")
    st.divider()
    st.info("💡 **사용 가이드**\n\n1. 탄산화 깊이 측정\n2. 반발경도(R) 측정 (20점)\n3. 통계 분석 및 보고서 다운로드")

# 메인 탭 구성 (3개)
tab1, tab2, tab3 = st.tabs(["🧪 1. 탄산화 평가", "🔨 2. 반발경도 평가", "📈 3. 강도 통계 (직접 입력)"])

# =========================================================
# [Tab 1] 탄산화 평가
# =========================================================
with tab1:
    st.header("🧪 탄산화 깊이 및 등급 평가")
    
    with st.container():
        c1, c2, c3 = st.columns(3)
        with c1:
            measured_depth = st.number_input("측정 탄산화 깊이 (mm)", 0.0, 100.0, 12.0, 0.1, format="%.1f")
        with c2:
            design_cover = st.number_input("설계 피복 두께 (mm)", 10.0, 200.0, 40.0, 1.0)
        with c3:
            age_years = st.number_input("건물 경과 년수 (년)", 1, 100, 20)
            
    if st.button("탄산화 평가 실행", type="primary", key="btn_carb"):
        remaining = design_cover - measured_depth
        rate_coeff = measured_depth / math.sqrt(age_years) if age_years > 0 else 0
        
        # 수명 예측
        life_str = ""
        is_danger = False
        if rate_coeff > 0:
            total_time = (design_cover / rate_coeff) ** 2
            life_years = total_time - age_years
            if remaining <= 0:
                life_str = "🚨 0년 (이미 도달함)"
                is_danger = True
            elif life_years > 0:
                life_str = f"{life_years:.1f} 년"
            else:
                life_str = "0년 (도달 임박)"
        elif measured_depth == 0:
            life_str = "99년 이상 (진행 안됨)"
        else:
            life_str = "계산 불가"
            
        # 등급 판정
        if remaining >= 30: grade, color, desc = "A 등급", "green", "매우 양호 (30mm 이상 여유)"
        elif remaining >= 10: grade, color, desc = "B 등급", "blue", "양호 (10mm 이상 여유)"
        elif remaining >= 0: grade, color, desc = "C 등급", "orange", "보통 (10mm 미만 여유)"
        else: grade, color, desc = "D 등급", "red", "불량 (철근 위치 초과 - 부식 위험)"
        
        st.divider()
        m1, m2, m3 = st.columns(3)
        m1.metric("잔여 깊이", f"{remaining:.1f} mm", delta_color="off")
        m2.metric("속도 계수", f"{rate_coeff:.4f} mm/√yr")
        m3.metric("예측 잔존 수명", life_str)
        
        if is_danger:
            st.error("🚨 **경고**: 탄산화가 철근 위치에 도달했습니다. 정밀 점검이 필요합니다.")
        
        grade_html = f"<h3 style='color:{color}'>{grade}</h3><p>{desc}</p>"
        st.markdown(grade_html, unsafe_allow_html=True)

# =========================================================
# [Tab 2] 반발경도 평가 (설계강도 비교 + 다운로드)
# =========================================================
with tab2:
    st.header("🔨 반발경도(슈미트해머) 강도 산정")
    st.markdown("##### 📝 측정값 20개를 입력하세요 (KS F 2730)")

    with st.container():
        col1, col2, col3 = st.columns(3)
        with col1:
            angle_opt = st.selectbox("타격 방향", [0, -90, -45, 45, 90], format_func=lambda x: f"{x}° (수평)" if x==0 else f"{x}°")
        with col2:
            days_inp = st.number_input("재령 (일수)", 10, 10000, 1000)
        with col3:
            # [Pro 기능] 설계기준강도 입력
            design_fck = st.number_input("설계기준강도 (MPa)", 15.0, 100.0, 24.0, help="도면상의 설계 강도")

        input_txt = st.text_area(
            "측정값 입력 (공백/줄바꿈 구분)", 
            "54 56 55 53 58 55 54 55 52 57 55 56 54 55 59 42 55 56 54 55",
            height=70
        )
        
    if st.button("🚀 강도 산정 및 등급 평가", type="primary", key="btn_reb"):
        try:
            # 데이터 전처리
            clean = input_txt.replace(',', ' ').replace('\n', ' ')
            readings = [float(x) for x in clean.split() if x.strip()]
            
            if len(readings) < 5:
                st.error("❗ 데이터가 너무 적습니다. (최소 5개)")
            else:
                # 이상치 제거
                avg1 = sum(readings) / len(readings)
                valid = [r for r in readings if avg1*0.8 <= r <= avg1*1.2]
                discard_cnt = len(readings) - len(valid)
                
                # KS 기준 기각 확인 (20% 초과 시)
                is_invalid = (len(readings) >= 20 and discard_cnt > 4)
                
                if not valid:
                    st.error("❌ 유효 데이터 없음")
                elif is_invalid:
                    st.error(f"❌ **시험 무효**: {discard_cnt}개 기각 (전체의 20% 초과). 재측정 필요.")
                else:
                    # R0 및 강도 계산
                    R_final = sum(valid) / len(valid)
                    corr = get_angle_correction(R_final, angle_opt)
                    R0 = R_final + corr
                    age_c = get_age_coefficient(days_inp)
                    
                    # 5개 공식
                    f_aij = (7.3 * R0 + 100) * 0.098 * age_c        
                    f_jsms = (1.27 * R0 - 18.0) * age_c             
                    f_mst = (15.2 * R0 - 112.8) * 0.098 * age_c     
                    f_kwon = (2.304 * R0 - 38.80) * age_c           
                    f_kalis = (1.3343 * R0 + 8.1977) * age_c 
                    est_list = [max(0, x) for x in [f_aij, f_jsms, f_mst, f_kwon, f_kalis]]
                    
                    # [Pro 기능] 안전율 및 등급 평가 (평균값 기준)
                    s_mean = np.mean(est_list)
                    ratio = (s_mean / design_fck) * 100
                    
                    grade_mk = "🟢 A (우수)" if ratio >= 100 else ("🔵 B (양호)" if ratio >= 90 else ("🟠 C (미흡)" if ratio >= 75 else "🔴 D/E (부족)"))
                    
                    # --- 결과 표시 ---
                    st.divider()
                    st.success("✅ 산정 완료")
                    
                    # 서브 탭
                    sub1, sub2 = st.tabs(["📊 결과 보고서 (Estimation)", "📈 상세 통계 (Statistics)"])
                    
                    # [Sub 1] 결과 테이블 및 다운로드
                    with sub1:
                        st.subheader("📋 압축강도 추정 및 등급")
                        
                        # 메트릭
                        c1, c2, c3, c4 = st.columns(4)
                        c1.metric("평균 추정강도", f"{s_mean:.2f} MPa")
                        c2.metric("설계기준강도", f"{design_fck:.1f} MPa")
                        c3.metric("강도비 (추정/설계)", f"{ratio:.1f} %", delta=f"{ratio-100:.1f}%")
                        c4.metric("종합 판정", grade_mk)
                        
                        # 상세 데이터프레임
                        df_res = pd.DataFrame({
                            "공식 구분": ["일본건축학회", "일본재료학회", "과기부(고강도)", "권영웅(고강도)", "KALIS"],
                            "추정 강도 (MPa)": est_list,
                            "설계 대비 비율 (%)": [x/design_fck*100 for x in est_list],
                            "적용 수식": [
                                "(7.3×R+100)×0.098", "1.27×R-18.0", "(15.2×R-112.8)×0.098", "2.304×R-38.8", "1.3343×R+8.1977"
                            ]
                        })
                        
                        st.dataframe(
                            df_res.style.format({"추정 강도 (MPa)": "{:.2f}", "설계 대비 비율 (%)": "{:.1f}%"})
                            .highlight_between(left=0, right=99.9, subset=["설계 대비 비율 (%)"], color="#ffcdd2"),
                            use_container_width=True
                        )
                        
                        # CSV 다운로드
                        csv_data = convert_df(df_res)
                        file_n = f"{project_name}_반발경도_결과.csv"
                        st.download_button("📥 결과 보고서 다운로드 (CSV)", csv_data, file_name=file_n, mime='text/csv')
                        
                        st.markdown("---")
                        st.caption(f"ℹ️ 산정 기초값: [반발경도 R0: {R0:.1f}] [보정계수: {corr:+.1f}] [재령계수: {age_c:.3f}] [기각 데이터: {discard_cnt}개]")

                    # [Sub 2] 산정된 값들의 통계
                    with sub2:
                        st.subheader("📈 추정 강도값 분포 (5개 제안식)")
                        st.info("각기 다른 5개 공식으로 산출된 값들의 편차를 분석합니다.")
                        
                        s_std = np.std(est_list, ddof=1)
                        s_cov = (s_std / s_mean * 100) if s_mean > 0 else 0
                        
                        col_s1, col_s2, col_s3, col_s4, col_s5 = st.columns(5)
                        col_s1.metric("평균", f"{s_mean:.2f} MPa")
                        col_s2.metric("최대", f"{max(est_list):.2f} MPa")
                        col_s3.metric("최소", f"{min(est_list):.2f} MPa")
                        col_s4.metric("표준편차", f"{s_std:.2f}")
                        col_s5.metric("변동계수", f"{s_cov:.1f} %")
                        
                        st.bar_chart(pd.DataFrame({"강도": est_list}, index=df_res["공식 구분"]))

        except ValueError:
            st.error("숫자만 입력해주세요.")

# =========================================================
# [Tab 3] 강도 통계 분석 (직접 입력)
# =========================================================
with tab3:
    st.header("📈 강도 데이터 통계 분석")
    st.markdown("##### 📝 이미 산정된 강도 값들을 입력하여 통계를 확인하세요.")
    
    with st.container():
        input_stats = st.text_area(
            "데이터 입력 (MPa)",
            placeholder="예: 21.5 22.1 23.0 24.5 ...",
            height=100
        )
        
    if st.button("📊 통계 분석 실행", type="primary", key="btn_stat"):
        if not input_stats.strip():
            st.warning("데이터를 입력해주세요.")
        else:
            try:
                # 데이터 파싱
                clean_s = input_stats.replace(',', ' ').replace('\n', ' ')
                data_s = [float(x) for x in clean_s.split() if x.strip()]
                
                if len(data_s) < 2:
                    st.error("데이터가 2개 이상이어야 합니다.")
                else:
                    st_mean = np.mean(data_s)
                    st_std = np.std(data_s, ddof=1)
                    st_max = np.max(data_s)
                    st_min = np.min(data_s)
                    st_cov = (st_std / st_mean * 100) if st_mean > 0 else 0
                    
                    st.divider()
                    st.success(f"✅ 총 {len(data_s)}개 데이터 분석 완료")
                    
                    k1, k2, k3, k4, k5 = st.columns(5)
                    k1.metric("평균 (Mean)", f"{st_mean:.2f} MPa")
                    k2.metric("최대 (Max)", f"{st_max:.2f} MPa")
                    k3.metric("최소 (Min)", f"{st_min:.2f} MPa")
                    k4.metric("표준편차 (SD)", f"{st_std:.2f}")
                    k5.metric("변동계수 (COV)", f"{st_cov:.1f} %")
                    
                    st.markdown("---")
                    
                    v1, v2 = st.columns([2, 1])
                    with v1:
                        st.subheader("📊 데이터 분포 (Sorted)")
                        sorted_d = sorted(data_s)
                        st.bar_chart(sorted_d)
                    with v2:
                        st.subheader("📋 데이터 목록")
                        st.dataframe(pd.DataFrame(data_s, columns=["강도(MPa)"]).style.format("{:.2f}"), use_container_width=True, height=300)
                        
            except ValueError:
                st.error("숫자만 입력해주세요.")
