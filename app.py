import streamlit as st
import math
import pandas as pd
import numpy as np
import io
import altair as alt
import re
import logging
import hashlib
import html
from PIL import Image

logger = logging.getLogger(__name__)

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
    .block-container {
        padding-top: 1rem !important;
        padding-bottom: 5rem !important;
        padding-left: 1rem !important;
        padding-right: 1rem !important;
        max-width: 100% !important;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        overflow-x: auto;
        white-space: nowrap;
        scrollbar-width: none;
        padding-left: 2px;
    }
    .stTabs [data-baseweb="tab"] {
        height: 45px;
        padding: 5px 15px;
        background-color: #f0f2f6;
        border-radius: 8px 8px 0px 0px;
        font-size: 14px;
    }
    div[data-testid="stExpander"] details > summary {
        list-style: none !important;
        display: flex !important;
        align-items: flex-start !important;
        padding: 10px !important;
        height: auto !important;
        min-height: 40px;
        border: 1px solid #f0f2f6;
        border-radius: 8px;
    }
    div[data-testid="stExpander"] details > summary::-webkit-details-marker { display: none !important; }
    div[data-testid="stExpander"] details > summary > svg {
        margin-right: 12px !important;
        margin-top: 3px !important;
        width: 18px !important;
        min-width: 18px !important;
        height: 18px !important;
        flex-shrink: 0 !important;
        display: block !important;
    }
    /* 일부 모바일 환경에서 아이콘 폰트가 텍스트(arrow_right)로 노출되는 현상 대응 */
    div[data-testid="stExpander"] details > summary [class*="material"],
    div[data-testid="stExpander"] details > summary [data-testid*="icon"],
    div[data-testid="stExpander"] details > summary [aria-hidden="true"] {
        display: none !important;
    }
    div[data-testid="stExpander"] details > summary {
        padding-left: 12px !important;
    }
    div[data-testid="stExpander"] details > summary p {
        font-size: 15px;
        font-weight: 600;
        margin: 0;
        line-height: 1.5;
        white-space: normal !important;
        word-break: keep-all;
    }
    [data-testid="stMetricValue"] { font-size: 1.1rem !important; word-break: break-all; }
    [data-testid="stMetricLabel"] { font-size: 0.9rem !important; }
    .calc-box { background-color: #f8f9fa; padding: 15px; border-radius: 10px; border-left: 5px solid #1f77b4; margin-bottom: 15px; }
    div[data-testid="stTable"] { overflow-x: auto; }

    /* 모바일에서 좌측 접힘 컨트롤(아이콘 텍스트 노출) 숨김 */
    @media (max-width: 768px) {
        [data-testid="collapsedControl"] { display: none !important; }
        [data-testid="stHeader"] { height: 0 !important; }
        .block-container { padding-top: 0.5rem !important; }
        div[data-testid="stExpander"] details > summary {
            padding-left: 10px !important;
        }
    }
    </style>
""", unsafe_allow_html=True)

# =========================================================
# 1-1. UI/UX 개선 스타일
# =========================================================
st.markdown("""
<style>
:root {
    --primary: #0F4C81;
    --primary-dark: #073763;
    --action: #2563EB;
    --success: #16A34A;
    --warning: #F59E0B;
    --danger: #DC2626;
    --bg-soft: #F8FAFC;
    --card: #FFFFFF;
    --border: #E2E8F0;
    --text-main: #0F172A;
    --text-sub: #64748B;
}

.block-container {
    background: linear-gradient(180deg, #F8FAFC 0%, #FFFFFF 42%) !important;
}

.app-hero {
    padding: 18px 22px;
    margin: 0 0 16px 0;
    border: 1px solid #dbeafe;
    border-left: 8px solid var(--primary);
    border-radius: 18px;
    background: linear-gradient(135deg, #ffffff 0%, #eff6ff 100%);
    box-shadow: 0 10px 24px rgba(15, 76, 129, 0.08);
}
.app-hero-title {
    font-size: 1.75rem;
    font-weight: 900;
    color: var(--text-main);
    margin-bottom: 4px;
    letter-spacing: -0.02em;
}
.app-hero-sub {
    font-size: 0.98rem;
    color: var(--text-sub);
    line-height: 1.55;
}

.workflow-wrap {
    display: flex;
    align-items: stretch;
    gap: 8px;
    margin: 10px 0 18px 0;
    padding: 12px;
    border: 1px solid #dbeafe;
    border-radius: 16px;
    background: #ffffff;
    box-shadow: 0 6px 16px rgba(15, 76, 129, 0.05);
}
.workflow-step {
    flex: 1;
    text-align: center;
    padding: 10px 8px;
    border-radius: 12px;
    border: 1px solid #d8e6f8;
    background: #f8fbff;
    color: #334155;
    font-size: 0.88rem;
    line-height: 1.35;
    min-height: 58px;
}
.workflow-step b { font-size: 0.96rem; }
.workflow-step.active {
    color: #ffffff;
    background: linear-gradient(135deg, var(--primary) 0%, #2563EB 100%);
    border-color: var(--primary);
    box-shadow: 0 6px 14px rgba(37, 99, 235, 0.18);
}
.workflow-arrow {
    align-self: center;
    color: var(--primary);
    font-weight: 900;
    padding: 0 2px;
}

.home-grid {
    display: grid;
    grid-template-columns: repeat(4, minmax(0, 1fr));
    gap: 12px;
    margin: 12px 0 18px 0;
}
.home-card {
    background: var(--card);
    border: 1px solid var(--border);
    border-radius: 16px;
    padding: 16px 18px;
    box-shadow: 0 8px 18px rgba(15, 76, 129, 0.05);
}
.home-card-title {
    color: var(--text-sub);
    font-size: 0.88rem;
    margin-bottom: 6px;
}
.home-card-value {
    color: var(--text-main);
    font-size: 1.55rem;
    font-weight: 900;
}
.home-card-sub {
    color: var(--text-sub);
    font-size: 0.82rem;
    margin-top: 4px;
}

.step-title {
    margin: 10px 0 10px 0;
    padding: 12px 14px;
    border-radius: 14px;
    border: 1px solid #dbeafe;
    background: linear-gradient(90deg, #eff6ff 0%, #ffffff 100%);
}
.step-title b {
    color: var(--primary);
    font-size: 1.08rem;
}
.step-title span {
    display: block;
    margin-top: 3px;
    color: var(--text-sub);
    font-size: 0.9rem;
    line-height: 1.5;
}

.result-hero {
    display: grid;
    grid-template-columns: 1.25fr 1fr 1fr;
    gap: 14px;
    padding: 18px 20px;
    margin: 14px 0 14px 0;
    border: 1px solid var(--border);
    border-left: 8px solid var(--primary);
    border-radius: 18px;
    background: #ffffff;
    box-shadow: 0 10px 24px rgba(15, 76, 129, 0.08);
}
.result-label {
    color: var(--text-sub);
    font-size: 0.88rem;
    margin-bottom: 6px;
}
.result-value {
    color: var(--text-main);
    font-size: 1.75rem;
    font-weight: 900;
    letter-spacing: -0.02em;
}
.result-grade {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    color: white;
    font-weight: 900;
    padding: 8px 16px;
    border-radius: 999px;
    font-size: 1.05rem;
    min-width: 88px;
}
.result-note {
    color: var(--text-sub);
    font-size: 0.82rem;
    margin-top: 6px;
}

.recommend-card {
    background: linear-gradient(135deg, #ecfdf5 0%, #ffffff 100%);
    border: 1px solid #bbf7d0;
    border-left: 8px solid var(--success);
    border-radius: 18px;
    padding: 18px 20px;
    margin: 12px 0 18px 0;
    box-shadow: 0 8px 18px rgba(22, 163, 74, 0.08);
}
.recommend-title {
    color: #166534;
    font-weight: 800;
    font-size: 0.95rem;
}
.recommend-main {
    color: #14532d;
    font-size: 1.9rem;
    font-weight: 900;
    margin-top: 4px;
}
.recommend-sub {
    color: #475569;
    font-size: 0.92rem;
    margin-top: 4px;
    line-height: 1.5;
}

.download-panel {
    border: 1px solid var(--border);
    border-radius: 16px;
    background: #ffffff;
    padding: 14px;
    margin-top: 10px;
}

@media (max-width: 900px) {
    .workflow-wrap { display: block; }
    .workflow-step { margin-bottom: 8px; }
    .workflow-arrow { text-align: center; padding: 2px 0; }
    .home-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
    .result-hero { grid-template-columns: 1fr; }
}
@media (max-width: 520px) {
    .home-grid { grid-template-columns: 1fr; }
    .app-hero-title { font-size: 1.35rem; }
    .result-value { font-size: 1.45rem; }
}
</style>
""", unsafe_allow_html=True)


# 세션 상태 초기화 (데이터 연동용)
if 'rebound_data' not in st.session_state:
    st.session_state['rebound_data'] = []

# 통계·비교 탭에서 사용할 공식별 강도 누적 (지점별 5개 공식 값)
if 'rebound_records' not in st.session_state:
    st.session_state['rebound_records'] = []  # list of dict: {"지점","일본재료","일본건축","과기부","권영웅","KALIS","평균"}

# 단일 반발경도 계산 결과 보관용
# Streamlit은 버튼 클릭 때마다 전체 스크립트를 다시 실행하므로,
# 계산 결과와 통계 추가 대상은 session_state에 저장해야 합니다.
if 'last_rebound_result' not in st.session_state:
    st.session_state['last_rebound_result'] = None

if 'last_rebound_meta' not in st.session_state:
    st.session_state['last_rebound_meta'] = {}

if 'last_rebound_error' not in st.session_state:
    st.session_state['last_rebound_error'] = None

if 'last_added_signature' not in st.session_state:
    st.session_state['last_added_signature'] = None

if 'last_add_message' not in st.session_state:
    st.session_state['last_add_message'] = None

if 'add_point_name' not in st.session_state:
    st.session_state['add_point_name'] = f"P{len(st.session_state['rebound_records']) + 1}"


def _make_rebound_record(point_name, res):
    """통계·비교 탭에 누적할 반발경도 결과 1건 생성"""
    rec = {
        "지점": str(point_name).strip() or f"P{len(st.session_state['rebound_records']) + 1}",
        "평균": round(float(res["Mean_Strength"]), 2),
    }
    for k, v in res.get("Formulas", {}).items():
        rec[k] = round(float(v), 2)
    return rec


def _make_rebound_signature(point_name, res):
    """동일 지점명·동일 계산값의 중복 추가를 막기 위한 서명"""
    formula_sig = tuple(
        (k, round(float(v), 6))
        for k, v in sorted(res.get("Formulas", {}).items())
    )
    return (
        str(point_name).strip(),
        round(float(res.get("Mean_Strength", 0.0)), 6),
        round(float(res.get("R_avg", 0.0)), 6),
        round(float(res.get("R0", 0.0)), 6),
        round(float(res.get("Age_Coeff", 0.0)), 6),
        round(float(res.get("Core_Coeff", 0.0)), 6),
        formula_sig,
    )


def add_current_rebound_to_stats():
    """최근 단일 계산 결과를 통계 분석 목록에 추가하는 버튼 콜백"""
    res = st.session_state.get('last_rebound_result')
    if not res:
        st.session_state['last_add_message'] = ("error", "먼저 [계산 실행]을 눌러 단일 반발경도 결과를 산출하세요.")
        return

    point_name = str(st.session_state.get('add_point_name', '')).strip()
    if not point_name:
        point_name = f"P{len(st.session_state['rebound_records']) + 1}"

    signature = _make_rebound_signature(point_name, res)
    if st.session_state.get('last_added_signature') == signature:
        st.session_state['last_add_message'] = ("warning", f"{point_name}은 이미 통계 분석 목록에 추가된 결과입니다.")
        return

    rec = _make_rebound_record(point_name, res)
    st.session_state['rebound_records'].append(rec)
    st.session_state['rebound_data'].append(rec['평균'])
    st.session_state['last_added_signature'] = signature
    st.session_state['last_add_message'] = ("success", f"{point_name} 추가 완료 (평균 {rec['평균']:.2f} MPa, 5개 공식값 포함)")

    # 다음 입력 기본값을 다음 지점 번호로 갱신
    st.session_state['add_point_name'] = f"P{len(st.session_state['rebound_records']) + 1}"


def is_mobile_client():
    """간단한 UA 기반 모바일/태블릿 판별"""
    try:
        ua = str(st.context.headers.get("user-agent", "")).lower()
    except Exception:
        ua = ""
    mobile_keys = ["android", "iphone", "ipad", "mobile", "tablet"]
    return any(k in ua for k in mobile_keys)


# =========================================================
# 1-2. UI/UX 렌더링 헬퍼
# =========================================================
def _safe_html(value):
    """HTML 렌더링용 문자열 이스케이프"""
    return html.escape(str(value), quote=True)


def render_app_header(project_name):
    st.markdown(
        f"""
        <div class="app-hero">
            <div class="app-hero-title">🏗️ 구조물 안전진단 통합 평가 Pro</div>
            <div class="app-hero-sub">
                프로젝트: <b>{_safe_html(project_name)}</b> · 반발경도 입력, 보정계산, 통계 비교, PDF/Excel 출력까지 한 화면에서 처리합니다.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_workflow_header(active_index=0):
    steps = [
        ("1", "프로젝트", "점검 정보 확인"),
        ("2", "측정값 입력", "Rawdata 확인"),
        ("3", "보정조건", "방향·재령·Ct"),
        ("4", "자동 계산", "강도·공식 산정"),
        ("5", "후속 작업", "통계·보고서"),
    ]
    html_steps = []
    for idx, (num, title, sub) in enumerate(steps):
        cls = "workflow-step active" if idx <= active_index else "workflow-step"
        html_steps.append(f'<div class="{cls}">{num}<br><b>{title}</b><br><small>{sub}</small></div>')
        if idx != len(steps) - 1:
            html_steps.append('<div class="workflow-arrow">→</div>')
    st.markdown(f'<div class="workflow-wrap">{"".join(html_steps)}</div>', unsafe_allow_html=True)


def render_step_heading(title, description=""):
    st.markdown(
        f"""
        <div class="step-title">
            <b>{_safe_html(title)}</b>
            <span>{_safe_html(description)}</span>
        </div>
        """,
        unsafe_allow_html=True,
    )


def get_strength_review(mean_strength, design_fck):
    """설계강도 대비율 기준 참고 검토 등급. 최종 판정은 책임기술자 검토 대상."""
    try:
        mean_strength = float(mean_strength)
        design_fck = float(design_fck)
        ratio = mean_strength / design_fck * 100 if design_fck > 0 else np.nan
    except Exception:
        ratio = np.nan

    if not np.isfinite(ratio):
        return "검토 필요", "#64748B", "설계강도 기준을 확인하세요.", ratio
    if ratio >= 100:
        return "양호", "#16A34A", "설계기준강도 이상으로 추정됩니다.", ratio
    if ratio >= 85:
        return "주의", "#F59E0B", "설계강도에 근접하므로 추가 검토가 권장됩니다.", ratio
    return "검토 필요", "#DC2626", "설계강도 대비 낮은 값으로 정밀 검토가 필요합니다.", ratio


def render_strength_result_card(res, design_fck):
    grade, color, note, ratio = get_strength_review(res.get("Mean_Strength", np.nan), design_fck)
    ratio_text = f"{ratio:.1f}%" if np.isfinite(ratio) else "-"
    st.markdown(
        f"""
        <div class="result-hero" style="border-left-color:{color};">
            <div>
                <div class="result-label">평균 추정 압축강도</div>
                <div class="result-value">{float(res['Mean_Strength']):.2f} MPa</div>
                <div class="result-note">코어 보정계수 Ct 반영 결과</div>
            </div>
            <div>
                <div class="result-label">설계강도 대비율</div>
                <div class="result-value">{ratio_text}</div>
                <div class="result-note">기준 설계강도 {float(design_fck):.1f} MPa</div>
            </div>
            <div>
                <div class="result-label">참고 검토 등급</div>
                <div class="result-grade" style="background:{color};">{_safe_html(grade)}</div>
                <div class="result-note">{_safe_html(note)}</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_formula_recommendation_card(best, worst):
    st.markdown(
        f"""
        <div class="recommend-card">
            <div class="recommend-title">✅ CV 기준 추천 공식</div>
            <div class="recommend-main">{_safe_html(best['공식'])}</div>
            <div class="recommend-sub">
                변동계수 {float(best['변동계수CV(%)']):.2f}% · 평균 {float(best['평균(MPa)']):.2f} MPa · 강도비 {float(best['강도비(%)']):.1f}%<br>
                비교상 가장 큰 산포 공식: {_safe_html(worst['공식'])} (CV {float(worst['변동계수CV(%)']):.2f}%)
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_home_overview(project_name):
    st.subheader("🏠 홈 / 업무 흐름")
    render_workflow_header(active_index=0)
    total_records = len(st.session_state.get("rebound_records", []))
    total_values = len(st.session_state.get("rebound_data", []))
    last_res = st.session_state.get("last_rebound_result")
    last_strength = f"{last_res['Mean_Strength']:.2f} MPa" if last_res else "-"
    last_status = "계산 완료" if last_res else "대기"
    st.markdown(
        f"""
        <div class="home-grid">
            <div class="home-card">
                <div class="home-card-title">프로젝트</div>
                <div class="home-card-value">{_safe_html(project_name)}</div>
                <div class="home-card-sub">사이드바에서 수정 가능</div>
            </div>
            <div class="home-card">
                <div class="home-card-title">최근 계산 상태</div>
                <div class="home-card-value">{last_status}</div>
                <div class="home-card-sub">최근 평균강도: {last_strength}</div>
            </div>
            <div class="home-card">
                <div class="home-card-title">통계 분석 목록</div>
                <div class="home-card-value">{total_records}개</div>
                <div class="home-card-sub">공식별 결과 누적</div>
            </div>
            <div class="home-card">
                <div class="home-card-title">간이 강도 데이터</div>
                <div class="home-card-value">{total_values}개</div>
                <div class="home-card-sub">평균·표준편차·CV 분석</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.info("사용 순서: ① 반발경도 계산 → ② 통계 분석 목록 추가 → ③ 통계·비교에서 공식별 CV 확인 → ④ PDF/Excel 결과 출력")

# =========================================================
# 2. 핵심 로직 및 함수 정의
# =========================================================

# 반발경도 계산 입력 검증 기준
# - UI에서 제한하더라도 엑셀/텍스트/직접 호출을 통해 비정상 값이 들어올 수 있으므로
#   최종 계산 함수에서 한 번 더 검증합니다.
# - 측정점수 정책은 "정확히 20개"와 "20개 이상 허용"을 명시적으로 분리합니다.
ALLOWED_REBOUND_ANGLES = {-90, -45, 0, 45, 90}
REBOUND_READING_MIN = 10.0
REBOUND_READING_MAX = 100.0
REBOUND_FORMULA_OPTIONS = ["일본재료", "일본건축", "과기부", "권영웅", "KALIS"]
REBOUND_FORMULA_NAMES = set(REBOUND_FORMULA_OPTIONS)
REBOUND_FORMULA_RECOMMEND_THRESHOLD = 40.0

REBOUND_POINT_POLICY_EXACT_20 = "exact_20"
REBOUND_POINT_POLICY_MIN_20 = "min_20"
REBOUND_POINT_POLICY_NO_MINIMUM = "no_minimum"  # 내부/테스트용: 지침 검증을 끄는 경우
DEFAULT_REBOUND_POINT_POLICY = REBOUND_POINT_POLICY_EXACT_20
REBOUND_DISCARD_COUNT_LIMIT_20 = 4  # 지침 ③: 버리는 값 4개 이상이면 시험값 군 전체 무효
REBOUND_DISCARD_RATIO_LIMIT = 0.20  # 지침 ③ 비례 적용(20점 기준 4개=20%)

REBOUND_POINT_POLICY_OPTIONS = {
    REBOUND_POINT_POLICY_EXACT_20: {
        "label": "정확히 20개",
        "short_label": "정확히20",
        "description": "1개소당 측정값을 정확히 20개로 제한합니다. 기각값이 4개 이상이면 시험 무효입니다.",
    },
    REBOUND_POINT_POLICY_MIN_20: {
        "label": "20개 이상 허용",
        "short_label": "20개이상",
        "description": "측정값을 20개 이상 허용합니다. 기각 기준은 20개 중 4개에 해당하는 20% 이상으로 판정합니다.",
    },
    REBOUND_POINT_POLICY_NO_MINIMUM: {
        "label": "측정점수 제한 없음",
        "short_label": "제한없음",
        "description": "내부 검증용 정책입니다. 일반 현장 계산에서는 사용하지 않는 것을 권장합니다.",
    },
}

REBOUND_POINT_POLICY_LABEL_TO_KEY = {}
for _policy_key, _policy_meta in REBOUND_POINT_POLICY_OPTIONS.items():
    REBOUND_POINT_POLICY_LABEL_TO_KEY[_policy_key] = _policy_key
    REBOUND_POINT_POLICY_LABEL_TO_KEY[_policy_meta["label"]] = _policy_key
    REBOUND_POINT_POLICY_LABEL_TO_KEY[_policy_meta["short_label"]] = _policy_key

# 사용자가 엑셀에 조금 다른 표현으로 적어도 읽을 수 있도록 별칭을 허용합니다.
REBOUND_POINT_POLICY_LABEL_TO_KEY.update({
    "정확히 20": REBOUND_POINT_POLICY_EXACT_20,
    "정확히20개": REBOUND_POINT_POLICY_EXACT_20,
    "20": REBOUND_POINT_POLICY_EXACT_20,
    "exact": REBOUND_POINT_POLICY_EXACT_20,
    "exact20": REBOUND_POINT_POLICY_EXACT_20,
    "exact_20": REBOUND_POINT_POLICY_EXACT_20,
    "20개 이상": REBOUND_POINT_POLICY_MIN_20,
    "20개이상허용": REBOUND_POINT_POLICY_MIN_20,
    "최소20": REBOUND_POINT_POLICY_MIN_20,
    "min20": REBOUND_POINT_POLICY_MIN_20,
    "min_20": REBOUND_POINT_POLICY_MIN_20,
    "at_least_20": REBOUND_POINT_POLICY_MIN_20,
    "제한 없음": REBOUND_POINT_POLICY_NO_MINIMUM,
    "제한없음": REBOUND_POINT_POLICY_NO_MINIMUM,
    "none": REBOUND_POINT_POLICY_NO_MINIMUM,
    "no_minimum": REBOUND_POINT_POLICY_NO_MINIMUM,
})


def normalize_rebound_point_policy(point_count_policy=None, require_20_points=True):
    """
    측정점수 정책을 내부 key로 정규화합니다.

    기존 코드 호환성:
    - point_count_policy가 None이고 require_20_points=True이면 기본값 "정확히 20개"를 사용합니다.
    - point_count_policy가 None이고 require_20_points=False이면 내부용 "제한 없음"으로 처리합니다.
    """
    if point_count_policy is None:
        return DEFAULT_REBOUND_POINT_POLICY if require_20_points else REBOUND_POINT_POLICY_NO_MINIMUM

    policy_text = str(point_count_policy).strip()
    if not policy_text:
        return DEFAULT_REBOUND_POINT_POLICY if require_20_points else REBOUND_POINT_POLICY_NO_MINIMUM

    policy_key = REBOUND_POINT_POLICY_LABEL_TO_KEY.get(policy_text)
    if policy_key:
        return policy_key

    normalized = policy_text.lower().replace(" ", "").replace("-", "_")
    policy_key = REBOUND_POINT_POLICY_LABEL_TO_KEY.get(normalized)
    if policy_key:
        return policy_key

    allowed = ", ".join(meta["label"] for key, meta in REBOUND_POINT_POLICY_OPTIONS.items()
                        if key != REBOUND_POINT_POLICY_NO_MINIMUM)
    raise ValueError(f"알 수 없는 측정점수 정책입니다: {point_count_policy!r}. 허용값: {allowed}")


def get_rebound_point_policy_label(point_count_policy):
    policy_key = normalize_rebound_point_policy(point_count_policy)
    return REBOUND_POINT_POLICY_OPTIONS[policy_key]["label"]


def get_rebound_point_policy_description(point_count_policy):
    policy_key = normalize_rebound_point_policy(point_count_policy)
    return REBOUND_POINT_POLICY_OPTIONS[policy_key]["description"]


def get_rebound_point_policy_short_label(point_count_policy):
    policy_key = normalize_rebound_point_policy(point_count_policy)
    return REBOUND_POINT_POLICY_OPTIONS[policy_key]["short_label"]


def get_discard_limit_for_policy(point_count, point_count_policy):
    """측정점수 정책별 기각 무효 기준 개수를 반환합니다."""
    n = int(point_count)
    policy_key = normalize_rebound_point_policy(point_count_policy)

    if policy_key == REBOUND_POINT_POLICY_EXACT_20:
        return REBOUND_DISCARD_COUNT_LIMIT_20

    if policy_key in (REBOUND_POINT_POLICY_MIN_20, REBOUND_POINT_POLICY_NO_MINIMUM):
        return max(1, int(math.ceil(n * REBOUND_DISCARD_RATIO_LIMIT)))

    return REBOUND_DISCARD_COUNT_LIMIT_20


def get_recommended_formulas(design_fck):
    """
    설계강도 기준 평균 산정 공식 자동추천.

    - 40MPa 미만: 일반강도 콘크리트로 보고 일본건축/일본재료 적용
    - 40MPa 이상: 고강도 영역까지 고려하여 과기부/권영웅/KALIS 적용
    """
    try:
        fck = float(design_fck)
    except (TypeError, ValueError):
        fck = 24.0

    if not np.isfinite(fck):
        fck = 24.0

    if fck < REBOUND_FORMULA_RECOMMEND_THRESHOLD:
        return ["일본건축", "일본재료"]
    return ["과기부", "권영웅", "KALIS"]


def get_recommended_formula_description(design_fck):
    """UI 표시용 자동추천 설명 문구를 반환합니다."""
    formulas = get_recommended_formulas(design_fck)
    try:
        fck = float(design_fck)
    except (TypeError, ValueError):
        fck = 24.0

    range_label = (
        f"{REBOUND_FORMULA_RECOMMEND_THRESHOLD:g}MPa 미만 일반강도 기준"
        if fck < REBOUND_FORMULA_RECOMMEND_THRESHOLD
        else f"{REBOUND_FORMULA_RECOMMEND_THRESHOLD:g}MPa 이상 고강도 기준"
    )
    return f"{range_label}: {', '.join(formulas)}"

@st.cache_resource
def load_ocr_model():
    import easyocr
    return easyocr.Reader(['en'], gpu=False)


def _normalize_ocr_token(text):
    """OCR 오인식 문자를 숫자 파싱 친화적으로 정규화"""
    text = str(text)

    # 천단위 콤마(예: 1,234)는 제거
    text = re.sub(r'(?<=\d),(?=\d{3}(?:\D|$))', '', text)

    replacements = {
        'O': '0', 'o': '0',
        'I': '1', 'l': '1', '|': '1',
        ',': '.', ';': '.',   # 기존 ';' -> ':' 오타성 치환 수정
    }
    for src, dst in replacements.items():
        text = text.replace(src, dst)
    return text.strip()


def _extract_numeric_candidates(ocr_result):
    """easyocr detail=1 결과에서 숫자 후보를 추출"""
    candidates = []
    for item in ocr_result:
        if len(item) < 3:
            continue
        bbox, raw_text, conf = item
        text = _normalize_ocr_token(str(raw_text))
        nums = re.findall(r'\d+(?:\.\d+)?', text)
        if not nums:
            continue

        ys = [pt[1] for pt in bbox]
        xs = [pt[0] for pt in bbox]
        y_center = float(sum(ys) / len(ys))
        x_center = float(sum(xs) / len(xs))
        h = float(max(ys) - min(ys)) if ys else 0.0

        for num in nums:
            try:
                val = float(num)
                candidates.append({
                    "value": val,
                    "x": x_center,
                    "y": y_center,
                    "h": h,
                    "conf": float(conf),
                })
            except Exception:
                continue
    return candidates


def _cluster_rows(candidates):
    """y 좌표 기반으로 OCR 숫자 후보를 행 단위로 군집화"""
    if not candidates:
        return []

    heights = [c["h"] for c in candidates if c["h"] > 0]
    row_tol = max(10.0, (float(np.median(heights)) * 0.75) if heights else 12.0)

    sorted_by_y = sorted(candidates, key=lambda c: c["y"])
    rows = []
    for c in sorted_by_y:
        if not rows:
            rows.append([c])
            continue

        last_row = rows[-1]
        last_y = float(np.mean([r["y"] for r in last_row]))
        if abs(c["y"] - last_y) <= row_tol:
            last_row.append(c)
        else:
            rows.append([c])

    for row in rows:
        row.sort(key=lambda c: c["x"])
    return rows


def _select_best_20_readings(ocr_result, target_count=20):
    """
    전표형(영수증형) 이미지에서 측정값 영역을 우선 추출하고
    목표 개수(target_count, 기본 20개)에 맞춰 숫자 목록을 반환
    """
    candidates = _extract_numeric_candidates(ocr_result)
    if not candidates:
        return []

    # 반발경도 범위 중심 후보 우선
    plausible = [c for c in candidates if 10 <= c["value"] <= 100]
    work = plausible if plausible else candidates

    rows = _cluster_rows(work)
    if not rows:
        return []

    # 측정치 블록은 하단에 밀집해 나타나는 경우가 많으므로, 하단의 다수 숫자 행 우선
    measurement_rows = [r for r in rows if len(r) >= 3]
    if measurement_rows:
        selected_rows = measurement_rows[-max(4, min(6, len(measurement_rows))):]
    else:
        selected_rows = rows

    ordered_values = [c["value"] for row in selected_rows for c in row]
    ordered_keys = {(c["x"], c["y"], c["value"]) for row in selected_rows for c in row}

    if len(ordered_values) >= target_count:
        return ordered_values[:target_count]

    # 부족하면 나머지 후보를 y/x 순서대로 보충
    remain = [
        c["value"]
        for c in sorted(work, key=lambda c: (c["y"], c["x"]))
        if (c["x"], c["y"], c["value"]) not in ordered_keys
    ]
    merged = []
    for v in ordered_values + remain:
        if len(merged) >= target_count:
            break
        merged.append(v)
    return merged


def _format_readings_for_text(values):
    formatted = []
    for v in values:
        if abs(v - round(v)) < 1e-6:
            formatted.append(str(int(round(v))))
        else:
            formatted.append(f"{v:.1f}")
    return " ".join(formatted)


def _normalize_manual_reading_text(raw_text):
    """
    사람이 직접 입력한 측정값 문자열을 파싱하기 쉽게 정리합니다.

    핵심 원칙:
    - 수동 입력에서 쉼표(,)는 기본적으로 숫자 구분자로 봅니다.
      예: "54,56,55" -> "54 56 55"
    - 소수점은 점(.) 사용을 권장합니다.
      예: "54.5 56.0 55.5"
    - OCR 오인식 보정(O->0, l->1 등)은 여기서 하지 않습니다.
      그런 보정은 _normalize_ocr_token()에서만 처리합니다.
    """
    if raw_text is None:
        return ""

    text = str(raw_text)

    # 유니코드 대시 문자를 일반 하이픈으로 통일합니다.
    text = text.replace("−", "-").replace("–", "-").replace("—", "-")

    # 천 단위 콤마는 제거합니다.
    # 예: "1,234" -> "1234"
    text = re.sub(r'(?<=\d),(?=\d{3}(?:\D|$))', '', text)

    # 숫자 사이 쉼표는 구분자로 처리합니다.
    # 예: "54,56,55" -> "54 56 55"
    text = re.sub(r'(?<=\d),(?=\d)', ' ', text)

    # 세미콜론, 탭, 줄바꿈, 슬래시 등도 구분자로 처리합니다.
    text = re.sub(r'[;\t\r\n/]+', ' ', text)

    # 괄호류는 공백 처리합니다.
    text = re.sub(r'[\[\]\(\)\{\}]', ' ', text)

    return text.strip()


def parse_readings_text(raw_text):
    """
    수동 입력/엑셀 입력/텍스트 입력에서 숫자 목록을 파싱합니다.

    주의:
    - 이 함수는 사람이 입력한 값을 대상으로 합니다.
    - OCR 원문 보정은 _normalize_ocr_token()에서 별도로 처리합니다.
    - 소수점은 '.' 사용을 권장합니다.
    """
    text = _normalize_manual_reading_text(raw_text)
    if not text:
        return []

    # 정수, 소수, .5 형태까지 허용합니다.
    tokens = re.findall(r'[-+]?(?:\d+(?:\.\d*)?|\.\d+)', text)

    vals = []
    for token in tokens:
        try:
            value = float(token)
        except (TypeError, ValueError):
            continue

        if np.isfinite(value):
            vals.append(value)

    return vals


def parse_ocr_readings_text(raw_text):
    """
    OCR 원문에서 숫자 목록을 파싱할 때 사용하는 함수입니다.

    현재 extract_numbers_from_image()는 내부에서 OCR 후보를 숫자로 정리한 뒤
    _format_readings_for_text()로 공백 구분 문자열을 반환하므로,
    일반적인 화면 흐름에서는 parse_readings_text()만으로도 충분합니다.

    다만 향후 OCR 원문을 직접 파싱할 일이 생길 수 있으므로 OCR 전용 함수를 분리해 둡니다.
    """
    if raw_text is None:
        return []

    normalized = _normalize_ocr_token(str(raw_text))
    tokens = re.findall(r'[-+]?(?:\d+(?:\.\d*)?|\.\d+)', normalized)

    vals = []
    for token in tokens:
        try:
            value = float(token)
        except (TypeError, ValueError):
            continue

        if np.isfinite(value):
            vals.append(value)

    return vals


def _safe_num(v, default, cast=float):
    n = pd.to_numeric(v, errors="coerce")
    if pd.isna(n):
        return cast(default)
    return cast(n)


def _float_or_nan(v):
    """표시/저장용 숫자 변환. 변환 실패 또는 NaN/inf는 np.nan으로 반환합니다."""
    try:
        n = float(v)
    except (TypeError, ValueError):
        return np.nan
    return n if np.isfinite(n) else np.nan


def _coerce_finite_float(value, field_name):
    """계산에 쓰는 입력값을 유한한 float로 변환합니다."""
    if isinstance(value, (bool, np.bool_)):
        return False, f"{field_name}은(는) True/False가 아니라 숫자로 입력해야 합니다."

    try:
        number = float(value)
    except (TypeError, ValueError):
        return False, f"{field_name}은(는) 숫자여야 합니다. 입력값: {value!r}"

    if not np.isfinite(number):
        return False, f"{field_name}에 NaN 또는 무한대 값이 포함되어 있습니다."

    return True, number


def validate_rebound_inputs(
    readings,
    angle,
    days,
    design_fck=24.0,
    selected_formulas=None,
    core_coeff=1.0,
):
    """
    반발경도 계산 전 입력값을 검증하고 계산 가능한 형태로 정규화합니다.

    검증 대상:
    - 측정값 리스트 여부, 숫자 여부, NaN/inf 여부
    - 반발경도 허용 범위(기본 10~100)
    - 타격각도 허용값(-90, -45, 0, 45, 90)
    - 재령, 설계강도, Ct가 0보다 큰 유한수인지 여부
    - 공식 선택값이 알려진 공식명인지 여부
    """
    if readings is None:
        return False, "데이터 없음: 측정값 목록이 비어 있습니다."

    if isinstance(readings, str):
        return False, "측정값은 숫자 리스트여야 합니다. 텍스트 입력은 parse_readings_text()로 먼저 변환하세요."

    try:
        raw_readings = list(readings)
    except TypeError:
        return False, "측정값은 반복 가능한 숫자 목록이어야 합니다."

    if len(raw_readings) == 0:
        return False, "데이터 없음: 측정값 목록이 비어 있습니다."

    cleaned_readings = []
    for idx, value in enumerate(raw_readings, start=1):
        ok, number = _coerce_finite_float(value, f"측정값 {idx}번")
        if not ok:
            return False, number

        if not (REBOUND_READING_MIN <= number <= REBOUND_READING_MAX):
            return (
                False,
                f"측정값 {idx}번({number:g})이 허용 범위 "
                f"{REBOUND_READING_MIN:g}~{REBOUND_READING_MAX:g}를 벗어났습니다."
            )

        cleaned_readings.append(number)

    ok, angle_num = _coerce_finite_float(angle, "타격각도")
    if not ok:
        return False, angle_num
    if not float(angle_num).is_integer():
        return False, f"타격각도는 정수 각도여야 합니다. 입력값: {angle_num:g}"
    angle_int = int(angle_num)
    if angle_int not in ALLOWED_REBOUND_ANGLES:
        allowed = ", ".join(f"{a}°" for a in sorted(ALLOWED_REBOUND_ANGLES))
        return False, f"허용되지 않는 타격각도입니다: {angle_int}°. 허용값: {allowed}"

    ok, days_num = _coerce_finite_float(days, "재령")
    if not ok:
        return False, days_num
    if days_num <= 0:
        return False, "재령은 0보다 큰 값이어야 합니다."

    ok, fck_num = _coerce_finite_float(design_fck, "설계강도")
    if not ok:
        return False, fck_num
    if fck_num <= 0:
        return False, "설계강도는 0보다 큰 값이어야 합니다."

    ok, ct_num = _coerce_finite_float(core_coeff, "코어 보정계수(Ct)")
    if not ok:
        return False, ct_num
    if ct_num <= 0:
        return False, "코어 보정계수(Ct)는 0보다 커야 합니다."

    # selected_formulas의 의미를 명확히 분리합니다.
    # - None: 설계강도 기준 자동추천
    # - list/tuple/set 등: 사용자가 직접 선택한 공식 목록
    # - 빈 리스트: 수동선택 모드에서 아무 공식도 고르지 않은 상태로 간주
    if selected_formulas is None:
        normalized_formulas = None
    else:
        if isinstance(selected_formulas, str):
            formulas = [selected_formulas]
        else:
            try:
                formulas = list(selected_formulas)
            except TypeError:
                return False, "평균 산정 공식 선택값은 리스트 형태여야 합니다."

        normalized_formulas = []
        invalid_formulas = []
        for formula in formulas:
            name = str(formula).strip()
            if not name:
                continue
            if name not in REBOUND_FORMULA_NAMES:
                invalid_formulas.append(name)
                continue
            if name not in normalized_formulas:
                normalized_formulas.append(name)

        if invalid_formulas:
            allowed = ", ".join(REBOUND_FORMULA_OPTIONS)
            return False, f"알 수 없는 평균 산정 공식이 포함되어 있습니다: {invalid_formulas}. 허용값: {allowed}"

    return True, {
        "readings": cleaned_readings,
        "angle": angle_int,
        "days": days_num,
        "design_fck": fck_num,
        "core_coeff": ct_num,
        "selected_formulas": normalized_formulas,
    }


def extract_numbers_from_image(image_input, ocr_mode="정밀"):
    """
    OCR 전처리 강화 + 전표형 측정지에서 20개 측정값 자동 추출
    """
    try:
        import cv2

        if isinstance(image_input, Image.Image):
            image = image_input.copy()
        else:
            image = Image.open(image_input)

        # cv2 처리 안정화를 위해 모드 정규화
        if image.mode not in ("RGB", "RGBA", "L"):
            image = image.convert("RGB")

        max_width = 800
        if image.width > max_width:
            ratio = max_width / float(image.width)
            new_height = int((float(image.height) * float(ratio)))
            resample = Image.Resampling.LANCZOS if hasattr(Image, "Resampling") else Image.LANCZOS
            image = image.resize((max_width, new_height), resample)

        image_np = np.array(image)

        # 이미지 채널 수에 맞게 안전 변환
        if image_np.ndim == 2:
            gray = image_np
        elif image_np.shape[2] == 4:
            gray = cv2.cvtColor(image_np, cv2.COLOR_RGBA2GRAY)
        else:
            gray = cv2.cvtColor(image_np, cv2.COLOR_RGB2GRAY)

        blur = cv2.medianBlur(gray, 3)

        # 다양한 조건 대응을 위한 전처리 후보군
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8)).apply(gray)
        th_adapt = cv2.adaptiveThreshold(
            blur, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY, 11, 2
        )
        _, th_otsu = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        _, th_clahe_otsu = cv2.threshold(clahe, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        morph = cv2.morphologyEx(th_adapt, cv2.MORPH_CLOSE, np.ones((2, 2), np.uint8), iterations=1)

        if ocr_mode == "빠른":
            variants = [gray, th_adapt]
        else:
            variants = [gray, th_adapt, th_otsu, th_clahe_otsu, morph]

        reader = load_ocr_model()

        best_values = []
        best_score = -1e9

        for processed in variants:
            result_detail = reader.readtext(
                processed,
                detail=1,
                paragraph=False,
                allowlist='0123456789.:- '
            )
            values = _select_best_20_readings(result_detail, target_count=20)

            # 목표 20개 충족, 값 범위, 평균 confidence를 종합 점수화
            score = len(values) * 5
            if len(values) >= 20:
                score += 100
            in_range = sum(1 for v in values if 10 <= v <= 100)
            score += in_range * 2

            confs = [float(item[2]) for item in result_detail if len(item) >= 3]
            if confs:
                score += float(np.mean(confs)) * 10

            if score > best_score:
                best_score = score
                best_values = values

        # 실패 시 기존 방식처럼 전체 숫자라도 최대한 반환
        if not best_values:
            fallback = reader.readtext(gray, detail=0, allowlist='0123456789. ')
            fallback_nums = []
            for token in fallback:
                nums = re.findall(r'\d+(?:\.\d+)?', _normalize_ocr_token(str(token)))
                for n in nums:
                    try:
                        fallback_nums.append(float(n))
                    except Exception:
                        pass
            best_values = fallback_nums[:20]

        return _format_readings_for_text(best_values)

    except Exception as e:
        logger.exception("OCR 처리 중 오류 발생: %s", e)
        return ""


# ---------------------------------------------------------
# [수정 1] 타격방향 보정(ΔR) : 엑셀(1. 원본) 2차식 그대로
# ---------------------------------------------------------
def get_angle_correction(R_val, angle):
    """
    엑셀(1. 원본) '타격방향 보정(ΔR)'과 동일한 2차식 적용.
    ΔR = a*R^2 + b*R + c
    """
    try:
        angle = int(angle)
        R = float(R_val)
    except (TypeError, ValueError):
        return 0.0

    if angle == 90:     # 상향 수직
        return (-0.0018 * R * R) + (0.2455 * R) - 11.906
    elif angle == 45:   # 상향 경사
        return (-0.0026 * R * R) + (0.2563 * R) - 9.24
    elif angle == -90:  # 하향 수직
        return (-0.0009 * R * R) + (0.0094 * R) + 4.48
    elif angle == -45:  # 하향 경사
        return (-0.0007 * R * R) + (0.0129 * R) + 3.14
    else:               # 0° 수평(또는 그 외)
        return 0.0


def get_age_coefficient(days):
    try:
        days = float(days)
    except (TypeError, ValueError):
        days = 3000.0

    # 엑셀과 동일 테이블(보간)
    age_table = {
        10: 1.55, 20: 1.12, 28: 1.00, 50: 0.87, 100: 0.78, 150: 0.74,
        200: 0.72, 300: 0.70, 500: 0.67, 1000: 0.65, 3000: 0.63
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


# ---------------------------------------------------------
# [수정 2,3,5] 20점 기준 + 마스크 기반 기각 + Ct 반영
# ---------------------------------------------------------
def calculate_strength(
    readings,
    angle,
    days,
    design_fck=24.0,
    selected_formulas=None,
    core_coeff=1.0,          # Ct
    require_20_points=True,  # 기존 호출부 호환용
    point_count_policy=None  # exact_20 / min_20
):
    # 계산 전 최종 방어선: 텍스트/엑셀/UI 어디에서 들어온 값이든 여기서 검증합니다.
    valid_input, validated = validate_rebound_inputs(
        readings=readings,
        angle=angle,
        days=days,
        design_fck=design_fck,
        selected_formulas=selected_formulas,
        core_coeff=core_coeff,
    )
    if not valid_input:
        return False, validated

    rd = validated["readings"]
    angle = validated["angle"]
    days = validated["days"]
    design_fck = validated["design_fck"]
    selected_formulas = validated["selected_formulas"]
    ct = validated["core_coeff"]

    n = len(rd)

    # 측정점수 정책 명확화
    try:
        point_policy = normalize_rebound_point_policy(point_count_policy, require_20_points=require_20_points)
    except ValueError as e:
        return False, str(e)

    point_policy_label = get_rebound_point_policy_label(point_policy)
    point_policy_description = get_rebound_point_policy_description(point_policy)

    if point_policy == REBOUND_POINT_POLICY_EXACT_20 and n != 20:
        return False, (
            f"시험 무효: 측정점수 {n}개 입력됨. "
            "현재 정책은 '정확히 20개'이므로 1개소당 측정값을 정확히 20개로 입력하세요."
        )

    if point_policy == REBOUND_POINT_POLICY_MIN_20 and n < 20:
        return False, (
            f"시험 무효: 측정점수 {n}개 입력됨. "
            "현재 정책은 '20개 이상 허용'이므로 최소 20개 이상 입력해야 합니다."
        )

    if point_policy == REBOUND_POINT_POLICY_NO_MINIMUM and n < 1:
        return False, "시험 무효: 측정값이 없습니다."

    # 1차 평균
    avg1 = float(np.mean(rd))

    # ±20% 기각 (마스크 기반: 중복값 오류 방지)
    low, high = avg1 * 0.8, avg1 * 1.2
    # 경계값(정확히 ±20%)이 부동소수점 오차로 기각되지 않도록 작은 허용오차를 둡니다.
    boundary_tol = 1e-12
    valid_mask = [(low - boundary_tol <= r <= high + boundary_tol) for r in rd]
    valid = [r for r, m in zip(rd, valid_mask) if m]
    excluded = [r for r, m in zip(rd, valid_mask) if not m]

    # 기각 판정 기준
    # - 정확히 20개 정책: 지침 문구 그대로 5개 이상 기각 시 무효
    # - 20개 이상 허용 정책: 20개 중 5개와 같은 25% 이상 기각 시 무효
    discard_ratio = (len(excluded) / n) if n else 1.0
    discard_limit = get_discard_limit_for_policy(n, point_policy)
    if point_policy == REBOUND_POINT_POLICY_EXACT_20:
        discard_rule = f"기각 {REBOUND_DISCARD_COUNT_LIMIT_20}개 이상"
    elif point_policy == REBOUND_POINT_POLICY_MIN_20:
        discard_rule = f"기각률 {REBOUND_DISCARD_RATIO_LIMIT * 100:.0f}% 이상(현재 {discard_limit}개 이상)"
    else:
        discard_rule = f"기각률 {REBOUND_DISCARD_RATIO_LIMIT * 100:.0f}% 이상(현재 {discard_limit}개 이상, 내부용)"

    if len(excluded) >= discard_limit:
        return False, (
            f"시험 무효: 기각 {len(excluded)}개({discard_ratio*100:.1f}%) → 재시험 권장 "
            f"(측정점수 정책: {point_policy_label}, 기각 기준: {discard_rule})"
        )

    if len(valid) == 0:
        return False, "유효 데이터 없음 (±20% 범위 내 값이 없습니다)"

    # 유효 평균
    R_avg = float(np.mean(valid))

    # 타격방향 보정(엑셀 2차식)
    corr = float(get_angle_correction(R_avg, angle))
    # 지침 ⑥: 보정반발경도(R0)는 소수 첫째자리 기준으로 결정하여 강도 추정에 적용
    R0 = round(R_avg + corr, 1)

    # 재령 계수
    age_c = float(get_age_coefficient(days))

    # 강도식 (원값)
    f_jsms = max(0.0, (1.27 * R0 - 18.0) * age_c)                # 일본재료학회
    f_aij = max(0.0, (7.3 * R0 + 100.0) * 0.098 * age_c)         # 일본건축학회
    f_mst = max(0.0, (15.2 * R0 - 112.8) * 0.098 * age_c)        # 과기부(고강도)
    f_kwon = max(0.0, (2.304 * R0 - 38.80) * age_c)              # 권영웅
    f_kalis = max(0.0, (1.3343 * R0 + 8.1977) * age_c)           # KALIS

    all_formulas_raw = {
        "일본재료": f_jsms,
        "일본건축": f_aij,
        "과기부": f_mst,
        "권영웅": f_kwon,
        "KALIS": f_kalis,
    }

    # Ct 반영
    all_formulas = {k: v * ct for k, v in all_formulas_raw.items()}

    # 평균 산정 공식 선택
    # selected_formulas=None이면 자동추천, []이면 수동선택 모드에서 미선택으로 처리합니다.
    recommended_formulas = get_recommended_formulas(design_fck)
    if selected_formulas is None:
        formula_mode = "자동추천"
        applied_formulas = recommended_formulas
    else:
        formula_mode = "수동선택"
        applied_formulas = list(selected_formulas)
        if not applied_formulas:
            return False, "수동 공식 선택 모드에서는 평균 산정에 사용할 공식을 1개 이상 선택하세요."

    target_fs = [all_formulas[k] for k in applied_formulas if k in all_formulas]

    if not target_fs:
        return False, "평균 산정에 사용할 유효한 공식이 없습니다."

    s_mean = float(np.mean(target_fs))

    return True, {
        "N": n,
        "Effective_N": len(valid),
        "R_initial": avg1,
        "R_avg": R_avg,
        "Angle_Corr": corr,
        "R0": R0,
        "Age_Coeff": age_c,
        "Core_Coeff": ct,
        "Design_Fck": design_fck,
        "Angle": angle,
        "Days": days,
        "Point_Count_Policy": point_policy,
        "Point_Count_Policy_Label": point_policy_label,
        "Point_Count_Policy_Description": point_policy_description,
        "Discard": len(excluded),
        "Discard_Ratio": discard_ratio,
        "Discard_Limit": discard_limit,
        "Discard_Rule": discard_rule,
        "Excluded": excluded,
        "Formulas": all_formulas,
        "Formulas_Raw": all_formulas_raw,
        "Recommended_Formulas": recommended_formulas,
        "Selected_Formulas": selected_formulas,
        "Applied_Formulas": applied_formulas,
        "Formula_Mode": formula_mode,
        "Formula_Selection_Mode": "수동 선택" if formula_mode == "수동선택" else "자동추천",
        "Formula_Recommendation_Basis": get_recommended_formula_description(design_fck),
        "Mean_Strength": s_mean
    }


def convert_df(df):
    return df.to_csv(index=False).encode('utf-8-sig')


# ---------------------------------------------------------
# PDF 보고서 생성 (한글 폰트 자동 탐색)
# ---------------------------------------------------------
def _find_korean_font():
    """시스템에 설치된 한글 폰트 경로 자동 탐색"""
    import os
    candidates = [
        "/usr/share/fonts/truetype/nanum/NanumGothic.ttf",
        "/usr/share/fonts/truetype/nanum/NanumBarunGothic.ttf",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
        "/Library/Fonts/AppleGothic.ttf",
        "/System/Library/Fonts/AppleSDGothicNeo.ttc",
        "C:/Windows/Fonts/malgun.ttf",
        "C:/Windows/Fonts/NanumGothic.ttf",
    ]
    for path in candidates:
        if os.path.exists(path):
            return path
    return None


def generate_pdf_report(project_name, report_type, summary_dict, detail_df=None, notes=None):
    """
    정밀안전점검 보고서 부록용 PDF 생성
    - report_type: '반발경도' / '통계'
    - summary_dict: 표 상단 요약 정보 (dict)
    - detail_df: 상세 데이터 (DataFrame, 선택)
    - notes: 추가 비고 (str, 선택)
    """
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib import colors
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import mm
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont
        from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer,
                                          Table, TableStyle, PageBreak)
    except ImportError:
        raise RuntimeError("PDF 생성을 위해 'reportlab' 라이브러리가 필요합니다. (pip install reportlab)")

    from datetime import datetime

    font_path = _find_korean_font()
    font_name = "Helvetica"
    if font_path:
        try:
            pdfmetrics.registerFont(TTFont("KFont", font_path))
            font_name = "KFont"
        except Exception:
            font_name = "Helvetica"

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4,
                             leftMargin=18*mm, rightMargin=18*mm,
                             topMargin=20*mm, bottomMargin=18*mm)

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle('K_Title', parent=styles['Title'],
                                  fontName=font_name, fontSize=16, leading=22,
                                  alignment=1)
    h2 = ParagraphStyle('K_H2', parent=styles['Heading2'],
                         fontName=font_name, fontSize=12, leading=16,
                         spaceBefore=8, spaceAfter=4)
    body = ParagraphStyle('K_Body', parent=styles['Normal'],
                           fontName=font_name, fontSize=9, leading=13)

    story = []
    story.append(Paragraph(f"{project_name}", title_style))
    story.append(Paragraph(f"비파괴검사 결과 보고서 ({report_type})", h2))
    story.append(Paragraph(f"작성일: {datetime.now().strftime('%Y-%m-%d %H:%M')}", body))
    story.append(Spacer(1, 6*mm))

    # 요약 표
    story.append(Paragraph("■ 평가 요약", h2))
    summary_rows = [["항목", "값"]]
    for k, v in summary_dict.items():
        summary_rows.append([str(k), str(v)])
    t = Table(summary_rows, colWidths=[60*mm, 110*mm])
    t.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), font_name),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#1f77b4")),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('GRID', (0, 0), (-1, -1), 0.4, colors.grey),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor("#f5f7fa")]),
    ]))
    story.append(t)
    story.append(Spacer(1, 6*mm))

    # 상세 데이터
    if detail_df is not None and not detail_df.empty:
        story.append(Paragraph("■ 상세 데이터", h2))
        # 컬럼이 너무 많으면 자르고 안내
        max_cols = 8
        df_show = detail_df.iloc[:, :max_cols].copy()
        if len(detail_df.columns) > max_cols:
            story.append(Paragraph(
                f"※ 컬럼이 많아 상위 {max_cols}개만 표시. 전체는 엑셀 파일 참조.", body))
        rows = [list(df_show.columns)]
        for _, r in df_show.iterrows():
            rows.append([("" if pd.isna(x) else str(x)) for x in r.tolist()])
        col_w = (170*mm) / max(1, len(df_show.columns))
        td = Table(rows, colWidths=[col_w]*len(df_show.columns), repeatRows=1)
        td.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), font_name),
            ('FONTSIZE', (0, 0), (-1, -1), 7.5),
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#4D96FF")),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('GRID', (0, 0), (-1, -1), 0.3, colors.grey),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        story.append(td)
        story.append(Spacer(1, 4*mm))

    if notes:
        story.append(Paragraph("■ 비고", h2))
        story.append(Paragraph(str(notes).replace("\n", "<br/>"), body))

    story.append(Spacer(1, 8*mm))
    story.append(Paragraph(
        "※ 본 보고서는 「시설물의 안전 및 유지관리에 관한 특별법」 세부지침에 따른 "
        "비파괴검사 결과를 자동 산정한 것으로, 최종 판정은 책임기술자의 검토를 거쳐야 합니다.",
        body))

    doc.build(story)
    return buffer.getvalue()


def to_excel(df):
    output = io.BytesIO()
    last_err = None

    for engine in ("xlsxwriter", "openpyxl"):
        try:
            output.seek(0)
            output.truncate(0)
            with pd.ExcelWriter(output, engine=engine) as writer:
                df.to_excel(writer, index=False, sheet_name='Result')
            return output.getvalue()
        except ImportError as e:
            last_err = e
            continue

    raise RuntimeError("엑셀 저장 엔진(xlsxwriter/openpyxl)이 설치되어 있지 않습니다.") from last_err


# =========================================================
# 2-1) 검증용 테스트 케이스 (엑셀 값과 동일한 케이스 포함)
# =========================================================
def run_validation_tests():
    """
    테스트 케이스:
    - TC0: 수동/엑셀 입력 파서가 공백, 쉼표, 줄바꿈, 소수 입력을 안전하게 처리하는지 확인
    - TC1: 첨부 엑셀(1. 원본 / 2. 정리)와 수치가 일치하는 대표 케이스(상부구조 S1, 바닥판, 90°, 3000일)
    - TC2: 20점 중 2개 outlier(±20% 밖) -> 기각 2개, 무효 아님
    - TC3: 20점 중 5개 outlier -> 시험 무효 처리 확인
    - TC4: Ct=1.10 적용 시 강도들이 1.10배 되는지 확인
    - TC5: NaN/inf, 허용 범위 밖 측정값, 잘못된 각도/재령/설계강도/Ct/공식명을 차단하는지 확인
    - TC6: 공식 자동추천/수동선택 모드가 의도대로 분리되는지 확인
    """
    results = []

    # ----- TC0: 입력 파서 검증 -----
    parser_cases = [
        ("54 56 55", [54.0, 56.0, 55.0]),
        ("54,56,55", [54.0, 56.0, 55.0]),
        ("54, 56, 55", [54.0, 56.0, 55.0]),
        ("54.5 56.0 55.5", [54.5, 56.0, 55.5]),
        ("54\n56\n55", [54.0, 56.0, 55.0]),
        ("[54, 56, 55]", [54.0, 56.0, 55.0]),
    ]

    parser_details = {}
    parser_pass = True

    for raw, expected in parser_cases:
        actual = parse_readings_text(raw)
        parser_details[raw] = actual
        if actual != expected:
            parser_pass = False

    results.append(("TC0(입력 파서)", parser_pass, parser_details))

    # ----- TC1: 엑셀 일치 케이스 -----
    readings_tc1 = [
        58.4, 57.0, 61.8, 61.2, 60.6,
        58.9, 59.9, 58.9, 58.2, 57.8,
        61.5, 60.1, 64.1, 57.9, 59.3,
        56.8, 57.1, 58.0, 58.4, 58.0
    ]
    ok, res = calculate_strength(
        readings_tc1, angle=90, days=3000,
        design_fck=40.0, selected_formulas=["일본재료", "일본건축", "과기부"],
        core_coeff=1.0, require_20_points=True
    )

    exp_Ravg = 59.195
    exp_dR = -3.680913945
    exp_R0 = 55.5  # 지침 ⑥: R0 소수 첫째자리 반올림(55.514086… → 55.5)
    exp_age = 0.63
    exp_jsms = 33.06555      # (1.27*55.5-18.0)*0.63
    exp_aij = 31.187961      # (7.3*55.5+100)*0.098*0.63
    exp_mst = 45.119592      # (15.2*55.5-112.8)*0.098*0.63

    def close(a, b, tol=1e-6):
        return abs(a - b) <= tol

    tc1_pass = (
        ok and
        close(res["R_avg"], exp_Ravg, 1e-3) and
        close(res["Angle_Corr"], exp_dR, 1e-6) and
        close(res["R0"], exp_R0, 1e-6) and
        close(res["Age_Coeff"], exp_age, 1e-12) and
        close(res["Formulas"]["일본재료"], exp_jsms, 1e-6) and
        close(res["Formulas"]["일본건축"], exp_aij, 1e-6) and
        close(res["Formulas"]["과기부"], exp_mst, 1e-6)
    )
    results.append(("TC1(엑셀 일치)", tc1_pass, res if ok else res))

    # ----- TC2: outlier 2개 -> 기각 2개 -----
    base = [50] * 18 + [10, 90]
    ok2, res2 = calculate_strength(base, angle=0, days=3000, design_fck=24, core_coeff=1.0, require_20_points=True)
    tc2_pass = ok2 and (res2["Discard"] == 2)
    results.append(("TC2(기각 2개, 무효X)", tc2_pass, res2 if ok2 else res2))

    # ----- TC3: outlier 5개 -> 무효 (지침상 4개 이상 기각 시 무효) -----
    base3 = [50] * 15 + [10, 90, 10, 90, 10]
    ok3, res3 = calculate_strength(base3, angle=0, days=3000, design_fck=24, core_coeff=1.0, require_20_points=True)
    tc3_pass = (not ok3) and ("시험 무효" in str(res3))
    results.append(("TC3(기각 5개, 무효)", tc3_pass, res3))

    # ----- TC4: Ct=1.10 배율 확인 -----
    ok4a, res4a = calculate_strength(readings_tc1, angle=90, days=3000, design_fck=40, core_coeff=1.0, require_20_points=True)
    ok4b, res4b = calculate_strength(readings_tc1, angle=90, days=3000, design_fck=40, core_coeff=1.10, require_20_points=True)
    tc4_pass = ok4a and ok4b and close(res4b["Formulas"]["과기부"], res4a["Formulas"]["과기부"] * 1.10, 1e-6)
    results.append(("TC4(Ct 배율)", tc4_pass, {"MST@1.0": res4a["Formulas"]["과기부"], "MST@1.10": res4b["Formulas"]["과기부"]}))

    # ----- TC5: 입력값 검증 -----
    validation_cases = {
        "NaN 측정값 차단": calculate_strength([50] * 19 + [np.nan], angle=0, days=3000, design_fck=24, core_coeff=1.0),
        "inf 측정값 차단": calculate_strength([50] * 19 + [np.inf], angle=0, days=3000, design_fck=24, core_coeff=1.0),
        "허용 범위 밖 측정값 차단": calculate_strength([50] * 19 + [5], angle=0, days=3000, design_fck=24, core_coeff=1.0),
        "잘못된 각도 차단": calculate_strength([50] * 20, angle=30, days=3000, design_fck=24, core_coeff=1.0),
        "재령 0 차단": calculate_strength([50] * 20, angle=0, days=0, design_fck=24, core_coeff=1.0),
        "설계강도 0 차단": calculate_strength([50] * 20, angle=0, days=3000, design_fck=0, core_coeff=1.0),
        "Ct 0 차단": calculate_strength([50] * 20, angle=0, days=3000, design_fck=24, core_coeff=0),
        "알 수 없는 공식 차단": calculate_strength([50] * 20, angle=0, days=3000, design_fck=24, selected_formulas=["없는공식"], core_coeff=1.0),
    }
    tc5_pass = all(not ok for ok, _ in validation_cases.values())
    validation_details = {name: detail for name, (ok, detail) in validation_cases.items()}
    results.append(("TC5(입력값 검증)", tc5_pass, validation_details))


    # ----- TC6: 공식 자동추천/수동선택 분리 검증 -----
    ok6a, res6a = calculate_strength([50] * 20, angle=0, days=3000, design_fck=24, selected_formulas=None, core_coeff=1.0)
    ok6b, res6b = calculate_strength([50] * 20, angle=0, days=3000, design_fck=40, selected_formulas=None, core_coeff=1.0)
    ok6c, res6c = calculate_strength([50] * 20, angle=0, days=3000, design_fck=24, selected_formulas=["KALIS"], core_coeff=1.0)
    ok6d, res6d = calculate_strength([50] * 20, angle=0, days=3000, design_fck=24, selected_formulas=[], core_coeff=1.0)

    tc6_pass = (
        ok6a and res6a.get("Formula_Mode") == "자동추천" and res6a.get("Applied_Formulas") == ["일본건축", "일본재료"] and
        ok6b and res6b.get("Formula_Mode") == "자동추천" and res6b.get("Applied_Formulas") == ["과기부", "권영웅", "KALIS"] and
        ok6c and res6c.get("Formula_Mode") == "수동선택" and res6c.get("Applied_Formulas") == ["KALIS"] and
        (not ok6d) and "1개 이상" in str(res6d)
    )
    results.append(("TC6(공식 선택 UX)", tc6_pass, {
        "24MPa 자동추천": res6a.get("Applied_Formulas") if ok6a else res6a,
        "40MPa 자동추천": res6b.get("Applied_Formulas") if ok6b else res6b,
        "수동선택 KALIS": res6c.get("Applied_Formulas") if ok6c else res6c,
        "수동 미선택": res6d,
    }))

    # ----- TC7: 측정점수 정책 명확화 검증 -----
    ok7a, res7a = calculate_strength([50] * 20, angle=0, days=3000, design_fck=24, core_coeff=1.0,
                                      point_count_policy=REBOUND_POINT_POLICY_EXACT_20)
    ok7b, res7b = calculate_strength([50] * 19, angle=0, days=3000, design_fck=24, core_coeff=1.0,
                                      point_count_policy=REBOUND_POINT_POLICY_EXACT_20)
    ok7c, res7c = calculate_strength([50] * 21, angle=0, days=3000, design_fck=24, core_coeff=1.0,
                                      point_count_policy=REBOUND_POINT_POLICY_EXACT_20)
    ok7d, res7d = calculate_strength([50] * 21, angle=0, days=3000, design_fck=24, core_coeff=1.0,
                                      point_count_policy=REBOUND_POINT_POLICY_MIN_20)
    ok7e, res7e = calculate_strength([50] * 20 + [20] * 4, angle=0, days=3000, design_fck=24, core_coeff=1.0,
                                      point_count_policy=REBOUND_POINT_POLICY_MIN_20)
    ok7f, res7f = calculate_strength([50] * 19 + [20] * 5, angle=0, days=3000, design_fck=24, core_coeff=1.0,
                                      point_count_policy=REBOUND_POINT_POLICY_MIN_20)

    tc7_pass = (
        ok7a and res7a.get("Point_Count_Policy") == REBOUND_POINT_POLICY_EXACT_20 and
        (not ok7b) and "정확히 20개" in str(res7b) and
        (not ok7c) and "정확히 20개" in str(res7c) and
        ok7d and res7d.get("Point_Count_Policy") == REBOUND_POINT_POLICY_MIN_20 and res7d.get("N") == 21 and
        ok7e and res7e.get("Discard") == 4 and res7e.get("Discard_Limit") == 5 and
        (not ok7f) and "기각" in str(res7f)
    )
    results.append(("TC7(측정점수 정책)", tc7_pass, {
        "정확히20_20개": res7a.get("Point_Count_Policy_Label") if ok7a else res7a,
        "정확히20_19개": res7b,
        "정확히20_21개": res7c,
        "20개이상_21개": {"N": res7d.get("N"), "정책": res7d.get("Point_Count_Policy_Label")} if ok7d else res7d,
        "20개이상_24개중4개기각": {"Discard": res7e.get("Discard"), "Discard_Limit": res7e.get("Discard_Limit")} if ok7e else res7e,
        "20개이상_24개중5개기각": res7f,
    }))

    return results


# =========================================================
# 2-2) pytest 자동 테스트 분리용 core 모듈 연동
# =========================================================
# v6부터 반발경도 계산/검증/파서 로직은 structural_safety_core_v6.py에서도
# 동일하게 제공됩니다. 앱 파일만 단독 실행하는 기존 사용성은 유지하되,
# core 모듈이 같은 폴더에 있으면 아래 순수 함수들을 core 버전으로 연결합니다.
# 이렇게 하면 pytest가 검증하는 함수와 앱에서 실제 사용하는 함수가 같아집니다.
try:
    from structural_safety_core_v6 import (  # type: ignore
        ALLOWED_REBOUND_ANGLES,
        REBOUND_READING_MIN,
        REBOUND_READING_MAX,
        REBOUND_FORMULA_OPTIONS,
        REBOUND_FORMULA_NAMES,
        REBOUND_FORMULA_RECOMMEND_THRESHOLD,
        REBOUND_POINT_POLICY_EXACT_20,
        REBOUND_POINT_POLICY_MIN_20,
        REBOUND_POINT_POLICY_NO_MINIMUM,
        DEFAULT_REBOUND_POINT_POLICY,
        REBOUND_DISCARD_COUNT_LIMIT_20,
        REBOUND_DISCARD_RATIO_LIMIT,
        REBOUND_POINT_POLICY_OPTIONS,
        REBOUND_POINT_POLICY_LABEL_TO_KEY,
        normalize_rebound_point_policy,
        get_rebound_point_policy_label,
        get_rebound_point_policy_description,
        get_rebound_point_policy_short_label,
        get_discard_limit_for_policy,
        get_recommended_formulas,
        get_recommended_formula_description,
        _normalize_ocr_token,
        _normalize_manual_reading_text,
        parse_readings_text,
        parse_ocr_readings_text,
        validate_rebound_inputs,
        get_angle_correction,
        get_age_coefficient,
        calculate_strength,
        run_validation_tests,
    )
except ImportError as e:
    logger.warning("structural_safety_core_v6.py를 불러오지 못해 앱 내장 계산 함수를 사용합니다: %s", e)


# =========================================================
# 3. 메인 UI 구성
# =========================================================

with st.sidebar:
    st.header("⚙️ 프로젝트 정보")
    p_name = st.text_input("프로젝트명", "OO시설물 정밀점검")
    st.divider()
    st.caption("시설물안전법 및 세부지침 준수")
    st.caption("※ 현장 사용 흐름에 맞춰 홈·계산·통계 순으로 재배치했습니다.")

render_app_header(p_name)

tab_home, tab2, tab4, tab1 = st.tabs([
    "🏠 홈",
    "🔨 반발경도 계산",
    "📊 통계·비교",
    "📖 매뉴얼",
])

# ---------------------------------------------------------
# [Home] 업무 흐름 및 현황 요약
# ---------------------------------------------------------
with tab_home:
    render_home_overview(p_name)

# ---------------------------------------------------------
# [Tab 1] 점검 매뉴얼 + 검증 테스트
# ---------------------------------------------------------
with tab1:
    st.subheader("💡 프로그램 사용 가이드")
    st.info("""
    **1. 반발경도 산정 시 설계기준강도를 입력해주세요.**
    * 설계기준강도 기준으로 평균 산정 공식이 자동추천됩니다.
    * 필요 시 [공식 직접 선택] 모드로 책임기술자가 평균 산정 공식을 수동 지정할 수 있습니다.

    **2. 타격방향 보정 값을 매뉴얼을 참고해서 상향 타격인지 하향타격인지를 구분해서 선택해주세요.**

    **3. 재령 등 별도로 적용하지 않을 시 프로그램상에서 재령 3000일, 설계기준강도 24MPa가 적용됩니다.**

    **4. 코어 보정계수(Ct)가 있으면 입력하세요.**
    * 최종 강도 = Ct × 비파괴(반발경도) 강도

    **5. 측정점수 정책을 확인하세요.**
    * 기본값은 [정확히 20개]입니다. 1개소당 20개 측정값만 사용하는 보수적인 방식입니다.
    * 추가 측정값까지 반영해야 하는 경우 [20개 이상 허용]을 선택할 수 있으며, 이때 기각 기준은 20% 이상으로 적용됩니다.

    **6. 통계ㆍ비교 탭 활용 안내**
    * 반발경도 단일평가 후 [통계 분석 목록에 추가] 버튼을 누르면 5개 공식별 결과가 모두 누적됩니다.
    * 누적된 지점들 간 변동계수(CV)가 가장 낮은 공식을 자동 추천합니다 — 해당 시설물에 가장 안정적인 산정식입니다.

    **7. PDF 보고서 출력**
    * 반발경도 및 통계 결과 하단의 [PDF 다운로드] 버튼으로 정밀안전점검 보고서 부록용 PDF를 받을 수 있습니다.
    """)

    st.divider()
    st.subheader("📋 시설물 안전점검·진단 세부지침 매뉴얼")

    with st.expander("1. 반발경도 시험 (Rebound Hardness Test) 상세 지침", expanded=False):
        st.markdown("""
        #### **✅ 개요 및 원리**
        * 콘크리트 표면을 슈미트 해머로 타격하여 반발되는 거리($R$)를 측정하고, 이와 압축강도 사이의 상관관계를 통해 비파괴 강도를 추정합니다.

        #### **✅ 측정 및 기각 룰**
        1. **타격 점수**: 1개소당 **20점 이상** 측정을 원칙으로 하되, 프로그램에서는 정책을 명확히 분리합니다.
           - **정확히 20개**: 20개가 아니면 계산하지 않으며, 기각값이 **4개 이상**이면 시험 무효입니다.
           - **20개 이상 허용**: 20개 초과 입력을 허용하며, 기각값이 **전체의 20% 이상**이면 시험 무효입니다.
        2. **이상치 기각**: 전체 측정값의 산술평균을 낸 후, 평균값에서 **±20%를 벗어나는 데이터는 무효**
        3. **시험 무효**: 선택한 측정점수 정책의 기각 기준을 초과하면 재시험 권장
        """)
        m_df = pd.DataFrame({
            "구분": ["상향 수직 (+90°)", "상향 경사 (+45°)", "수평 타격 (0°)", "하향 경사 (-45°)", "하향 수직 (-90°)"],
            "대상 부재 예시": ["슬래브 하부 (천장)", "보 경사면", "벽체, 기둥 측면", "교대/교각 경사부", "슬래브 상면 (바닥)"]
        })
        st.table(m_df)
        st.info("※ 본 프로그램은 각도 선택 시 엑셀(1. 원본) 보정식(2차식)을 그대로 적용하여 $R_0$를 산정합니다.")

    with st.expander("🧪 검증용 테스트 케이스 실행(개발/검증)", expanded=False):
        st.caption("앱 내부 버튼으로 TC0~TC7을 확인할 수 있고, v6부터는 같은 검증을 pytest 명령어로도 자동 실행할 수 있습니다.")
        if st.button("테스트 실행", type="primary"):
            test_results = run_validation_tests()
            for name, passed, detail in test_results:
                if passed:
                    st.success(f"{name}: PASS")
                else:
                    st.error(f"{name}: FAIL")
                st.code(str(detail))

# ---------------------------------------------------------
# [Tab 2] 반발경도 평가
# ---------------------------------------------------------
with tab2:
    st.subheader("🔨 반발경도 정밀 강도 산정")
    render_workflow_header(active_index=1)

    mobile_client = is_mobile_client()
    if mobile_client:
        st.caption("📱 모바일/태블릿 최적화 모드")

    mode = st.radio("입력 방식", ["단일 지점 (카메라/파일)", "다중 지점 (엑셀 업로드)"], horizontal=True)

    if mode.startswith("단일"):
        with st.container(border=True):
            render_step_heading("1️⃣ 측정값 입력", "사진/OCR, 직접 입력, 표 편집을 통해 1개소 반발경도 Rawdata를 확인합니다.")

            ocr_mode = st.radio(
                "OCR 처리 모드",
                ["빠른", "정밀"],
                horizontal=not mobile_client,
                index=1,
                help="빠른: 처리속도 우선 / 정밀: 인식률 우선"
            )

            cam_mode = st.toggle("💻 웹캠(PC) 모드로 전환하기", value=False)

            img_file = None
            rot_val = 0

            if not cam_mode:
                st.caption("📱 모바일: '사진 촬영' 선택 시 **후면 카메라(고화질/자동초점)**가 실행됩니다.")
                img_file = st.file_uploader("촬영 버튼 또는 갤러리 선택", type=['png', 'jpg', 'jpeg', 'bmp'])
            else:
                st.caption("💡 PC/노트북 웹캠을 사용할 때 적합합니다.")
                img_file = st.camera_input("측정 기록표를 촬영하세요")

            if img_file:
                st.caption("이미지가 회전되어 보이면 아래에서 회전값을 조정하세요. 회전값이 바뀌면 OCR을 다시 실행합니다.")
                rot_val = st.radio("이미지 회전(반시계)", [0, 90, 180, 270], index=0, horizontal=True, key="img_rot")

            if img_file is not None:
                # -------------------------------------------------
                # OCR 재실행 방지
                # -------------------------------------------------
                # Streamlit은 위젯 값이 바뀔 때마다 전체 스크립트를 다시 실행합니다.
                # 이미지가 그대로인데 재령/설계강도/Ct/공식 선택만 바뀌어도
                # OCR이 반복 실행되지 않도록 이미지 조합별 처리 여부를 저장합니다.

                file_bytes = None
                file_hash = ""
                file_size = getattr(img_file, "size", 0)

                try:
                    # name + size만으로는 같은 이름/같은 크기의 다른 이미지를 구분하기 어렵습니다.
                    # 짧은 내용 해시를 signature에 포함해 stale OCR 결과 사용 위험을 줄입니다.
                    file_bytes = img_file.getvalue()
                    file_size = len(file_bytes)
                    file_hash = hashlib.blake2b(file_bytes, digest_size=8).hexdigest()
                except Exception:
                    file_hash = ""

                try:
                    upload_sig = (
                        getattr(img_file, "name", ""),
                        file_size,
                        file_hash,
                        rot_val,
                        ocr_mode,
                        cam_mode,
                    )
                except Exception:
                    upload_sig = (
                        str(img_file),
                        file_hash,
                        rot_val,
                        ocr_mode,
                        cam_mode,
                    )

                sig_changed = st.session_state.get("ocr_upload_sig") != upload_sig

                # 이미지/회전/OCR 모드가 바뀐 경우 기존 OCR 상태를 초기화합니다.
                if sig_changed:
                    st.session_state["ocr_upload_sig"] = upload_sig
                    st.session_state.pop("ocr_result", None)
                    st.session_state.pop("ocr_error", None)
                    st.session_state.pop("ocr_processed_sig", None)

                rerun_ocr = st.button(
                    "🔁 OCR 다시 실행",
                    key="btn_rerun_ocr",
                    use_container_width=True,
                    help="이미지, 회전값, OCR 모드는 그대로 두고 숫자 인식만 다시 실행합니다."
                )

                # 이 이미지 조합에 대해 아직 OCR을 실행하지 않았거나,
                # 사용자가 수동 재실행 버튼을 누른 경우에만 OCR을 실행합니다.
                should_run_ocr = (
                    rerun_ocr
                    or st.session_state.get("ocr_processed_sig") != upload_sig
                )

                if should_run_ocr:
                    # 성공/실패 여부와 관계없이 '이 이미지 조합은 OCR 시도 완료'로 기록합니다.
                    # 그래야 OCR 실패 이미지도 Streamlit 재실행 때마다 반복 처리되지 않습니다.
                    st.session_state["ocr_processed_sig"] = upload_sig

                    with st.spinner("이미지 처리 및 숫자 인식 중..."):
                        recognized_text = ""

                        try:
                            if file_bytes is not None:
                                image_source = io.BytesIO(file_bytes)
                            else:
                                try:
                                    img_file.seek(0)
                                except Exception:
                                    pass
                                image_source = img_file

                            pil_image = Image.open(image_source)

                            if rot_val != 0:
                                pil_image = pil_image.rotate(rot_val, expand=True)

                            recognized_text = extract_numbers_from_image(
                                pil_image,
                                ocr_mode=ocr_mode
                            )

                        except Exception as e:
                            logger.exception("OCR 실행 중 오류 발생: %s", e)
                            recognized_text = ""
                            st.session_state["ocr_error"] = (
                                "OCR 처리 중 오류가 발생했습니다. "
                                "이미지를 다시 업로드하거나 직접 입력해주세요."
                            )

                        if recognized_text:
                            st.session_state["ocr_result"] = recognized_text
                            st.session_state.pop("ocr_error", None)
                        else:
                            st.session_state.pop("ocr_result", None)
                            if "ocr_error" not in st.session_state:
                                st.session_state["ocr_error"] = (
                                    "숫자를 인식하지 못했습니다. 직접 입력해주세요."
                                )

                # -------------------------------------------------
                # OCR 결과 표시
                # -------------------------------------------------
                # OCR을 방금 실행했든, 이전 결과를 재사용하든,
                # 화면 표시는 이곳에서 한 번만 처리합니다.
                recognized_text = st.session_state.get("ocr_result", "")

                if recognized_text:
                    ocr_vals = parse_readings_text(recognized_text)

                    if should_run_ocr:
                        st.success(f"인식 성공 ({len(ocr_vals)}개): {recognized_text}")
                    else:
                        st.info(f"저장된 OCR 결과 사용 중 ({len(ocr_vals)}개): {recognized_text}")

                    if len(ocr_vals) != 20:
                        st.warning("자동 인식값이 20개가 아닙니다. 아래 입력창에서 확인/수정 후 계산하세요.")

                elif st.session_state.get("ocr_error"):
                    st.warning(st.session_state["ocr_error"])

            render_step_heading("2️⃣ 보정조건 설정", "타격방향, 재령, 설계강도, 코어 보정계수(Ct), 평균 산정 공식을 지정합니다.")

            # ---- 입력 파라미터: 모바일은 단일 컬럼, 데스크톱은 4열 ----
            if mobile_client:
                angle = st.selectbox(
                    "타격 방향",
                    [90, 45, 0, -45, -90],
                    format_func=lambda x: {90: "+90°(상향수직)", 45: "+45°(상향경사)", 0: "0°(수평)", -45: "-45°(하향경사)", -90: "-90°(하향수직)"}[x]
                )
                days = st.number_input("재령(일)", 10, 10000, 3000,
                                      help="공용연수(년) × 365 + 양생기간. 미입력 시 3000일(약 8년) 적용")
                fck = st.number_input("설계강도(MPa)", 15.0, 100.0, 24.0)
                ct = st.number_input("코어 보정계수 Ct", 0.10, 2.00, 1.00, step=0.01)
            else:
                c1, c2, c3, c4 = st.columns(4)
                with c1:
                    angle = st.selectbox(
                        "타격 방향",
                        [90, 45, 0, -45, -90],
                        format_func=lambda x: {90: "+90°(상향수직)", 45: "+45°(상향경사)", 0: "0°(수평)", -45: "-45°(하향경사)", -90: "-90°(하향수직)"}[x]
                    )
                with c2:
                    days = st.number_input("재령(일)", 10, 10000, 3000,
                                          help="공용연수(년) × 365 + 양생기간. 미입력 시 3000일(약 8년) 적용")
                with c3:
                    fck = st.number_input("설계강도(MPa)", 15.0, 100.0, 24.0)
                with c4:
                    ct = st.number_input("코어 보정계수 Ct", 0.10, 2.00, 1.00, step=0.01)

            # 측정점수 정책 선택
            point_policy_labels = [
                REBOUND_POINT_POLICY_OPTIONS[REBOUND_POINT_POLICY_EXACT_20]["label"],
                REBOUND_POINT_POLICY_OPTIONS[REBOUND_POINT_POLICY_MIN_20]["label"],
            ]
            point_policy_label = st.radio(
                "측정점수 정책",
                point_policy_labels,
                index=0,
                horizontal=not mobile_client,
                help=(
                    "기본값은 정확히 20개입니다. 추가 측정값을 평균 산정에 포함해야 하는 경우에만 "
                    "20개 이상 허용을 선택하세요."
                )
            )
            point_count_policy = normalize_rebound_point_policy(point_policy_label)
            st.info(f"측정점수 정책: {get_rebound_point_policy_description(point_count_policy)}")

            # 공식 선택 옵션
            formula_opts = REBOUND_FORMULA_OPTIONS
            recommended_methods = get_recommended_formulas(fck)
            formula_mode_label = st.radio(
                "평균 산정 공식 선택 방식",
                ["설계강도 기준 자동추천", "공식 직접 선택"],
                horizontal=not mobile_client,
                help=(
                    "자동추천은 설계강도 기준으로 평균 산정 공식을 자동 적용합니다. "
                    "직접 선택은 책임기술자 판단으로 평균 산정에 사용할 공식을 지정할 때 사용합니다."
                )
            )

            if formula_mode_label == "설계강도 기준 자동추천":
                selected_methods = None
                st.info(f"자동추천 적용 공식: {get_recommended_formula_description(fck)}")
            else:
                selected_methods = st.multiselect(
                    "평균 산정 적용 공식",
                    formula_opts,
                    default=[],
                    help="직접 선택 모드에서는 1개 이상의 공식을 선택해야 계산할 수 있습니다."
                )
                if selected_methods:
                    st.info(f"수동 선택 적용 공식: {', '.join(selected_methods)}")
                else:
                    st.warning("직접 선택 모드에서는 평균 산정에 사용할 공식을 1개 이상 선택하세요.")

            default_txt = "54 56 55 53 58 55 54 55 52 57 55 56 54 55 59 42 55 56 54 55"
            if 'ocr_result' in st.session_state:
                default_txt = st.session_state['ocr_result']

            render_step_heading("3️⃣ 측정값 확인·편집", "인식 또는 입력된 측정값을 표에서 최종 확인한 뒤 계산을 실행합니다.")

            txt = st.text_area(
                "측정값 입력/수정",
                value=default_txt,
                height=120 if mobile_client else 80,
                help="여러 값은 공백, 줄바꿈, 쉼표로 구분할 수 있습니다. 소수점은 58.4처럼 점(.)을 사용하세요."
            )

            # OCR/텍스트 결과를 표 편집 UI로 제공합니다.
            # - 정확히 20개 정책: 20칸 고정
            # - 20개 이상 허용 정책: 입력된 값 개수만큼 행을 표시하고, 20개보다 적으면 20칸 표시
            preview_vals = parse_readings_text(txt)
            if point_count_policy == REBOUND_POINT_POLICY_EXACT_20:
                grid_row_count = 20
                grid_num_rows = "fixed"
                if len(preview_vals) > 20:
                    st.warning("정확히 20개 정책에서는 입력값이 20개를 초과하면 첫 20개만 편집표에 반영됩니다. 추가값까지 쓰려면 [20개 이상 허용]을 선택하세요.")
            else:
                grid_row_count = max(20, len(preview_vals))
                grid_num_rows = "dynamic"

            base_vals = (preview_vals + [np.nan] * grid_row_count)[:grid_row_count]
            grid_df = pd.DataFrame({
                "No": list(range(1, grid_row_count + 1)),
                "측정값": base_vals
            })
            grid_key = f"ocr_grid_{point_count_policy}_{grid_row_count}_{abs(hash(txt)) % (10**8)}"
            edited_grid = st.data_editor(
                grid_df,
                column_config={
                    "No": st.column_config.NumberColumn("No", disabled=True),
                    "측정값": st.column_config.NumberColumn("측정값", min_value=REBOUND_READING_MIN, max_value=REBOUND_READING_MAX, step=0.1),
                },
                hide_index=True,
                use_container_width=True,
                num_rows=grid_num_rows,
                key=grid_key
            )

            valid_grid_vals = [float(v) for v in edited_grid["측정값"].tolist() if not pd.isna(v)]
            input_count = len(valid_grid_vals)
            if point_count_policy == REBOUND_POINT_POLICY_EXACT_20:
                if input_count == 20:
                    st.success("측정값 20개가 입력되었습니다. 정확히 20개 정책 조건을 만족합니다.")
                else:
                    st.warning(f"현재 측정값 {input_count}개입니다. 정확히 20개 정책에서는 20개가 필요합니다.")
            else:
                if input_count >= 20:
                    discard_limit_preview = get_discard_limit_for_policy(input_count, point_count_policy)
                    st.success(f"측정값 {input_count}개가 입력되었습니다. 20개 이상 허용 정책 조건을 만족합니다. 현재 기각 무효 기준은 {discard_limit_preview}개 이상입니다.")
                else:
                    st.warning(f"현재 측정값 {input_count}개입니다. 20개 이상 허용 정책에서도 최소 20개가 필요합니다.")

            if valid_grid_vals:
                txt = " ".join([str(int(v)) if abs(v - round(v)) < 1e-6 else f"{v:.1f}" for v in valid_grid_vals])

        render_step_heading("4️⃣ 계산 실행 및 결과 확인", "입력값이 확정되면 자동 이상치 기각, 방향·재령·Ct 보정, 공식별 강도 산정을 수행합니다.")
        if st.button("🚀 계산 실행", type="primary", use_container_width=True):
            rd = parse_readings_text(txt)
            ok, res = calculate_strength(
                rd, angle, days,
                design_fck=fck,
                selected_formulas=selected_methods,
                core_coeff=ct,
                require_20_points=True,
                point_count_policy=point_count_policy
            )
            if ok:
                st.session_state['last_rebound_result'] = res
                st.session_state['last_rebound_meta'] = {
                    "project_name": p_name,
                    "angle": angle,
                    "days": days,
                    "fck": fck,
                    "ct": ct,
                    "formula_mode": res.get("Formula_Mode", "자동추천"),
                    "selected_methods": list(selected_methods) if selected_methods else [],
                    "applied_methods": list(res.get("Applied_Formulas", [])),
                    "recommended_methods": list(res.get("Recommended_Formulas", get_recommended_formulas(fck))),
                    "point_count_policy": res.get("Point_Count_Policy", point_count_policy),
                    "point_count_policy_label": res.get("Point_Count_Policy_Label", get_rebound_point_policy_label(point_count_policy)),
                    "discard_rule": res.get("Discard_Rule", ""),
                    "raw_text": txt,
                    "readings": rd,
                }
                st.session_state['last_rebound_error'] = None
                # 새 계산 결과는 다시 통계 목록에 추가할 수 있도록 중복 방지 서명을 초기화
                st.session_state['last_added_signature'] = None
                st.session_state['last_add_message'] = None
                st.session_state['add_point_name'] = f"P{len(st.session_state['rebound_records']) + 1}"
            else:
                st.session_state['last_rebound_result'] = None
                st.session_state['last_rebound_meta'] = {}
                st.session_state['last_rebound_error'] = res
                st.session_state['last_add_message'] = None

        # ---------------------------------------------------------
        # 최근 단일 계산 결과 표시 + 통계 분석 목록 추가
        # 중요: 이 블록은 [계산 실행] 버튼 if문 밖에 있어야 합니다.
        # 버튼 클릭 시 Streamlit이 전체 스크립트를 재실행하므로,
        # 결과를 session_state에서 다시 불러와야 [통계 분석 목록에 추가]가 정상 동작합니다.
        # ---------------------------------------------------------
        if st.session_state.get('last_rebound_error'):
            st.error(st.session_state['last_rebound_error'])

        res = st.session_state.get('last_rebound_result')
        meta = st.session_state.get('last_rebound_meta', {}) or {}

        if res is not None:
            result_fck = float(meta.get("fck", fck))
            result_angle = meta.get("angle", angle)
            result_days = meta.get("days", days)
            result_formula_mode = meta.get("formula_mode", res.get("Formula_Mode", "자동추천"))
            result_methods = meta.get("applied_methods", res.get("Applied_Formulas", []))
            if not result_methods:
                result_methods = get_recommended_formulas(result_fck)
            result_point_policy_label = meta.get(
                "point_count_policy_label",
                res.get("Point_Count_Policy_Label", get_rebound_point_policy_label(DEFAULT_REBOUND_POINT_POLICY))
            )
            result_discard_rule = meta.get("discard_rule", res.get("Discard_Rule", ""))

            render_strength_result_card(res, result_fck)
            st.caption(f"측정점수 정책: {result_point_policy_label} / 기각 기준: {result_discard_rule}")
            st.caption(f"평균 산정 방식: {result_formula_mode} / 적용 공식: {', '.join(result_methods)}")
            st.caption("※ 아래 결과는 마지막으로 [계산 실행]을 누른 시점의 입력값 기준입니다. 입력값을 변경한 경우 다시 계산하세요.")

            with st.expander("🔍 계산 상세값 보기", expanded=False):
                r1, r2, r3 = st.columns(3)
                r1.metric("유효 평균 R", f"{res['R_avg']:.3f}")
                r2.metric("각도 보정 ΔR(엑셀식)", f"{res['Angle_Corr']:+.6f}")
                r3.metric("측정/유효/기각", f"{res['N']} / {res.get('Effective_N', res['N'] - res['Discard'])} / {res['Discard']}")

                r4, r5, r6 = st.columns(3)
                r4.metric("최종 R₀", f"{res['R0']:.1f}")
                r5.metric("재령 계수 α", f"{res['Age_Coeff']:.2f}")
                r6.metric("Ct", f"{res['Core_Coeff']:.2f}")

            render_step_heading("5️⃣ 후속 작업", "계산 결과를 통계 분석 목록에 추가하거나 PDF 보고서로 출력합니다.")

            # 데이터 연동 버튼: 계산 버튼 밖에서 항상 렌더링
            add_col1, add_col2 = st.columns(2)
            with add_col1:
                st.text_input(
                    "지점명",
                    key="add_point_name"
                )
            with add_col2:
                st.button(
                    "➕ 통계 분석 목록에 추가",
                    key="add_to_stats",
                    use_container_width=True,
                    on_click=add_current_rebound_to_stats
                )

            # 추가 결과 메시지 표시
            add_msg = st.session_state.get('last_add_message')
            if add_msg:
                msg_type, msg_text = add_msg
                if msg_type == "success":
                    st.success(msg_text)
                elif msg_type == "warning":
                    st.warning(msg_text)
                elif msg_type == "error":
                    st.error(msg_text)
                else:
                    st.info(msg_text)

            st.caption(f"현재 통계 분석 목록: {len(st.session_state['rebound_records'])}개 지점")

            st.markdown("### 📊 공식별 추정강도 비교")
            df_f = pd.DataFrame({"공식": list(res["Formulas"].keys()), "강도": list(res["Formulas"].values())})
            chart = alt.Chart(df_f).mark_bar().encode(
                x=alt.X('공식', sort=None),
                y='강도',
                color=alt.condition(alt.datum.강도 >= result_fck, alt.value('#4D96FF'), alt.value('#FF6B6B'))
            ).properties(height=350)

            rule_chart = alt.Chart(pd.DataFrame({'y': [result_fck]})).mark_rule(color='red', strokeDash=[5, 3], size=2).encode(y='y')
            st.altair_chart(chart + rule_chart, use_container_width=True)

            # ----- PDF 보고서 다운로드 -----
            with st.expander("📄 PDF 보고서 다운로드 (정밀안전점검 부록용)", expanded=False):
                summary = {
                    "프로젝트명": meta.get("project_name", p_name),
                    "타격 방향": f"{result_angle}°",
                    "재령(일)": int(result_days),
                    "설계강도(MPa)": f"{result_fck:.1f}",
                    "측정점수 정책": result_point_policy_label,
                    "기각 판정 기준": result_discard_rule,
                    "측정점수 / 유효점수 / 기각수": f"{res['N']} / {res.get('Effective_N', res['N'] - res['Discard'])} / {res['Discard']}",
                    "유효 평균 R": f"{res['R_avg']:.3f}",
                    "타격방향 보정 ΔR": f"{res['Angle_Corr']:+.4f}",
                    "보정 R₀": f"{res['R0']:.1f}",
                    "재령계수 α": f"{res['Age_Coeff']:.3f}",
                    "코어 보정계수 Ct": f"{res['Core_Coeff']:.2f}",
                    "평균 산정 방식": result_formula_mode,
                    "적용 공식": ", ".join(result_methods),
                    "평균 추정 압축강도": f"{res['Mean_Strength']:.2f} MPa",
                    "강도비(설계 대비)": f"{(res['Mean_Strength']/result_fck*100):.1f} %" if result_fck else "-",
                }
                detail_pdf = pd.DataFrame({
                    "공식": list(res["Formulas"].keys()),
                    "강도(MPa)": [f"{v:.2f}" for v in res["Formulas"].values()],
                    "강도비(%)": [f"{(v/result_fck*100):.1f}" if result_fck else "-" for v in res["Formulas"].values()],
                })
                try:
                    pdf_bytes = generate_pdf_report(
                        project_name=p_name,
                        report_type="반발경도",
                        summary_dict=summary,
                        detail_df=detail_pdf,
                        notes=f"공식 선택 방식: {result_formula_mode}\n"
                              f"추천 기준: {get_recommended_formula_description(result_fck)}\n"
                              f"적용 공식: {', '.join(result_methods) if result_methods else '-'}\n"
                              f"기각 데이터: {res['Excluded']}"
                    )
                    st.download_button(
                        "📥 PDF 다운로드",
                        data=pdf_bytes,
                        file_name=f"{p_name}_반발경도_보고서.pdf",
                        mime="application/pdf",
                        use_container_width=True
                    )
                except RuntimeError as e:
                    st.warning(str(e))

    else:
        # ---------------------------------------------------------
        # [수정 4] 배치(엑셀) 템플릿 + 파싱 + 계산에 Ct 반영
        # ---------------------------------------------------------
        st.info("💡 엑셀 업로드 시 아래 양식을 다운로드하여 작성해주세요. (Ct 및 측정정책 컬럼 포함)")

        template_df = pd.DataFrame({
            "지점": ["S1-Deck", "S2-Deck"],
            "각도": [90, -90],
            "재령": [3000, 3000],
            "설계": [40, 40],
            "Ct": [1.00, 1.00],
            "측정정책": ["정확히20", "정확히20"],
            "데이터": [
                "58.4 57 61.8 61.2 60.6 58.9 59.9 58.9 58.2 57.8 61.5 60.1 64.1 57.9 59.3 56.8 57.1 58 58.4 58.0",
                "32 33 35 34 32 33 35 34 32 33 35 34 32 33 35 34 32 33 35 34"
            ]
        })

        try:
            template_excel = to_excel(template_df)
            st.download_button(
                label="📥 입력 양식(엑셀) 다운로드",
                data=template_excel,
                file_name='반발경도_입력양식_측정정책_Ct포함.xlsx',
                mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            )
        except RuntimeError as e:
            st.error(str(e))

        uploaded_file = st.file_uploader("작성된 파일 업로드", type=["csv", "xlsx"])
        init_data = []

        if uploaded_file:
            try:
                if uploaded_file.name.endswith('.csv'):
                    df_up = pd.read_csv(uploaded_file)
                else:
                    df_up = pd.read_excel(uploaded_file)

                for idx, row in df_up.iterrows():
                    try:
                        init_data.append({
                            "선택": True,
                            "지점": row.get("지점", f"P{idx+1}"),
                            "각도": _safe_num(row.get("각도", 0), 0, int),
                            "재령": _safe_num(row.get("재령", 3000), 3000, int),
                            "설계": _safe_num(row.get("설계", 24.0), 24.0, float),
                            "Ct": _safe_num(row.get("Ct", 1.0), 1.0, float),
                            "측정정책": str(row.get("측정정책", "정확히20")),
                            "데이터": str(row.get("데이터", ""))
                        })
                    except Exception as row_err:
                        logger.warning("업로드 %s행 파싱 실패: %s", idx + 1, row_err)

            except ImportError:
                st.error("엑셀 파일을 읽으려면 'openpyxl' 라이브러리가 필요합니다.")
            except Exception as e:
                st.error(f"파일 파싱 실패: {e}")

        df_batch = pd.DataFrame(init_data) if init_data else pd.DataFrame(columns=["선택", "지점", "각도", "재령", "설계", "Ct", "측정정책", "데이터"])
        edited_df = st.data_editor(
            df_batch,
            column_config={
                "선택": st.column_config.CheckboxColumn("선택", default=True),
                "각도": st.column_config.SelectboxColumn("각도", options=[90, 45, 0, -45, -90], required=True),
                "재령": st.column_config.NumberColumn("재령", min_value=1, max_value=100000, default=3000),
                "설계": st.column_config.NumberColumn("설계", min_value=0.1, max_value=200.0, default=24.0),
                "Ct": st.column_config.NumberColumn("Ct", min_value=0.01, max_value=5.0, default=1.00, step=0.01),
                "측정정책": st.column_config.SelectboxColumn(
                    "측정정책",
                    options=[
                        REBOUND_POINT_POLICY_OPTIONS[REBOUND_POINT_POLICY_EXACT_20]["short_label"],
                        REBOUND_POINT_POLICY_OPTIONS[REBOUND_POINT_POLICY_MIN_20]["short_label"],
                    ],
                    required=True,
                    help="정확히20: 20개가 아니면 무효 / 20개이상: 20개 초과 입력 허용, 기각률 20% 이상 무효"
                ),
            },
            use_container_width=True,
            hide_index=True,
            num_rows="dynamic"
        )

        if st.button("🚀 일괄 계산 실행", type="primary", use_container_width=True):
            batch_res = []
            for _, row in edited_df.iterrows():
                if not row.get("선택", True):
                    continue

                try:
                    rd_list = parse_readings_text(row.get("데이터", ""))
                    ang_v = row.get("각도", 0)
                    age_v = row.get("재령", 3000)
                    fck_v = row.get("설계", 24.0)
                    ct_v = row.get("Ct", 1.0)
                    policy_v = normalize_rebound_point_policy(row.get("측정정책", "정확히20"))

                    ok, res = calculate_strength(
                        rd_list,
                        ang_v,
                        age_v,
                        design_fck=fck_v,
                        selected_formulas=None,      # 배치 모드는 자동 추천 로직
                        core_coeff=ct_v,
                        require_20_points=True,
                        point_count_policy=policy_v
                    )

                    if ok:
                        result_fck = float(res.get("Design_Fck", fck_v))
                        result_ct = float(res.get("Core_Coeff", ct_v))
                        data_entry = {
                            "지점": row.get("지점", "P"),
                            "설계": result_fck,
                            "Ct": result_ct,
                            "측정정책": res.get("Point_Count_Policy_Label", get_rebound_point_policy_label(policy_v)),
                            "기각기준": res.get("Discard_Rule", ""),
                            "측정점수": int(res.get("N", len(rd_list))),
                            "유효점수": int(res.get("Effective_N", max(0, len(rd_list) - res.get("Discard", 0)))),
                            "공식선택방식": res.get("Formula_Mode", "자동추천"),
                            "적용공식": ", ".join(res.get("Applied_Formulas", [])),
                            "추정강도": round(res["Mean_Strength"], 2),
                            "강도비(%)": round((res["Mean_Strength"] / result_fck) * 100, 1) if result_fck != 0 else np.nan,
                            "유효평균R": round(res["R_avg"], 3),
                            "보정ΔR": round(res["Angle_Corr"], 6),
                            "보정R0": round(res["R0"], 6),
                            "재령계수": round(res["Age_Coeff"], 2),
                            "기각수": int(res["Discard"]),
                            "기각데이터": str(res["Excluded"])
                        }
                        for f_name, f_val in res["Formulas"].items():
                            data_entry[f_name] = round(f_val, 3)

                        batch_res.append(data_entry)
                    else:
                        batch_res.append({
                            "지점": row.get("지점", "P"),
                            "설계": _float_or_nan(fck_v),
                            "Ct": _float_or_nan(ct_v),
                            "측정정책": get_rebound_point_policy_label(policy_v),
                            "기각기준": "",
                            "측정점수": len(rd_list),
                            "유효점수": np.nan,
                            "공식선택방식": "자동추천",
                            "적용공식": ", ".join(get_recommended_formulas(fck_v)),
                            "추정강도": np.nan,
                            "강도비(%)": np.nan,
                            "유효평균R": np.nan,
                            "보정ΔR": np.nan,
                            "보정R0": np.nan,
                            "재령계수": np.nan,
                            "기각수": np.nan,
                            "기각데이터": "",
                            "오류": str(res)
                        })
                except Exception as e:
                    batch_res.append({
                        "지점": row.get("지점", "P"),
                        "오류": f"행 처리 실패: {e}"
                    })

            if batch_res:
                final_df = pd.DataFrame(batch_res)
                res_tab1, res_tab2 = st.tabs(["📋 요약", "🔍 세부 데이터"])
                with res_tab1:
                    cols = ["지점", "설계", "Ct", "측정정책", "측정점수", "유효점수", "기각수", "공식선택방식", "적용공식", "추정강도", "강도비(%)"]
                    cols = [c for c in cols if c in final_df.columns]
                    st.dataframe(final_df[cols], use_container_width=True, hide_index=True)
                with res_tab2:
                    st.dataframe(final_df, use_container_width=True, hide_index=True)

                st.divider()
                st.subheader("💾 결과 저장")
                col_dl1, col_dl2 = st.columns(2)
                with col_dl1:
                    try:
                        excel_data = to_excel(final_df)
                        st.download_button(
                            label="📊 엑셀 다운로드",
                            data=excel_data,
                            file_name=f"{p_name}_반발경도_평가결과_측정정책_Ct포함.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            type="primary",
                            use_container_width=True
                        )
                    except RuntimeError as e:
                        st.error(str(e))
                with col_dl2:
                    try:
                        valid_rows = final_df.dropna(subset=["추정강도"]) if "추정강도" in final_df.columns else final_df
                        if not valid_rows.empty and "추정강도" in valid_rows.columns:
                            mean_s = float(valid_rows["추정강도"].mean())
                            summary_b = {
                                "프로젝트명": p_name,
                                "평가 지점 수": len(final_df),
                                "유효 지점 수": len(valid_rows),
                                "전체 평균 추정강도": f"{mean_s:.2f} MPa",
                            }
                        else:
                            summary_b = {"프로젝트명": p_name, "평가 지점 수": len(final_df)}
                        pdf_bytes = generate_pdf_report(
                            project_name=p_name,
                            report_type="반발경도(다중지점)",
                            summary_dict=summary_b,
                            detail_df=final_df,
                            notes="다중 지점 일괄 평가 결과"
                        )
                        st.download_button(
                            label="📄 PDF 다운로드",
                            data=pdf_bytes,
                            file_name=f"{p_name}_반발경도_보고서.pdf",
                            mime="application/pdf",
                            use_container_width=True
                        )
                    except RuntimeError as e:
                        st.warning(str(e))

# ---------------------------------------------------------
# [Tab 3] 통계 및 비교 (세션 연동 적용)
# ---------------------------------------------------------
with tab4:
    st.subheader("📊 강도 통계 및 공식 적합성 비교")
    render_workflow_header(active_index=4)

    st.caption("반발경도 단일 평가 후 [통계 분석 목록에 추가] 버튼으로 누적된 지점별 5개 공식 결과를 비교하여, "
               "변동계수(CV)가 가장 낮은 = 해당 시설물에 가장 안정적인 공식을 자동 추천합니다.")

    c1, c2 = st.columns([1, 3])
    with c1:
        st_fck = st.number_input("기준 설계강도(MPa)", 15.0, 100.0, 24.0, key="stat_fck")
    with c2:
        st.markdown("**누적된 평가 지점**")
        st.caption(f"현재 {len(st.session_state['rebound_records'])}개 지점 / "
                   f"수동 입력 데이터 {len(st.session_state['rebound_data'])}개")

    st.markdown(
        f"""
        <div class="home-grid">
            <div class="home-card"><div class="home-card-title">공식 비교 지점</div><div class="home-card-value">{len(st.session_state['rebound_records'])}개</div><div class="home-card-sub">2개 이상부터 CV 비교 가능</div></div>
            <div class="home-card"><div class="home-card-title">간이 강도 데이터</div><div class="home-card-value">{len(st.session_state['rebound_data'])}개</div><div class="home-card-sub">수동 통계 분석용</div></div>
            <div class="home-card"><div class="home-card-title">기준 설계강도</div><div class="home-card-value">{st_fck:.1f}</div><div class="home-card-sub">MPa</div></div>
            <div class="home-card"><div class="home-card-title">분석 상태</div><div class="home-card-value">{"가능" if len(st.session_state['rebound_records']) >= 2 else "대기"}</div><div class="home-card-sub">공식별 평균·표준편차·CV</div></div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # ----- 1) 지점별 공식 비교 모드 (rebound_records 기반) -----
    st.divider()
    st.markdown("### 📌 지점별 공식 비교 (자동 추천)")

    if st.session_state['rebound_records']:
        recs_df = pd.DataFrame(st.session_state['rebound_records'])
        # 누적 데이터 편집 (지점 삭제 가능)
        recs_df.insert(0, "유지", True)
        edited_recs = st.data_editor(
            recs_df,
            column_config={
                "유지": st.column_config.CheckboxColumn("유지", default=True, help="해제 후 [데이터 갱신]을 누르면 제거됩니다"),
            },
            use_container_width=True, hide_index=True, num_rows="fixed",
            key="recs_editor"
        )

        b1, b2 = st.columns(2)
        with b1:
            if st.button("🔄 데이터 갱신(체크 해제 항목 삭제)", use_container_width=True):
                keep = edited_recs[edited_recs["유지"] == True].drop(columns=["유지"]).to_dict("records")
                st.session_state['rebound_records'] = keep
                st.session_state['rebound_data'] = [r["평균"] for r in keep]
                st.rerun()
        with b2:
            if st.button("🗑️ 전체 초기화", use_container_width=True):
                st.session_state['rebound_records'] = []
                st.session_state['rebound_data'] = []
                st.rerun()

        # 공식별 통계
        formula_cols = [c for c in REBOUND_FORMULA_OPTIONS if c in edited_recs.columns]
        active_recs = edited_recs[edited_recs["유지"] == True]

        if len(active_recs) >= 2 and formula_cols:
            stats_rows = []
            for fcol in formula_cols:
                vals = pd.to_numeric(active_recs[fcol], errors="coerce").dropna()
                if len(vals) >= 2:
                    mu = float(vals.mean())
                    sd = float(vals.std(ddof=1))
                    cv = (sd / mu * 100.0) if mu else np.nan
                    stats_rows.append({
                        "공식": fcol,
                        "지점수": len(vals),
                        "평균(MPa)": round(mu, 2),
                        "표준편차σ": round(sd, 2),
                        "변동계수CV(%)": round(cv, 2) if np.isfinite(cv) else np.nan,
                        "강도비(%)": round(mu / st_fck * 100, 1) if st_fck else np.nan,
                    })

            if stats_rows:
                stats_df = pd.DataFrame(stats_rows).sort_values("변동계수CV(%)").reset_index(drop=True)
                # 최저 CV = 추천 공식
                best = stats_df.iloc[0]
                worst = stats_df.iloc[-1]

                render_formula_recommendation_card(best, worst)
                st.caption("※ CV가 가장 낮은 공식은 현재 누적 데이터에서 산포가 가장 작은 공식입니다. 최종 공식 채택은 책임기술자 검토를 거쳐야 합니다.")

                # 설계강도별 권장 공식과의 일치 여부 안내
                recommended_set = set(get_recommended_formulas(st_fck))
                if best["공식"] not in recommended_set:
                    st.warning(f"⚠️ 자동 추천 공식({best['공식']})이 설계강도 {st_fck}MPa 기준 "
                               f"권장 공식군({', '.join(recommended_set)})과 다릅니다. "
                               f"책임기술자 검토 후 채택 여부를 결정하세요.")

                st.dataframe(stats_df, use_container_width=True, hide_index=True)

                # 공식별 CV 차트
                cv_chart = alt.Chart(stats_df).mark_bar().encode(
                    x=alt.X("공식:N", sort=stats_df["공식"].tolist()),
                    y=alt.Y("변동계수CV(%):Q"),
                    color=alt.condition(
                        alt.datum["공식"] == best["공식"],
                        alt.value("#2ecc71"),
                        alt.value("#95a5a6")
                    )
                ).properties(height=280, title="공식별 변동계수 비교 (낮을수록 안정적)")
                st.altair_chart(cv_chart, use_container_width=True)

                # 지점별 공식 결과 분포
                melted = active_recs.melt(id_vars=["지점"],
                                           value_vars=formula_cols,
                                           var_name="공식", value_name="강도")
                melted["강도"] = pd.to_numeric(melted["강도"], errors="coerce")
                point_chart = alt.Chart(melted).mark_circle(size=80, opacity=0.7).encode(
                    x=alt.X("지점:N"),
                    y=alt.Y("강도:Q", title="추정강도(MPa)"),
                    color="공식:N",
                    tooltip=["지점", "공식", "강도"]
                ).properties(height=300, title="지점별 공식 결과 분포")
                fck_rule = alt.Chart(pd.DataFrame({"y": [st_fck]})).mark_rule(
                    color="red", strokeDash=[5, 3]).encode(y="y")
                st.altair_chart(point_chart + fck_rule, use_container_width=True)

                # 통계 PDF
                with st.expander("📄 통계·비교 PDF 보고서 다운로드", expanded=False):
                    summary_st = {
                        "프로젝트명": p_name,
                        "기준 설계강도": f"{st_fck:.1f} MPa",
                        "평가 지점 수": len(active_recs),
                        "추천 공식": f"{best['공식']} (CV {best['변동계수CV(%)']:.2f}%)",
                        "추천 공식 평균강도": f"{best['평균(MPa)']:.2f} MPa",
                        "강도비(설계 대비)": f"{best['강도비(%)']:.1f} %",
                    }
                    try:
                        pdf_bytes = generate_pdf_report(
                            project_name=p_name, report_type="통계·비교",
                            summary_dict=summary_st, detail_df=stats_df,
                            notes="변동계수(CV) 최저 공식이 해당 시설물 콘크리트 특성에 가장 안정적이며, "
                                  "설계강도 기준 권장 공식군과의 일치 여부를 함께 검토하여 채택하시기 바랍니다."
                        )
                        st.download_button("📥 PDF 다운로드", data=pdf_bytes,
                                          file_name=f"{p_name}_통계비교_보고서.pdf",
                                          mime="application/pdf", use_container_width=True)
                    except RuntimeError as e:
                        st.warning(str(e))
        else:
            st.info("공식별 비교는 최소 2개 지점이 필요합니다.")

    else:
        st.info("⬅️ 먼저 '반발경도' 탭에서 단일 지점 평가를 수행하고 [통계 분석 목록에 추가] 버튼을 눌러주세요.")

    # ----- 2) 수동 입력 강도 데이터 통계 (기존 호환) -----
    st.divider()
    with st.expander("📋 수동 입력 강도 데이터 통계 (간이 분석)", expanded=False):
        session_data_str = " ".join([f"{x:.1f}" for x in st.session_state['rebound_data']])
        default_stat_txt = session_data_str if session_data_str else "24.5 26.2 23.1 21.8 25.5 27.0"

        raw_txt = st.text_area(
            "강도 데이터 목록",
            default_stat_txt,
            height=68,
            key="stat_raw",
            help="여러 값은 공백, 줄바꿈, 쉼표로 구분할 수 있습니다. 소수점은 24.5처럼 점(.)을 사용하세요."
        )
        parsed = parse_readings_text(raw_txt)

        if parsed and len(parsed) >= 2:
            data = sorted(parsed)
            avg_v = float(np.mean(data))
            std_v = float(np.std(data, ddof=1))
            cv_v = (std_v / avg_v * 100.0) if avg_v != 0 else np.nan

            with st.container(border=True):
                m1, m2, m3 = st.columns(3)
                m1.metric("평균", f"{avg_v:.2f} MPa", delta=f"{(avg_v / st_fck * 100):.1f}%")
                m2.metric("표준편차 (σ)", f"{std_v:.2f} MPa")
                m3.metric("변동계수 (CV)", f"{cv_v:.1f}%" if np.isfinite(cv_v) else "N/A")

            chart = alt.Chart(pd.DataFrame({"번호": range(1, len(data) + 1), "강도": data})).mark_bar().encode(
                x='번호:O', y='강도:Q',
                color=alt.condition(alt.datum.강도 >= st_fck, alt.value('#4D96FF'), alt.value('#FF6B6B'))
            )
            rule = alt.Chart(pd.DataFrame({'y': [st_fck]})).mark_rule(color='red', strokeDash=[5, 3], size=2).encode(y='y')
            st.altair_chart(chart + rule, use_container_width=True)
        elif parsed:
            st.warning("최소 2개 이상의 숫자가 필요합니다.")
