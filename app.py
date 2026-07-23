import extra_streamlit_components as stx
from google.oauth2.service_account import Credentials
import gspread
import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st

# 페이지 기본 설정
st.set_page_config(
    page_title="PLC S/W 역량 진단 평가 시스템",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# -------------------------------------------------------------------
# 🎨 Modern CSS Custom Styling
# -------------------------------------------------------------------
CUSTOM_CSS = """
<style>
    /* 메인 배경 및 기본 폰트 설정 */
    .main {
        background-color: #f8fafc;
        font-family: 'Pretendard', -apple-system, BlinkMacSystemFont, system-ui, Roboto, sans-serif;
    }
    
    /* 카드 디자인 공통 */
    .modern-card {
        background-color: #ffffff;
        border-radius: 12px;
        padding: 20px 24px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05), 0 2px 4px -1px rgba(0, 0, 0, 0.03);
        border: 1px solid #e2e8f0;
        margin-bottom: 20px;
    }
    
    /* 메트릭 카드 디자인 */
    div[data-testid="stMetric"] {
        background-color: #ffffff;
        border-radius: 12px;
        padding: 16px;
        border: 1px solid #e2e8f0;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
        transition: transform 0.2s ease, box-shadow 0.2s ease;
    }
    div[data-testid="stMetric"]:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(0,0,0,0.08);
    }
    div[data-testid="stMetricLabel"] {
        font-size: 0.88rem !important;
        font-weight: 600 !important;
        color: #64748b !important;
    }
    div[data-testid="stMetricValue"] {
        font-size: 1.5rem !important;
        font-weight: 700 !important;
        color: #0f172a !important;
    }

    /* 탭 스타일링 */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        border-bottom: 2px solid #e2e8f0;
    }
    .stTabs [data-baseweb="tab"] {
        height: 48px;
        white-space: pre-wrap;
        border-radius: 8px 8px 0px 0px;
        font-weight: 600;
        color: #64748b;
        padding: 0px 20px;
    }
    .stTabs [aria-selected="true"] {
        color: #2563eb !important;
        background-color: #ffffff !important;
        border-bottom: 2px solid #2563eb !important;
    }

    /* 슬라이더 점수 표시 뱃지 */
    .slider-score-badge {
        display: inline-block;
        background-color: #eff6ff;
        color: #1d4ed8;
        font-weight: 700;
        font-size: 1.1rem;
        padding: 2px 10px;
        border-radius: 6px;
        float: right;
    }

    /* 모던 테이블 스타일 */
    .styled-table {
        width: 100%;
        border-collapse: separate;
        border-spacing: 0;
        margin: 15px 0;
        font-size: 0.92rem;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
        border-radius: 10px;
        overflow: hidden;
        border: 1px solid #e2e8f0;
    }
    .styled-table thead tr {
        background-color: #1e293b;
        color: #f8fafc;
        text-align: center;
        font-weight: 600;
        letter-spacing: 0.5px;
    }
    .styled-table th, .styled-table td {
        padding: 12px 14px;
        text-align: center;
        border-bottom: 1px solid #f1f5f9;
    }
    .styled-table tbody tr {
        background-color: #ffffff;
        transition: background-color 0.15s ease;
    }
    .styled-table tbody tr:nth-of-type(even) {
        background-color: #f8fafc;
    }
    .styled-table tbody tr:hover {
        background-color: #f1f5f9;
    }

    /* 등급 뱃지 스타일 */
    .grade-badge {
        display: inline-block;
        padding: 2px 8px;
        border-radius: 6px;
        font-weight: 700;
        font-size: 0.9rem;
    }
    .grade-S { background-color: #f3e8ff; color: #7e22ce; }
    .grade-A { background-color: #dbeafe; color: #1e40af; }
    .grade-B { background-color: #dcfce7; color: #15803d; }
    .grade-C { background-color: #ffedd5; color: #c2410c; }
    .grade-D { background-color: #fee2e2; color: #b91c1c; }
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

# -------------------------------------------------------------------
# 🍪 쿠키 매니저 설정 (새로고침 시 로그인 상태 유지)
# -------------------------------------------------------------------
cookie_manager = stx.CookieManager()

saved_user = cookie_manager.get(cookie="logged_in_user")

if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False

if saved_user and not st.session_state["logged_in"]:
    st.session_state["logged_in"] = True
    st.session_state["user_name"] = saved_user

ITEMS = ["S/W 분석 및 이해", "발표 자료 완성도", "발표력", "활용도", "S/W 난이도"]
EVALUATORS = ["정준영", "차영진", "김태환", "김남권", "최치웅"]
TARGETS = [
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
]


# -------------------------------------------------------------------
# 📊 사전 역량 진단 데이터 파싱
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
# 🎨 등급별 모던 HTML 뱃지 생성 함수 [평가등급 (사전등급)]
# -------------------------------------------------------------------
def get_colored_grade_html(est_grade, pre_grade):
    e_g = str(est_grade).strip()[0:1]
    p_g = str(pre_grade).strip()[0:1]

    html_str = f'<span class="grade-badge grade-{e_g}">{est_grade}</span> <span style="color:#94a3b8; font-size:0.85rem;">(</span><span class="grade-badge grade-{p_g}">{pre_grade}</span><span style="color:#94a3b8; font-size:0.85rem;">)</span>'
    return html_str


def get_pre_grade(target_full_name):
    if df_comp.empty:
        return "-"
    clean_name = str(target_full_name).split()[0]
    m = df_comp[df_comp["이름"] == clean_name]
    if not m.empty:
        return m.iloc[0]["등급"]
    return "-"


def calculate_grade(avg_score):
    if avg_score >= 9.0:
        return "S"
    elif avg_score >= 8.0:
        return "A"
    elif avg_score >= 7.0:
        return "B"
    elif avg_score >= 6.0:
        return "C"
    else:
        return "D"


# -------------------------------------------------------------------
# 🔐 로그인 화면
# -------------------------------------------------------------------
if not st.session_state["logged_in"]:
    st.markdown("<br><br>", unsafe_allow_html=True)
    c_left, c_mid, c_right = st.columns([1, 1.2, 1])

    with c_mid:
        st.markdown(
            """
            <div class="modern-card" style="text-align: center;">
                <h2 style="margin-bottom: 8px; color: #0f172a;">⚡ PLC S/W 역량 진단 시스템</h2>
                <p style="color: #64748b; font-size: 0.95rem; margin-bottom: 24px;">평가 진행을 위해 접속 권한을 인증해 주세요.</p>
            </div>
        """,
            unsafe_allow_html=True,
        )

        with st.form("login_form"):
            user_name = st.selectbox("👤 평가자(이름) 선택", EVALUATORS)
            input_pw = st.text_input("🔑 비밀번호 입력", type="password")
            submit = st.form_submit_button(
                "시스템 접속", use_container_width=True, type="primary"
            )

            if submit:
                correct_pw = st.secrets.get("common_password", "2026")

                if input_pw == str(correct_pw):
                    st.session_state["logged_in"] = True
                    st.session_state["user_name"] = user_name
                    cookie_manager.set(
                        "logged_in_user", user_name, max_age=86400
                    )
                    st.success(f"반갑습니다, {user_name}님!")
                    st.rerun()
                else:
                    st.error("비밀번호가 올바르지 않습니다.")

    st.stop()

# -------------------------------------------------------------------
# 👤 사이드바
# -------------------------------------------------------------------
st.sidebar.markdown(
    """
    <div style="padding: 10px 0px 20px 0px;">
        <h2 style="font-size: 1.2rem; margin:0; color:#0f172a;">⚡ PLC 역량진단</h2>
        <p style="font-size: 0.8rem; color:#64748b; margin:0;">Software Assessment Platform</p>
    </div>
""",
    unsafe_allow_html=True,
)

st.sidebar.markdown(
    f"""
    <div style="background-color: #f1f5f9; padding: 12px 16px; border-radius: 8px; margin-bottom: 20px;">
        <span style="font-size: 0.8rem; color: #64748b; display: block;">현재 접속자</span>
        <strong style="font-size: 1rem; color: #1e293b;">{st.session_state['user_name']} 님</strong>
    </div>
""",
    unsafe_allow_html=True,
)

if st.sidebar.button("🚪 로그아웃", use_container_width=True):
    st.session_state["logged_in"] = False
    st.session_state["user_name"] = None
    cookie_manager.delete("logged_in_user")
    st.rerun()


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


def load_data():
    try:
        sheet = get_worksheet()
        records = sheet.get_all_records()
        df = pd.DataFrame(records)
        if df.empty:
            df = pd.DataFrame(columns=["evaluator", "target"] + ITEMS)
        return df
    except Exception as e:
        st.error(f"구글 시트 데이터를 불러오는 중 오류가 발생했습니다: {e}")
        return pd.DataFrame(columns=["evaluator", "target"] + ITEMS)


st.markdown(
    "<h2 style='font-weight:700; color:#0f172a; margin-bottom: 20px;'>⚡ PLC S/W 역량 진단 평가 시스템</h2>",
    unsafe_allow_html=True,
)

# 탭 구성
tab1, tab2, tab3 = st.tabs([
    "📝 평가 점수 입력",
    "📊 종합 평가 결과 대시보드",
    "🔍 상세 내역 및 필터 조회",
])

# -------------------------------------------------------------------
# TAB 1: 평가 점수 입력
# -------------------------------------------------------------------
with tab1:
    evaluator = st.session_state["user_name"]

    col1, col2 = st.columns(2)
    with col1:
        st.text_input(
            "평가자", value=f"{evaluator} (본인 인증 완료)", disabled=True
        )
    with col2:
        target = st.selectbox("🎯 평가 대상자 선택", TARGETS)

    # 사전 역량 진단 참고 정보 표출
    if target and not df_comp.empty:
        target_clean_name = target.split()[0]
        match = df_comp[df_comp["이름"] == target_clean_name]

        if not match.empty:
            t_info = match.iloc[0]

            grade_badge = {
                "S": "🟣 S (최우수)",
                "A": "🔵 A (우수)",
                "B": "🟢 B (숙련)",
                "C": "🟡 C (보통)",
                "D": "🔴 D (기초)",
            }.get(t_info["등급"], f"{t_info['등급']} 등급")

            st.markdown(
                f"""
                <div class="modern-card" style="margin-top: 15px;">
                    <h4 style="margin-top:0; color:#1e293b; font-size:1.05rem;">💡 [{target}] 님의 사전 역량 진단 현황</h4>
                </div>
            """,
                unsafe_allow_html=True,
            )

            m1, m2, m3, m4, m5 = st.columns(5)
            m1.metric("사전 진단 등급", grade_badge)
            m2.metric(
                "L3 (전문가)", f"{t_info['L3_cnt']}건", f"{t_info['L3_pct']}%"
            )
            m3.metric(
                "L2 (우수/숙련)",
                f"{t_info['L2_cnt']}건",
                f"{t_info['L2_pct']}%",
            )
            m4.metric(
                "L1 (보통/실무)",
                f"{t_info['L1_cnt']}건",
                f"{t_info['L1_pct']}%",
            )
            m5.metric(
                "L0 (기초/미흡)",
                f"{t_info['L0_cnt']}건",
                f"{t_info['L0_pct']}%",
                delta_color="inverse",
            )

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("##### 📌 항목별 역량 점수 부여 (0점 ~ 10점)")

    scores = {}
    cols = st.columns(len(ITEMS))
    for i, item in enumerate(ITEMS):
        with cols[i]:
            val = st.slider(f"{item}", 0, 10, 5, key=f"slide_{item}")
            scores[item] = val

    st.markdown("<br>", unsafe_allow_html=True)
    if st.button(
        "💾 평가 점수 제출하기", type="primary", use_container_width=True
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
                df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)

            sheet = get_worksheet()
            sheet.clear()
            sheet.update([df.columns.values.tolist()] + df.values.tolist())

            st.success(
                f"[{evaluator}] 평가자의 [{target}] 대상자에 대한 평가가 성공적으로 저장되었습니다!"
            )
        except Exception as e:
            st.error(f"저장 중 오류가 발생했습니다: {e}")

# -------------------------------------------------------------------
# TAB 2: 종합 평가 결과 대시보드
# -------------------------------------------------------------------
with tab2:
    df = load_data()

    if df.empty or len(df) == 0:
        st.info("아직 입력된 평가 데이터가 없습니다.")
    else:
        for item in ITEMS:
            df[item] = pd.to_numeric(df[item], errors="coerce").fillna(0)

        summary_list = []
        raw_grades_list = []
        download_list = []

        for target_person in df["target"].unique():
            sub_df = df[df["target"] == target_person]
            eval_count = len(sub_df)
            item_means = sub_df[ITEMS].mean()
            total_avg = item_means.mean()

            est_grade = calculate_grade(total_avg)
            pre_grade = get_pre_grade(target_person)
            raw_grades_list.append(est_grade)

            colored_grade_html = get_colored_grade_html(est_grade, pre_grade)

            row = {
                "피평가자": target_person,
                "평가인원": eval_count,
                "종합 평균점수": round(total_avg, 1),
                "기술 평가 등급(사전)": colored_grade_html,
            }
            row_dl = {
                "피평가자": target_person,
                "평가인원": eval_count,
                "종합 평균점수": round(total_avg, 1),
                "기술 평가 등급(사전)": f"{est_grade} ({pre_grade})",
            }

            for item in ITEMS:
                score_val = round(item_means[item], 1)
                row[item] = score_val
                row_dl[item] = score_val

            summary_list.append(row)
            download_list.append(row_dl)

        summary_df = pd.DataFrame(summary_list)
        download_df = pd.DataFrame(download_list)

        st.markdown(
            "#### 📊 대상자별 종합 평가 요약", unsafe_allow_html=True
        )
        html_table = summary_df.to_html(
            index=False, escape=False, classes="styled-table"
        )
        st.markdown(html_table, unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("#### 🏆 등급 분포 현황")
        grade_series = pd.Series(raw_grades_list)
        grade_counts = grade_series.value_counts().reindex(
            ["S", "A", "B", "C", "D"], fill_value=0
        )

        c1, c2, c3, c4, c5 = st.columns(5)
        for i, g in enumerate(["S", "A", "B", "C", "D"]):
            eval(f"c{i+1}").metric(f"{g} 등급 인원", f"{grade_counts[g]} 명")

        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("#### 📈 피평가자 역량 밸런스 방사형 차트")
        selected_target = st.selectbox(
            "분석할 피평가자 선택", summary_df["피평가자"].unique()
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
        fig.update_traces(
            fill="toself",
            fillcolor="rgba(37, 99, 235, 0.2)",
            line_color="#2563eb",
            line_width=2,
        )
        fig.update_layout(
            polar=dict(
                radialaxis=dict(visible=True, range=[0, 10], gridcolor="#e2e8f0"),
                angularaxis=dict(gridcolor="#e2e8f0"),
            ),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            margin=dict(l=40, r=40, t=30, b=30),
        )
        st.plotly_chart(fig, use_container_width=True)

        st.download_button(
            label="📥 평가 결과 CSV 다운로드",
            data=download_df.to_csv(index=False).encode("utf-8-sig"),
            file_name="PLC_Software_역량진단_결과.csv",
            mime="text/csv",
        )

# -------------------------------------------------------------------
# TAB 3: 평가자별 / 대상자별 상세 조회
# -------------------------------------------------------------------
with tab3:
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

        st.markdown("<br>", unsafe_allow_html=True)
        m_col1, m_col2 = st.columns(2)
        m_col1.metric(
            "평가 완료 건수", f"{len(evaluated_targets)} / {len(TARGETS)} 명"
        )
        m_col2.metric("남은 미평가 인원", f"{len(not_evaluated_targets)} 명")

        if not_evaluated_targets:
            with st.expander(
                f"⚠️ [{sel_evaluator}] 평가자 미완료 대상자 목록 ({len(not_evaluated_targets)}명)",
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

    st.markdown("<br>", unsafe_allow_html=True)
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

        display_df["평균 점수"] = display_df[ITEMS].mean(axis=1).round(1)
        for item in ITEMS:
            display_df[item] = display_df[item].round(1)

        display_df["_temp_est_grade"] = display_df["평균 점수"].apply(
            calculate_grade
        )
        display_df["_temp_pre_grade"] = display_df["평가 대상자"].apply(
            get_pre_grade
        )

        display_df["기술 평가 등급(사전)"] = display_df.apply(
            lambda r: get_colored_grade_html(
                r["_temp_est_grade"], r["_temp_pre_grade"]
            ),
            axis=1,
        )

        column_order = (
            ["평가자", "평가 대상자", "기술 평가 등급(사전)", "평균 점수"]
            + ITEMS
        )
        display_df = display_df[column_order]

        filtered_df = display_df.copy()

        if sel_evaluator != "전체":
            filtered_df = filtered_df[filtered_df["평가자"] == sel_evaluator]

        if sel_target != "전체":
            filtered_df = filtered_df[filtered_df["평가 대상자"] == sel_target]

        st.markdown(
            f"**검색 결과: 총 {len(filtered_df)}건의 평가 데이터**"
        )

        html_filtered_table = filtered_df.to_html(
            index=False, escape=False, classes="styled-table"
        )
        st.markdown(html_filtered_table, unsafe_allow_html=True)
