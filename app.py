import streamlit as st
import math
import pandas as pd
import numpy as np
import altair as alt

# =========================================================
# 0. 전역 상수 (CONFIG) - 매직넘버 상수화
# =========================================================
DEFAULT_AGE_DAYS = 3000          # 기본 재령 (일)
DEFAULT_FCK = 24.0               # 기본 설계기준강도 (MPa)
HIGH_STRENGTH_THRESHOLD = 40.0   # 고강도/일반강도 콘크리트 경계 (MPa)
OUTLIER_LOWER = 0.8              # 이상치 기각 하한 (평균의 80%)
OUTLIER_UPPER = 1.2              # 이상치 기각 상한 (평균의 120%)
DISCARD_RATIO_LIMIT = 0.20       # 기각률 한계 (20% 초과 시 시험 무효)
KGF_TO_MPA = 0.098               # kgf/cm² → MPa 환산 계수
SCHMIDT_R_MIN = 20               # 슈미트해머 유효 반발도 하한
SCHMIDT_R_MAX = 60               # 슈미트해머 유효 반발도 상한

# =========================================================
# 1. 페이지 기본 설정 및 스타일
# =========================================================
st.set_page_config(
    page_title="구조물 안전진단 통합 평가 Pro",
    page_icon="🏗️",
    layout="wide",
    initial_sidebar_state="collapsed"
)

st.markdown("""
    <style>
    .stTabs [data-baseweb="tab-list"] { gap: 2px; }
    .stTabs [data-baseweb="tab"] {
        height: 50px; white-space: pre-wrap; background-color: #f0f2f6;
        border-radius: 4px 4px 0px 0px; gap: 1px; padding-top: 10px; padding-bottom: 10px;
    }
    [data-testid="stMetricValue"] { font-size: 1.2rem !important; }
    .calc-box { background-color: #f8f9fa; padding: 15px; border-radius: 10px; border-left: 5px solid #1f77b4; margin-bottom: 15px; }
    </style>
""", unsafe_allow_html=True)

# 세션 상태 초기화
if "batch_results" not in st.session_state:
    st.session_state.batch_results = None
if "single_result" not in st.session_state:
    st.session_state.single_result = None

# =========================================================
# 2. 공통 유틸리티 함수
# =========================================================

def parse_numbers(text):
    """ 문자열에서 숫자만 안전하게 파싱 (음수, 소수, 과학표기법, 전각쉼표 모두 지원) """
    if text is None:
        return []
    s = str(text)
    # 전각 쉼표/구분자 처리
    for sep in [',', '，', '、', ';', '\t']:
        s = s.replace(sep, ' ')
    out = []
    for token in s.split():
        try:
            out.append(float(token))
        except ValueError:
            continue
    return out


def convert_df_to_csv(df):
    """ DataFrame을 UTF-8 BOM CSV 바이트로 변환 """
    return df.to_csv(index=False).encode('utf-8-sig')


# =========================================================
# 3. 반발경도 강도 산정 함수
# =========================================================

def get_angle_correction(R_val, angle):
    """
    타격 방향 보정값 (KS F 2730 / 시설물 안전점검 세부지침 기준)

    부호 규약:
      +90° : 상향 수직 타격 (천장면 등) → 중력 반대 → R 작게 측정 → (+) 보정
      +45° : 상향 경사 타격 → (+) 보정
       0°  : 수평 타격 → 보정 없음
      -45° : 하향 경사 타격 → (-) 보정
      -90° : 하향 수직 타격 (바닥면) → 중력 방향 → R 크게 측정 → (-) 보정
    """
    try:
        angle = int(angle)
    except (ValueError, TypeError):
        angle = 0

    correction_table = {
        +90: {20: +5.4, 30: +4.7, 40: +3.9, 50: +3.1, 60: +2.3},  # 상향 수직
        +45: {20: +3.5, 30: +3.1, 40: +2.6, 50: +2.0, 60: +1.6},  # 상향 경사
          0: {20:  0.0, 30:  0.0, 40:  0.0, 50:  0.0, 60:  0.0},  # 수평
        -45: {20: -2.4, 30: -2.3, 40: -2.0, 50: -1.6, 60: -1.3},  # 하향 경사
        -90: {20: -3.2, 30: -3.1, 40: -2.7, 50: -2.2, 60: -1.7},  # 하향 수직
    }

    if angle not in correction_table:
        return 0.0

    data = correction_table[angle]
    sorted_keys = sorted(data.keys())

    # R 값에 해당하는 구간 키 선택 (이하 절상 방식)
    target_key = sorted_keys[0]
    for key in sorted_keys:
        if R_val >= key:
            target_key = key
        else:
            break
    return data[target_key]


def get_age_coefficient(days):
    """ 재령 보정계수 (시설물 안전점검 세부지침 기준, 선형 보간) """
    try:
        days = float(days)
    except (ValueError, TypeError):
        days = float(DEFAULT_AGE_DAYS)

    age_table = {
        10: 1.55, 20: 1.12, 28: 1.00, 50: 0.87,
        100: 0.78, 150: 0.74, 200: 0.72, 300: 0.70,
        500: 0.67, 1000: 0.65, 3000: 0.63
    }
    sorted_days = sorted(age_table.keys())

    if days >= sorted_days[-1]:
        return age_table[sorted_days[-1]]
    if days <= sorted_days[0]:
        return age_table[sorted_days[0]]

    for i in range(len(sorted_days) - 1):
        d1, d2 = sorted_days[i], sorted_days[i + 1]
        if d1 <= days <= d2:
            c1, c2 = age_table[d1], age_table[d2]
            return c1 + (days - d1) / (d2 - d1) * (c2 - c1)
    return 1.0


def calculate_strength(readings, angle, days, design_fck=DEFAULT_FCK):
    """
    반발경도 강도 산정 메인 로직

    Returns:
        (성공여부, 결과 dict 또는 오류 메시지)

    각 공식의 원 단위:
      - 일본건축학회(AIJ): kgf/cm² → 0.098 곱해 MPa 환산
      - 일본재료학회(JSMS): N/mm² (MPa) - 환산 불필요
      - 과학기술처(MST): kgf/cm² → 환산
      - 권영웅: N/mm² (MPa) - 환산 불필요
      - KALIS: N/mm² (MPa) - 환산 불필요
    """
    if not readings or len(readings) < 5:
        return False, "데이터 부족 (최소 5개 이상 필요)"

    n_total = len(readings)
    avg1 = sum(readings) / n_total

    # 인덱스 기반으로 유효/기각 분리 (중복값 누락 방지)
    valid, excluded = [], []
    for r in readings:
        if avg1 * OUTLIER_LOWER <= r <= avg1 * OUTLIER_UPPER:
            valid.append(r)
        else:
            excluded.append(r)

    # 기각률 기준으로 시험 무효 판정
    discard_ratio = len(excluded) / n_total
    if discard_ratio > DISCARD_RATIO_LIMIT:
        return False, f"시험 무효 (기각률 {discard_ratio*100:.0f}% > 20%)"

    if not valid:
        return False, "유효 데이터 없음"

    R_avg = sum(valid) / len(valid)

    # 슈미트해머 유효범위 경고용 플래그
    out_of_range = not (SCHMIDT_R_MIN <= R_avg <= SCHMIDT_R_MAX)

    corr = get_angle_correction(R_avg, angle)
    R0 = R_avg + corr
    age_c = get_age_coefficient(days)

    # 각 공식별 추정 압축강도 (단위: MPa)
    f_aij   = max(0, (7.3 * R0 + 100) * KGF_TO_MPA * age_c)   # 일본건축학회 (kgf/cm²)
    f_jsms  = max(0, (1.27 * R0 - 18.0) * age_c)              # 일본재료학회 (N/mm²)
    f_mst   = max(0, (15.2 * R0 - 112.8) * KGF_TO_MPA * age_c) # 과학기술처 (kgf/cm²)
    f_kwon  = max(0, (2.304 * R0 - 38.80) * age_c)            # 권영웅 (N/mm²)
    f_kalis = max(0, (1.3343 * R0 + 8.1977) * age_c)          # KALIS (N/mm²)

    # 설계강도 구간별 적용 공식군
    if design_fck < HIGH_STRENGTH_THRESHOLD:
        target_fs = [f_aij, f_jsms]
    else:
        target_fs = [f_mst, f_kwon, f_kalis]

    s_mean = float(np.mean(target_fs))
    s_median = float(np.median(target_fs))
    s_min = float(np.min(target_fs))

    return True, {
        "R_initial": avg1,
        "R_avg": R_avg,
        "Angle_Corr": corr,
        "R0": R0,
        "Age_Coeff": age_c,
        "Discard": len(excluded),
        "Discard_Ratio": discard_ratio,
        "Excluded": excluded,
        "Out_Of_Range": out_of_range,
        "Formulas": {
            "일본건축": f_aij,
            "일본재료": f_jsms,
            "과기부": f_mst,
            "권영웅": f_kwon,
            "KALIS": f_kalis
        },
        "Mean_Strength": s_mean,
        "Median_Strength": s_median,
        "Min_Strength": s_min
    }


# =========================================================
# 4. 탄산화 평가 함수
# =========================================================

def carbonation_grade(remaining_cover):
    """ 잔여 피복 두께 기반 등급 판정 """
    if remaining_cover >= 30:
        return "A", "green", "매우 양호"
    if remaining_cover >= 10:
        return "B", "blue", "양호"
    if remaining_cover >= 0:
        return "C", "orange", "보통"
    return "D", "red", "불량"


# =========================================================
# 5. 메인 UI 구성
# =========================================================

st.title("🏗️ 구조물 안전진단 통합 평가 Pro")

with st.sidebar:
    st.header("⚙️ 프로젝트 정보")
    p_name = st.text_input("프로젝트명", "OO시설물 정밀점검")
    st.divider()
    st.caption("시설물안전법 및 세부지침 준수")
    st.caption(f"기본값: 재령 {DEFAULT_AGE_DAYS}일 / fck {DEFAULT_FCK}MPa")

tab1, tab2, tab3, tab4 = st.tabs(["📖 점검 매뉴얼", "🔨 반발경도", "🧪 탄산화", "📈 통계·비교"])

# ---------------------------------------------------------
# [Tab 1] 점검 매뉴얼
# ---------------------------------------------------------
with tab1:
    st.subheader("💡 프로그램 사용 가이드")
    st.info("""
    **1. 반발경도 산정 시 설계기준강도를 입력해주세요.**
    * 설계기준강도를 바탕으로 압축강도 추정에 필요한 공식 적용 로직이 자동으로 변경됩니다 (40MPa 기준).

    **2. 타격방향 보정**
    * 매뉴얼을 참고해서 상향 타격(+) 인지 하향 타격(-) 인지 구분하여 선택하세요.
    * 부호 규약: 상향(+), 수평(0), 하향(-)

    **3. 기본값**
    * 별도로 지정하지 않으면 재령 3000일, 설계기준강도 24MPa가 적용됩니다.

    **4. 통계ㆍ비교 탭 활용 안내**
    * 추정된 압축강도의 표준편차와 변동계수 등을 계산하여 해당 시설물에 가장 적합한 산정식을 검토합니다.
    """)

    st.divider()
    st.subheader("📋 시설물 안전점검·진단 세부지침 매뉴얼")

    with st.expander("1. 반발경도 시험 (Rebound Hardness Test) 상세 지침", expanded=False):
        st.markdown("""
        #### **✅ 개요 및 원리**
        * 콘크리트 표면을 슈미트 해머로 타격하여 반발되는 거리($R$)를 측정하고, 이와 압축강도 사이의 상관관계를 통해 비파괴 강도를 추정합니다.

        #### **✅ 측정 장소 선정 (지침 기준)**
        * **부재 두께**: 최소 10cm 이상인 부위를 선정합니다.
        * **이격 거리**: 부재의 모서리나 끝부분으로부터 3~6cm 이상 떨어진 곳을 타격합니다.
        * **표면 처리**: 도장재, 요철, 이물질 등을 제거하고 평탄한 콘크리트 면을 노출시킨 후 측정합니다.

        #### **✅ 측정 및 기각 룰**
        1. **타격 점수**: 1개소당 **20점 이상** 측정을 원칙으로 합니다 (가로·세로 3cm 간격 격자망).
        2. **이상치 기각**: 전체 측정값의 산술평균을 낸 후, 평균값에서 **±20%를 벗어나는 데이터는 무효**로 처리합니다.
        3. **시험 무효**: 기각률이 **20%를 초과**하는 경우 해당 측정 지점의 시험은 무효로 보고 재시험을 실시합니다.

        #### **📍 타격 방향 보정 (Angle Correction)**
        """)

        m_df = pd.DataFrame({
            "구분": ["상향 수직 (+90°)", "상향 경사 (+45°)", "수평 타격 (0°)", "하향 경사 (-45°)", "하향 수직 (-90°)"],
            "대상 부재 예시": ["슬래브 하부 (천장)", "보 경사면", "벽체, 기둥 측면", "교대/교각 경사부", "슬래브 상면 (바닥)"],
            "보정 부호": ["(+) 가산", "(+) 가산", "0", "(-) 감산", "(-) 감산"]
        })
        st.table(m_df)
        st.info("※ 본 프로그램은 위 각도 선택 시 세부지침의 보정표 값을 자동으로 가감하여 $R_0$를 산출합니다.")

    with st.expander("2. 탄산화 깊이 측정 (Carbonation Test) 상세 지침", expanded=False):
        st.markdown("""
        #### **✅ 개요 및 측정 방법**
        * 공기 중의 탄산가스가 콘크리트 내부로 침투하여 알칼리성을 저하시키는 현상을 측정합니다.
        * **시약**: 1% 페놀프탈레인 용액을 사용합니다.
        * **측정**: 신선한 콘크리트 파쇄면에 시약을 분무한 후, **적자색으로 변하지 않는 구간(무색)**의 깊이를 0.5mm 단위로 측정합니다.

        #### **✅ 탄산화 속도 및 수명 산식**
        * **$C = A\\sqrt{t}$** ($C$: 깊이mm, $A$: 속도계수, $t$: 년수)
        * 철근위치 도달 시간: $T = (d_{cover}/A)^2$

        #### **✅ 등급 판정 기준 (잔여 피복 두께 기반)**
        * **A (매우 양호)**: 잔여 피복 두께 30mm 이상
        * **B (양호)**: 잔여 피복 두께 10mm ~ 30mm 미만
        * **C (보통)**: 잔여 피복 두께 0mm ~ 10mm 미만
        * **D (불량)**: 탄산화 깊이가 철근 위치를 초과 (잔여 피복 < 0)
        """)

# ---------------------------------------------------------
# [Tab 2] 반발경도 평가
# ---------------------------------------------------------
with tab2:
    st.subheader("🔨 반발경도 정밀 강도 산정")
    mode = st.radio("입력 방식", ["단일 지점", "다중 지점 (Batch/File)"], horizontal=True)

    angle_label = lambda x: {
        90: "+90°(상향수직)", 45: "+45°(상향경사)", 0: "0°(수평)",
        -45: "-45°(하향경사)", -90: "-90°(하향수직)"
    }[x]

    if mode == "단일 지점":
        with st.container(border=True):
            c1, c2, c3 = st.columns(3)
            with c1:
                angle = st.selectbox("타격 방향", [90, 45, 0, -45, -90], format_func=angle_label)
            with c2:
                days = st.number_input("재령(일)", 1, 10000, DEFAULT_AGE_DAYS)
            with c3:
                fck = st.number_input("설계강도(MPa)", 15.0, 100.0, DEFAULT_FCK)
            txt = st.text_area(
                "측정값 (공백/줄바꿈/쉼표 구분)",
                "54 56 55 53 58 55 54 55 52 57 55 56 54 55 59 42 55 56 54 55",
                height=80
            )

        if st.button("계산 실행", type="primary", use_container_width=True):
            rd = parse_numbers(txt)
            ok, res = calculate_strength(rd, angle, days, fck)

            if not ok:
                st.error(f"❌ {res}")
                st.session_state.single_result = None
            else:
                st.session_state.single_result = res
                st.success(f"✅ 평균 추정 압축강도: **{res['Mean_Strength']:.2f} MPa** "
                          f"(중앙값 {res['Median_Strength']:.2f} / 최저 {res['Min_Strength']:.2f})")

                if res["Out_Of_Range"]:
                    st.warning(f"⚠️ 평균 R값({res['R_avg']:.1f})이 슈미트해머 유효범위"
                              f"({SCHMIDT_R_MIN}~{SCHMIDT_R_MAX})를 벗어났습니다. 신뢰도 검토 필요.")

                with st.container(border=True):
                    m1, m2, m3, m4 = st.columns(4)
                    m1.metric("유효 평균 R", f"{res['R_avg']:.1f}")
                    m2.metric("각도 보정", f"{res['Angle_Corr']:+.1f}")
                    m3.metric("최종 R₀", f"{res['R0']:.1f}")
                    m4.metric("재령 계수 α", f"{res['Age_Coeff']:.2f}")
                    st.caption(f"기각 데이터: {res['Discard']}개 ({res['Discard_Ratio']*100:.1f}%) - {res['Excluded']}")

                df_f = pd.DataFrame({
                    "공식": list(res["Formulas"].keys()),
                    "강도": list(res["Formulas"].values())
                })
                bar = alt.Chart(df_f).mark_bar().encode(
                    x=alt.X('공식', sort=None),
                    y=alt.Y('강도', title='추정 압축강도 (MPa)'),
                    color=alt.condition(
                        alt.datum.강도 >= fck,
                        alt.value('#4D96FF'),
                        alt.value('#FF6B6B')
                    ),
                    tooltip=['공식', alt.Tooltip('강도:Q', format='.2f')]
                ).properties(height=350)
                rule = alt.Chart(pd.DataFrame({'y': [fck]})).mark_rule(
                    color='red', strokeDash=[5, 3], size=2
                ).encode(y='y')
                st.altair_chart(bar + rule, use_container_width=True)

                # CSV 다운로드
                df_export = df_f.copy()
                df_export["설계강도"] = fck
                df_export["강도비(%)"] = (df_export["강도"] / fck * 100).round(1)
                st.download_button(
                    "📥 결과 CSV 다운로드",
                    convert_df_to_csv(df_export),
                    f"{p_name}_단일지점_반발경도.csv",
                    "text/csv"
                )

    else:
        uploaded_file = st.file_uploader("CSV 또는 Excel 파일 업로드", type=["csv", "xlsx"])
        init_data = []

        if uploaded_file:
            try:
                if uploaded_file.name.endswith('.csv'):
                    df_up = pd.read_csv(uploaded_file)
                else:
                    df_up = pd.read_excel(uploaded_file)
                for _, row in df_up.iterrows():
                    init_data.append({
                        "선택": True,
                        "지점": row.get("지점", "P"),
                        "각도": int(row.get("각도", 0)),
                        "재령": int(row.get("재령", DEFAULT_AGE_DAYS)),
                        "설계": float(row.get("설계", DEFAULT_FCK)),
                        "데이터": str(row.get("데이터", ""))
                    })
            except (ValueError, KeyError, pd.errors.ParserError) as e:
                st.error(f"파일 파싱 실패: {e}")

        df_batch = pd.DataFrame(init_data) if init_data else pd.DataFrame(
            columns=["선택", "지점", "각도", "재령", "설계", "데이터"]
        )
        edited_df = st.data_editor(
            df_batch,
            column_config={
                "선택": st.column_config.CheckboxColumn("선택", default=True),
                "각도": st.column_config.SelectboxColumn(
                    "각도", options=[90, 45, 0, -45, -90], required=True
                ),
                "재령": st.column_config.NumberColumn("재령(일)", default=DEFAULT_AGE_DAYS),
                "설계": st.column_config.NumberColumn("설계강도", default=DEFAULT_FCK),
                "데이터": st.column_config.TextColumn("측정값(공백구분)", width="large")
            },
            use_container_width=True,
            hide_index=True,
            num_rows="dynamic"
        )

        if st.button("🚀 일괄 계산 실행", type="primary", use_container_width=True):
            batch_res = []
            errors = []
            for idx, row in edited_df.iterrows():
                if not row["선택"]:
                    continue
                try:
                    rd_list = parse_numbers(row["데이터"])
                    ang_v = 0 if pd.isna(row["각도"]) else int(row["각도"])
                    age_v = DEFAULT_AGE_DAYS if pd.isna(row["재령"]) else float(row["재령"])
                    fck_v = DEFAULT_FCK if pd.isna(row["설계"]) else float(row["설계"])

                    ok, res = calculate_strength(rd_list, ang_v, age_v, fck_v)
                    if ok:
                        data_entry = {
                            "지점": row["지점"],
                            "설계": fck_v,
                            "추정강도": round(res["Mean_Strength"], 2),
                            "강도비(%)": round((res["Mean_Strength"] / fck_v) * 100, 1),
                            "유효평균R": round(res["R_avg"], 1),
                            "보정R0": round(res["R0"], 1),
                            "재령계수": round(res["Age_Coeff"], 2),
                            "기각수": res["Discard"],
                            "기각데이터": str(res["Excluded"])
                        }
                        for f_name, f_val in res["Formulas"].items():
                            data_entry[f_name] = round(f_val, 1)
                        batch_res.append(data_entry)
                    else:
                        errors.append(f"[{row.get('지점', idx)}] {res}")
                except (ValueError, TypeError, KeyError) as e:
                    errors.append(f"[{row.get('지점', idx)}] 처리 오류: {e}")
                    continue

            if errors:
                with st.expander(f"⚠️ 처리 실패 {len(errors)}건", expanded=False):
                    for e in errors:
                        st.text(e)

            if batch_res:
                final_df = pd.DataFrame(batch_res)
                st.session_state.batch_results = final_df

                res_tab1, res_tab2 = st.tabs(["📋 요약", "🔍 세부 데이터"])
                with res_tab1:
                    st.dataframe(
                        final_df[["지점", "설계", "추정강도", "강도비(%)"]],
                        use_container_width=True,
                        hide_index=True
                    )
                with res_tab2:
                    st.dataframe(final_df, use_container_width=True, hide_index=True)

                st.download_button(
                    "📥 일괄 결과 CSV 다운로드",
                    convert_df_to_csv(final_df),
                    f"{p_name}_배치_반발경도.csv",
                    "text/csv"
                )
            elif not errors:
                st.warning("선택된 행이 없거나 유효한 데이터가 없습니다.")

# ---------------------------------------------------------
# [Tab 3] 탄산화 평가
# ---------------------------------------------------------
with tab3:
    st.subheader("🧪 탄산화 깊이 및 상세 분석")
    with st.container(border=True):
        c1, c2, c3 = st.columns(3)
        with c1:
            m_depth = st.number_input("측정 깊이(mm)", 0.0, 100.0, 12.0)
        with c2:
            d_cover = st.number_input("설계 피복(mm)", 10.0, 200.0, 40.0)
        with c3:
            a_years = st.number_input("경과 년수(년)", 1, 100, 20)

    if st.button("평가 실행", type="primary", key="btn_carb_run", use_container_width=True):
        rem = d_cover - m_depth
        rate_a = m_depth / math.sqrt(a_years) if a_years > 0 else 0
        years_to_rebar = (d_cover / rate_a) ** 2 if rate_a > 0 else 99.9
        years_remaining = years_to_rebar - a_years

        grade, color, grade_desc = carbonation_grade(rem)

        # 1. 등급 결과 및 상세 계산 지표
        st.markdown(f"### 결과: :{color}[{grade} 등급] - {grade_desc}")
        with st.container(border=True):
            cc1, cc2, cc3 = st.columns(3)
            cc1.metric("잔여 피복량", f"{rem:.1f} mm")
            cc2.metric("탄산화 속도계수 (A)", f"{rate_a:.3f}")
            cc3.metric("철근위치 도달까지", f"{max(0, years_remaining):.1f} 년")
            st.info(
                f"**계산 근거:** $A = {m_depth} / \\sqrt{{{a_years}}} = {rate_a:.3f}$ , "
                f"철근 도달까지 잔여 $T = ({d_cover}/{rate_a:.3f})^2 - {a_years} = {years_remaining:.1f}$년"
            )

        # 2. 탄산화 예측 그래프
        year_steps = np.linspace(0, 100, 101)
        depth_steps = rate_a * np.sqrt(year_steps)
        df_plot = pd.DataFrame({'경과년수': year_steps, '탄산화깊이': depth_steps})

        line = alt.Chart(df_plot).mark_line(color='#1f77b4', strokeWidth=2).encode(
            x=alt.X('경과년수:Q', title='경과년수 (년)'),
            y=alt.Y('탄산화깊이:Q', title='탄산화 깊이 (mm)'),
            tooltip=[alt.Tooltip('경과년수:Q', format='.0f'),
                     alt.Tooltip('탄산화깊이:Q', format='.2f')]
        )
        rule = alt.Chart(pd.DataFrame({'y': [d_cover], 'label': ['설계 피복']})).mark_rule(
            color='red', strokeDash=[5, 5], size=2
        ).encode(y='y')
        point = alt.Chart(pd.DataFrame({'x': [a_years], 'y': [m_depth]})).mark_point(
            color='orange', size=150, filled=True
        ).encode(x='x', y='y')
        st.altair_chart((line + rule + point).properties(height=350), use_container_width=True)

        # 결과 다운로드
        df_carb = pd.DataFrame([{
            "프로젝트": p_name,
            "측정깊이(mm)": m_depth,
            "설계피복(mm)": d_cover,
            "경과년수": a_years,
            "잔여피복(mm)": round(rem, 1),
            "속도계수A": round(rate_a, 3),
            "철근도달잔여(년)": round(max(0, years_remaining), 1),
            "등급": grade,
            "상태": grade_desc
        }])
        st.download_button(
            "📥 탄산화 결과 CSV 다운로드",
            convert_df_to_csv(df_carb),
            f"{p_name}_탄산화평가.csv",
            "text/csv"
        )

# ---------------------------------------------------------
# [Tab 4] 통계 및 비교
# ---------------------------------------------------------
with tab4:
    st.subheader("📊 강도 통계 및 비교 분석")

    # Tab2 배치 결과 자동 연동 옵션
    use_batch = False
    if st.session_state.batch_results is not None and len(st.session_state.batch_results) > 0:
        use_batch = st.checkbox(
            f"🔗 반발경도 배치 결과 ({len(st.session_state.batch_results)}건) 불러오기",
            value=False
        )

    c1, c2 = st.columns([1, 2])
    with c1:
        st_fck = st.number_input("기준 설계강도(MPa)", 15.0, 100.0, DEFAULT_FCK, key="stat_fck")
    with c2:
        if use_batch:
            default_text = " ".join(
                str(v) for v in st.session_state.batch_results["추정강도"].tolist()
            )
        else:
            default_text = "24.5 26.2 23.1 21.8 25.5 27.0"
        raw_txt = st.text_area("강도 데이터 목록", default_text, height=68)

    parsed = parse_numbers(raw_txt)

    if parsed:
        df_stat = pd.DataFrame({
            "순번": range(1, len(parsed) + 1),
            "추정강도": parsed,
            "적용공식": ["전체평균(추천)"] * len(parsed)
        })
        label_df = st.data_editor(
            df_stat,
            column_config={
                "순번": st.column_config.NumberColumn("No.", disabled=True),
                "적용공식": st.column_config.SelectboxColumn(
                    "공식 선택",
                    options=["일본건축", "일본재료", "과기부", "권영웅", "KALIS", "전체평균(추천)"],
                    required=True
                )
            },
            use_container_width=True,
            hide_index=True
        )

        if st.button("통계 분석 실행", type="primary", use_container_width=True):
            if st_fck < HIGH_STRENGTH_THRESHOLD:
                valid_f = ["일본건축", "일본재료", "전체평균(추천)"]
            else:
                valid_f = ["과기부", "권영웅", "KALIS", "전체평균(추천)"]

            filtered = label_df[label_df["적용공식"].isin(valid_f)]
            data = sorted(filtered["추정강도"].tolist())

            if len(data) >= 2:
                avg_v = float(np.mean(data))
                std_v = float(np.std(data, ddof=1))
                cv_v = (std_v / avg_v * 100) if avg_v > 0 else 0
                median_v = float(np.median(data))
                min_v = float(np.min(data))
                max_v = float(np.max(data))

                with st.container(border=True):
                    m1, m2, m3 = st.columns(3)
                    m1.metric("평균", f"{avg_v:.2f} MPa", delta=f"{(avg_v/st_fck*100):.1f}%")
                    m2.metric("표준편차 (σ)", f"{std_v:.2f} MPa")
                    m3.metric("변동계수 (CV)", f"{cv_v:.1f}%")

                    m4, m5, m6 = st.columns(3)
                    m4.metric("중앙값", f"{median_v:.2f} MPa")
                    m5.metric("최저", f"{min_v:.2f} MPa")
                    m6.metric("최고", f"{max_v:.2f} MPa")

                # CV에 따른 신뢰성 코멘트
                if cv_v < 10:
                    st.success(f"✅ 변동계수 {cv_v:.1f}% — 데이터 균질성 양호")
                elif cv_v < 20:
                    st.info(f"ℹ️ 변동계수 {cv_v:.1f}% — 보통 수준")
                else:
                    st.warning(f"⚠️ 변동계수 {cv_v:.1f}% — 데이터 산포가 큼, 추가 시험 권장")

                bar = alt.Chart(pd.DataFrame({
                    "번호": range(1, len(data) + 1),
                    "강도": data
                })).mark_bar().encode(
                    x='번호:O',
                    y=alt.Y('강도:Q', title='추정강도 (MPa)'),
                    color=alt.condition(
                        alt.datum.강도 >= st_fck,
                        alt.value('#4D96FF'),
                        alt.value('#FF6B6B')
                    ),
                    tooltip=['번호', alt.Tooltip('강도:Q', format='.2f')]
                )
                rule = alt.Chart(pd.DataFrame({'y': [st_fck]})).mark_rule(
                    color='red', strokeDash=[5, 3], size=2
                ).encode(y='y')
                st.altair_chart((bar + rule).properties(height=350), use_container_width=True)
            else:
                st.warning("통계 분석을 위해 최소 2개 이상의 데이터를 선택하세요.")
    else:
        st.info("강도 데이터를 입력해주세요.")
