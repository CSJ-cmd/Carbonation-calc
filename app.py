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
import json
from datetime import datetime, timezone, timedelta

logger = logging.getLogger(__name__)

# =========================================================
# 1. 페이지 기본 설정 및 스타일 (재설계)
# =========================================================
st.set_page_config(
    page_title="구조물 안전진단 통합 평가 Pro",
    page_icon="🏗️",
    layout="wide",
    initial_sidebar_state="collapsed"
)

st.markdown("""
    <style>
    /* =====================================================================
       디자인 토큰
       · 색상은 모두 흰 배경 기준 WCAG AA(본문 4.5:1, 흰 글씨 칩 4.5:1)를 만족하도록
         조정했습니다. (기존 --warning:#F59E0B 는 흰 글씨 대비 2.1:1 로 판독 불가)
       · --ctl-h : 버튼·업로드 등 모든 조작 요소의 공통 높이(정렬 통일의 기준값)
       ===================================================================== */
    :root {
        --primary: #0F4C81;
        --primary-dark: #0A3A63;
        --primary-050: #EFF5FB;
        --primary-100: #D9E7F4;
        --action: #2563EB;
        --success: #15803D;
        --success-050: #F1FAF4;
        --success-100: #BBF7D0;
        --warning: #B45309;
        --warning-050: #FFF7ED;
        --warning-100: #FDE4C4;
        --danger: #DC2626;
        --neutral: #546274;
        --bg-soft: #F6F8FB;
        --card: #FFFFFF;
        --border: #E3E9F0;
        --border-strong: #C7D2DF;
        --text-main: #0F172A;
        --text-sub: #546274;
        --r-md: 10px;
        --r-lg: 14px;
        --ctl-h: 42px;
        --sh-1: 0 1px 2px rgba(15, 23, 42, 0.06);
        --sh-2: 0 6px 18px rgba(15, 23, 42, 0.07);
        /* 기존 인라인 클래스 호환용 별칭 */
        --brand: #0F4C81;
        --brand-deep: #0A3A63;
        --pass: #15803D;
        --fail: #DC2626;
        --warn: #B45309;
    }

    .block-container {
        padding-top: 1rem !important;
        padding-bottom: 5rem !important;
        padding-left: 1rem !important;
        padding-right: 1rem !important;
        max-width: 1440px !important;
        background: transparent !important;
    }
    [data-testid="stAppViewContainer"] { background: var(--bg-soft); }

    /* ---------------------------------------------------------------------
       탭 — 세그먼트 컨트롤
       Streamlit 1.60 은 BaseWeb 탭을 걷어내고 react-aria 로 바뀌어
       [data-baseweb="tab"] 선택자가 더 이상 걸리지 않습니다.
       현재 DOM: .stTabs > [role="tablist"] > [role="tab"][aria-selected]
       (구버전 호환을 위해 baseweb 선택자도 함께 둡니다)
       --------------------------------------------------------------------- */
    .stTabs [role="tablist"],
    .stTabs [data-baseweb="tab-list"] {
        display: flex; gap: 4px;
        padding: 5px !important;
        margin-bottom: 18px;
        background: var(--primary-050) !important;
        border: 1px solid var(--border) !important;
        border-bottom: 1px solid var(--border) !important;
        border-radius: var(--r-lg) !important;
        box-shadow: inset 0 1px 2px rgba(15, 23, 42, 0.04);
        overflow-x: auto; scrollbar-width: none;
    }
    .stTabs [role="tablist"]::-webkit-scrollbar,
    .stTabs [data-baseweb="tab-list"]::-webkit-scrollbar { display: none; }

    .stTabs [role="tab"],
    .stTabs [data-baseweb="tab"] {
        flex: 0 0 auto;
        display: inline-flex; align-items: center; justify-content: center;
        height: 40px !important; min-height: 40px !important;
        padding: 0 18px !important; margin: 0 !important;
        background: transparent !important;
        border: none !important; border-bottom: none !important;
        border-radius: var(--r-md) !important;
        color: var(--text-sub) !important;
        white-space: nowrap;
        transition: background-color .16s ease, color .16s ease, box-shadow .16s ease;
    }
    .stTabs [role="tab"] p,
    .stTabs [data-baseweb="tab"] p {
        margin: 0 !important; font-size: 0.95rem !important; font-weight: 600 !important;
        color: inherit !important;
    }
    .stTabs [role="tab"]:hover,
    .stTabs [data-baseweb="tab"]:hover {
        background: rgba(15, 76, 129, 0.07) !important; color: var(--text-main) !important;
    }
    .stTabs [role="tab"][aria-selected="true"],
    .stTabs [data-baseweb="tab"][aria-selected="true"] {
        background: var(--card) !important;
        color: var(--primary) !important;
        box-shadow: var(--sh-1), 0 2px 8px rgba(15, 76, 129, 0.10) !important;
    }
    .stTabs [role="tab"][aria-selected="true"] p,
    .stTabs [data-baseweb="tab"][aria-selected="true"] p { font-weight: 700 !important; }
    /* 기본 테마가 그리는 하단 하이라이트 바 제거 */
    .stTabs [data-baseweb="tab-highlight"],
    .stTabs [data-baseweb="tab-border"] { display: none !important; }

    /* ---------------------------------------------------------------------
       버튼 — 저장/불러오기/다운로드/팝오버 전부 같은 높이·반경·굵기
       height 대신 min-height 를 써서 긴 라벨은 줄바꿈되며 높이만 늘어납니다.
       --------------------------------------------------------------------- */
    .stButton > button,
    .stDownloadButton > button,
    [data-testid="stPopover"] button,
    [data-testid="stPopoverButton"],
    [data-testid="stFormSubmitButton"] button {
        min-height: var(--ctl-h) !important;
        padding: 0 16px !important;
        border-radius: var(--r-md) !important;
        font-weight: 700 !important;
        font-size: 0.95rem !important;
        line-height: 1.3 !important;
        transition: background-color .15s ease, border-color .15s ease,
                    color .15s ease, box-shadow .15s ease;
    }
    .stButton > button[kind="primary"],
    .stDownloadButton > button[kind="primary"],
    [data-testid="stBaseButton-primary"] {
        background: var(--primary) !important;
        border: 1px solid var(--primary) !important;
        color: #FFFFFF !important;
        box-shadow: var(--sh-1) !important;
    }
    .stButton > button[kind="primary"]:hover,
    .stDownloadButton > button[kind="primary"]:hover,
    [data-testid="stBaseButton-primary"]:hover {
        background: var(--primary-dark) !important; border-color: var(--primary-dark) !important;
    }
    .stButton > button[kind="secondary"],
    .stDownloadButton > button[kind="secondary"],
    [data-testid="stBaseButton-secondary"],
    [data-testid="stPopoverButton"] {
        background: var(--card) !important;
        border: 1px solid var(--border-strong) !important;
        color: var(--text-main) !important;
    }
    .stButton > button[kind="secondary"]:hover,
    .stDownloadButton > button[kind="secondary"]:hover,
    [data-testid="stBaseButton-secondary"]:hover,
    [data-testid="stPopoverButton"]:hover {
        background: var(--primary-050) !important;
        border-color: var(--primary) !important;
        color: var(--primary) !important;
    }

    /* 키보드 포커스 링 (마우스 클릭 시에는 나타나지 않음) */
    button:focus-visible,
    [role="tab"]:focus-visible,
    input:focus-visible,
    textarea:focus-visible,
    select:focus-visible {
        outline: 2px solid var(--action) !important;
        outline-offset: 2px !important;
    }

    /* 메트릭 — 숫자는 자릿수 정렬(tabular) */
    [data-testid="stMetricValue"] {
        font-size: 1.35rem !important; font-weight: 700 !important;
        font-variant-numeric: tabular-nums; letter-spacing: -0.01em;
        word-break: break-all; color: var(--text-main);
    }
    [data-testid="stMetricLabel"] { font-size: 0.82rem !important; color: var(--text-sub) !important; }

    /* ===== 앱 헤더 =====
       기존의 8px 파란 좌측 바 + 그라데이션을 걷어내고 1px 테두리 카드로 정리했습니다.
       (굵은 색 좌측 바는 화면 곳곳에서 반복돼 '투박함'의 주된 원인이었습니다) */
    .app-hero {
        padding: 16px 20px; margin: 0 0 14px 0;
        border: 1px solid var(--border); border-radius: var(--r-lg);
        background: var(--card); box-shadow: var(--sh-1);
    }
    .app-hero-title { font-size: 1.3rem; font-weight: 800; color: var(--text-main); letter-spacing: -0.02em; line-height: 1.3; }
    .app-hero-sub { font-size: 0.88rem; color: var(--text-sub); line-height: 1.5; margin-top: 4px; }

    /* ===== 진행 스텝퍼 (완료 / 현재 / 예정 3단계 구분) ===== */
    .wf { display: flex; align-items: flex-start; margin: 4px 0 20px 0; }
    .wf-step {
        position: relative; flex: 1 1 0; min-width: 0;
        display: flex; flex-direction: column; align-items: center; gap: 7px;
        padding: 0 4px; text-align: center;
    }
    .wf-step::before {
        content: ""; position: absolute; z-index: 0;
        top: 15px; right: 50%; width: 100%; height: 2px; background: var(--border);
    }
    .wf-step:first-child::before { display: none; }
    .wf-step.is-done::before, .wf-step.is-current::before { background: var(--primary); }
    .wf-num {
        position: relative; z-index: 1;
        width: 32px; height: 32px; border-radius: 50%;
        display: flex; align-items: center; justify-content: center;
        font-size: 0.85rem; font-weight: 800; font-variant-numeric: tabular-nums;
        background: var(--card); border: 2px solid var(--border); color: var(--text-sub);
    }
    .wf-step.is-done .wf-num { background: var(--primary); border-color: var(--primary); color: #FFFFFF; }
    .wf-step.is-current .wf-num {
        background: var(--card); border-color: var(--primary); color: var(--primary);
        box-shadow: 0 0 0 4px rgba(15, 76, 129, 0.13);
    }
    .wf-title { font-size: 0.85rem; font-weight: 700; color: var(--text-sub); line-height: 1.25; word-break: keep-all; }
    .wf-step.is-done .wf-title, .wf-step.is-current .wf-title { color: var(--text-main); }
    .wf-sub { font-size: 0.74rem; color: var(--text-sub); line-height: 1.3; word-break: keep-all; }

    /* ===== 섹션 제목 ===== */
    .step-title { margin: 4px 0 16px 0; padding: 0 0 12px 0; border-bottom: 1px solid var(--border); }
    .step-title b { display: block; color: var(--text-main); font-size: 1.15rem; font-weight: 800; letter-spacing: -0.015em; }
    .step-title span { display: block; margin-top: 5px; color: var(--text-sub); font-size: 0.88rem; line-height: 1.55; }

    /* ===== 결과 카드 ===== */
    .result-hero {
        display: grid; grid-template-columns: 1.4fr 1fr 1fr; gap: 0;
        align-items: center;
        padding: 20px 22px; margin: 16px 0;
        border: 1px solid var(--border); border-radius: var(--r-lg);
        background: var(--card); box-shadow: var(--sh-2);
    }
    .result-hero > div + div { padding-left: 20px; border-left: 1px solid var(--border); }
    .result-hero > div { padding-right: 20px; }
    .result-label { color: var(--text-sub); font-size: 0.82rem; font-weight: 600; margin-bottom: 6px; }
    .result-value {
        color: var(--text-main); font-size: 2rem; font-weight: 800;
        letter-spacing: -0.03em; line-height: 1.1; font-variant-numeric: tabular-nums;
    }
    .result-unit { font-size: 0.95rem; color: var(--text-sub); font-weight: 700; margin-left: 3px; letter-spacing: 0; }
    .result-grade {
        display: inline-flex; align-items: center; justify-content: center;
        color: #FFFFFF; font-weight: 800; padding: 8px 18px;
        border-radius: 999px; font-size: 1rem; min-width: 92px;
    }
    .result-note { color: var(--text-sub); font-size: 0.82rem; margin-top: 7px; line-height: 1.45; }

    /* ===== 추천 카드 ===== */
    .recommend-card {
        background: var(--success-050); border: 1px solid var(--success-100);
        border-radius: var(--r-lg); padding: 18px 20px; margin: 12px 0 16px 0;
    }
    .recommend-title { color: #166534; font-weight: 700; font-size: 0.85rem; }
    .recommend-main { color: #14532D; font-size: 1.8rem; font-weight: 800; margin-top: 6px; letter-spacing: -0.02em; }
    .recommend-sub { color: #3F5666; font-size: 0.9rem; margin-top: 6px; line-height: 1.5; font-variant-numeric: tabular-nums; }

    /* ===== 인라인 안내문 (st.info 남용 대체) ===== */
    .hint {
        display: block; padding: 10px 13px; margin: 6px 0 2px 0;
        border: 1px solid var(--border); border-radius: var(--r-md);
        background: var(--bg-soft); color: var(--text-sub);
        font-size: 0.86rem; line-height: 1.55;
    }
    .hint b { color: var(--text-main); font-weight: 700; }
    .hint.is-accent { background: var(--primary-050); border-color: var(--primary-100); }
    .hint.is-warn { background: var(--warning-050); border-color: var(--warning-100); color: #7C3D09; }
    .hint.is-warn b { color: #7C3D09; }

    /* ===== 진행상황(체크포인트) 바 ===== */
    .cp-label {
        font-size: 0.78rem; font-weight: 700; letter-spacing: 0.02em;
        color: var(--text-sub); margin: 0 0 8px 2px;
    }
    .cp-status {
        display: inline-flex; align-items: center; gap: 8px;
        min-height: var(--ctl-h); padding: 0 14px;
        border: 1px solid transparent; border-radius: var(--r-md);
        font-size: 0.85rem; font-weight: 600; color: var(--text-sub);
        line-height: 1.35;
    }
    .cp-dot { flex: 0 0 auto; width: 8px; height: 8px; border-radius: 50%; background: var(--neutral); }
    .cp-status.is-dirty { background: var(--warning-050); border-color: var(--warning-100); color: #7C3D09; }
    .cp-status.is-dirty .cp-dot { background: var(--warning); }
    .cp-status.is-saved { background: var(--success-050); border-color: var(--success-100); color: #14532D; }
    .cp-status.is-saved .cp-dot { background: var(--success); }

    div[data-testid="stTable"] { overflow-x: auto; }
    [data-testid="stAlert"] { border-radius: var(--r-md) !important; }

    /* ---------------------------------------------------------------------
       expander — 카드형 + 헤더 정렬
       기본 토글 아이콘(머티리얼 폰트)은 폰트 로딩 실패 시 'keyboard_arrow_right'
       라는 글자가 그대로 노출되므로 계속 숨기고, 대신 폰트에 의존하지 않는
       CSS 셰브론을 직접 그립니다. (기존에는 아이콘만 숨겨 열림/닫힘 단서가 없었음)
       --------------------------------------------------------------------- */
    div[data-testid="stExpander"] details {
        border: 1px solid var(--border) !important; border-radius: var(--r-lg) !important;
        background: var(--card); box-shadow: var(--sh-1); overflow: hidden;
    }
    div[data-testid="stExpander"] details > summary {
        list-style: none !important; display: flex !important; align-items: flex-start !important;
        gap: 10px; padding: 13px 16px !important; height: auto !important; min-height: 44px;
        border: none !important; border-radius: 0 !important;
        background: var(--bg-soft); cursor: pointer;
    }
    div[data-testid="stExpander"] details[open] > summary { border-bottom: 1px solid var(--border) !important; }
    div[data-testid="stExpander"] details > summary::-webkit-details-marker { display: none !important; }
    div[data-testid="stExpander"] details > summary > svg { margin-right: 12px !important; margin-top: 3px !important; width: 18px !important; min-width: 18px !important; height: 18px !important; flex-shrink: 0 !important; display: block !important; }
    div[data-testid="stExpander"] details > summary [class*="material"],
    div[data-testid="stExpander"] details > summary [data-testid*="icon"],
    div[data-testid="stExpander"] details > summary [aria-hidden="true"] { display: none !important; }
    div[data-testid="stExpander"] details > summary p { font-size: 0.95rem; font-weight: 700; margin: 0; line-height: 1.5; white-space: normal !important; word-break: keep-all; color: var(--text-main); }
    div[data-testid="stExpander"] details > summary::after {
        content: ""; flex: 0 0 auto; margin-left: auto; margin-top: 5px;
        width: 8px; height: 8px;
        border-right: 2px solid var(--text-sub); border-bottom: 2px solid var(--text-sub);
        transform: rotate(-45deg); transition: transform .18s ease;
    }
    div[data-testid="stExpander"] details[open] > summary::after { transform: rotate(45deg); margin-top: 2px; }

    @media (max-width: 900px) {
        .result-hero { grid-template-columns: 1fr; gap: 14px; }
        .result-hero > div + div { padding-left: 0; padding-top: 14px; border-left: none; border-top: 1px solid var(--border); }
        .result-hero > div { padding-right: 0; }
    }
    @media (max-width: 768px) {
        [data-testid="collapsedControl"] { display: none !important; }
        [data-testid="stHeader"] { height: 0 !important; }
        .block-container { padding-top: 0.5rem !important; }
        div[data-testid="stExpander"] details > summary { padding: 12px 13px !important; }
        .wf-sub { display: none; }
    }
    @media (max-width: 520px) {
        .app-hero { padding: 14px 16px; }
        .app-hero-title { font-size: 1.1rem; }
        .app-hero-sub { font-size: 0.82rem; }
        .result-value { font-size: 1.65rem; }
        .recommend-main { font-size: 1.5rem; }
        .wf-title { font-size: 0.76rem; }
        .wf-num { width: 28px; height: 28px; font-size: 0.78rem; }
        .wf-step::before { top: 13px; }
    }
    @media (prefers-reduced-motion: reduce) {
        *, *::before, *::after { transition-duration: 0.01ms !important; animation-duration: 0.01ms !important; }
    }
    </style>
""", unsafe_allow_html=True)


# =========================================================
# UI/UX 렌더링 헬퍼 (재설계 디자인)
# =========================================================
def _safe_html(value):
    """HTML 렌더링용 문자열 이스케이프"""
    return html.escape(str(value), quote=True)


def _safe_filename(value, fallback="프로젝트"):
    r"""다운로드 파일명에 쓸 수 없는 문자(\ / * ? : " < > |)를 _ 로 치환한다.

    진행상황 저장에만 적용돼 있던 처리를 PDF·엑셀 다운로드에도 동일하게 씁니다.
    프로젝트명에 'A동/B동'처럼 슬래시가 들어가면 파일명이 깨졌습니다.
    """
    name = re.sub(r'[\\/*?:"<>|]', "_", str(value or "").strip())
    return name or fallback


def render_app_header(project_name):
    st.markdown(
        f"""
        <div class="app-hero">
            <div class="app-hero-title">\U0001F3D7\uFE0F 구조물 안전진단 통합 평가 Pro</div>
            <div class="app-hero-sub">
                프로젝트: <b>{_safe_html(project_name)}</b> · 반발경도 입력, 보정계산, 통계 비교, PDF/Excel 출력까지 한 화면에서 처리합니다.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_workflow_header(current_index=0):
    """진행 스텝퍼. 완료(체크) / 현재(강조 링) / 예정(회색)을 서로 다르게 표시한다.

    이전에는 '현재 단계까지 전부' 같은 active 스타일이라 마지막 단계에 도달하면
    5칸이 모두 파랗게 칠해져 지금 어느 단계인지 읽을 수 없었습니다.
    단계 순서도 실제 화면 순서(보정조건 다음 측정값 입력)에 맞게 바로잡았습니다.
    """
    steps = [
        ("프로젝트", "점검 정보 확인"),
        ("보정조건", "방향·재령·Ct"),
        ("측정값 입력", "Rawdata 확인"),
        ("자동 계산", "강도·공식 산정"),
        ("후속 작업", "통계·보고서"),
    ]
    parts = []
    for idx, (title, sub) in enumerate(steps):
        if idx < current_index:
            state, badge = "is-done", "✓"
        elif idx == current_index:
            state, badge = "is-current", str(idx + 1)
        else:
            state, badge = "is-todo", str(idx + 1)
        parts.append(
            f'<div class="wf-step {state}">'
            f'<div class="wf-num">{badge}</div>'
            f'<div class="wf-title">{_safe_html(title)}</div>'
            f'<div class="wf-sub">{_safe_html(sub)}</div>'
            '</div>'
        )
    st.markdown(f'<div class="wf">{"".join(parts)}</div>', unsafe_allow_html=True)


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
    # 등급 색은 흰 글씨 칩(.result-grade) 배경으로 쓰이므로 흰색 대비 4.5:1 이상인 값만 사용합니다.
    # (기존 #F59E0B 는 흰 글씨 대비 2.1:1 로 '주의' 배지가 사실상 읽히지 않았습니다)
    if not np.isfinite(ratio):
        return "검토 필요", "#546274", "설계강도 기준을 확인하세요.", ratio
    if ratio >= 100:
        return "양호", "#15803D", "설계기준강도 이상으로 추정됩니다.", ratio
    if ratio >= 85:
        return "주의", "#B45309", "설계강도에 근접하므로 추가 검토가 권장됩니다.", ratio
    return "검토 필요", "#DC2626", "설계강도 대비 낮은 값으로 정밀 검토가 필요합니다.", ratio

# 세션 상태 초기화 (데이터 연동용)
if 'rebound_data' not in st.session_state:
    st.session_state['rebound_data'] = []

if 'rebound_records' not in st.session_state:
    st.session_state['rebound_records'] = []

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

    st.session_state['add_point_name'] = f"P{len(st.session_state['rebound_records']) + 1}"


def _format_reading_values(vals):
    """측정값 리스트를 텍스트칸/격자 공통 표기(정수는 정수, 소수는 .1f)로 직렬화"""
    return " ".join(
        str(int(v)) if abs(v - round(v)) < 1e-6 else f"{v:.1f}"
        for v in vals
    )


def _sync_text_to_grid():
    """텍스트칸을 고치면 호출 — 캔버스 텍스트(reb_src_txt) 갱신 후 격자 시드 버전 증가."""
    st.session_state['reb_src_txt'] = st.session_state.get('reb_paste_area', '')
    st.session_state['reb_grid_ver'] = st.session_state.get('reb_grid_ver', 0) + 1


def _sync_grid_to_text(grid_key, grid_cols):
    """격자를 고치면 호출 — 편집 델타를 시드 행에 적용해 텍스트칸으로 역동기화.

    셀 값 편집은 격자 버전을 올리지 않아(키 고정) 연속 입력 중 입력판이 리셋되지
    않습니다. 행 추가/삭제(구조 변경)일 때만 버전을 올려 격자를 깨끗이 다시 시드합니다.
    """
    state = st.session_state.get(grid_key)
    if not isinstance(state, dict):
        return

    base_rows = st.session_state.get('_reb_grid_base_rows', []) or []
    rows = [list(r) for r in base_rows]

    for ridx, changes in (state.get("edited_rows", {}) or {}).items():
        try:
            ridx = int(ridx)
        except (TypeError, ValueError):
            continue
        if 0 <= ridx < len(rows):
            for col, val in (changes or {}).items():
                if col in grid_cols:
                    rows[ridx][grid_cols.index(col)] = val

    deleted = state.get("deleted_rows", []) or []
    for ridx in sorted(deleted, reverse=True):
        if 0 <= ridx < len(rows):
            rows.pop(ridx)

    added = state.get("added_rows", []) or []
    for arow in added:
        rows.append([(arow or {}).get(c) for c in grid_cols])

    vals = []
    for r in rows:
        for v in r:
            if v is None:
                continue
            try:
                fv = float(v)
            except (TypeError, ValueError):
                continue
            if math.isfinite(fv):
                vals.append(fv)

    new_txt = _format_reading_values(vals)
    st.session_state['reb_src_txt'] = new_txt
    st.session_state['reb_paste_area'] = new_txt

    if deleted or added:
        st.session_state['reb_grid_ver'] = st.session_state.get('reb_grid_ver', 0) + 1


def inject_numeric_keypad():
    """[숫자패드] 모바일 입력 보정 — 측정값 입력 요소에 숫자 키패드를 강제한다.

    · Streamlit 은 리렌더마다 DOM 을 새로 그리므로 MutationObserver 로 재적용한다.
    · textarea 는 숫자 키패드에 공백 키가 없어 값 구분이 불가능하다.
      → 소수점을 연속 두 번 누르면 공백으로 자동 치환한다 ("54..56" → "54 56").
    · 데스크톱 물리 키보드는 inputmode 를 무시하므로 영향이 없다.
    """
    import streamlit.components.v1 as components
    components.html(
        r"""
<script>
(function () {
  const doc = window.parent.document;

  function markTextArea(el) {
    if (el.dataset.numpadReady === "1") return;
    el.dataset.numpadReady = "1";
    el.setAttribute("inputmode", "decimal");
    el.setAttribute("autocomplete", "off");
    el.setAttribute("autocorrect", "off");
    el.setAttribute("autocapitalize", "off");
    el.setAttribute("spellcheck", "false");

    // 숫자 키패드에는 공백 키가 없다 → '..' 를 구분자로 자동 치환
    el.addEventListener("input", function () {
      if (el.value.indexOf("..") === -1) return;
      const pos = el.selectionStart;
      const before = el.value;
      el.value = before.replace(/\.\./g, " ");
      const shift = before.length - el.value.length;
      try { el.setSelectionRange(pos - shift, pos - shift); } catch (e) {}
      // Streamlit(React) 에 값 변경을 알린다
      el.dispatchEvent(new Event("input", { bubbles: true }));
    });
  }

  function markNumberInput(el) {
    if (el.dataset.numpadReady === "1") return;
    el.dataset.numpadReady = "1";
    el.setAttribute("inputmode", "decimal");
  }

  function apply() {
    // 측정값 붙여넣기 칸 (aria-label 로 특정)
    doc.querySelectorAll("textarea").forEach(function (el) {
      const label = (el.getAttribute("aria-label") || "") + (el.placeholder || "");
      if (label.indexOf("측정값") !== -1) markTextArea(el);
    });
    // 격자 셀 / number_input (기기 편차 대비 보정)
    doc.querySelectorAll('input[type="number"], [data-testid="stDataFrame"] input')
       .forEach(markNumberInput);
  }

  apply();
  new MutationObserver(apply).observe(doc.body, { childList: true, subtree: true });
})();
</script>
        """,
        height=0,
    )


def is_mobile_client():
    """간단한 UA 기반 모바일/태블릿 판별"""
    try:
        ua = str(st.context.headers.get("user-agent", "")).lower()
    except Exception:
        ua = ""
    mobile_keys = ["android", "iphone", "ipad", "mobile", "tablet"]
    return any(k in ua for k in mobile_keys)

# =========================================================
# 2. 핵심 로직 및 함수 정의 (기존 로직 유지)
# =========================================================
ALLOWED_REBOUND_ANGLES = {-90, -45, 0, 45, 90}
REBOUND_READING_MIN = 10.0
REBOUND_READING_MAX = 100.0
# 격자/텍스트칸 초기 예시값(상단 상수로 고정해 지역 변수 누락에 따른 NameError 방지)
REBOUND_DEFAULT_GRID_TEXT = "54 56 55 53 58 55 54 55 52 57 55 56 54 55 59 42 55 56 54 55"
REBOUND_FORMULA_OPTIONS = ["일본재료", "일본건축", "과기부", "권영웅", "KALIS"]
REBOUND_FORMULA_NAMES = set(REBOUND_FORMULA_OPTIONS)
REBOUND_FORMULA_RECOMMEND_THRESHOLD = 40.0

REBOUND_POINT_POLICY_EXACT_20 = "exact_20"
REBOUND_POINT_POLICY_MIN_20 = "min_20"
REBOUND_POINT_POLICY_NO_MINIMUM = "no_minimum"
DEFAULT_REBOUND_POINT_POLICY = REBOUND_POINT_POLICY_EXACT_20
REBOUND_DISCARD_COUNT_LIMIT_20 = 4
REBOUND_DISCARD_RATIO_LIMIT = 0.20

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
    n = int(point_count)
    policy_key = normalize_rebound_point_policy(point_count_policy)

    if policy_key == REBOUND_POINT_POLICY_EXACT_20:
        return REBOUND_DISCARD_COUNT_LIMIT_20

    if policy_key in (REBOUND_POINT_POLICY_MIN_20, REBOUND_POINT_POLICY_NO_MINIMUM):
        return max(1, int(math.ceil(n * REBOUND_DISCARD_RATIO_LIMIT)))

    return REBOUND_DISCARD_COUNT_LIMIT_20


def get_recommended_formulas(design_fck):
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


def _normalize_manual_reading_text(raw_text):
    if raw_text is None:
        return ""

    text = str(raw_text)
    text = text.replace("−", "-").replace("–", "-").replace("—", "-")
    text = re.sub(r'(?<=\d),(?=\d{3}(?:\D|$))', '', text)
    text = re.sub(r'(?<=\d),(?=\d)', ' ', text)
    text = re.sub(r'[;\t\r\n/]+', ' ', text)
    text = re.sub(r'[\[\]\(\)\{\}]', ' ', text)
    return text.strip()


def parse_readings_text(raw_text):
    text = _normalize_manual_reading_text(raw_text)
    if not text:
        return []

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


def _batch_policy_text(value, default="정확히20"):
    """엑셀 업로드의 측정정책 셀 정규화.

    빈 셀은 NaN 이라 str() 하면 'nan' 이 되고, 그 값이 정책 파서에 들어가면
    ValueError 가 나서 해당 행 전체가 '행 처리 실패'로 버려졌습니다.
    """
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return default
    text = str(value).strip()
    return text or default


def _safe_num(v, default, cast=float):
    n = pd.to_numeric(v, errors="coerce")
    if pd.isna(n):
        return cast(default)
    return cast(n)


def _float_or_nan(v):
    try:
        n = float(v)
    except (TypeError, ValueError):
        return np.nan
    return n if np.isfinite(n) else np.nan


def _coerce_finite_float(value, field_name):
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


def get_angle_correction(R_val, angle):
    try:
        angle = int(angle)
        R = float(R_val)
    except (TypeError, ValueError):
        return 0.0

    if angle == 90:
        return (-0.0018 * R * R) + (0.2455 * R) - 11.906
    elif angle == 45:
        return (-0.0026 * R * R) + (0.2563 * R) - 9.24
    elif angle == -90:
        return (-0.0009 * R * R) + (0.0094 * R) + 4.48
    elif angle == -45:
        return (-0.0007 * R * R) + (0.0129 * R) + 3.14
    else:
        return 0.0


def get_age_coefficient(days):
    try:
        days = float(days)
    except (TypeError, ValueError):
        days = 3000.0

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


def calculate_strength(
    readings,
    angle,
    days,
    design_fck=24.0,
    selected_formulas=None,
    core_coeff=1.0,
    require_20_points=True,
    point_count_policy=None
):
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

    avg1 = float(np.mean(rd))

    low, high = avg1 * 0.8, avg1 * 1.2
    boundary_tol = 1e-12
    valid_mask = [(low - boundary_tol <= r <= high + boundary_tol) for r in rd]
    valid = [r for r, m in zip(rd, valid_mask) if m]
    excluded = [r for r, m in zip(rd, valid_mask) if not m]

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

    R_avg = float(np.mean(valid))

    corr = float(get_angle_correction(R_avg, angle))
    R0 = round(R_avg + corr, 1)

    age_c = float(get_age_coefficient(days))

    f_jsms = max(0.0, (1.27 * R0 - 18.0) * age_c)
    f_aij = max(0.0, (7.3 * R0 + 100.0) * 0.098 * age_c)
    f_mst = max(0.0, (15.2 * R0 - 112.8) * 0.098 * age_c)
    f_kwon = max(0.0, (2.304 * R0 - 38.80) * age_c)
    f_kalis = max(0.0, (1.3343 * R0 + 8.1977) * age_c)

    all_formulas_raw = {
        "일본재료": f_jsms,
        "일본건축": f_aij,
        "과기부": f_mst,
        "권영웅": f_kwon,
        "KALIS": f_kalis,
    }

    all_formulas = {k: v * ct for k, v in all_formulas_raw.items()}

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


def _find_korean_font():
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
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib import colors
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import mm
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont
        from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer,
                                          Table, TableStyle)
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
    story.append(Paragraph(_safe_html(project_name), title_style))
    story.append(Paragraph(f"비파괴검사 결과 보고서 ({report_type})", h2))
    story.append(Paragraph(f"작성일: {datetime.now().strftime('%Y-%m-%d %H:%M')}", body))
    story.append(Spacer(1, 6*mm))

    story.append(Paragraph("■ 평가 요약", h2))
    summary_rows = [["항목", "값"]]
    for k, v in summary_dict.items():
        summary_rows.append([str(k), str(v)])
    t = Table(summary_rows, colWidths=[60*mm, 110*mm])
    t.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), font_name),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#0F4C81")),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('GRID', (0, 0), (-1, -1), 0.4, colors.grey),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor("#f5f7fa")]),
    ]))
    story.append(t)
    story.append(Spacer(1, 6*mm))

    if detail_df is not None and not detail_df.empty:
        story.append(Paragraph("■ 상세 데이터", h2))
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
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#0F4C81")),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('GRID', (0, 0), (-1, -1), 0.3, colors.grey),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        story.append(td)
        story.append(Spacer(1, 4*mm))

    if notes:
        story.append(Paragraph("■ 비고", h2))
        story.append(Paragraph(_safe_html(notes).replace("\n", "<br/>"), body))

    story.append(Spacer(1, 8*mm))
    story.append(Paragraph(
        "※ 본 보고서는 「시설물의 안전 및 유지관리에 관한 특별법」 세부지침에 따른 "
        "비파괴검사 결과를 자동 산정한 것으로, 최종 판정은 책임기술자의 검토를 거쳐야 합니다.",
        body))

    doc.build(story)
    return buffer.getvalue()


@st.cache_data(show_spinner=False, max_entries=32)
def cached_pdf_report(project_name, report_type, summary_dict, detail_df=None, notes=None):
    """[성능] PDF 생성은 expander 안에 있어도 매 rerun 마다 실행됩니다.

    expander 는 접혀 있어도 본문 코드가 항상 실행되므로, 값을 하나 고칠 때마다
    reportlab 이 보고서를 통째로 다시 그리고 있었습니다(입력 지연의 주원인).
    입력이 같으면 기존 결과를 그대로 돌려줍니다.
    """
    return generate_pdf_report(project_name, report_type, summary_dict, detail_df, notes)


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


CHECKPOINT_SCHEMA_VERSION = 1


def build_checkpoint_payload(state, now=None):
    """진행상황 저장용 payload를 만든다.
    state는 st.session_state처럼 .get(key, default)을 지원하는 매핑이면 된다
    (테스트에서는 plain dict를 넘긴다)."""
    if now is None:
        now = datetime.now(timezone(timedelta(hours=9)))

    formula_mode_label = state.get("reb_formula_mode_label")
    if formula_mode_label == "공식 직접 선택":
        selected_formulas = list(state.get("reb_selected_methods") or [])
    else:
        selected_formulas = None

    point_policy_label = state.get("reb_point_policy_label")
    point_count_policy = (
        normalize_rebound_point_policy(point_policy_label)
        if point_policy_label else DEFAULT_REBOUND_POINT_POLICY
    )

    return {
        "schema_version": CHECKPOINT_SCHEMA_VERSION,
        "saved_at": now.isoformat(),
        "project_name": state.get("proj_name", "") or "",
        "rebound": {
            "records": list(state.get("rebound_records", []) or []),
            "add_point_name": state.get("add_point_name") or "P1",
            "readings_text": state.get("reb_src_txt", "") or "",
            "in_progress_inputs": {
                "angle": state.get("reb_angle"),
                "days": state.get("reb_days"),
                "design_fck": state.get("reb_fck"),
                "core_coeff": state.get("reb_ct"),
                "selected_formulas": selected_formulas,
                "point_count_policy": point_count_policy,
            },
        },
    }


def apply_checkpoint_payload(payload):
    """체크포인트 JSON을 st.session_state에 반영할 {key: value} 딕셔너리로 변환한다.
    형식이 잘못되면 사용자에게 그대로 보여줄 수 있는 한국어 메시지의 ValueError를 던진다."""
    if not isinstance(payload, dict):
        raise ValueError("체크포인트 파일 형식이 올바르지 않습니다 (JSON 객체가 아님).")

    version = payload.get("schema_version")
    if version != CHECKPOINT_SCHEMA_VERSION:
        raise ValueError(
            f"지원하지 않는 체크포인트 파일 버전입니다: {version!r} "
            f"(현재 지원 버전: {CHECKPOINT_SCHEMA_VERSION})."
        )

    rebound = payload.get("rebound")
    if not isinstance(rebound, dict):
        raise ValueError("체크포인트 파일에 'rebound' 데이터가 없습니다.")

    records = rebound.get("records")
    if not isinstance(records, list):
        raise ValueError("체크포인트 파일의 반발경도 지점 데이터(records)가 올바르지 않습니다.")

    in_progress = rebound.get("in_progress_inputs") or {}

    angle_value = in_progress.get("angle")
    if angle_value is not None and angle_value not in ALLOWED_REBOUND_ANGLES:
        raise ValueError(f"체크포인트 파일의 타격각도 값이 올바르지 않습니다: {angle_value!r}")

    selected_formulas = in_progress.get("selected_formulas")
    if selected_formulas is not None:
        invalid_names = [f for f in selected_formulas if f not in REBOUND_FORMULA_NAMES]
        if invalid_names:
            raise ValueError(f"체크포인트 파일에 알 수 없는 공식이 포함되어 있습니다: {invalid_names}")
    formula_mode_label = "공식 직접 선택" if selected_formulas is not None else "설계강도 기준 자동추천"

    point_count_policy = in_progress.get("point_count_policy") or DEFAULT_REBOUND_POINT_POLICY
    point_policy_label = get_rebound_point_policy_label(point_count_policy)

    add_point_name = rebound.get("add_point_name") or f"P{len(records) + 1}"

    return {
        "proj_name": payload.get("project_name", "") or "",
        "rebound_records": records,
        "rebound_data": [
            r.get("평균") for r in records if isinstance(r, dict) and "평균" in r
        ],
        "add_point_name": add_point_name,
        "reb_src_txt": rebound.get("readings_text", "") or "",
        "reb_paste_area": rebound.get("readings_text", "") or "",
        "reb_angle": in_progress.get("angle"),
        "reb_days": in_progress.get("days"),
        "reb_fck": in_progress.get("design_fck"),
        "reb_ct": in_progress.get("core_coeff"),
        "reb_selected_methods": selected_formulas or [],
        "reb_formula_mode_label": formula_mode_label,
        "reb_point_policy_label": point_policy_label,
    }


def run_validation_tests():
    results = []

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
    exp_R0 = 55.5
    exp_age = 0.63
    exp_jsms = 33.06555
    exp_aij = 31.187961
    exp_mst = 45.119592

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

    base = [50] * 18 + [10, 90]
    ok2, res2 = calculate_strength(base, angle=0, days=3000, design_fck=24, core_coeff=1.0, require_20_points=True)
    tc2_pass = ok2 and (res2["Discard"] == 2)
    results.append(("TC2(기각 2개, 무효X)", tc2_pass, res2 if ok2 else res2))

    base3 = [50] * 15 + [10, 90, 10, 90, 10]
    ok3, res3 = calculate_strength(base3, angle=0, days=3000, design_fck=24, core_coeff=1.0, require_20_points=True)
    tc3_pass = (not ok3) and ("시험 무효" in str(res3))
    results.append(("TC3(기각 5개, 무효)", tc3_pass, res3))

    ok4a, res4a = calculate_strength(readings_tc1, angle=90, days=3000, design_fck=40, core_coeff=1.0, require_20_points=True)
    ok4b, res4b = calculate_strength(readings_tc1, angle=90, days=3000, design_fck=40, core_coeff=1.10, require_20_points=True)
    tc4_pass = ok4a and ok4b and close(res4b["Formulas"]["과기부"], res4a["Formulas"]["과기부"] * 1.10, 1e-6)
    results.append(("TC4(Ct 배율)", tc4_pass, {"MST@1.0": res4a["Formulas"]["과기부"], "MST@1.10": res4b["Formulas"]["과기부"]}))

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

    checkpoint_state_full = {
        "proj_name": "테스트 시설물",
        "rebound_records": [{"지점": "P1", "평균": 33.5, "과기부": 33.5}],
        "add_point_name": "P2",
        "reb_src_txt": "54 56 55",
        "reb_angle": 90,
        "reb_days": 3000,
        "reb_fck": 40.0,
        "reb_ct": 1.0,
        "reb_formula_mode_label": "공식 직접 선택",
        "reb_selected_methods": ["과기부", "권영웅"],
        "reb_point_policy_label": "정확히 20개",
    }
    fixed_now = datetime(2026, 7, 28, 10, 0, 0, tzinfo=timezone(timedelta(hours=9)))
    payload_full = build_checkpoint_payload(checkpoint_state_full, now=fixed_now)
    restored_full = apply_checkpoint_payload(payload_full)

    tc8a_pass = (
        payload_full["saved_at"] == "2026-07-28T10:00:00+09:00"
        and restored_full["proj_name"] == "테스트 시설물"
        and restored_full["rebound_records"] == checkpoint_state_full["rebound_records"]
        and restored_full["rebound_data"] == [33.5]
        and restored_full["add_point_name"] == "P2"
        and restored_full["reb_src_txt"] == "54 56 55"
        and restored_full["reb_angle"] == 90
        and restored_full["reb_formula_mode_label"] == "공식 직접 선택"
        and restored_full["reb_selected_methods"] == ["과기부", "권영웅"]
    )

    checkpoint_state_auto = dict(checkpoint_state_full)
    checkpoint_state_auto["reb_formula_mode_label"] = "설계강도 기준 자동추천"
    payload_auto = build_checkpoint_payload(checkpoint_state_auto, now=fixed_now)
    restored_auto = apply_checkpoint_payload(payload_auto)
    tc8b_pass = (
        payload_auto["rebound"]["in_progress_inputs"]["selected_formulas"] is None
        and restored_auto["reb_formula_mode_label"] == "설계강도 기준 자동추천"
        and restored_auto["reb_selected_methods"] == []
    )

    checkpoint_errors = {}
    for bad_name, bad_payload in [
        ("스키마 버전 불일치", {**payload_full, "schema_version": 99}),
        ("rebound 누락", {k: v for k, v in payload_full.items() if k != "rebound"}),
        ("records가 리스트 아님", {**payload_full, "rebound": {**payload_full["rebound"], "records": "x"}}),
        ("잘못된 타격각도", {**payload_full, "rebound": {**payload_full["rebound"], "in_progress_inputs": {**payload_full["rebound"]["in_progress_inputs"], "angle": 30}}}),
        ("알 수 없는 공식", {**payload_full, "rebound": {**payload_full["rebound"], "in_progress_inputs": {**payload_full["rebound"]["in_progress_inputs"], "selected_formulas": ["존재하지않는공식"]}}}),
    ]:
        try:
            apply_checkpoint_payload(bad_payload)
            checkpoint_errors[bad_name] = "에러 없이 통과함(실패)"
        except ValueError as e:
            checkpoint_errors[bad_name] = str(e)
    tc8c_pass = all(
        "에러 없이 통과함" not in v for v in checkpoint_errors.values()
    )

    results.append(("TC8(체크포인트 저장/복원 왕복)", tc8a_pass and tc8b_pass and tc8c_pass, {
        "수동선택_왕복": tc8a_pass,
        "자동추천_왕복": tc8b_pass,
        "잘못된_파일_거부": checkpoint_errors,
    }))

    return results


# [수정 #1] 외부 모듈(structural_safety_core_v6)에서 같은 이름들을 다시 import 해
# 위에서 정의한 계산 함수/상수를 통째로 덮어쓰던 블록을 제거했습니다.
# 이 파일에 정의된 함수가 유일한 '진실의 원천(single source of truth)'입니다.
# → 화면에 보이는 코드와 실제 실행되는 계산식이 항상 일치합니다.
# 만약 계산 로직을 별도 모듈로 분리하려면, 이 파일의 중복 정의를 지우고
# 그때 import 블록을 다시 추가하세요(둘을 동시에 두지 마세요).

# =========================================================
# 3. 메인 UI 구성 (재설계)
# =========================================================

with st.sidebar:
    st.header("⚙️ 프로젝트 정보")
    p_name = st.text_input("프로젝트명", "OO시설물 정밀점검", key="proj_name")
    st.divider()
    st.caption("시설물안전법 및 세부지침 준수")

render_app_header(p_name)


def _checkpoint_state_hash(payload):
    payload_for_hash = {k: v for k, v in payload.items() if k != "saved_at"}
    return hashlib.blake2b(
        json.dumps(payload_for_hash, sort_keys=True, ensure_ascii=False).encode("utf-8"),
        digest_size=8,
    ).hexdigest()


checkpoint_panel = st.container(border=True)
checkpoint_msg = st.container()

tab1, tab2, tab4 = st.tabs(["📖 점검 매뉴얼", "🔨 반발경도", "📈 통계·비교"])

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
    * 기본값은 [20개]입니다. 1개소당 20개 측정값만 사용하는 보수적인 방식입니다.
    * 추가 측정값까지 반영해야 하는 경우 [20개 이상 허용]을 선택할 수 있으며, 이때 기각 기준은 20% 이상으로 적용됩니다.

    **6. 통계ㆍ비교 탭 활용 안내**
    * 반발경도 단일평가 후 [통계 분석 목록에 추가] 버튼을 누르면 5개 공식별 결과가 모두 누적됩니다.
    * 누적된 지점들 간 변동계수(CV)가 가장 낮은 공식을 자동 추천합니다 — 해당 시설물에 가장 안정적인 산정식입니다.

    **7. PDF 보고서 출력**
    * 각 평가(반발경도/통계) 결과 하단의 [PDF 다운로드] 버튼으로 정밀안전점검 보고서 부록용 PDF를 받을 수 있습니다.
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
    render_step_heading(
        "🔨 반발경도 정밀 강도 산정",
        "측정값 입력 → 보정조건(타격방향·재령·설계기준강도) → 자동 계산 → 통계·보고서 순으로 진행합니다."
    )
    render_workflow_header(current_index=(4 if st.session_state.get('last_rebound_result') else 1))

    mobile_client = is_mobile_client()
    if mobile_client:
        st.caption("📱 모바일/태블릿 최적화 모드")
        inject_numeric_keypad()   # [숫자패드] 측정값 입력 요소에 숫자 키패드 강제

    mode = st.radio("입력 방식", ["단일 지점 (직접 입력)", "다중 지점 (엑셀 업로드)"], horizontal=True)

    if mode.startswith("단일"):
        with st.expander("⚙️ 1단계 · 보정조건 (방향·재령·강도·정책·공식)", expanded=True):
            # ---- 입력 파라미터: 모바일은 단일 컬럼, 데스크톱은 4열 ----
            if mobile_client:
                angle = st.selectbox(
                    "타격 방향",
                    [90, 45, 0, -45, -90],
                    format_func=lambda x: {90: "+90°(상향수직)", 45: "+45°(상향경사)", 0: "0°(수평)", -45: "-45°(하향경사)", -90: "-90°(하향수직)"}[x],
                    key="reb_angle"
                )
                days = st.number_input("재령(일)", 1, 10000, 3000,
                                      help="공용연수(년) × 365 + 양생기간. 기본 3000일(약 8년) 적용",
                                      key="reb_days")
                fck = st.number_input("설계강도(MPa)", 15.0, 100.0, 24.0, key="reb_fck")
                ct = st.number_input("코어 보정계수 Ct", 0.10, 2.00, 1.00, step=0.01, key="reb_ct")
            else:
                c1, c2, c3, c4 = st.columns(4)
                with c1:
                    angle = st.selectbox(
                        "타격 방향",
                        [90, 45, 0, -45, -90],
                        format_func=lambda x: {90: "+90°(상향수직)", 45: "+45°(상향경사)", 0: "0°(수평)", -45: "-45°(하향경사)", -90: "-90°(하향수직)"}[x],
                        key="reb_angle"
                    )
                with c2:
                    days = st.number_input("재령(일)", 1, 10000, 3000,
                                          help="공용연수(년) × 365 + 양생기간. 기본 3000일(약 8년) 적용",
                                          key="reb_days")
                with c3:
                    fck = st.number_input("설계강도(MPa)", 15.0, 100.0, 24.0, key="reb_fck")
                with c4:
                    ct = st.number_input("코어 보정계수 Ct", 0.10, 2.00, 1.00, step=0.01, key="reb_ct")

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
                    "기본값은 20개입니다. 추가 측정값을 평균 산정에 포함해야 하는 경우에만 "
                    "20개 이상 허용을 선택하세요."
                ),
                key="reb_point_policy_label"
            )
            point_count_policy = normalize_rebound_point_policy(point_policy_label)
            # st.info 3개가 연달아 쌓이면 파란 박스만 눈에 들어와 정작 값이 안 읽힙니다.
            # 조건 설명은 조용한 인라인 힌트로 낮추고, 경고만 st.warning 으로 남깁니다.
            st.markdown(
                f'<div class="hint">{_safe_html(get_rebound_point_policy_description(point_count_policy))}</div>',
                unsafe_allow_html=True,
            )

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
                ),
                key="reb_formula_mode_label"
            )

            if formula_mode_label == "설계강도 기준 자동추천":
                selected_methods = None
                st.markdown(
                    '<div class="hint is-accent"><b>자동추천 적용 공식</b> · '
                    f'{_safe_html(get_recommended_formula_description(fck))}</div>',
                    unsafe_allow_html=True,
                )
            else:
                selected_methods = st.multiselect(
                    "평균 산정 적용 공식",
                    formula_opts,
                    default=[],
                    help="직접 선택 모드에서는 1개 이상의 공식을 선택해야 계산할 수 있습니다.",
                    key="reb_selected_methods"
                )
                if selected_methods:
                    st.markdown(
                        '<div class="hint is-accent"><b>수동 선택 적용 공식</b> · '
                        f'{_safe_html(", ".join(selected_methods))}</div>',
                        unsafe_allow_html=True,
                    )
                else:
                    st.warning("직접 선택 모드에서는 평균 산정에 사용할 공식을 1개 이상 선택하세요.")

        with st.expander("✍️ 2단계 · 측정값 입력 (텍스트·격자)", expanded=False):
            # ============ 측정값 입력판 (격자형 + 실시간 기각 미리보기) ============
            GRID_COLS = 5  # 현장 측정 기록표와 동일한 5칸 가로 배열

            # [실시간 연동] 텍스트칸 ↔ 격자: 단일 상태(reb_src_txt) 기반 양방향 동기화 초기화
            if 'reb_src_txt' not in st.session_state:
                st.session_state['reb_src_txt'] = ""   # 빈 값으로 시작 → 텍스트칸은 placeholder(예시)만 표시
            if 'reb_paste_area' not in st.session_state:
                st.session_state['reb_paste_area'] = st.session_state['reb_src_txt']
            if 'reb_grid_ver' not in st.session_state:
                st.session_state['reb_grid_ver'] = 0

            # [중첩 expander 금지] 2단계 expander 안이므로 내부는 일반 블록으로 표시
            st.markdown("###### 📋 텍스트로 붙여넣기 / 한 번에 수정")
            st.text_area(
                "측정값 (공백·쉼표·줄바꿈으로 구분, 소수점은 58.4처럼 점 사용)",
                height=90,
                key="reb_paste_area",
                on_change=_sync_text_to_grid,
                placeholder=REBOUND_DEFAULT_GRID_TEXT,
                help="여기서 값을 고치면 아래 격자에 즉시 반영되고, 격자를 고치면 이 칸도 자동 갱신됩니다."
            )
            if mobile_client:
                # [숫자패드] 숫자 키패드에는 공백 키가 없다 → 점 두 번(..)이 구분자 역할
                st.caption("⌨️ 숫자 키패드 입력 중에는 **점을 두 번(..)** 눌러 값을 구분하세요. "
                           "예) 54..56..55 → 54 56 55 로 자동 변환됩니다.")
            st.caption("🔄 텍스트칸과 아래 격자가 실시간 양방향 동기화됩니다. (별도 버튼 불필요)")

            source_txt = st.session_state.get('reb_src_txt', "")
            seed_vals = parse_readings_text(source_txt)
            grid_ver = st.session_state.get('reb_grid_ver', 0)

            # 격자 셀 개수는 버전·정책이 바뀔 때만 재계산 → 셀 편집 중에는 격자가 리셋되지 않음
            _shape = st.session_state.get('_reb_grid_shape')
            if (not isinstance(_shape, dict)) or _shape.get('ver') != grid_ver or _shape.get('policy') != point_count_policy:
                if point_count_policy == REBOUND_POINT_POLICY_EXACT_20:
                    _cells = 20
                else:
                    _rows = max(4, math.ceil(max(20, len(seed_vals)) / GRID_COLS))
                    _cells = _rows * GRID_COLS
                _shape = {'ver': grid_ver, 'policy': point_count_policy, 'cells': _cells}
                st.session_state['_reb_grid_shape'] = _shape
            total_cells = _shape['cells']
            grid_num_rows = "fixed" if point_count_policy == REBOUND_POINT_POLICY_EXACT_20 else "dynamic"

            if point_count_policy == REBOUND_POINT_POLICY_EXACT_20 and len(seed_vals) > 20:
                st.warning("‘20개’ 정책에서는 앞 20개만 격자에 반영됩니다. "
                           "추가값까지 쓰려면 [20개 이상 허용]을 선택하세요.")

            padded = (list(seed_vals) + [np.nan] * total_cells)[:total_cells]
            grid_rows = [padded[i:i + GRID_COLS] for i in range(0, total_cells, GRID_COLS)]
            grid_cols = [f"{c + 1}열" for c in range(GRID_COLS)]
            grid_df = pd.DataFrame(grid_rows, columns=grid_cols)

            # 격자 변경 콜백이 편집 델타를 풀어내기 위한 기준(시드) 행 저장
            st.session_state['_reb_grid_base_rows'] = grid_rows
            grid_key = f"reb_grid_{point_count_policy}_{total_cells}_{grid_ver}"

            st.markdown("##### ✍️ 측정값 입력판  ·  가로 5칸 = 기록표와 동일 배열")
            num_col_cfg = st.column_config.NumberColumn(
                min_value=REBOUND_READING_MIN,
                max_value=REBOUND_READING_MAX,
                step=0.1,
                format="%.1f",
            )
            edited_grid = st.data_editor(
                grid_df,
                column_config={c: num_col_cfg for c in grid_cols},
                hide_index=True,
                use_container_width=True,
                num_rows=grid_num_rows,
                key=grid_key,
                on_change=_sync_grid_to_text,
                kwargs={"grid_key": grid_key, "grid_cols": grid_cols},
            )

            ordered_vals = []
            for _, grow in edited_grid.iterrows():
                for c in edited_grid.columns:
                    v = grow[c]
                    if pd.notna(v):
                        ordered_vals.append(float(v))
            input_count = len(ordered_vals)

            if input_count >= 1:
                avg1 = float(np.mean(ordered_vals))
                tol = 1e-12
                low, high = avg1 * 0.8, avg1 * 1.2
                outlier_flags = [not (low - tol <= v <= high + tol) for v in ordered_vals]
                valid_vals = [v for v, o in zip(ordered_vals, outlier_flags) if not o]
                discard_n = sum(outlier_flags)
                eff_mean = float(np.mean(valid_vals)) if valid_vals else float('nan')
                discard_limit = get_discard_limit_for_policy(max(input_count, 1), point_count_policy)

                cells_html = ""
                for v, is_out in zip(ordered_vals, outlier_flags):
                    v_txt = f"{v:.0f}" if abs(v - round(v)) < 1e-6 else f"{v:.1f}"
                    if is_out:
                        cells_html += (
                            "<div style='position:relative;padding:9px 0;text-align:center;"
                            "font-size:17px;font-weight:600;font-variant-numeric:tabular-nums;"
                            "background:rgba(220,38,38,0.14);border:1.5px solid #DC2626;"
                            "border-radius:8px;color:#DC2626;'>"
                            f"{v_txt}<span style='position:absolute;top:2px;right:5px;"
                            "font-size:10px;'>⚠</span></div>"
                        )
                    else:
                        cells_html += (
                            "<div style='padding:9px 0;text-align:center;font-size:17px;"
                            "font-weight:500;font-variant-numeric:tabular-nums;"
                            "background:rgba(127,127,127,0.06);"
                            "border:1px solid rgba(127,127,127,0.22);border-radius:8px;"
                            f"color:inherit;'>{v_txt}</div>"
                        )
                st.markdown(
                    f"<div style='display:grid;grid-template-columns:repeat({GRID_COLS},1fr);"
                    f"gap:7px;margin:6px 0 14px;'>{cells_html}</div>",
                    unsafe_allow_html=True,
                )

                s1, s2, s3, s4 = st.columns(4)
                s1.metric("1차 평균", f"{avg1:.2f}")
                s2.metric("±20% 기각밴드", f"{low:.1f}–{high:.1f}")
                s3.metric("기각", f"{discard_n}개")
                s4.metric("유효 평균 R", f"{eff_mean:.2f}" if valid_vals else "—")
            else:
                st.info("격자에 측정값을 입력하면 평균과 ±20% 기각밴드, 기각 개수가 실시간으로 표시됩니다.")
                discard_n = 0
                discard_limit = get_discard_limit_for_policy(20, point_count_policy)

            if point_count_policy == REBOUND_POINT_POLICY_EXACT_20:
                if input_count == 20 and discard_n < discard_limit:
                    st.success("측정값 20개 입력 완료 — ‘20개’ 정책 조건을 만족합니다.")
                elif input_count != 20:
                    st.warning(f"현재 {input_count}개 — ‘20개’ 정책에서는 정확히 20개가 필요합니다.")
                else:
                    st.error(f"기각 {discard_n}개 (무효 기준 {discard_limit}개 이상) — "
                             "이대로 계산하면 시험 무효입니다. 재타격을 권장합니다.")
            else:
                if input_count >= 20 and discard_n < discard_limit:
                    st.success(f"측정값 {input_count}개 입력 — ‘20개 이상 허용’ 조건 만족 "
                               f"(기각 무효 기준 {discard_limit}개 이상).")
                elif input_count < 20:
                    st.warning(f"현재 {input_count}개 — 최소 20개가 필요합니다.")
                else:
                    st.error(f"기각 {discard_n}개 (무효 기준 {discard_limit}개 이상) — "
                             "이대로 계산하면 시험 무효입니다.")

            if ordered_vals:
                txt = " ".join(
                    str(int(v)) if abs(v - round(v)) < 1e-6 else f"{v:.1f}"
                    for v in ordered_vals
                )
            else:
                txt = ""

        if st.button("계산 실행", type="primary", use_container_width=True):
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
                st.session_state['last_added_signature'] = None
                st.session_state['last_add_message'] = None
                st.session_state['add_point_name'] = f"P{len(st.session_state['rebound_records']) + 1}"
            else:
                st.session_state['last_rebound_result'] = None
                st.session_state['last_rebound_meta'] = {}
                st.session_state['last_rebound_error'] = res
                st.session_state['last_add_message'] = None

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

            # ----- 결과 카드 (result-hero + 참고 검토등급) -----
            mean_s = float(res['Mean_Strength'])
            grade, grade_color, grade_msg, ratio = get_strength_review(mean_s, result_fck)
            if not np.isfinite(ratio):
                ratio = 0.0

            st.markdown(
                f"""
                <div class="result-hero">
                  <div>
                    <div class="result-label">평균 추정 압축강도 (코어보정 반영)</div>
                    <div class="result-value" style="color:{grade_color};">{mean_s:.2f}<span class="result-unit">MPa</span></div>
                    <div class="result-note">{_safe_html(grade_msg)}</div>
                  </div>
                  <div>
                    <div class="result-label">설계강도 대비</div>
                    <div class="result-value">{ratio:.0f}<span class="result-unit">%</span></div>
                    <div class="result-note">설계기준강도 {result_fck:.0f} MPa</div>
                  </div>
                  <div>
                    <div class="result-label">참고 검토등급</div>
                    <span class="result-grade" style="background:{grade_color};">{_safe_html(grade)}</span>
                    <div class="result-note">최종 판정은 책임기술자 검토 대상</div>
                  </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

            st.caption(f"측정점수 정책: {result_point_policy_label} / 기각 기준: {result_discard_rule}")
            st.caption(f"평균 산정 방식: {result_formula_mode} / 적용 공식: {', '.join(result_methods)}")
            st.caption("※ 아래 결과는 마지막으로 [계산 실행]을 누른 시점의 입력값 기준입니다. 입력값을 변경한 경우 다시 계산하세요.")

            with st.container(border=True):
                r1, r2, r3 = st.columns(3)
                r1.metric("유효 평균 R", f"{res['R_avg']:.3f}")
                r2.metric("각도 보정 ΔR(엑셀식)", f"{res['Angle_Corr']:+.6f}")
                r3.metric("측정/유효/기각", f"{res['N']} / {res.get('Effective_N', res['N'] - res['Discard'])} / {res['Discard']}")

                r4, r5, r6 = st.columns(3)
                r4.metric("최종 R₀", f"{res['R0']:.1f}")
                r5.metric("재령 계수 α", f"{res['Age_Coeff']:.2f}")
                r6.metric("Ct", f"{res['Core_Coeff']:.2f}")

            add_col1, add_col2 = st.columns(2)
            with add_col1:
                st.text_input("지점명", key="add_point_name")
            with add_col2:
                st.button(
                    "➕ 통계 분석 목록에 추가",
                    key="add_to_stats",
                    use_container_width=True,
                    on_click=add_current_rebound_to_stats
                )

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

            df_f = pd.DataFrame({"공식": list(res["Formulas"].keys()), "강도": list(res["Formulas"].values())})
            formula_order = list(res["Formulas"].keys())

            st.caption("공식별 추정강도 · 빨간 점선 = 설계강도")

            # 세로로 쌓이는 가로 막대(공식이 행으로, 강도가 막대 길이로) — 첫 제안 목업 형식
            base_chart = alt.Chart(df_f).encode(
                y=alt.Y('공식:N', sort=formula_order, title=None),
                x=alt.X('강도:Q', title='추정강도 (MPa)'),
            )
            bars = base_chart.mark_bar(cornerRadiusEnd=3, height=24).encode(
                color=alt.condition(alt.datum.강도 >= result_fck, alt.value('#15803D'), alt.value('#DC2626')),
                tooltip=[alt.Tooltip('공식:N'), alt.Tooltip('강도:Q', format='.2f', title='강도(MPa)')]
            )
            value_labels = base_chart.mark_text(align='left', baseline='middle', dx=5, fontWeight='bold').encode(
                text=alt.Text('강도:Q', format='.1f')
            )
            rule_chart = alt.Chart(pd.DataFrame({'x': [result_fck]})).mark_rule(
                color='#DC2626', strokeDash=[5, 3], size=2).encode(x='x:Q')

            st.altair_chart((bars + rule_chart + value_labels).properties(height=260), use_container_width=True)

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
                    pdf_bytes = cached_pdf_report(
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
                        file_name=f"{_safe_filename(p_name)}_반발경도_보고서.pdf",
                        mime="application/pdf",
                        use_container_width=True
                    )
                except RuntimeError as e:
                    st.warning(str(e))

    else:
        # ---------------------------------------------------------
        # 배치(엑셀) 템플릿 + 파싱 + 계산에 Ct 반영
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
                mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                use_container_width=True
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

                # [수정 #7] 헤더 앞뒤 공백 제거 → "설계 "처럼 공백이 낀 컬럼명도 정상 인식.
                # 공백 때문에 값이 조용히 기본값으로 둔갑하는 '조용한 오답'을 방지합니다.
                df_up.columns = df_up.columns.astype(str).str.strip()

                for idx, row in df_up.iterrows():
                    try:
                        # row.get 은 셀이 비어 있어도 기본값 대신 NaN 을 돌려주므로
                        # 지점명이 'nan' 으로 표시되는 문제를 막기 위해 따로 걸러냅니다.
                        _point_name = row.get("지점")
                        if pd.isna(_point_name) or str(_point_name).strip() == "":
                            _point_name = f"P{idx + 1}"
                        init_data.append({
                            "선택": True,
                            "지점": str(_point_name).strip(),
                            "각도": _safe_num(row.get("각도", 0), 0, int),
                            "재령": _safe_num(row.get("재령", 3000), 3000, int),
                            "설계": _safe_num(row.get("설계", 24.0), 24.0, float),
                            "Ct": _safe_num(row.get("Ct", 1.0), 1.0, float),
                            "측정정책": _batch_policy_text(row.get("측정정책")),
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
                        selected_formulas=None,
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
                            file_name=f"{_safe_filename(p_name)}_반발경도_평가결과_측정정책_Ct포함.xlsx",
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
                        pdf_bytes = cached_pdf_report(
                            project_name=p_name,
                            report_type="반발경도(다중지점)",
                            summary_dict=summary_b,
                            detail_df=final_df,
                            notes="다중 지점 일괄 평가 결과"
                        )
                        st.download_button(
                            label="📄 PDF 다운로드",
                            data=pdf_bytes,
                            file_name=f"{_safe_filename(p_name)}_반발경도_보고서.pdf",
                            mime="application/pdf",
                            use_container_width=True
                        )
                    except RuntimeError as e:
                        st.warning(str(e))

# ---------------------------------------------------------
# [Tab 4] 통계 및 비교 (세션 연동 적용)
# ---------------------------------------------------------
with tab4:
    st.subheader("📊 강도 통계 및 공식 적합성 비교")

    st.caption("반발경도 단일 평가 후 [통계 분석 목록에 추가] 버튼으로 누적된 지점별 5개 공식 결과를 비교하여, "
               "변동계수(CV)가 가장 낮은 = 해당 시설물에 가장 안정적인 공식을 자동 추천합니다.")

    c1, c2 = st.columns([1, 3])
    with c1:
        st_fck = st.number_input("기준 설계강도(MPa)", 15.0, 100.0, 24.0, key="stat_fck")
    with c2:
        st.markdown("**누적된 평가 지점**")
        st.caption(f"현재 {len(st.session_state['rebound_records'])}개 지점 / "
                   f"수동 입력 데이터 {len(st.session_state['rebound_data'])}개")

    st.divider()
    st.markdown("### 📌 지점별 공식 비교 (자동 추천)")

    if st.session_state['rebound_records']:
        recs_df = pd.DataFrame(st.session_state['rebound_records'])
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
                best = stats_df.iloc[0]
                worst = stats_df.iloc[-1]

                st.markdown(
                    f"""
                    <div class="recommend-card">
                      <div class="recommend-title">✅ 자동 추천 공식 · 변동계수(CV) 최저</div>
                      <div class="recommend-main">{_safe_html(str(best['공식']))}</div>
                      <div class="recommend-sub">CV {best['변동계수CV(%)']:.2f}% · 평균 {best['평균(MPa)']:.2f} MPa · 강도비 {best['강도비(%)']:.1f}%</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
                st.caption(f"※ 변동계수가 가장 낮은 공식이 해당 시설물의 콘크리트 특성에 가장 일관된 결과를 보입니다. "
                           f"가장 부적합: {worst['공식']} (CV {worst['변동계수CV(%)']:.2f}%)")

                recommended_set = set(get_recommended_formulas(st_fck))
                if best["공식"] not in recommended_set:
                    st.warning(f"⚠️ 자동 추천 공식({best['공식']})이 설계강도 {st_fck}MPa 기준 "
                               f"권장 공식군({', '.join(recommended_set)})과 다릅니다. "
                               f"책임기술자 검토 후 채택 여부를 결정하세요.")

                st.dataframe(stats_df, use_container_width=True, hide_index=True)

                cv_chart = alt.Chart(stats_df).mark_bar().encode(
                    x=alt.X("공식:N", sort=stats_df["공식"].tolist()),
                    y=alt.Y("변동계수CV(%):Q"),
                    color=alt.condition(
                        alt.datum["공식"] == best["공식"],
                        alt.value("#15803D"),
                        alt.value("#546274")
                    )
                ).properties(height=280, title="공식별 변동계수 비교 (낮을수록 안정적)")
                st.altair_chart(cv_chart, use_container_width=True)

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
                    color="#DC2626", strokeDash=[5, 3]).encode(y="y")
                st.altair_chart(point_chart + fck_rule, use_container_width=True)

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
                        pdf_bytes = cached_pdf_report(
                            project_name=p_name, report_type="통계·비교",
                            summary_dict=summary_st, detail_df=stats_df,
                            notes="변동계수(CV) 최저 공식이 해당 시설물 콘크리트 특성에 가장 안정적이며, "
                                  "설계강도 기준 권장 공식군과의 일치 여부를 함께 검토하여 채택하시기 바랍니다."
                        )
                        st.download_button("📥 PDF 다운로드", data=pdf_bytes,
                                          file_name=f"{_safe_filename(p_name)}_통계비교_보고서.pdf",
                                          mime="application/pdf", use_container_width=True)
                    except RuntimeError as e:
                        st.warning(str(e))
        else:
            st.info("공식별 비교는 최소 2개 지점이 필요합니다.")

    else:
        st.info("⬅️ 먼저 '반발경도' 탭에서 단일 지점 평가를 수행하고 [통계 분석 목록에 추가] 버튼을 눌러주세요.")

    st.divider()
    with st.expander("📋 수동 입력 강도 데이터 통계 (간이 분석)", expanded=False):
        session_data_str = " ".join([f"{x:.1f}" for x in st.session_state['rebound_data']])
        default_stat_txt = session_data_str if session_data_str else "24.5 26.2 23.1 21.8 25.5 27.0"

        # [수정 A] st.text_area는 key가 세션에 존재하면 value 인자를 무시한다.
        # 그대로 두면 반발경도 탭에서 지점을 추가해도 이 칸이 첫 렌더 값에 고정된다.
        # 누적 데이터의 서명이 바뀐 경우에만 세션 값을 직접 갱신해,
        # 사용자가 손으로 편집한 내용은 보존한다.
        if 'stat_raw' not in st.session_state:
            st.session_state['stat_raw'] = default_stat_txt
            st.session_state['_stat_sig'] = session_data_str
        elif session_data_str and st.session_state.get('_stat_sig') != session_data_str:
            st.session_state['stat_raw'] = session_data_str
            st.session_state['_stat_sig'] = session_data_str

        if session_data_str:
            st.caption(f"↺ 반발경도 탭 누적 지점 {len(st.session_state['rebound_data'])}개의 "
                       "평균강도가 자동 반영됩니다. 직접 수정해도 됩니다.")

        raw_txt = st.text_area(
            "강도 데이터 목록",
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
                color=alt.condition(alt.datum.강도 >= st_fck, alt.value('#15803D'), alt.value('#DC2626'))
            )
            rule = alt.Chart(pd.DataFrame({'y': [st_fck]})).mark_rule(color='#DC2626', strokeDash=[5, 3], size=2).encode(y='y')
            st.altair_chart(chart + rule, use_container_width=True)
        elif parsed:
            st.warning("최소 2개 이상의 숫자가 필요합니다.")

with checkpoint_panel:
    # [레이아웃 통일] 예전에는 [저장]이 버튼, [불러오기]가 파일 드롭존이라
    # 두 요소의 높이·모양·정렬이 전혀 달랐습니다.
    # 드롭존을 팝오버 안으로 넣어 바깥에는 같은 규격의 버튼 2개만 남깁니다.
    st.markdown('<div class="cp-label">진행상황</div>', unsafe_allow_html=True)
    cp_col1, cp_col2, cp_col3 = st.columns([1, 1, 2], vertical_alignment="center")

    _current_payload = build_checkpoint_payload(st.session_state)
    _current_hash = _checkpoint_state_hash(_current_payload)

    with cp_col1:
        _checkpoint_json = json.dumps(_current_payload, ensure_ascii=False, indent=2)
        _safe_proj_name = _safe_filename(st.session_state.get("proj_name", ""))
        _checkpoint_filename = f"{_safe_proj_name}_진행상황_{datetime.now().strftime('%Y%m%d_%H%M')}.json"
        if st.download_button(
            "💾 진행상황 저장",
            data=_checkpoint_json.encode("utf-8"),
            file_name=_checkpoint_filename,
            mime="application/json",
            use_container_width=True,
            help="현재 입력값과 누적 지점을 JSON 파일 하나로 내려받습니다.",
        ):
            st.session_state["_checkpoint_saved_hash"] = _current_hash

    with cp_col2:
        with st.popover("📂 진행상황 불러오기", use_container_width=True):
            st.caption("저장해 둔 진행상황 파일(.json)을 선택하세요.")
            _checkpoint_file = st.file_uploader(
                "진행상황 파일",
                type=["json"],
                key="checkpoint_uploader",
                label_visibility="collapsed",
            )

    with cp_col3:
        _saved_hash = st.session_state.get("_checkpoint_saved_hash")
        _has_data = bool(st.session_state.get("rebound_records"))
        if _saved_hash is None and _has_data:
            _cp_status_cls, _cp_status_txt = "is-dirty", "이번 세션에서 아직 저장하지 않았습니다"
        elif _saved_hash is not None and _current_hash != _saved_hash:
            _cp_status_cls, _cp_status_txt = "is-dirty", "마지막 저장 이후 변경사항이 있습니다"
        elif _saved_hash is not None:
            _cp_status_cls, _cp_status_txt = "is-saved", "마지막 저장 시점과 동일합니다"
        else:
            _cp_status_cls, _cp_status_txt = "", ""
        if _cp_status_txt:
            st.markdown(
                f'<div class="cp-status {_cp_status_cls}"><span class="cp-dot"></span>'
                f'{_safe_html(_cp_status_txt)}</div>',
                unsafe_allow_html=True,
            )

if _checkpoint_file is not None:
    _upload_sig = (_checkpoint_file.name, _checkpoint_file.size)
    if st.session_state.get("_checkpoint_upload_sig") != _upload_sig:
        st.session_state["_checkpoint_upload_sig"] = _upload_sig
        try:
            _payload = json.loads(_checkpoint_file.getvalue().decode("utf-8"))
            _pending_updates = apply_checkpoint_payload(_payload)
        except (ValueError, json.JSONDecodeError, UnicodeDecodeError) as e:
            st.session_state["_checkpoint_load_error"] = str(e)
            st.session_state["_checkpoint_pending_restore"] = None
        else:
            st.session_state["_checkpoint_load_error"] = None
            st.session_state["_checkpoint_pending_restore"] = {
                "updates": _pending_updates,
                "project_name": _payload.get("project_name", ""),
                "n_records": len(_payload.get("rebound", {}).get("records", [])),
                "saved_at": _payload.get("saved_at", "알 수 없음"),
            }

if st.session_state.get("_checkpoint_load_error"):
    with checkpoint_msg:
        st.error(f"불러오기 실패: {st.session_state['_checkpoint_load_error']}")

_pending_restore = st.session_state.get("_checkpoint_pending_restore")
if _pending_restore:
    @st.dialog("진행상황 불러오기 확인")
    def _confirm_checkpoint_restore():
        st.write(
            f"**불러올 파일:** {_pending_restore['project_name']} · "
            f"지점 {_pending_restore['n_records']}개 · "
            f"저장 시각 {_pending_restore['saved_at']}"
        )
        st.warning("지금 화면의 작업 중인 내용은 사라집니다.")
        dlg_col1, dlg_col2 = st.columns(2)
        if dlg_col1.button("예, 불러오기", type="primary", use_container_width=True):
            for _k, _v in _pending_restore["updates"].items():
                if _v is None:
                    continue
                st.session_state[_k] = _v
            st.session_state["last_added_signature"] = None
            st.session_state["last_add_message"] = None
            st.session_state["reb_grid_ver"] = st.session_state.get("reb_grid_ver", 0) + 1
            st.session_state["last_rebound_result"] = None
            st.session_state["last_rebound_meta"] = {}
            st.session_state["last_rebound_error"] = None
            st.session_state["_checkpoint_saved_hash"] = None
            st.session_state["_checkpoint_pending_restore"] = None
            st.rerun()
        if dlg_col2.button("취소", use_container_width=True):
            st.session_state["_checkpoint_pending_restore"] = None
            st.rerun()

    _confirm_checkpoint_restore()
