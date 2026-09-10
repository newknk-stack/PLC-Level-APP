import time
from io import BytesIO

import extra_streamlit_components as stx
from google.oauth2.service_account import Credentials
import gspread
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# 페이지 기본 설정
st.set_page_config(page_title="PLC S/W 역량 진단 평가 툴", layout="wide")

# -------------------------------------------------------------------
# 🎨 탭, 테이블 및 버튼 디자인 커스텀 CSS (더 연하고 은은한 소프트 블루 톤 적용)
# -------------------------------------------------------------------
CUSTOM_STYLE = """
<style>
    /* 탭 네비게이션 컨테이너 */
    .stTabs [data-baseweb="tab-list"] {
        gap: 10px;
        background-color: #F8FAFC;
        padding: 10px 14px;
        border-radius: 14px;
        border: 1px solid #E2E8F0;
    }
    
    /* 각 탭 버튼 기본 스타일 (부드러운 라운드 & 차분한 글자색) */
    .stTabs [data-baseweb="tab"] {
        height: 46px;
        white-space: pre-wrap;
        background-color: #FFFFFF;
        border-radius: 10px;
        gap: 8px;
        padding: 0px 22px;
        font-size: 0.95rem;
        font-weight: 600;
        color: #64748B;
        border: 1px solid #E2E8F0;
        transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
    }

    /* 탭 마우스 호버 시 */
    .stTabs [data-baseweb="tab"]:hover {
        background-color: #F1F5F9;
        color: #334155;
        border-color: #CBD5E1;
    }

    /* 선택된 활성 탭 스타일 (눈이 편안한 은은한 소프트 파스텔 블루 톤) */
    .stTabs [aria-selected="true"] {
        background: linear-gradient(135deg, #EFF6FF 0%, #DBEAFE 100%) !important;
        color: #1E40AF !important;
        border-color: #BFDBFE !important;
        border-radius: 10px !important;
        box-shadow: 0 2px 8px rgba(59, 130, 246, 0.12);
    }
    
    /* 스트림릿 기본 하단 인디케이터 제거 */
    .stTabs [data-baseweb="tab-highlight"] {
        display: none !important;
    }

    /* 🎨 스트림릿 primary 버튼 스타일을 훨씬 더 옅고 부드러운 하늘색(Light Sky Blue)으로 커스텀 */
    div.stButton > button[kind="primary"] {
        background: linear-gradient(135deg, #E0F2FE 0%, #BAE6FD 100%) !important;
        color: #0369A1 !important;
        border: 1px solid #7DD3FC !important;
        border-radius: 10px !important;
        box-shadow: 0 2px 6px rgba(125, 211, 252, 0.25);
        transition: all 0.2s ease-in-out;
    }
    div.stButton > button[kind="primary"]:hover {
        background: linear-gradient(135deg, #BAE6FD 0%, #7DD3FC 100%) !important;
        color: #0C4A6E !important;
        border-color: #38BDF8 !important;
        box-shadow: 0 4px 10px rgba(56, 189, 248, 0.35);
    }

    /* 기존 테이블 스타일 */
    .styled-table {
        width: 100%;
        border-collapse: collapse;
        margin: 10px 0;
        font-size: 0.85rem;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05), 0 2px 4px -1px rgba(0, 0, 0, 0.03);
        border-radius: 8px;
        overflow: hidden;
        border: 1px solid #E2E8F0;
    }
    .styled-table thead tr {
        background-color: #1E293B;
        color: #FFFFFF;
        text-align: center;
        font-weight: 600;
        white-space: normal;
        word-break: keep-all;
        line-height: 1.3;
    }
    .styled-table th {
        padding: 10px 8px;
        text-align: center;
        border-right: 1px solid #334155;
    }
    .styled-table th:last-child {
        border-right: none;
    }
    .styled-table td {
        padding: 8px 10px;
        text-align: center;
        border-bottom: 1px solid #E2E8F0;
        color: #334155;
        white-space: nowrap;
    }
    .styled-table tbody tr:nth-of-type(even) {
        background-color: #F8FAFC;
    }
    .styled-table tbody tr:hover {
        background-color: #EEF2FF;
    }
</style>
"""

st.markdown(CUSTOM_STYLE, unsafe_allow_html=True)

# -------------------------------------------------------------------
# 🍪 쿠키 매니저 및 로그인 세션 제어
# -------------------------------------------------------------------
cookie_manager = stx.CookieManager(key="cookie_manager")

if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False
if "user_name" not in st.session_state:
    st.session_state["user_name"] = None
if "logout_triggered" not in st.session_state:
    st.session_state["logout_triggered"] = False

# 쿠키에서 로그인 정보 복원
if not st.session_state["logged_in"] and not st.session_state["logout_triggered"]:
    saved_user = cookie_manager.get("logged_in_user")
    if saved_user:
        st.session_state["logged_in"] = True
        st.session_state["user_name"] = saved_user

# 평가 항목 (10선) 및 평가자/대상자 기본 정의
ITEMS = [
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
    """10개 항목 합산 점수(100점 만점) 기준 등급 산정"""
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
        total_score = item_means.sum()

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
# 🔐 로그인 화면
# -------------------------------------------------------------------
if not st.session_state["logged_in"]:
    col_l_title, col_l_logo = st.columns([3.5, 2.5])
    with col_l_title:
        st.markdown(
            '<p style="color: #64748B; font-size: 1.25rem; font-weight: 600; margin-bottom: 2px;">물류자동화그룹 / 공항사업섹션 / T1 T2 BHS운영</p>',
            unsafe_allow_html=True,
        )
        st.markdown(
            '<h1 style="font-size: 2.7rem; font-weight: 800; padding-top: 0px; margin-top: 0px;">🔐 PLC S/W 역량 진단 평가 시스템</h1>',
            unsafe_allow_html=True,
        )
    with col_l_logo:
        st.markdown(
            '<div style="display: flex; flex-direction: column; align-items: flex-end; justify-content: center; height: 100%; padding-top: 5px;">'
            '<span style="font-size: 1.7rem; font-weight: 900; font-family: sans-serif; letter-spacing: 1px; color: #111; line-height: 1.1;">posco</span>'
            '<span style="font-size: 2.2rem; font-weight: 900; font-family: sans-serif; letter-spacing: -0.5px; color: #111; line-height: 1.2;">포스코<span style="color: #0056B3;">DX</span></span>'
            '<span style="font-size: 1.1rem; font-weight: 700; font-family: sans-serif; letter-spacing: 0.5px;"><span style="color: #C68A00;">AI</span> <span style="color: #555;">Native Company</span></span>'
            '</div>',
            unsafe_allow_html=True,
        )

    st.write("시스템에 접속하려면 본인 이름 선택 및 공동 비밀번호를 입력해 주세요.")

    with st.form("login_form"):
        user_name = st.selectbox("👤 평가자(이름) 선택", EVALUATORS)
        input_pw = st.text_input("🔑 공동 비밀번호 입력", type="password")
        submit = st.form_submit_button("로그인", type="primary")

        if submit:
            correct_pw = st.secrets.get("common_password", "2026")

            if input_pw == str(correct_pw):
                st.session_state["logged_in"] = True
                st.session_state["user_name"] = user_name
                st.session_state["logout_triggered"] = False

                cookie_manager.set("logged_in_user", user_name, max_age=86400)

                st.success(f"반갑습니다, {user_name}님! 시스템에 접속합니다.")
                time.sleep(0.3)
                st.rerun()
            else:
                st.error("비밀번호가 올바르지 않습니다. 다시 확인해 주세요.")

    st.stop()


# -------------------------------------------------------------------
# 👤 사이드바
# -------------------------------------------------------------------
st.sidebar.markdown(f"### 👤 **접속자 정보**")
st.sidebar.info(f"현재 접속자: **{st.session_state['user_name']}** 님")

if st.sidebar.button("🚪 로그아웃", type="secondary"):
    st.session_state["logged_in"] = False
    st.session_state["user_name"] = None
    st.session_state["logout_triggered"] = True

    cookie_manager.delete("logged_in_user")
    st.rerun()

col_title, col_logo = st.columns([3.5, 2.5])
with col_title:
    st.markdown(
        '<p style="color: #64748B; font-size: 1.25rem; font-weight: 600; margin-bottom: 2px;">물류자동화그룹 / 공항사업섹션 / T1 T2 BHS운영</p>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<h1 style="font-size: 2.7rem; font-weight: 800; padding-top: 0px; margin-top: 0px;">⚡ PLC S/W 역량 진단 평가 시스템</h1>',
        unsafe_allow_html=True,
    )
with col_logo:
    st.markdown(
        '<div style="display: flex; flex-direction: column; align-items: flex-end; justify-content: center; height: 100%; padding-top: 5px;">'
        '<span style="font-size: 1.7rem; font-weight: 900; font-family: sans-serif; letter-spacing: 1px; color: #111; line-height: 1.1;">posco</span>'
        '<span style="font-size: 2.2rem; font-weight: 900; font-family: sans-serif; letter-spacing: -0.5px; color: #111; line-height: 1.2;">포스코<span style="color: #0056B3;">DX</span></span>'
        '<span style="font-size: 1.1rem; font-weight: 700; font-family: sans-serif; letter-spacing: 0.5px;"><span style="color: #C68A00;">AI</span> <span style="color: #555;">Native Company</span></span>'
        '</div>',
        unsafe_allow_html=True,
    )


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


# -------------------------------------------------------------------
# 🛡️ 관리자 계정 설정 (평가 데이터 삭제/수정 권한)
# -------------------------------------------------------------------
ADMIN_USERS = ["김남권"]
is_admin = st.session_state.get("user_name") in ADMIN_USERS


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
            st.markdown("---")

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

            raw_levels = [
                ("Level 3", l3_p, "#5C5470", "white"),
                ("Level 2", l2_p, "#7C83FD", "white"),
                ("Level 1", l1_p, "#70A288", "white"),
                ("Level 0", l0_p, "#D9B48F", "#333333"),
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

    st.markdown("---")
    if target in completed_targets:
        st.write("각 항목별 점수를 입력하세요 (0점 ~ 10점) — ✅ 이미 제출한 평가이며, 아래에 기존 점수가 표시됩니다. 수정 후 다시 저장할 수 있습니다.")
    else:
        st.write("각 항목별 점수를 입력하세요 (0점 ~ 10점)")

    # 이미 평가를 완료한 대상자를 다시 선택하면 기존에 저장된 점수를 슬라이더 기본값으로 표시한다.
    existing_row = completed_rows_by_target.get(target)

    scores = {}

    items_per_row = 2
    for i in range(0, len(ITEMS), items_per_row):
        row_items = ITEMS[i : i + items_per_row]
        cols = st.columns(len(row_items))
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

    current_total_score = float(np.sum(list(scores.values()))) if scores else 0.0
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
            <div style="background-color: #f8f9fa; padding: 10px 12px; border-radius: 6px; border: 1px solid #e0e0e0; text-align: center; height: 100%; min-height: 72px; display: flex; align-items: center; justify-content: center;">
                <div style="white-space: nowrap;">
                    <span style="font-size: 0.95rem; color: #555; margin-right: 8px;">기술평가 등급(역량 본인 평가):</span>
                    <span style="font-size: 1.2rem;">{colored_grade_display}</span>
                    <span style="font-size: 0.9rem; color: #888; margin-left: 4px;">(합계 {current_total_score:.1f}점)</span>
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

        radar_df = pd.DataFrame(
            {"항목": ITEMS, "점수": [target_info[item] for item in ITEMS]}
        )

        fig = px.line_polar(
            radar_df, r="점수", theta="항목", line_close=True, range_r=[0, 10]
        )
        fig.update_traces(fill="toself")
        st.plotly_chart(fig, use_container_width=True)

        # -------------------------------------------------------------------
        # 💡 평가 기반 장점 및 보완점 자동 요약 표출 영역
        # -------------------------------------------------------------------
        st.markdown("---")
        st.markdown(f"#### 📝 **[{selected_target}] 역량 진단 요약 리포트**")

        item_scores_series = pd.Series({item: target_info[item] for item in ITEMS})
        sorted_scores = item_scores_series.sort_values(ascending=False)

        top_items = sorted_scores.head(3)
        bottom_items = sorted_scores.tail(3).sort_values(ascending=True)

        sum_col1, sum_col2 = st.columns(2)

        with sum_col1:
            st.success("##### 🌟 주요 강점 요약")
            strengths_text = ""
            for idx, (it_name, it_score) in enumerate(top_items.items(), 1):
                strengths_text += f"**{idx}. {it_name}** ({it_score}점)\n"
            strengths_text += f"\n👉 해당 인원은 **{top_items.index[0]}** 및 **{top_items.index[1]}** 분야에서 상대적으로 우수한 역량을 보여주고 있습니다."
            st.markdown(strengths_text)

        with sum_col2:
            st.info("##### 💡 보완 및 발전 제안")
            weaknesses_text = ""
            for idx, (it_name, it_score) in enumerate(bottom_items.items(), 1):
                weaknesses_text += f"**{idx}. {it_name}** ({it_score}점)\n"
            weaknesses_text += f"\n👉 향후 **{bottom_items.index[0]}** 영역을 중심으로 집중적인 직무 교육과 피드백을 통해 역량을 보완할 필요가 있습니다."
            st.markdown(weaknesses_text)

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

        display_df["합산 점수"] = display_df[ITEMS].sum(axis=1).round(1)
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

        # 📌 1차: 평가자 이름순(오름차순), 2차: 합산 점수 높은순(내림차순) 정렬 적용
        filtered_full_df = filtered_full_df.sort_values(
            by=["평가자", "합산 점수"],
            ascending=[True, False],
        )

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
            df_admin["합산 점수"] = df_admin[ITEMS].sum(axis=1).round(1)

            st.markdown("#### 📋 전체 평가 데이터")
            st.dataframe(
                df_admin.rename(columns={"evaluator": "평가자", "target": "평가 대상자"}),
                use_container_width=True,
                hide_index=True,
            )

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
                    cols = st.columns(len(row_items))
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
