import time
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
# 🍪 쿠키 매니저 및 로그인 세션 제어
# -------------------------------------------------------------------
cookie_manager = stx.CookieManager()

# 세션 상태 초기화
if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False
if "logout_triggered" not in st.session_state:
    st.session_state["logout_triggered"] = False

# 브라우저 쿠키 확인
saved_user = cookie_manager.get(cookie="logged_in_user")

# 🔥 핵심: 로그아웃을 방금 누른 게 아닐 때만 쿠키로 자동 로그인 수행
if (
    saved_user
    and not st.session_state["logged_in"]
    and not st.session_state["logout_triggered"]
):
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

EVALUATORS = ["정준영", "차영진", "김태환", "김남권", "최치웅"]

# 가나다순 정렬된 평가 대상자 목록
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
# 📊 2026년 상반기 역량 진단 데이터 파싱 함수 (Level 0 ~ Level 3 포함)
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
# 🎨 등급별 개별 HTML 색상 생성 함수 [평가등급 (사전등급)]
# -------------------------------------------------------------------
def get_colored_grade_html(est_grade, pre_grade):
    color_map = {
        "S": "#8E44AD",  # 보라색
        "A": "#2980B9",  # 파란색
        "B": "#27AE60",  # 초록색
        "C": "#D35400",  # 주황색
        "D": "#C0392B",  # 빨간색
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


# HTML 테이블 렌더링용 스타일
TABLE_STYLE = """
<style>
    .styled-table {
        width: 100%;
        border-collapse: collapse;
        margin: 15px 0;
        font-size: 0.95rem;
        font-family: sans-serif;
        box-shadow: 0 0 10px rgba(0, 0, 0, 0.05);
        border-radius: 5px;
        overflow: hidden;
    }
    .styled-table thead tr {
        background-color: #0E1117;
        color: #ffffff;
        text-align: center;
        font-weight: bold;
    }
    .styled-table th, .styled-table td {
        padding: 10px 12px;
        text-align: center;
        border-bottom: 1px solid #dddddd;
    }
    .styled-table tbody tr:nth-of-type(even) {
        background-color: #f8f9fa;
    }
    .styled-table tbody tr:hover {
        background-color: #f1f3f5;
    }
</style>
"""

# -------------------------------------------------------------------
# 🔐 로그인 화면
# -------------------------------------------------------------------
if not st.session_state["logged_in"]:
    st.title("🔐 PLC S/W 역량 진단 평가 시스템")
    st.write("시스템에 접속하려면 본인 이름 선택 및 공동 비밀번호를 입력해 주세요.")

    with st.form("login_form"):
        user_name = st.selectbox("👤 평가자(이름) 선택", EVALUATORS)
        input_pw = st.text_input("🔑 공동 비밀번호 입력", type="password")
        submit = st.form_submit_button("로그인")

        if submit:
            correct_pw = st.secrets.get("common_password", "2026")

            if input_pw == str(correct_pw):
                st.session_state["logged_in"] = True
                st.session_state["user_name"] = user_name
                st.session_state[
                    "logout_triggered"
                ] = False  # 로그인 성공 시 로그아웃 플래그 초기화

                # 쿠키에 1일(86400초) 간 저장
                cookie_manager.set("logged_in_user", user_name, max_age=86400)

                st.success(f"반갑습니다, {user_name}님! 시스템에 접속합니다.")
                time.sleep(0.3)
                st.rerun()
            else:
                st.error("비밀번호가 올바르지 않습니다. 다시 확인해 주세요.")

    st.stop()

# -------------------------------------------------------------------
# 👤 사이드바 (로그아웃 처리)
# -------------------------------------------------------------------
st.sidebar.markdown(f"### 👤 **접속자 정보**")
st.sidebar.info(f"현재 접속자: **{st.session_state['user_name']}** 님")

if st.sidebar.button("🚪 로그아웃", type="secondary"):
    # 1. 세션 상태 즉시 초기화 + 로그아웃 플래그 설정
    st.session_state["logged_in"] = False
    st.session_state["user_name"] = None
    st.session_state["logout_triggered"] = True

    # 2. 브라우저 쿠키 삭제
    cookie_manager.delete("logged_in_user")

    # 3. 즉시 새로고침하여 로그인 화면으로 이동
    st.rerun()

st.title("⚡ PLC S/W 역량 진단 평가 시스템")


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
        else:
            for item in ITEMS:
                if item not in df.columns:
                    df[item] = 0
        return df
    except Exception as e:
        st.error(f"구글 시트 데이터를 불러오는 중 오류가 발생했습니다: {e}")
        return pd.DataFrame(columns=["evaluator", "target"] + ITEMS)


# 탭 구성
tab1, tab2, tab3 = st.tabs([
    "📝 평가 입력",
    "📊 종합 평가 결과 대시보드",
    "🔍 평가자별/대상자별 상세 조회",
])

# -------------------------------------------------------------------
# TAB 1: 평가 점수 입력
# -------------------------------------------------------------------
with tab1:
    st.subheader("평가 점수 제출")

    evaluator = st.session_state["user_name"]

    col1, col2 = st.columns(2)
    with col1:
        st.text_input(
            "평가자", value=f"{evaluator} (본인 로그인 완료)", disabled=True
        )
    with col2:
        target = st.selectbox("평가 대상자 선택", TARGETS)

    # 사전 역량 진단 참고 정보 표출
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
                f"##### 💡 **[{target}]** 님의 사전 역량 진단 참고 현황"
            )

            m1, m2, m3, m4, m5 = st.columns(5)
            m1.metric("사전 진단 등급", grade_badge)
            m2.metric(
                "Level 3 (난이도 최상 S/W 이해 건수)",
                f"{t_info['L3_cnt']}건",
                f"{t_info['L3_pct']}%",
            )
            m3.metric(
                "Level 2 (난이도 상 S/W 이해 건수)",
                f"{t_info['L2_cnt']}건",
                f"{t_info['L2_pct']}%",
            )
            m4.metric(
                "Level 1 (난이도 중 S/W 이해 건수)",
                f"{t_info['L1_cnt']}건",
                f"{t_info['L1_pct']}%",
            )
            m5.metric(
                "Level 0 (난이도 하 S/W 이해 건수)",
                f"{t_info['L0_cnt']}건",
                f"{t_info['L0_pct']}%",
                delta_color="inverse",
            )

            # 역량 수준별 비중 값
            l0_p = t_info["L0_pct"]
            l1_p = t_info["L1_pct"]
            l2_p = t_info["L2_pct"]
            l3_p = t_info["L3_pct"]

            st.caption("역량 수준별 분포 현황")

            # ✨ [개선] Plotly를 이용한 100% 분할 플랫 막대 차트 (깨짐 현상 완벽 방지)
            levels = [
                ("L0", l0_p, "#00A859", "white"),
                ("L1", l1_p, "#FFEE00", "#222222"),
                ("L2", l2_p, "#702F98", "white"),
                ("L3", l3_p, "#00A3E0", "white"),
            ]

            fig_bar = go.Figure()

            for lbl, val, color, text_color in levels:
                if val > 0:  # 0%인 항목은 깔끔하게 표시 제외
                    text_str = (
                        f"<b>{lbl} ({val}%)</b>" if val >= 5.0 else f"{val}%"
                    )
                    fig_bar.add_trace(
                        go.Bar(
                            y=["분포"],
                            x=[val],
                            name=lbl,
                            orientation="h",
                            marker=dict(color=color),
                            text=text_str,
                            textposition="inside",
                            textfont=dict(
                                color=text_color, size=13, family="sans-serif"
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

            # ✨ 기존 형식 텍스트 라벨 유지
            st.caption(
                f"L3(최상): {l3_p}% | L2(상): {l2_p}% | L1(중): {l1_p}% | L0(하): {l0_p}%"
            )

    st.markdown("---")
    st.write("각 항목별 점수를 입력하세요 (0점 ~ 10점)")

    scores = {}

    # 항목 슬라이더 배치 (2열 구조)
    items_per_row = 2
    for i in range(0, len(ITEMS), items_per_row):
        row_items = ITEMS[i : i + items_per_row]
        cols = st.columns(len(row_items))
        for j, item in enumerate(row_items):
            with cols[j]:
                scores[item] = st.slider(
                    f"{item}", 0, 10, 5, key=f"slide_{item}"
                )

    st.markdown("---")

    # 제출 버튼 영역 (현재 입력 점수 기준 기술평가 등급 표출)
    current_avg = np.mean(list(scores.values())) if scores else 0.0
    current_est_grade = calculate_grade(current_avg)
    current_pre_grade = get_pre_grade(target)
    colored_grade_display = get_colored_grade_html(
        current_est_grade, current_pre_grade
    )

    btn_col1, btn_col2 = st.columns([1, 2])

    with btn_col1:
        st.markdown(
            f"""
            <div style="background-color: #f8f9fa; padding: 8px 12px; border-radius: 6px; border: 1px solid #e0e0e0; text-align: center;">
                <span style="font-size: 0.9rem; color: #555;">기술평가 등급(사전):</span><br>
                <span style="font-size: 1.2rem;">{colored_grade_display}</span>
                <span style="font-size: 0.85rem; color: #888;"> (평균 {current_avg:.1f}점)</span>
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
    st.subheader("종합 평가 현황")
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

        html_table = summary_df.to_html(
            index=False, escape=False, classes="styled-table"
        )
        st.markdown(TABLE_STYLE + html_table, unsafe_allow_html=True)

        st.markdown("### 🏆 등급 현황 통계")
        grade_series = pd.Series(raw_grades_list)
        grade_counts = grade_series.value_counts().reindex(
            ["S", "A", "B", "C", "D"], fill_value=0
        )

        c1, c2, c3, c4, c5 = st.columns(5)
        for i, g in enumerate(["S", "A", "B", "C", "D"]):
            eval(f"c{i+1}").metric(f"{g} 등급", f"{grade_counts[g]} 명")

        st.markdown("### 📈 피평가자별 역량 방사형 차트")
        selected_target = st.selectbox(
            "분석할 대상자 선택", summary_df["피평가자"].unique()
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

        column_order = [
            "평가자",
            "평가 대상자",
            "기술 평가 등급(사전)",
            "평균 점수",
        ] + ITEMS
        display_df = display_df[column_order]

        filtered_df = display_df.copy()

        if sel_evaluator != "전체":
            filtered_df = filtered_df[filtered_df["평가자"] == sel_evaluator]

        if sel_target != "전체":
            filtered_df = filtered_df[filtered_df["평가 대상자"] == sel_target]

        st.markdown(
            f"**총 {len(filtered_df)}건의 완료된 평가 데이터가 검색되었습니다.**"
        )

        html_filtered_table = filtered_df.to_html(
            index=False, escape=False, classes="styled-table"
        )
        st.markdown(TABLE_STYLE + html_filtered_table, unsafe_allow_html=True)
