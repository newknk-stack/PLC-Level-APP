import html
import time
from io import BytesIO

from google.oauth2.service_account import Credentials
import gspread
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

# 페이지 기본 설정
st.set_page_config(page_title="PLC S/W 역량 진단 평가 툴", layout="wide")

# -------------------------------------------------------------------
# 🎨 UI 디자인 커스텀 CSS — "모던 SaaS 대시보드" 스타일
# (카드형 레이아웃 + 부드러운 그림자, 바이올렛 포인트 컬러, 슬레이트 배경)
# -------------------------------------------------------------------
ACCENT = "#7C3AED"          # 포인트 컬러 (바이올렛)
ACCENT_DARK = "#6D28D9"
ACCENT_SOFT = "#F5F3FF"     # 포인트 컬러의 아주 옅은 틴트 (배경용)
ACCENT_SOFT_BORDER = "#EDE9FE"
SURFACE = "#FFFFFF"
SURFACE_MUTED = "#F8FAFC"   # 카드 내부의 은은한 구분 배경
APP_BG = "#F1F5F9"          # 전체 배경(슬레이트)
TEXT_MAIN = "#0F172A"
TEXT_SUB = "#64748B"
BORDER = "#E2E8F0"

CUSTOM_STYLE = f"""
<style>
    /* 전체 배경: 카드가 떠 보이도록 은은한 슬레이트 톤 */
    .stApp {{
        background-color: {APP_BG};
    }}
    .block-container {{
        padding-top: 2rem;
        padding-bottom: 3rem;
    }}

    /* 탭 네비게이션: 세그먼트(필) 스타일 트랙 */
    .stTabs [data-baseweb="tab-list"] {{
        gap: 2px;
        background-color: #E2E8F0;
        padding: 4px;
        border-radius: 12px;
        border: none;
        width: fit-content;
    }}

    /* 각 탭 버튼: 트랙 위에 놓인 투명 필 */
    .stTabs [data-baseweb="tab"] {{
        height: 42px;
        white-space: pre-wrap;
        background-color: transparent;
        border-radius: 9px;
        gap: 8px;
        padding: 0px 20px;
        font-size: 0.92rem;
        font-weight: 600;
        color: {TEXT_SUB};
        border: none;
        transition: all 0.15s ease-in-out;
    }}

    .stTabs [data-baseweb="tab"]:hover {{
        color: {TEXT_MAIN};
    }}

    /* 선택된 탭: 흰색 필 + 은은한 그림자 + 포인트 컬러 텍스트 */
    .stTabs [aria-selected="true"] {{
        background-color: {SURFACE} !important;
        color: {ACCENT} !important;
        border-radius: 9px !important;
        box-shadow: 0 1px 2px rgba(15, 23, 42, 0.06), 0 2px 6px rgba(15, 23, 42, 0.06);
    }}

    .stTabs [data-baseweb="tab-highlight"] {{
        display: none !important;
    }}

    /* primary 버튼: 바이올렛 솔리드 + 부드러운 컬러 그림자 */
    div.stButton > button[kind="primary"] {{
        background-color: {ACCENT} !important;
        color: #FFFFFF !important;
        border: none !important;
        border-radius: 10px !important;
        box-shadow: 0 4px 12px rgba(124, 58, 237, 0.28);
        font-weight: 600;
        transition: all 0.15s ease-in-out;
    }}
    div.stButton > button[kind="primary"]:hover {{
        background-color: {ACCENT_DARK} !important;
        box-shadow: 0 6px 16px rgba(124, 58, 237, 0.36);
    }}

    /* 선택 박스 / 입력창: 카드(흰 배경)와 뚜렷이 구분되도록 은은한 바이올렛 톤 배경 +
       또렷한 테두리를 준다.
       (실제로 확인해보니, Streamlit의 selectbox는 버전에 따라 내부 DOM 구조가 아예
       다르다 — 구버전은 [data-baseweb="select"] 기반이고, 최신 버전은 react-aria 기반
       콤보박스(input[role="combobox"] + 감싸는 [role="group"])를 쓴다. 특히 최신 구조에서
       테두리/배경이 그려지는 실제 요소([role="group"])의 기본 배경색이 페이지 배경색과
       완전히 같아서(둘 다 #F1F5F9) 선택창이 안 보이는 문제였다. 두 구조 모두에 대응하도록
       선택자를 전부 지정한다. 로그인 화면 포함 전체 적용.) */
    div[data-baseweb="select"],
    div[data-baseweb="select"] > div,
    div[data-baseweb="select"] > div > div,
    [data-testid="stSelectbox"] [role="group"] {{
        background-color: {ACCENT_SOFT} !important;
        border-radius: 10px !important;
    }}
    div[data-baseweb="select"] > div,
    [data-testid="stSelectbox"] [role="group"] {{
        border: 1.5px solid #C4B5FD !important;
        box-shadow: 0 1px 2px rgba(15, 23, 42, 0.03) !important;
    }}
    div[data-baseweb="select"] > div:hover,
    [data-testid="stSelectbox"] [role="group"]:hover,
    [data-testid="stSelectbox"] [role="group"]:focus-within {{
        border-color: {ACCENT} !important;
    }}
    div[data-baseweb="select"] span,
    [data-testid="stSelectbox"] input[role="combobox"] {{
        color: {TEXT_MAIN} !important;
        background-color: transparent !important;
    }}
    div[data-baseweb="popover"] li,
    [role="listbox"] [role="option"] {{
        background-color: {SURFACE} !important;
    }}
    div[data-baseweb="popover"] li:hover,
    [role="listbox"] [role="option"]:hover,
    [role="listbox"] [role="option"][data-focused="true"] {{
        background-color: {ACCENT_SOFT} !important;
    }}
    .stTextInput input,
    .stNumberInput input {{
        background-color: {ACCENT_SOFT} !important;
        border-radius: 10px !important;
        border: 1.5px solid #C4B5FD !important;
    }}
    .stTextInput input:focus,
    .stNumberInput input:focus {{
        border-color: {ACCENT} !important;
        box-shadow: 0 0 0 1px {ACCENT} !important;
    }}

    /* 메트릭: 옅은 카드 타일 느낌 + 값이 길어도 잘리지 않고 줄바꿈되도록 처리
       ("C등급 (보통)" 같은 값이 좁은 칸에서 말줄임(...)으로 잘리는 문제 수정) */
    [data-testid="stMetric"] {{
        background-color: {SURFACE_MUTED};
        border-radius: 12px;
        padding: 14px 16px;
        border: 1px solid {BORDER};
    }}
    [data-testid="stMetricValue"] {{
        font-size: 1.15rem !important;
        white-space: normal !important;
        overflow: visible !important;
        text-overflow: unset !important;
        line-height: 1.3 !important;
        word-break: keep-all;
    }}
    [data-testid="stMetricLabel"] {{
        white-space: normal !important;
    }}

    /* st.container(border=True) 카드: 흰 배경 + 둥근 모서리 + 은은한 그림자
       (탭1의 대상자 선택 / 사전 진단 / 점수 입력 섹션을 카드로 묶는 데 사용) */
    div[data-testid="stVerticalBlockBorderWrapper"] {{
        border-radius: 16px !important;
        box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04), 0 8px 20px rgba(15, 23, 42, 0.05);
    }}
    div[data-testid="stVerticalBlockBorderWrapper"] > div {{
        border-radius: 16px !important;
        border-color: {BORDER} !important;
        background-color: {SURFACE} !important;
    }}

    /* 결과 표: 카드형 컨테이너 + 열 균등 폭 + 좌우 스크롤 없이 컨테이너 폭에 맞춤 */
    .styled-table {{
        width: 100%;
        table-layout: fixed;
        border-collapse: separate;
        border-spacing: 0;
        margin: 10px 0;
        font-size: 0.82rem;
        font-family: 'Noto Sans KR', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
        box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04), 0 8px 20px rgba(15, 23, 42, 0.06);
        border-radius: 14px;
        overflow: hidden;
        border: 1px solid {BORDER};
    }}
    .styled-table thead tr {{
        background-color: {SURFACE_MUTED};
        color: #334155;
        text-align: center;
        font-weight: 700;
        white-space: normal;
        word-break: keep-all;
        overflow-wrap: break-word;
        line-height: 1.35;
    }}
    .styled-table th {{
        padding: 12px 8px;
        text-align: center;
        border-bottom: 1px solid {BORDER};
    }}
    .styled-table td {{
        padding: 10px 8px;
        text-align: center;
        border-bottom: 1px solid #F1F5F9;
        color: #334155;
        white-space: normal;
        word-break: keep-all;
        overflow-wrap: break-word;
    }}
    .styled-table tbody tr:last-child td {{
        border-bottom: none;
    }}
    .styled-table tbody tr:nth-of-type(even) {{
        background-color: #FAFAFC;
    }}
    .styled-table tbody tr:hover {{
        background-color: {ACCENT_SOFT};
    }}

    /* 사이드바: 접속자 정보/관리자 패널도 카드 톤에 맞춰 은은하게 */
    section[data-testid="stSidebar"] {{
        background-color: {SURFACE_MUTED};
        border-right: 1px solid {BORDER};
    }}
</style>
"""

st.markdown(CUSTOM_STYLE, unsafe_allow_html=True)

# -------------------------------------------------------------------
# 🔐 로그인 세션 제어
# -------------------------------------------------------------------
# 예전에는 쿠키에 로그인 정보를 24시간 동안 저장해서, 브라우저를 새로 열거나
# 다시 접속해도 이전에 로그인했던 계정으로 자동 로그인되었다. 접속할 때마다
# 반드시 로그인 화면을 거치도록, 로그인 상태는 쿠키가 아닌 이번 세션(브라우저
# 탭 연결)에만 존재하는 st.session_state로만 관리한다 — 새로 접속하면 항상
# 로그아웃 상태로 시작한다.
if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False
if "user_name" not in st.session_state:
    st.session_state["user_name"] = None

# 평가 항목 (5선) 및 평가자/대상자 기본 정의
ITEMS = [
    "S/W 이해 및 제어 로직 분석력",
    "상위 시스템 인터페이스 이해 및 연동 능력",
    "코드 문제점 진단 및 개선 능력",
    "트러블슈팅 및 장애 대응력",
    "신기술 적용 및 향후 성장 가능성",
]

# 2026년 상반기까지 사용하던 예전 10개 항목 (구글 시트 마이그레이션용으로만 사용)
LEGACY_ITEMS = [
    "S/W 이해 및 제어 분석",
    "상위 인터페이스 분석",
    "코드 문제점 및 개선점 발굴",
    "트러블 슈팅 대응 방안",
    "발표 자료의 논리적 구성",
    "핵심 기술 요약력",
    "발표 시간 및 태도",
    "답변의 논리성 및 깊이",
    "현장 업무 적용 가능성",
    "향후 개발 역량 발전성",
]

# 신규 항목 → 예전 항목 매핑 (1~4번은 문구만 다듬은 동일 항목이라 그대로 이관,
# 5번 "신기술 적용 및 향후 성장 가능성"은 가장 개념이 가까운 예전 10번
# "향후 개발 역량 발전성" 점수를 그대로 이관한다)
LEGACY_ITEM_MAP = {
    "S/W 이해 및 제어 로직 분석력": "S/W 이해 및 제어 분석",
    "상위 시스템 인터페이스 이해 및 연동 능력": "상위 인터페이스 분석",
    "코드 문제점 진단 및 개선 능력": "코드 문제점 및 개선점 발굴",
    "트러블슈팅 및 장애 대응력": "트러블 슈팅 대응 방안",
    "신기술 적용 및 향후 성장 가능성": "향후 개발 역량 발전성",
}

# 항목별 점수(0~10점) 합계를 100점 만점 기준으로 환산하는 배율.
# 항목이 10개(만점 100점)에서 5개(만점 50점)로 줄었지만, 등급 기준(S/A/B/C/D =
# 90/80/70/60점)과 화면 표시는 기존처럼 "100점 만점" 기준을 그대로 유지하기로
# 결정했기 때문에, 합산 점수는 항상 이 배율을 곱해 100점 만점으로 환산한다.
SCORE_NORMALIZE_FACTOR = 100.0 / (len(ITEMS) * 10)

EVALUATORS = ["정준영", "차영진", "김태환", "김남권", "최치웅", "김동우", "송지호"]

TARGETS = sorted([
    "박상규 CL4",
    "이영표 CL4",
    "이윤열 CL3",
    "임성민 CL4",
    "김용남 CL3",
    "왕종표 CL4",
    "이동민 CL4",
    "이준식 CL4",
    "이진호 CL4",
    "길지훈 CL4",
    "이창배 CL3",
    "채경용 CL4",
    "하운기 CL4",
    "박광윤 CL4",
    "안상윤 CL3",
    "오성균 CL4",
    "이동준 CL4",
    "임채환 CL4",
    "권준성 CL3",
    "서창성 CL3",
    "유승우 CL4",
    "이도윤 CL3",
    "박시후 CL4",
    "손병효 CL3",
    "이준혁 CL4",
    "장정윤 CL3",
    "한정훈 CL4",
])


# -------------------------------------------------------------------
# 📊 2026년 상반기 역량 진단 데이터 파싱 함수
# -------------------------------------------------------------------
@st.cache_data
def load_competency_data(excel_path="2026년 상반기 역량 진단표.xlsx"):
    try:
        df_raw = pd.read_excel(excel_path)
        data = []
        for col in df_raw.columns[1:]:
            grade = col.split(".")[0]
            name = df_raw[col].iloc[0]

            l0_cnt = int(df_raw[col].iloc[1])
            l0_pct = float(df_raw[col].iloc[2]) * 100

            l1_cnt = int(df_raw[col].iloc[3])
            l1_pct = float(df_raw[col].iloc[4]) * 100

            l2_cnt = int(df_raw[col].iloc[5])
            l2_pct = float(df_raw[col].iloc[6]) * 100

            l3_cnt = int(df_raw[col].iloc[7])
            l3_pct = float(df_raw[col].iloc[8]) * 100

            data.append({
                "이름": name,
                "등급": grade,
                "L0_cnt": l0_cnt,
                "L0_pct": round(l0_pct, 1),
                "L1_cnt": l1_cnt,
                "L1_pct": round(l1_pct, 1),
                "L2_cnt": l2_cnt,
                "L2_pct": round(l2_pct, 1),
                "L3_cnt": l3_cnt,
                "L3_pct": round(l3_pct, 1),
            })
        return pd.DataFrame(data)
    except Exception as e:
        st.warning(f"사전 역량 진단표 파일 로드 중 참고용 데이터 오류: {e}")
        return pd.DataFrame()


df_comp = load_competency_data()


# -------------------------------------------------------------------
# 🎨 등급 계산 및 HTML 색상 함수
# -------------------------------------------------------------------
def calculate_grade(total_score):
    """항목 합산 점수(100점 만점 환산 기준) 기준 등급 산정"""
    if total_score >= 90.0:
        return "S"
    elif total_score >= 80.0:
        return "A"
    elif total_score >= 70.0:
        return "B"
    elif total_score >= 60.0:
        return "C"
    else:
        return "D"


def get_colored_grade_html(est_grade, pre_grade):
    color_map = {
        "S": "#8E44AD",
        "A": "#2980B9",
        "B": "#27AE60",
        "C": "#D35400",
        "D": "#C0392B",
    }

    c_est = color_map.get(str(est_grade).strip()[0:1], "#333333")
    c_pre = color_map.get(str(pre_grade).strip()[0:1], "#333333")

    html_str = f'<span style="color: {c_est}; font-weight: bold;">{est_grade}</span> (<span style="color: {c_pre}; font-weight: bold;">{pre_grade}</span>)'
    return html_str


def get_pre_grade(target_full_name):
    if df_comp.empty:
        return "-"
    clean_name = str(target_full_name).split()[0]
    m = df_comp[df_comp["이름"] == clean_name]
    if not m.empty:
        return m.iloc[0]["등급"]
    return "-"


def compute_dashboard_summary(df):
    """대상자별 종합 평가 요약(항목별 평균, 합계 점수, 등급 등)을 계산한다.
    TAB2(종합 평가 결과 대시보드) 화면 표시와, TAB3 엑셀 내보내기에서 대상자별
    시트를 만들 때 공통으로 사용한다."""
    df = df.copy()
    for item in ITEMS:
        df[item] = pd.to_numeric(df[item], errors="coerce").fillna(0)

    summary_list = []
    raw_grades_list = []
    download_list = []

    for target_person in df["target"].unique():
        sub_df = df[df["target"] == target_person]
        eval_count = len(sub_df)

        item_means = sub_df[ITEMS].mean()
        # 합산 점수는 100점 만점 기준으로 환산해서 등급을 산정한다.
        total_score = item_means.sum() * SCORE_NORMALIZE_FACTOR

        est_grade = calculate_grade(total_score)
        pre_grade = get_pre_grade(target_person)
        raw_grades_list.append(est_grade)

        colored_grade_html = get_colored_grade_html(est_grade, pre_grade)

        row = {
            "피평가자": target_person,
            "평가인원": eval_count,
            "종합 평균점수": round(total_score, 1),
            "기술 평가 등급(역량 본인 평가)": colored_grade_html,
        }
        row_dl = {
            "피평가자": target_person,
            "평가인원": eval_count,
            "종합 평균점수": round(total_score, 1),
            "기술 평가 등급(역량 본인 평가)": f"{est_grade} ({pre_grade})",
        }

        for item in ITEMS:
            score_val = round(item_means[item], 1)
            row[item] = score_val
            row_dl[item] = score_val

        summary_list.append(row)
        download_list.append(row_dl)

    summary_df = pd.DataFrame(summary_list)
    download_df = pd.DataFrame(download_list)
    return summary_df, download_df, raw_grades_list


def sanitize_sheet_name(name):
    """엑셀 시트 이름 제약(31자 이내, 특수문자 금지)에 맞게 문자열을 정리한다."""
    invalid_chars = ["\\", "/", "?", "*", "[", "]", ":"]
    clean = str(name)
    for ch in invalid_chars:
        clean = clean.replace(ch, "_")
    return clean[:31] if clean else "Sheet"


def build_evaluation_excel(detail_df, dashboard_targets_df):
    """상세 평가 기록(detail_df)과 대상자별 종합 대시보드 요약을
    (dashboard_targets_df, target별로 미리 계산된 요약 dict)
    하나의 엑셀 워크북(BytesIO)으로 묶어서 반환한다."""
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        # 1) 상세 평가 기록 시트
        detail_sheet_name = sanitize_sheet_name("평가상세")
        if detail_df.empty:
            pd.DataFrame(columns=["평가자", "평가 대상자"] + ITEMS).to_excel(
                writer, sheet_name=detail_sheet_name, index=False
            )
        else:
            detail_df.to_excel(writer, sheet_name=detail_sheet_name, index=False)

        # 2) 대상자별 종합 평가 대시보드 요약 시트 (대상자 1명당 시트 1개)
        used_sheet_names = {detail_sheet_name}
        for target_name, target_info in dashboard_targets_df.items():
            base_name = sanitize_sheet_name(target_name)
            sheet_name = base_name
            suffix = 2
            while sheet_name in used_sheet_names:
                sheet_name = sanitize_sheet_name(f"{base_name}_{suffix}")
                suffix += 1
            used_sheet_names.add(sheet_name)

            header_df = pd.DataFrame(
                [
                    {
                        "피평가자": target_name,
                        "평가인원": target_info["평가인원"],
                        "종합 평균점수": target_info["종합 평균점수"],
                        "기술 평가 등급(역량 본인 평가)": target_info["등급표시"],
                    }
                ]
            )
            items_df = pd.DataFrame(
                {
                    "평가 항목": ITEMS,
                    "항목별 평균점수": [target_info[it] for it in ITEMS],
                }
            )

            header_df.to_excel(
                writer, sheet_name=sheet_name, index=False, startrow=0
            )
            items_df.to_excel(
                writer, sheet_name=sheet_name, index=False, startrow=3
            )

    output.seek(0)
    return output.getvalue()


# -------------------------------------------------------------------
# 🔐 로그인 화면 — 중앙 정렬 카드형 레이아웃
# -------------------------------------------------------------------
if not st.session_state["logged_in"]:
    _login_l, _login_c, _login_r = st.columns([1, 1.2, 1])
    with _login_c:
        with st.container(border=True):
            st.markdown(
                '<div style="display:flex;flex-direction:column;align-items:center;text-align:center;padding:6px 4px 2px 4px;">'
                '<div style="width:52px;height:52px;border-radius:14px;background:#7C3AED;'
                'display:flex;align-items:center;justify-content:center;'
                'box-shadow:0 6px 16px rgba(124,58,237,0.35);margin-bottom:16px;">'
                '<svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="#FFFFFF" '
                'stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">'
                '<rect x="4" y="10" width="16" height="10" rx="1.5"></rect>'
                '<path d="M8 10V7a4 4 0 0 1 8 0v3"></path></svg>'
                '</div>'
                '<h1 style="font-size:1.45rem;font-weight:800;color:#0F172A;margin:0 0 6px 0;line-height:1.3;">'
                'PLC S/W 역량 진단 평가 시스템</h1>'
                '<p style="color:#64748B;font-size:0.85rem;font-weight:600;margin:0;">'
                '물류자동화그룹 · 공항사업섹션 · T1 T2 BHS운영</p>'
                '</div>',
                unsafe_allow_html=True,
            )

            st.markdown(
                '<p style="color:#94A3B8;font-size:0.82rem;text-align:center;margin:20px 0 6px 0;">'
                '본인 이름 선택 및 공동 비밀번호를 입력해 주세요</p>',
                unsafe_allow_html=True,
            )

            with st.form("login_form"):
                user_name = st.selectbox("👤 평가자(이름) 선택", EVALUATORS)
                input_pw = st.text_input("🔑 공동 비밀번호 입력", type="password")
                submit = st.form_submit_button(
                    "로그인", type="primary", use_container_width=True
                )

                if submit:
                    correct_pw = st.secrets.get("common_password", "2026")

                    if input_pw == str(correct_pw):
                        st.session_state["logged_in"] = True
                        st.session_state["user_name"] = user_name

                        st.success(f"반갑습니다, {user_name}님! 시스템에 접속합니다.")
                        time.sleep(0.3)
                        st.rerun()
                    else:
                        st.error("비밀번호가 올바르지 않습니다. 다시 확인해 주세요.")

            st.markdown(
                '<div style="text-align:center;margin-top:18px;padding-top:14px;'
                'border-top:1px solid #F1F5F9;">'
                '<span style="font-size:0.92rem;font-weight:900;font-family:sans-serif;'
                'letter-spacing:0.5px;color:#94A3B8;">posco </span>'
                '<span style="font-size:0.92rem;font-weight:900;font-family:sans-serif;color:#334155;">'
                '포스코<span style="color:#7C3AED;">DX</span></span>'
                '</div>',
                unsafe_allow_html=True,
            )

    st.stop()


# -------------------------------------------------------------------
# 🛡️ 관리자 계정 설정 (평가 데이터 삭제/수정 권한)
# — 사이드바(접속 중 평가자 표시 등)에서도 필요하므로 로그인 직후,
#   사이드바를 그리기 전에 먼저 계산해 둔다.
# -------------------------------------------------------------------
ADMIN_USERS = ["김남권"]
is_admin = st.session_state.get("user_name") in ADMIN_USERS


# -------------------------------------------------------------------
# 🟢 접속 중인 평가자 실시간 트래킹
# st.cache_resource로 만든 객체는 같은 서버 프로세스에서 실행되는 모든
# 세션(브라우저 탭)이 공유하는 싱글턴이므로, "누가 지금 접속해 있는지"를
# 세션 간에 공유하는 저장소로 사용할 수 있다. (st.session_state는 세션별로
# 분리되어 있어 이 용도로는 사용할 수 없다.)
# -------------------------------------------------------------------
@st.cache_resource
def _active_sessions_store():
    return {}


def _touch_active_session(name):
    """현재 세션이 살아있음을 공유 저장소에 기록(마지막 접속 시각 갱신)."""
    if name:
        _active_sessions_store()[name] = time.time()


def _clear_active_session(name):
    """로그아웃 시 공유 저장소에서 즉시 제거."""
    if name:
        _active_sessions_store().pop(name, None)


def _get_currently_active_evaluators(timeout_seconds=300):
    """최근 timeout_seconds 이내에 화면이 갱신된 평가자만 '접속 중'으로 간주.
    (탭을 닫아도 서버에 별도 알림이 오지 않으므로, 일정 시간 활동이 없으면
    자동으로 목록에서 제외하는 방식으로 근사한다.)"""
    store = _active_sessions_store()
    now = time.time()
    stale = [n for n, ts in store.items() if now - ts > timeout_seconds]
    for n in stale:
        store.pop(n, None)
    return sorted(store.keys(), key=lambda n: store[n], reverse=True)


_touch_active_session(st.session_state.get("user_name"))


# -------------------------------------------------------------------
# ☁️ 구글 시트 연동 설정
# -------------------------------------------------------------------
@st.cache_resource
def get_gspread_client():
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    ]
    creds_dict = dict(st.secrets["gcp_service_account"])

    if "\\n" in creds_dict["private_key"]:
        creds_dict["private_key"] = creds_dict["private_key"].replace(
            "\\n", "\n"
        )

    creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
    client = gspread.authorize(creds)
    return client


def get_worksheet():
    client = get_gspread_client()
    sheet_url = st.secrets["private_gsheets_url"]
    sheet = client.open_by_url(sheet_url).sheet1
    return sheet


@st.cache_data(ttl=15)
def load_data():
    try:
        sheet = get_worksheet()
        records = sheet.get_all_records()
        df = pd.DataFrame(records)
        if df.empty:
            df = pd.DataFrame(columns=["evaluator", "target"] + ITEMS)
        else:
            for item in ITEMS:
                if item not in df.columns:
                    df[item] = 0
        return df
    except Exception as e:
        if "429" in str(e):
            time.sleep(2)
            return load_data()
        st.error(f"구글 시트 데이터를 불러오는 중 오류가 발생했습니다: {e}")
        return pd.DataFrame(columns=["evaluator", "target"] + ITEMS)


def save_dataframe_to_sheet(df):
    """평가 데이터프레임을 구글 시트에 그대로 반영(덮어쓰기)한다.
    저장/수정/삭제 로직에서 공통으로 사용한다."""
    sheet = get_worksheet()
    sheet.clear()
    if df.empty:
        sheet.update([["evaluator", "target"] + ITEMS])
    else:
        sheet.update([df.columns.values.tolist()] + df.values.tolist())
    st.cache_data.clear()


def get_or_create_worksheet(title, header_row):
    """지정한 이름의 보조 시트가 없으면 새로 만들고 헤더를 채운다.
    (평가 확정 상태, 채팅 메시지처럼 평가 점수와는 별도로 관리해야 하는
    정보를 담는 시트를 준비할 때 공통으로 사용한다.)"""
    client = get_gspread_client()
    sheet_url = st.secrets["private_gsheets_url"]
    spreadsheet = client.open_by_url(sheet_url)
    try:
        ws = spreadsheet.worksheet(title)
    except gspread.exceptions.WorksheetNotFound:
        ws = spreadsheet.add_worksheet(
            title=title, rows=300, cols=max(len(header_row), 3)
        )
        ws.update([header_row])
    return ws


# -------------------------------------------------------------------
# ✅ 평가 확정 상태 ("confirmations" 시트: evaluator, confirmed, confirmed_at)
# 평가자가 본인의 모든 평가를 마친 뒤 "최종 확정"을 누르면 기록되는
# 평가자별 진행 상태이다. (평가중 / 평가완료 / 평가확정 3단계 중 마지막 단계)
# -------------------------------------------------------------------
def get_confirmation_worksheet():
    return get_or_create_worksheet(
        "confirmations", ["evaluator", "confirmed", "confirmed_at"]
    )


@st.cache_data(ttl=10)
def load_confirmations():
    try:
        ws = get_confirmation_worksheet()
        records = ws.get_all_records()
        result = {}
        for r in records:
            result[r.get("evaluator", "")] = {
                "confirmed": str(r.get("confirmed", "")).strip()
                in ("True", "TRUE", "1", "true"),
                "confirmed_at": r.get("confirmed_at", ""),
            }
        return result
    except Exception:
        return {}


def set_evaluator_confirmation(evaluator, confirmed):
    """특정 평가자의 최종 확정 상태를 저장한다(이미 기록이 있으면 갱신, 없으면 추가)."""
    ws = get_confirmation_worksheet()
    records = ws.get_all_records()
    now_str = time.strftime("%Y-%m-%d %H:%M:%S")
    row_idx = None
    for i, r in enumerate(records):
        if r.get("evaluator") == evaluator:
            row_idx = i + 2  # 헤더(1행) + 1-based 인덱스 보정
            break
    new_row = [evaluator, str(confirmed), now_str if confirmed else ""]
    if row_idx:
        ws.update(f"A{row_idx}:C{row_idx}", [new_row])
    else:
        ws.append_row(new_row)
    load_confirmations.clear()


def get_evaluator_progress_status(evaluator_name, all_data_df, confirmations):
    """평가자 한 명의 진행 상태를 '평가중' / '평가완료' / '평가확정' 3단계로 계산한다."""
    if confirmations.get(evaluator_name, {}).get("confirmed"):
        return "평가확정"
    if not all_data_df.empty and "evaluator" in all_data_df.columns:
        done_count = len(all_data_df[all_data_df["evaluator"] == evaluator_name])
    else:
        done_count = 0
    if done_count >= len(TARGETS):
        return "평가완료"
    return "평가중"


# -------------------------------------------------------------------
# 💬 접속자 간 채팅 ("chat_messages" 시트: timestamp, sender, message)
# -------------------------------------------------------------------
def get_chat_worksheet():
    return get_or_create_worksheet(
        "chat_messages", ["timestamp", "sender", "message"]
    )


@st.cache_data(ttl=5)
def load_chat_messages():
    try:
        ws = get_chat_worksheet()
        records = ws.get_all_records()
        return records[-100:]  # 최근 100건만 사용 (시트가 무한정 길어지는 것 방지)
    except Exception:
        return []


def send_chat_message(sender, message):
    if not message or not message.strip():
        return
    ws = get_chat_worksheet()
    now_str = time.strftime("%Y-%m-%d %H:%M:%S")
    ws.append_row([now_str, sender, message.strip()[:500]])
    load_chat_messages.clear()


def migrate_legacy_items_if_needed():
    """평가 항목이 10개 → 5개로 개편되면서, 예전 스키마(10개 항목)로 저장된
    구글 시트 데이터를 새 스키마(5개 항목)로 1회성 변환한다.

    변환 규칙 (사용자 확정):
      - 1~4번 항목: 문구만 다듬은 동일 항목이라 예전 점수를 그대로 이관
      - 5번 "신기술 적용 및 향후 성장 가능성": 예전 10번 "향후 개발 역량 발전성"
        점수를 그대로 이관 (신기술 적용 측면은 예전에 별도로 평가한 적이 없어
        가장 개념이 가까운 항목 점수로 대체)

    이미 새 스키마로 변환되어 있으면 아무 것도 하지 않는다(멱등).
    """
    try:
        sheet = get_worksheet()
        records = sheet.get_all_records()
        if not records:
            return  # 저장된 평가 데이터가 없으면 변환할 것도 없음

        raw_df = pd.DataFrame(records)

        has_new_schema = all(item in raw_df.columns for item in ITEMS)
        has_legacy_schema = any(item in raw_df.columns for item in LEGACY_ITEMS)

        if has_new_schema and not has_legacy_schema:
            return  # 이미 새 스키마로 변환 완료된 상태

        if not has_legacy_schema:
            # 예전 항목도 새 항목도 아닌 알 수 없는 컬럼 구조 -> 손대지 않음
            return

        new_rows = []
        for _, row in raw_df.iterrows():
            new_row = {
                "evaluator": row.get("evaluator", ""),
                "target": row.get("target", ""),
            }
            for new_item in ITEMS:
                legacy_item = LEGACY_ITEM_MAP.get(new_item)
                raw_val = row.get(legacy_item, 0) if legacy_item else 0
                try:
                    new_row[new_item] = float(raw_val) if str(raw_val) != "" else 0
                except (ValueError, TypeError):
                    new_row[new_item] = 0
            new_rows.append(new_row)

        new_df = pd.DataFrame(new_rows, columns=["evaluator", "target"] + ITEMS)
        save_dataframe_to_sheet(new_df)
    except Exception as e:
        st.warning(f"평가 항목 스키마(10개→5개) 자동 변환 중 문제가 발생했습니다: {e}")


# 평가 항목 스키마(10개→5개) 자동 변환은 세션당 한 번만 시도한다.
# (ADMIN_USERS / is_admin은 사이드바에서도 필요해 로그인 직후로 이동했다.)
if "legacy_items_migration_checked" not in st.session_state:
    migrate_legacy_items_if_needed()
    st.session_state["legacy_items_migration_checked"] = True



# -------------------------------------------------------------------
# 📚 사이드바 콘텐츠 — 시스템 사용 매뉴얼 / 업데이트 내역 (관리자 전용 항목 포함)
# -------------------------------------------------------------------
MANUAL_TEXT = """
- **로그인**: 이름 선택 + 공동 비밀번호 입력 (접속마다 매번 로그인, 자동 로그인 없음)
- **📝 평가 입력**: 대상자 선택 → 5개 항목 0~10점 입력 → [점수 저장 및 제출]. 완료한 대상자는 "✅ 평가 완료"로 표시되고, 다시 선택하면 기존 점수를 불러와 수정할 수 있습니다.
- **✅ 최종 확정**: 모든 대상자를 다 평가하면 평가 입력 탭 하단에서 진행률을 확인하고 [평가 확정] 버튼을 누를 수 있습니다(확정 취소도 가능).
- **📊 대시보드**: 등급 통계, 종합 점수 표, 방사형 차트(전체 평균 비교), 역량 요약 리포트, CSV 다운로드
- **🔍 상세 조회**: 평가자·대상자별 검색/정렬(평가자순·대상자순·등급순), 엑셀 다운로드
- **💬 채팅방**: 사이드바에서 다른 접속자와 간단한 메시지를 주고받을 수 있습니다.
"""

ADMIN_MANUAL_TEXT = """
**🛡️ 관리자 전용 (김남권 계정)**
- 사이드바: 현재 접속 중인 평가자 + 평가자별 진행 현황(평가중 / 평가완료 / 평가확정) 실시간 확인
- [🛠️ 관리자] 탭: 평가자·대상자 필터 + 이름 검색, 점수 직접 수정·삭제 (삭제는 확인 체크박스 선택 후 가능)
"""

CHANGELOG = [
    {
        "title": "평가 저장 즉시 반영 + 관리자 계정(김남권) 도입",
        "desc": "저장 직후 완료 상태가 바로 반영되도록 수정하고, 대상자 재선택 시 기존 점수를 불러오도록 개선했습니다. 김남권 계정에 평가 데이터 수정/삭제 권한을 부여했습니다.",
    },
    {
        "title": "상세조회 탭 엑셀 내보내기 추가",
        "desc": "조회된 평가 기록과 대상자별 종합 대시보드 요약을 엑셀 파일(여러 시트)로 내려받을 수 있습니다.",
    },
    {
        "title": "평가 항목 10개 → 5개로 개편",
        "desc": "핵심 5개 항목으로 평가 항목을 간소화하고, 기존 평가 데이터를 새 기준(100점 만점 유지)으로 자동 환산했습니다.",
    },
    {
        "title": "상세조회 표 정렬 기능 추가",
        "desc": "평가자순 / 평가 대상자순 / 평가등급순(S~D)으로 표를 정렬할 수 있습니다.",
    },
    {
        "title": "로그인 자동 유지 기능 제거",
        "desc": "접속할 때마다 반드시 로그인하도록 변경했습니다(쿠키 기반 자동 로그인 제거).",
    },
    {
        "title": "UI '모던 SaaS 대시보드' 스타일 적용 + 화면 구조 개편",
        "desc": "바이올렛 포인트 컬러의 카드형 디자인을 전체 화면에 적용하고, 로그인 화면을 중앙 카드형으로, 상단 헤더를 슬림 바 형태로 재구성했습니다. 평가 입력 화면의 각 섹션도 카드로 구분했습니다.",
    },
    {
        "title": "관리자용 '현재 접속 중인 평가자' 사이드바 패널 추가",
        "desc": "김남권 관리자 계정으로 접속하면 사이드바에서 현재 접속 중인 평가자 목록을 실시간으로 확인할 수 있습니다.",
    },
    {
        "title": "역량 진단 요약 리포트 및 방사형 차트 고도화",
        "desc": "방사형 차트에 전체 평균 비교선과 순위·팀 평균 대비 지표를 추가하고, 요약 리포트에 항목별 팀 평균 대비 상세 비교표를 추가했습니다.",
    },
    {
        "title": "시스템 사용 매뉴얼 / 업데이트 내역 사이드바 메뉴 추가",
        "desc": "사이드바에서 시스템 사용법과 지금까지의 업데이트 내역을 바로 확인할 수 있습니다. 관리자 전용 매뉴얼은 김남권 계정에서만 표시됩니다.",
    },
    {
        "title": "화면 가독성 개선 (등급 표시 잘림 / 슬라이더 크기 / 선택창 대비)",
        "desc": "사전 진단 현황의 등급 표시가 좁은 칸에서 잘리던 문제, 마지막 평가 항목 슬라이더만 유독 커 보이던 문제를 수정했습니다. 선택창·입력창에 은은한 배경색을 더해 카드 배경과 구분되도록 했습니다(로그인 화면 포함).",
    },
    {
        "title": "관리자 탭에 필터/검색 기능 추가",
        "desc": "전체 평가 데이터 표에도 상세조회와 동일한 평가자·대상자 필터를 적용하고, 이름 일부로 검색할 수 있는 검색창을 추가했습니다.",
    },
    {
        "title": "평가자 최종 확정 기능 + 진행 현황 실시간 표시",
        "desc": "평가자가 본인의 평가 결과를 확인하고 [평가 확정] 버튼을 누를 수 있는 기능을 추가했습니다. 관리자 사이드바에서 평가자별 진행 상태(평가중 / 평가완료 / 평가확정)를 실시간으로 확인할 수 있습니다.",
    },
    {
        "title": "접속자 간 채팅방 기능 추가",
        "desc": "사이드바에서 접속 중인 평가자들과 간단한 메시지를 주고받을 수 있는 채팅 기능을 추가했습니다.",
    },
]


# -------------------------------------------------------------------
# 👤 사이드바
# -------------------------------------------------------------------
st.sidebar.markdown("### 👤 접속자 정보")
st.sidebar.info(f"현재 접속자: **{st.session_state['user_name']}** 님")

if is_admin:
    st.sidebar.markdown("#### 🟢 현재 접속 중인 평가자")
    _active_now = _get_currently_active_evaluators()
    if _active_now:
        for _name in _active_now:
            _tag = " · 관리자" if _name in ADMIN_USERS else ""
            st.sidebar.markdown(
                f'<div style="display:flex;align-items:center;gap:7px;'
                f'font-size:0.85rem;color:#334155;padding:2px 0;">'
                f'<span style="width:8px;height:8px;border-radius:50%;'
                f'background:#22C55E;display:inline-block;flex-shrink:0;"></span>'
                f'{_name}{_tag}</div>',
                unsafe_allow_html=True,
            )
    else:
        st.sidebar.caption("현재 접속 중인 평가자가 없습니다.")
    st.sidebar.caption("※ 5분 이상 활동이 없으면 자동으로 제외됩니다.")

    st.sidebar.markdown("#### 📋 평가자별 진행 현황")
    _progress_data_df = load_data()
    _confirmations = load_confirmations()
    _status_style = {
        "평가확정": ("#22C55E", "#FFFFFF"),
        "평가완료": ("#7C3AED", "#FFFFFF"),
        "평가중": ("#E2E8F0", "#475569"),
    }
    for _ev in EVALUATORS:
        _status = get_evaluator_progress_status(_ev, _progress_data_df, _confirmations)
        _bg, _fg = _status_style[_status]
        st.sidebar.markdown(
            f'<div style="display:flex;align-items:center;justify-content:space-between;'
            f'padding:3px 0;font-size:0.83rem;color:#334155;">'
            f'<span>{_ev}</span>'
            f'<span style="background:{_bg};color:{_fg};font-size:0.7rem;font-weight:700;'
            f'padding:2px 8px;border-radius:999px;">{_status}</span>'
            f'</div>',
            unsafe_allow_html=True,
        )

if st.sidebar.button("🚪 로그아웃", type="secondary"):
    _clear_active_session(st.session_state.get("user_name"))
    st.session_state["logged_in"] = False
    st.session_state["user_name"] = None
    st.rerun()

st.sidebar.markdown("---")

# ---------------------------------------------------------------
# 💬 접속자 간 채팅방 — 모든 로그인 사용자에게 노출
# (Streamlit은 서버 푸시 없이 화면 재실행 시에만 갱신되므로, 완전한
#  실시간 메신저는 아니고 화면이 갱신될 때마다 최신 메시지를 보여주는
#  방식이다. 메시지를 보내면 즉시 rerun되어 본인 화면에는 바로 보인다.)
# ---------------------------------------------------------------
with st.sidebar.expander("💬 채팅방", expanded=False):
    st.caption("접속자들과 간단한 메시지를 주고받을 수 있습니다. (다른 사람의 새 메시지는 화면이 갱신될 때 보입니다)")
    _chat_msgs = load_chat_messages()
    if not _chat_msgs:
        st.caption("아직 채팅 메시지가 없습니다. 첫 메시지를 보내보세요!")
    else:
        for _msg in _chat_msgs[-30:]:
            _sender = html.escape(str(_msg.get("sender", "")))
            _text = html.escape(str(_msg.get("message", "")))
            _ts = str(_msg.get("timestamp", ""))
            _is_me = _msg.get("sender") == st.session_state.get("user_name")
            _bubble_bg = "#EDE9FE" if _is_me else "#F8FAFC"
            st.markdown(
                f'<div style="background:{_bubble_bg};border:1px solid {"#DDD6FE" if _is_me else "#E2E8F0"};'
                f'border-radius:10px;padding:6px 10px;margin-bottom:6px;font-size:0.8rem;">'
                f'<b style="color:#7C3AED;">{_sender}</b> '
                f'<span style="color:#94A3B8;font-size:0.7rem;">{_ts[-8:] if _ts else ""}</span><br>'
                f'<span style="color:#334155;">{_text}</span>'
                f'</div>',
                unsafe_allow_html=True,
            )
    with st.form("chat_form", clear_on_submit=True):
        _chat_input = st.text_input(
            "메시지 입력", label_visibility="collapsed", placeholder="메시지를 입력하세요..."
        )
        _chat_send = st.form_submit_button("보내기", use_container_width=True)
        if _chat_send and _chat_input.strip():
            send_chat_message(st.session_state.get("user_name"), _chat_input)
            st.rerun()

st.sidebar.markdown("---")
st.sidebar.markdown("### 📚 도움말")
with st.sidebar.expander("📖 시스템 사용 매뉴얼"):
    st.markdown(MANUAL_TEXT)
    if is_admin:
        st.markdown("---")
        st.markdown(ADMIN_MANUAL_TEXT)

with st.sidebar.expander("🕘 업데이트 내역"):
    st.caption("최신 업데이트가 위에 표시됩니다.")
    for _entry in reversed(CHANGELOG):
        st.markdown(f"**• {_entry['title']}**")
        st.caption(_entry["desc"])

# -------------------------------------------------------------------
# 🏷️ 메인 상단 바 — 슬림 한 줄 헤더 (아이콘 + 타이틀 + 부서명)
# -------------------------------------------------------------------
st.markdown(
    '<div style="display:flex;align-items:center;gap:14px;padding:6px 0 18px 0;'
    'border-bottom:1px solid #E2E8F0;margin-bottom:18px;">'
    '<div style="width:40px;height:40px;border-radius:11px;background:#7C3AED;'
    'display:flex;align-items:center;justify-content:center;flex-shrink:0;'
    'box-shadow:0 4px 10px rgba(124,58,237,0.28);">'
    '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#FFFFFF" '
    'stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">'
    '<rect x="4" y="10" width="16" height="10" rx="1.5"></rect>'
    '<path d="M8 10V7a4 4 0 0 1 8 0v3"></path></svg>'
    '</div>'
    '<div style="display:flex;flex-direction:column;gap:1px;">'
    '<span style="font-size:1.3rem;font-weight:800;color:#0F172A;line-height:1.25;">'
    'PLC S/W 역량 진단 평가 시스템</span>'
    '<span style="font-size:0.82rem;color:#64748B;font-weight:600;">'
    '물류자동화그룹 · 공항사업섹션 · T1 T2 BHS운영</span>'
    '</div>'
    '<div style="margin-left:auto;display:flex;align-items:center;gap:6px;">'
    '<span style="font-size:0.85rem;font-weight:900;font-family:sans-serif;color:#94A3B8;">posco </span>'
    '<span style="font-size:0.85rem;font-weight:900;font-family:sans-serif;color:#334155;">'
    '포스코<span style="color:#7C3AED;">DX</span></span>'
    '</div>'
    '</div>',
    unsafe_allow_html=True,
)



# -------------------------------------------------------------------
# 📌 메인 탭 화면 (소프트 파스텔 블루 톤 탭 적용)
# -------------------------------------------------------------------
_tab_labels = [
    "📝  평가 입력",
    "📊  종합 평가 결과 대시보드",
    "🔍  평가자별 / 대상자별 상세 조회",
]
if is_admin:
    _tab_labels.append("🛠️  관리자 (평가 데이터 관리)")

_tabs = st.tabs(_tab_labels)
tab1, tab2, tab3 = _tabs[0], _tabs[1], _tabs[2]
if is_admin:
    tab4 = _tabs[3]

# -------------------------------------------------------------------
# TAB 1: 평가 점수 입력
# -------------------------------------------------------------------
with tab1:
    st.subheader("평가 점수 제출")

    evaluator = st.session_state["user_name"]

    # 저장 직후 리런된 경우, 완료 안내 메시지를 한 번만 표시
    if st.session_state.get("save_flash_message"):
        st.success(st.session_state["save_flash_message"])
        del st.session_state["save_flash_message"]

    df_current = load_data()
    completed_targets = []
    completed_rows_by_target = {}
    if not df_current.empty and "evaluator" in df_current.columns and "target" in df_current.columns:
        my_rows = df_current[df_current["evaluator"] == evaluator]
        completed_targets = my_rows["target"].tolist()
        for _, _row in my_rows.iterrows():
            completed_rows_by_target[_row["target"]] = _row

    def _format_target_option(t):
        if t in completed_targets:
            return f"{t}  (✅ 평가 완료)"
        return t

    with st.container(border=True):
        st.markdown("**👤 평가자 / 🎯 평가 대상자 선택**")
        col1, col2 = st.columns(2)
        with col1:
            st.text_input(
                "평가자", value=f"{evaluator} (본인 로그인 완료)", disabled=True
            )
        with col2:
            # 옵션 값 자체(TARGETS)는 매 리런마다 동일하게 유지하고, 완료 표시는
            # format_func로만 붙여서 저장/리런 후에도 선택값이 유지되도록 한다.
            # (기존에는 "이름 (✅ 평가 완료)" 형태로 옵션 문자열 자체를 바꿔서,
            #  저장 후 리런되면 이전 선택값을 옵션 목록에서 찾지 못해 정렬순 첫 번째
            #  대상자인 "권준성 CL3"로 되돌아가는 버그가 있었다.)
            target = st.selectbox(
                "평가 대상자 선택",
                TARGETS,
                format_func=_format_target_option,
                key="tab1_selected_target",
            )

    if target and not df_comp.empty:
        target_clean_name = target.split()[0]
        match = df_comp[df_comp["이름"] == target_clean_name]

        if not match.empty:
            t_info = match.iloc[0]

            with st.container(border=True):
                grade_badge = {
                    "S": "🟣 S등급 (최우수)",
                    "A": "🔵 A등급 (우수)",
                    "B": "🟢 B등급 (숙련)",
                    "C": "🟡 C등급 (보통)",
                    "D": "🔴 D등급 (기초)",
                }.get(t_info["등급"], f"{t_info['등급']} 등급")

                st.markdown(
                    f"##### 💡 **[{target}]** 님의 역량 본인 평가 참고 현황"
                )

                m1, m2, m3, m4, m5 = st.columns(5)
                m1.metric("역량 본인 평가", grade_badge)
                m2.metric(
                    "Level 3 (전문가 건수)",
                    f"{t_info['L3_cnt']}건",
                    f"{t_info['L3_pct']}%",
                )
                m3.metric(
                    "Level 2 (우수/숙련 건수)",
                    f"{t_info['L2_cnt']}건",
                    f"{t_info['L2_pct']}%",
                )
                m4.metric(
                    "Level 1 (보통/실전 건수)",
                    f"{t_info['L1_cnt']}건",
                    f"{t_info['L1_pct']}%",
                )
                m5.metric(
                    "Level 0 (기초/미흡 건수)",
                    f"{t_info['L0_cnt']}건",
                    f"{t_info['L0_pct']}%",
                    delta_color="inverse",
                )

                l0_p = t_info["L0_pct"]
                l1_p = t_info["L1_pct"]
                l2_p = t_info["L2_pct"]
                l3_p = t_info["L3_pct"]

                st.markdown(
                    f"<div style='font-size: 0.85rem; color: #666; margin-top: 10px; margin-bottom: 4px;'>"
                    f"<b>역량 수준별 분포 현황</b> &nbsp;&nbsp;|&nbsp;&nbsp; "
                    f"<span style='color: #888;'>Level 3(전문가): {l3_p}% &nbsp;|&nbsp; Level 2(우수/숙련): {l2_p}% &nbsp;|&nbsp; Level 1(보통/실전): {l1_p}% &nbsp;|&nbsp; Level 0(기초/미흡): {l0_p}%</span>"
                    f"</div>",
                    unsafe_allow_html=True,
                )

                # 바이올렛 톤 단일 색상 램프 (Level 3 -> 0 로 갈수록 옅어짐)
                raw_levels = [
                    ("Level 3", l3_p, "#6D28D9", "white"),
                    ("Level 2", l2_p, "#A78BFA", "white"),
                    ("Level 1", l1_p, "#DDD6FE", "#4C1D95"),
                    ("Level 0", l0_p, "#F5F3FF", "#6D28D9"),
                ]

                active_levels = [item for item in raw_levels if item[1] > 0]

                min_width = 8.0
                chart_data = []

                if active_levels:
                    visual_widths = [
                        max(val, min_width) for _, val, _, _ in active_levels
                    ]
                    sum_v_w = sum(visual_widths)
                    norm_widths = [(w / sum_v_w) * 100 for w in visual_widths]

                    for (lbl, val, color, text_color), n_w in zip(
                        active_levels, norm_widths
                    ):
                        text_str = f"<b>{lbl} ({val}%)</b>"
                        chart_data.append(
                            (lbl, val, n_w, color, text_color, text_str)
                        )

                fig_bar = go.Figure()

                for lbl, val, vis_w, color, text_color, text_str in chart_data:
                    fig_bar.add_trace(
                        go.Bar(
                            y=["분포"],
                            x=[vis_w],
                            name=lbl,
                            orientation="h",
                            marker=dict(color=color),
                            text=text_str,
                            textposition="inside",
                            textfont=dict(
                                color=text_color, size=12, family="sans-serif"
                            ),
                            hovertemplate=f"{lbl}: {val}%<extra></extra>",
                        )
                    )

                fig_bar.update_layout(
                    barmode="stack",
                    xaxis=dict(
                        range=[0, 100],
                        showgrid=False,
                        showticklabels=False,
                        zeroline=False,
                    ),
                    yaxis=dict(showgrid=False, showticklabels=False),
                    margin=dict(l=0, r=0, t=0, b=0),
                    height=32,
                    showlegend=False,
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(0,0,0,0)",
                )

                st.plotly_chart(
                    fig_bar,
                    use_container_width=True,
                    config={"displayModeBar": False},
                )

    with st.container(border=True):
        st.markdown("**📝 항목별 점수 입력** (0점 ~ 10점)")
        if target in completed_targets:
            st.caption("✅ 이미 제출한 평가이며, 아래에 기존 점수가 표시됩니다. 수정 후 다시 저장할 수 있습니다.")

        # 이미 평가를 완료한 대상자를 다시 선택하면 기존에 저장된 점수를 슬라이더 기본값으로 표시한다.
        existing_row = completed_rows_by_target.get(target)

        scores = {}

        items_per_row = 2
        for i in range(0, len(ITEMS), items_per_row):
            row_items = ITEMS[i : i + items_per_row]
            # 항상 items_per_row 개의 칸을 만들어서, 마지막 줄에 항목이 하나만
            # 남더라도 그 슬라이더가 혼자 전체 폭을 차지해 다른 항목들과 크기가
            # 달라 보이지 않고 동일한 폭을 유지하도록 한다.
            cols = st.columns(items_per_row)
            for j, item in enumerate(row_items):
                with cols[j]:
                    if existing_row is not None:
                        try:
                            default_val = int(existing_row[item])
                        except (ValueError, TypeError):
                            default_val = 5
                    else:
                        default_val = 5

                    # 대상자별로 슬라이더 key를 분리해서, 평가 대상자를 바꿨을 때
                    # 이전 대상자에 입력하던 점수가 그대로 남아있지 않도록 한다.
                    scores[item] = st.slider(
                        f"{item}", 0, 10, default_val, key=f"slide_{target}_{item}"
                    )

    st.markdown("---")

    # 합산 점수는 100점 만점 기준으로 환산해서 등급을 산정하고 화면에 표시한다.
    current_total_score = (
        float(np.sum(list(scores.values()))) * SCORE_NORMALIZE_FACTOR
        if scores
        else 0.0
    )
    current_est_grade = calculate_grade(current_total_score)
    current_pre_grade = get_pre_grade(target)
    colored_grade_display = get_colored_grade_html(
        current_est_grade, current_pre_grade
    )

    st.markdown(
        """
        <style>
            div[data-testid="stColumn"]:nth-child(2) div.stButton > button {
                height: 100% !important;
                min-height: 72px !important;
                font-size: 1.05rem !important;
                font-weight: bold !important;
            }
        </style>
        """,
        unsafe_allow_html=True,
    )

    btn_col1, btn_col2 = st.columns([1, 1])

    with btn_col1:
        st.markdown(
            f"""
            <div style="background-color: #F5F3FF; border: 1px solid #EDE9FE; border-radius: 12px; padding: 14px 4px; text-align: center; height: 100%; min-height: 72px; display: flex; align-items: center; justify-content: center;">
                <div style="white-space: nowrap;">
                    <span style="font-size: 0.95rem; color: #6B7280; margin-right: 8px;">기술평가 등급(역량 본인 평가):</span>
                    <span style="font-size: 1.2rem;">{colored_grade_display}</span>
                    <span style="font-size: 0.9rem; color: #7C3AED; font-weight: 600; margin-left: 4px;">(합계 {current_total_score:.1f}점)</span>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with btn_col2:
        if st.button(
            "점수 저장 및 제출", type="primary", use_container_width=True
        ):
            try:
                df = load_data()

                existing_idx = df[
                    (df["evaluator"] == evaluator) & (df["target"] == target)
                ].index
                new_row = {"evaluator": evaluator, "target": target, **scores}

                if len(existing_idx) > 0:
                    for key, val in new_row.items():
                        df.loc[existing_idx[0], key] = val
                else:
                    df = pd.concat(
                        [df, pd.DataFrame([new_row])], ignore_index=True
                    )

                save_dataframe_to_sheet(df)

                # 저장 직후 바로 "평가 완료" 상태가 반영되도록 리런한다.
                # 대상자 선택 selectbox는 key로 고정된 값(target 원본 문자열)을
                # 그대로 유지하므로, 리런 후에도 다른 대상자로 튕기지 않는다.
                st.session_state["save_flash_message"] = (
                    f"[{evaluator}] 평가자의 [{target}] 대상자에 대한 평가가 성공적으로 저장되었습니다!"
                )
                st.rerun()
            except Exception as e:
                st.error(f"저장 중 오류가 발생했습니다: {e}")

    # ---------------------------------------------------------------
    # 📋 내 평가 현황 모니터링 + 최종 확정
    # 평가자가 본인이 지금까지 제출한 평가 결과를 한눈에 확인하고,
    # 모든 대상자에 대한 평가를 마쳤을 때 "최종 확정"을 누를 수 있게 한다.
    # 확정 여부는 별도의 confirmations 시트에 기록되며, 관리자 사이드바의
    # "평가자별 진행 현황"(평가중/평가완료/평가확정)에 실시간으로 반영된다.
    # ---------------------------------------------------------------
    st.markdown("---")
    with st.container(border=True):
        st.markdown("**📋 내 평가 현황 및 최종 확정**")

        _my_confirmations = load_confirmations()
        _my_confirmed_info = _my_confirmations.get(evaluator, {})
        _my_confirmed = _my_confirmed_info.get("confirmed", False)

        _my_done_count = len(completed_targets)
        _my_total_count = len(TARGETS)
        _my_progress = _my_done_count / _my_total_count if _my_total_count else 0

        st.progress(
            _my_progress, text=f"{_my_done_count} / {_my_total_count}명 평가 완료"
        )

        if completed_rows_by_target:
            _my_summary_rows = []
            for _t, _row in completed_rows_by_target.items():
                try:
                    _t_score = (
                        sum(float(_row[it]) for it in ITEMS) * SCORE_NORMALIZE_FACTOR
                    )
                except (ValueError, TypeError):
                    _t_score = 0.0
                _my_summary_rows.append(
                    {
                        "평가 대상자": _t,
                        "합산 점수": round(_t_score, 1),
                        "등급": calculate_grade(_t_score),
                    }
                )
            _my_summary_df = pd.DataFrame(_my_summary_rows).sort_values("평가 대상자")
            with st.expander(f"내가 제출한 평가 목록 보기 ({len(_my_summary_df)}건)"):
                _my_html = _my_summary_df.to_html(
                    index=False, escape=False, classes="styled-table"
                )
                st.markdown(CUSTOM_STYLE + _my_html, unsafe_allow_html=True)

        if _my_confirmed:
            st.success(f"✅ 평가확정 완료 ({_my_confirmed_info.get('confirmed_at', '')})")
            if st.button("🔓 확정 취소", key="unconfirm_btn"):
                set_evaluator_confirmation(evaluator, False)
                st.rerun()
        else:
            if _my_done_count >= _my_total_count and _my_total_count > 0:
                st.info("모든 대상자에 대한 평가를 완료하셨습니다. 최종 결과를 확인하신 후 확정해 주세요.")
                if st.button("✅ 평가 확정", type="primary", key="confirm_btn"):
                    set_evaluator_confirmation(evaluator, True)
                    st.rerun()
            else:
                st.caption(
                    f"전체 {_my_total_count}명 중 {_my_total_count - _my_done_count}명의 평가가 남아있습니다. "
                    "모든 대상자를 평가하면 확정할 수 있습니다."
                )

# -------------------------------------------------------------------
# TAB 2: 종합 평가 결과 대시보드
# -------------------------------------------------------------------
with tab2:
    st.subheader("종합 평가 현황")
    df = load_data()

    if df.empty or len(df) == 0:
        st.info("아직 입력된 평가 데이터가 없습니다.")
    else:
        for item in ITEMS:
            df[item] = pd.to_numeric(df[item], errors="coerce").fillna(0)

        summary_df, download_df, raw_grades_list = compute_dashboard_summary(df)

        # 🏆 등급 현황 통계를 맨 위로 이동
        st.markdown("### 🏆 등급 현황 통계")
        grade_series = pd.Series(raw_grades_list)
        grade_counts = grade_series.value_counts().reindex(
            ["S", "A", "B", "C", "D"], fill_value=0
        )

        c1, c2, c3, c4, c5 = st.columns(5)
        for i, g in enumerate(["S", "A", "B", "C", "D"]):
            eval(f"c{i+1}").metric(f"{g} 등급", f"{grade_counts[g]} 명")

        st.markdown("---")

        sort_option = st.radio(
            "📌 **표 정렬 방식 선택**",
            ["피평가자 이름순", "종합 평균점수 높은순 ➔ 피평가자 이름순"],
            horizontal=True,
        )

        if sort_option == "피평가자 이름순":
            summary_df.sort_values(by=["피평가자"], ascending=[True], inplace=True)
        else:
            summary_df.sort_values(
                by=["종합 평균점수", "피평가자"], ascending=[False, True], inplace=True
            )

        html_table = summary_df.to_html(
            index=False, escape=False, classes="styled-table"
        )
        st.markdown(CUSTOM_STYLE + html_table, unsafe_allow_html=True)

        st.markdown("### 📈 피평가자별 역량 방사형 차트")
        selected_target = st.selectbox(
            "분석할 대상자 선택", sorted(summary_df["피평가자"].unique())
        )

        target_info = summary_df[
            summary_df["피평가자"] == selected_target
        ].iloc[0]

        # 팀 전체 평균(항목별) 및 순위 — 방사형 차트에 비교선으로 함께 표시하고
        # 요약 리포트에서도 "전체 평균 대비" 코멘트를 만드는 데 사용한다.
        team_avg_by_item = summary_df[ITEMS].mean()
        team_avg_total = round(team_avg_by_item.sum() * SCORE_NORMALIZE_FACTOR, 1)

        rank_df = summary_df.sort_values(
            by=["종합 평균점수"], ascending=False
        ).reset_index(drop=True)
        target_rank = int(
            rank_df[rank_df["피평가자"] == selected_target].index[0]
        ) + 1
        total_people = len(rank_df)

        rk1, rk2, rk3 = st.columns(3)
        rk1.metric("종합 평균점수", f"{target_info['종합 평균점수']}점")
        rk2.metric("전체 내 순위", f"{target_rank} / {total_people}위")
        rk3.metric(
            "팀 평균 대비",
            f"{target_info['종합 평균점수'] - team_avg_total:+.1f}점",
        )

        fig = go.Figure()
        fig.add_trace(
            go.Scatterpolar(
                r=[team_avg_by_item[item] for item in ITEMS]
                + [team_avg_by_item[ITEMS[0]]],
                theta=ITEMS + [ITEMS[0]],
                fill="toself",
                name="전체 평균",
                line=dict(color="#CBD5E1", width=1.5, dash="dot"),
                fillcolor="rgba(148, 163, 184, 0.10)",
            )
        )
        fig.add_trace(
            go.Scatterpolar(
                r=[target_info[item] for item in ITEMS] + [target_info[ITEMS[0]]],
                theta=ITEMS + [ITEMS[0]],
                fill="toself",
                name=selected_target,
                line=dict(color="#7C3AED", width=2.5),
                fillcolor="rgba(124, 58, 237, 0.18)",
            )
        )
        fig.update_layout(
            polar=dict(
                radialaxis=dict(visible=True, range=[0, 10], gridcolor="#E2E8F0"),
                angularaxis=dict(gridcolor="#E2E8F0"),
                bgcolor="rgba(0,0,0,0)",
            ),
            showlegend=True,
            legend=dict(
                orientation="h", yanchor="bottom", y=-0.18, xanchor="center", x=0.5
            ),
            margin=dict(t=20, b=10),
            paper_bgcolor="rgba(0,0,0,0)",
        )
        st.plotly_chart(fig, use_container_width=True)

        # -------------------------------------------------------------------
        # 💡 평가 기반 장점 및 보완점 자동 요약 표출 영역 (항목별 팀 평균 대비 비교 포함)
        # -------------------------------------------------------------------
        st.markdown("---")
        st.markdown(f"#### 📝 **[{selected_target}] 역량 진단 요약 리포트**")

        overall_grade = calculate_grade(target_info["종합 평균점수"])
        grade_desc = {
            "S": "최우수 수준으로, 팀 내 최상위권 역량을 보유하고 있습니다.",
            "A": "우수한 수준으로, 대부분의 항목에서 안정적인 역량을 보여주고 있습니다.",
            "B": "숙련된 수준으로, 실무 수행에 무리가 없는 역량을 갖추고 있습니다.",
            "C": "보통 수준으로, 일부 항목에 대한 보완 학습이 필요합니다.",
            "D": "기초 수준으로, 핵심 항목에 대한 집중적인 육성이 필요합니다.",
        }.get(overall_grade, "")
        vs_team_word = "높은" if target_info["종합 평균점수"] >= team_avg_total else "낮은"
        st.markdown(
            f"종합 평가 등급은 **{overall_grade}등급**({grade_desc}) 이며, "
            f"전체 {total_people}명 중 **{target_rank}위**, 팀 평균({team_avg_total}점)보다 "
            f"**{abs(target_info['종합 평균점수'] - team_avg_total):.1f}점 {vs_team_word}** 수준입니다."
        )

        item_scores_series = pd.Series({item: target_info[item] for item in ITEMS})
        sorted_scores = item_scores_series.sort_values(ascending=False)

        top_items = sorted_scores.head(3)
        bottom_items = sorted_scores.tail(3).sort_values(ascending=True)

        sum_col1, sum_col2 = st.columns(2)

        with sum_col1:
            st.success("##### 🌟 주요 강점 요약")
            strengths_text = ""
            for idx, (it_name, it_score) in enumerate(top_items.items(), 1):
                it_diff = round(it_score - team_avg_by_item[it_name], 1)
                strengths_text += f"**{idx}. {it_name}** — {it_score}점 (팀 평균 대비 {it_diff:+.1f})\n"
            strengths_text += f"\n👉 해당 인원은 **{top_items.index[0]}** 및 **{top_items.index[1]}** 분야에서 상대적으로 우수한 역량을 보여주고 있습니다."
            st.markdown(strengths_text)

        with sum_col2:
            st.info("##### 💡 보완 및 발전 제안")
            weaknesses_text = ""
            for idx, (it_name, it_score) in enumerate(bottom_items.items(), 1):
                it_diff = round(it_score - team_avg_by_item[it_name], 1)
                weaknesses_text += f"**{idx}. {it_name}** — {it_score}점 (팀 평균 대비 {it_diff:+.1f})\n"
            weaknesses_text += f"\n👉 향후 **{bottom_items.index[0]}** 영역을 중심으로 집중적인 직무 교육과 피드백을 통해 역량을 보완할 필요가 있습니다."
            st.markdown(weaknesses_text)

        with st.expander("📊 항목별 점수 상세 비교 (팀 평균 대비)"):
            compare_rows = []
            for item in ITEMS:
                my_score = round(target_info[item], 1)
                team_score = round(team_avg_by_item[item], 1)
                diff = round(my_score - team_score, 1)
                compare_rows.append(
                    {
                        "평가 항목": item,
                        f"{selected_target}": my_score,
                        "전체 평균": team_score,
                        "차이": f"{diff:+.1f}",
                    }
                )
            compare_df = pd.DataFrame(compare_rows)
            compare_html = compare_df.to_html(
                index=False, escape=False, classes="styled-table"
            )
            st.markdown(CUSTOM_STYLE + compare_html, unsafe_allow_html=True)

        st.markdown("---")

        st.download_button(
            label="📥 평가 집계 결과 엑셀(CSV) 다운로드",
            data=download_df.to_csv(index=False).encode("utf-8-sig"),
            file_name="PLC_Software_역량진단_결과.csv",
            mime="text/csv",
        )

# -------------------------------------------------------------------
# TAB 3: 평가자별 / 대상자별 상세 조회
# -------------------------------------------------------------------
with tab3:
    st.subheader("🔍 개별 평가 내역 상세 조회")
    df = load_data()

    filter_col1, filter_col2 = st.columns(2)

    evaluator_list = ["전체"] + EVALUATORS
    target_list = ["전체"] + TARGETS

    default_eval_idx = (
        evaluator_list.index(st.session_state["user_name"])
        if st.session_state["user_name"] in evaluator_list
        else 0
    )

    with filter_col1:
        sel_evaluator = st.selectbox(
            "👤 평가자 필터", evaluator_list, index=default_eval_idx
        )
    with filter_col2:
        sel_target = st.selectbox("🎯 평가 대상자 필터", target_list)

    if sel_evaluator != "전체":
        evaluated_targets = (
            df[df["evaluator"] == sel_evaluator]["target"].tolist()
            if not df.empty
            else []
        )
        not_evaluated_targets = [
            t for t in TARGETS if t not in evaluated_targets
        ]

        st.markdown("---")
        m_col1, m_col2 = st.columns(2)
        m_col1.metric(
            "진행한 평가 건수",
            f"{len(evaluated_targets)} / {len(TARGETS)} 명",
        )
        m_col2.metric("남은 미평가 인원", f"{len(not_evaluated_targets)} 명")

        if not_evaluated_targets:
            with st.expander(
                f"⚠️ [{sel_evaluator}] 평가자가 아직 평가하지 않은 대상자 목록 ({len(not_evaluated_targets)}명)",
                expanded=True,
            ):
                cols_per_row = 4
                for i in range(0, len(not_evaluated_targets), cols_per_row):
                    cols = st.columns(cols_per_row)
                    for j, target_name in enumerate(
                        not_evaluated_targets[i : i + cols_per_row]
                    ):
                        cols[j].write(f"• {target_name}")
        else:
            st.success(
                f"🎉 [{sel_evaluator}] 평가자는 모든 대상자에 대한 평가를 완료했습니다!"
            )
        st.markdown("---")

    if df.empty or len(df) == 0:
        st.info("아직 입력된 평가 데이터가 없습니다.")
    else:
        for item in ITEMS:
            df[item] = pd.to_numeric(df[item], errors="coerce").fillna(0)

        display_df = df.copy()
        display_df.rename(
            columns={"evaluator": "평가자", "target": "평가 대상자"},
            inplace=True,
        )

        # 합산 점수는 100점 만점 기준으로 환산해서 등급을 산정하고 화면에 표시한다.
        display_df["합산 점수"] = (
            display_df[ITEMS].sum(axis=1) * SCORE_NORMALIZE_FACTOR
        ).round(1)
        for item in ITEMS:
            display_df[item] = display_df[item].round(1)

        display_df["_temp_est_grade"] = display_df["합산 점수"].apply(
            calculate_grade
        )
        display_df["_temp_pre_grade"] = display_df["평가 대상자"].apply(
            get_pre_grade
        )

        display_df["기술 평가 등급(역량 본인 평가)"] = display_df.apply(
            lambda r: get_colored_grade_html(
                r["_temp_est_grade"], r["_temp_pre_grade"]
            ),
            axis=1,
        )
        # 엑셀 내보내기용 일반 텍스트 등급 (색상 HTML이 아닌 순수 텍스트)
        display_df["기술 평가 등급(역량 본인 평가) [텍스트]"] = display_df.apply(
            lambda r: f"{r['_temp_est_grade']} ({r['_temp_pre_grade']})", axis=1
        )

        column_order = [
            "평가자",
            "평가 대상자",
            "기술 평가 등급(역량 본인 평가)",
            "합산 점수",
        ] + ITEMS
        export_column_order = [
            "평가자",
            "평가 대상자",
            "기술 평가 등급(역량 본인 평가) [텍스트]",
            "합산 점수",
        ] + ITEMS

        filtered_full_df = display_df.copy()

        if sel_evaluator != "전체":
            filtered_full_df = filtered_full_df[
                filtered_full_df["평가자"] == sel_evaluator
            ]

        if sel_target != "전체":
            filtered_full_df = filtered_full_df[
                filtered_full_df["평가 대상자"] == sel_target
            ]

        # 표 정렬 기준 선택 — 평가자 / 평가 대상자 / 평가등급 중에서 선택
        detail_sort_option = st.radio(
            "📌 **표 정렬 기준 선택**",
            ["평가자순", "평가 대상자순", "평가등급순"],
            horizontal=True,
            key="tab3_sort_option",
        )

        if detail_sort_option == "평가자순":
            # 1차: 평가자 이름순(오름차순), 2차: 합산 점수 높은순(내림차순)
            filtered_full_df = filtered_full_df.sort_values(
                by=["평가자", "합산 점수"],
                ascending=[True, False],
            )
        elif detail_sort_option == "평가 대상자순":
            # 1차: 평가 대상자 이름순(오름차순), 2차: 합산 점수 높은순(내림차순)
            filtered_full_df = filtered_full_df.sort_values(
                by=["평가 대상자", "합산 점수"],
                ascending=[True, False],
            )
        else:
            # 평가등급순: S -> A -> B -> C -> D 순으로 정렬하고,
            # 같은 등급 안에서는 합산 점수 높은순, 그다음 평가자 이름순으로 정렬
            grade_rank_map = {"S": 0, "A": 1, "B": 2, "C": 3, "D": 4}
            filtered_full_df = filtered_full_df.copy()
            filtered_full_df["_grade_rank"] = (
                filtered_full_df["_temp_est_grade"].map(grade_rank_map).fillna(99)
            )
            filtered_full_df = filtered_full_df.sort_values(
                by=["_grade_rank", "합산 점수", "평가자"],
                ascending=[True, False, True],
            )
            filtered_full_df = filtered_full_df.drop(columns=["_grade_rank"])

        filtered_df = filtered_full_df[column_order]

        st.markdown(
            f"**총 {len(filtered_df)}건의 완료된 평가 데이터가 검색되었습니다.**"
        )

        html_filtered_table = filtered_df.to_html(
            index=False, escape=False, classes="styled-table"
        )
        st.markdown(CUSTOM_STYLE + html_filtered_table, unsafe_allow_html=True)

        # -----------------------------------------------------------
        # 📥 엑셀 내보내기 — 현재 조회 중인 상세 평가 기록 + 관련 대상자별
        # 종합 평가 대시보드 요약을 각각 시트(탭)로 묶어서 다운로드
        # -----------------------------------------------------------
        st.markdown("---")
        st.markdown("#### 📥 현재 조회 결과 엑셀로 내보내기")
        st.caption(
            "‘평가상세’ 시트에는 현재 필터로 조회된 평가 기록이, "
            "이후 시트들에는 조회 결과에 포함된 대상자별 종합 평가 대시보드 요약이 각각 담깁니다."
        )

        if filtered_df.empty:
            st.info("내보낼 평가 데이터가 없습니다. 필터 조건을 확인해 주세요.")
        else:
            export_detail_df = filtered_full_df[export_column_order].rename(
                columns={
                    "기술 평가 등급(역량 본인 평가) [텍스트]": "기술 평가 등급(역량 본인 평가)"
                }
            )

            # 조회 결과에 포함된 대상자들의 종합 평가 대시보드(전체 평가자 평균 기준) 요약을 준비
            dashboard_targets_for_export = {}
            all_df_for_dashboard = load_data()
            if (
                not all_df_for_dashboard.empty
                and "target" in all_df_for_dashboard.columns
            ):
                dash_summary_df, _, _ = compute_dashboard_summary(
                    all_df_for_dashboard
                )
                targets_in_view = filtered_full_df["평가 대상자"].unique().tolist()
                for t_name in targets_in_view:
                    t_row_match = dash_summary_df[
                        dash_summary_df["피평가자"] == t_name
                    ]
                    if t_row_match.empty:
                        continue
                    t_row = t_row_match.iloc[0]
                    dashboard_targets_for_export[t_name] = {
                        "평가인원": t_row["평가인원"],
                        "종합 평균점수": t_row["종합 평균점수"],
                        "등급표시": t_row["기술 평가 등급(역량 본인 평가)"],
                        **{it: t_row[it] for it in ITEMS},
                    }
                    # 위 dash_summary_df의 등급 컬럼은 색상 HTML이므로, 엑셀에는
                    # 순수 텍스트 등급으로 대체한다.
                    plain_grade_match = filtered_full_df[
                        filtered_full_df["평가 대상자"] == t_name
                    ]
                    dashboard_targets_for_export[t_name]["등급표시"] = (
                        f"{calculate_grade(t_row['종합 평균점수'])} ({get_pre_grade(t_name)})"
                    )

            excel_bytes = build_evaluation_excel(
                export_detail_df, dashboard_targets_for_export
            )

            st.download_button(
                label="📥 상세 평가 기록 + 대상자별 대시보드 요약 (엑셀) 다운로드",
                data=excel_bytes,
                file_name="PLC_Software_역량진단_상세조회_결과.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )

# -------------------------------------------------------------------
# TAB 4: 관리자 전용 — 평가 데이터 수정 / 삭제 (김남권 계정만 접근 가능)
# -------------------------------------------------------------------
if is_admin:
    with tab4:
        st.subheader("🛠️ 관리자 - 평가 데이터 관리")
        st.caption("이 메뉴는 관리자 계정(김남권)만 접근할 수 있으며, 모든 평가자의 점수를 수정하거나 삭제할 수 있습니다.")

        if st.session_state.get("admin_flash_message"):
            st.success(st.session_state["admin_flash_message"])
            del st.session_state["admin_flash_message"]

        df_admin = load_data()

        if df_admin.empty:
            st.info("아직 입력된 평가 데이터가 없습니다.")
        else:
            for item in ITEMS:
                df_admin[item] = pd.to_numeric(df_admin[item], errors="coerce").fillna(0)
            # 합산 점수는 100점 만점 기준으로 환산해서 표시한다.
            df_admin["합산 점수"] = (
                df_admin[ITEMS].sum(axis=1) * SCORE_NORMALIZE_FACTOR
            ).round(1)

            st.markdown("#### 📋 전체 평가 데이터")

            admin_display_df = df_admin.rename(
                columns={"evaluator": "평가자", "target": "평가 대상자"}
            )
            admin_column_order = ["평가자", "평가 대상자", "합산 점수"] + ITEMS
            admin_display_df = admin_display_df[admin_column_order]
            for item in ITEMS:
                admin_display_df[item] = admin_display_df[item].round(1)

            # ---------------------------------------------------------
            # 🔎 필터 + 검색 — 상세조회(탭3)와 동일한 평가자/대상자 필터에,
            # 이름 일부만 입력해도 찾을 수 있는 검색창을 추가로 제공한다.
            # ---------------------------------------------------------
            admin_filter_col1, admin_filter_col2, admin_filter_col3 = st.columns(3)
            with admin_filter_col1:
                admin_filter_evaluator = st.selectbox(
                    "👤 평가자 필터",
                    ["전체"] + sorted(admin_display_df["평가자"].unique()),
                    key="admin_filter_evaluator",
                )
            with admin_filter_col2:
                admin_filter_target = st.selectbox(
                    "🎯 평가 대상자 필터",
                    ["전체"] + sorted(admin_display_df["평가 대상자"].unique()),
                    key="admin_filter_target",
                )
            with admin_filter_col3:
                admin_search_text = st.text_input(
                    "🔍 이름 검색 (평가자/대상자 일부만 입력해도 검색됩니다)",
                    key="admin_search_text",
                )

            admin_filtered_view_df = admin_display_df.copy()
            if admin_filter_evaluator != "전체":
                admin_filtered_view_df = admin_filtered_view_df[
                    admin_filtered_view_df["평가자"] == admin_filter_evaluator
                ]
            if admin_filter_target != "전체":
                admin_filtered_view_df = admin_filtered_view_df[
                    admin_filtered_view_df["평가 대상자"] == admin_filter_target
                ]
            if admin_search_text.strip():
                _kw = admin_search_text.strip()
                admin_filtered_view_df = admin_filtered_view_df[
                    admin_filtered_view_df["평가자"].str.contains(_kw, case=False, na=False)
                    | admin_filtered_view_df["평가 대상자"].str.contains(_kw, case=False, na=False)
                ]

            st.caption(f"총 {len(admin_filtered_view_df)}건 조회됨 (전체 {len(admin_display_df)}건 중)")

            if admin_filtered_view_df.empty:
                st.info("조건에 맞는 평가 데이터가 없습니다.")
            else:
                admin_html_table = admin_filtered_view_df.to_html(
                    index=False, escape=False, classes="styled-table"
                )
                st.markdown(CUSTOM_STYLE + admin_html_table, unsafe_allow_html=True)

            st.markdown("---")
            st.markdown("#### ✏️ 개별 평가 데이터 수정 / 삭제")

            admin_col1, admin_col2 = st.columns(2)
            with admin_col1:
                admin_evaluator = st.selectbox(
                    "평가자 선택",
                    sorted(df_admin["evaluator"].unique()),
                    key="admin_sel_evaluator",
                )

            admin_target_options = sorted(
                df_admin[df_admin["evaluator"] == admin_evaluator]["target"].unique()
            )
            with admin_col2:
                admin_target = st.selectbox(
                    "평가 대상자 선택",
                    admin_target_options,
                    key="admin_sel_target",
                )

            admin_row_match = df_admin[
                (df_admin["evaluator"] == admin_evaluator)
                & (df_admin["target"] == admin_target)
            ]

            if admin_row_match.empty:
                st.info("선택한 평가자/대상자 조합의 평가 데이터가 없습니다.")
            else:
                admin_row = admin_row_match.iloc[0]
                st.markdown(
                    f"**[{admin_evaluator}] 평가자 → [{admin_target}] 대상자** 평가 데이터 (합산 {admin_row['합산 점수']:.1f}점)"
                )

                admin_scores = {}
                items_per_row = 2
                for i in range(0, len(ITEMS), items_per_row):
                    row_items = ITEMS[i : i + items_per_row]
                    cols = st.columns(items_per_row)
                    for j, item in enumerate(row_items):
                        with cols[j]:
                            try:
                                cur_val = int(admin_row[item])
                            except (ValueError, TypeError):
                                cur_val = 0
                            admin_scores[item] = st.slider(
                                f"{item}",
                                0,
                                10,
                                cur_val,
                                key=f"admin_slide_{admin_evaluator}_{admin_target}_{item}",
                            )

                st.markdown("---")
                admin_btn_col1, admin_btn_col2 = st.columns(2)

                with admin_btn_col1:
                    if st.button(
                        "💾 수정 내용 저장",
                        type="primary",
                        use_container_width=True,
                        key="admin_save_btn",
                    ):
                        try:
                            df_full = load_data()
                            idx = df_full[
                                (df_full["evaluator"] == admin_evaluator)
                                & (df_full["target"] == admin_target)
                            ].index
                            if len(idx) > 0:
                                for key, val in admin_scores.items():
                                    df_full.loc[idx[0], key] = val
                                save_dataframe_to_sheet(df_full)
                                st.session_state["admin_flash_message"] = (
                                    f"[{admin_evaluator}] → [{admin_target}] 평가 데이터가 수정되었습니다."
                                )
                                st.rerun()
                            else:
                                st.warning("해당 데이터를 찾을 수 없습니다. (다른 관리자가 이미 삭제했을 수 있습니다)")
                        except Exception as e:
                            st.error(f"수정 중 오류가 발생했습니다: {e}")

                with admin_btn_col2:
                    admin_confirm_delete = st.checkbox(
                        "⚠️ 삭제를 확인합니다 (되돌릴 수 없습니다)",
                        key=f"admin_confirm_del_{admin_evaluator}_{admin_target}",
                    )
                    if st.button(
                        "🗑️ 해당 평가 삭제",
                        use_container_width=True,
                        key="admin_delete_btn",
                        disabled=not admin_confirm_delete,
                    ):
                        try:
                            df_full = load_data()
                            idx = df_full[
                                (df_full["evaluator"] == admin_evaluator)
                                & (df_full["target"] == admin_target)
                            ].index
                            if len(idx) > 0:
                                df_full = df_full.drop(idx)
                                save_dataframe_to_sheet(df_full)
                                st.session_state["admin_flash_message"] = (
                                    f"[{admin_evaluator}] → [{admin_target}] 평가 데이터가 삭제되었습니다."
                                )
                                st.rerun()
                            else:
                                st.warning("해당 데이터를 찾을 수 없습니다. (다른 관리자가 이미 삭제했을 수 있습니다)")
                        except Exception as e:
                            st.error(f"삭제 중 오류가 발생했습니다: {e}")
