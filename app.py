import pandas as pd
import plotly.express as px
import streamlit as st
import gspread
from google.oauth2.service_account import Credentials

# 평가 항목 및 기본 정보 정의
ITEMS = ["S/W 분석 및 이해", "발표 자료 완성도", "발표력", "활용도", "S/W 난이도"]
EVALUATORS = ["정준영", "차영진", "김태환", "김남권", "최치웅"]
TARGETS = [
    "박상규", "이영표", "이윤열", "임성민", "김용남", "왕종표", "이동민", 
    "이준식", "이진호", "길지훈", "이창배", "채경용", "하운기", "박광윤", 
    "안상윤", "오성균", "이동준", "임채환", "권준성", "서창성", "유승우", 
    "이도윤", "박시후", "손병효", "이준혁", "장정윤", "한정훈"
]

# 페이지 기본 설정
st.set_page_config(page_title="PLC S/W 역량 진단 평가 툴", layout="wide")

# -------------------------------------------------------------------
# 🔐 공동 로그인 로직
# -------------------------------------------------------------------
if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False

if not st.session_state["logged_in"]:
    st.title("🔐 PLC S/W 역량 진단 평가 시스템")
    st.write("시스템에 접속하려면 본인 이름 선택 및 공동 비밀번호를 입력해 주세요.")

    with st.form("login_form"):
        user_name = st.selectbox("👤 평가자(이름) 선택", EVALUATORS)
        input_pw = st.text_input("🔑 공동 비밀번호 입력", type="password")
        submit = st.form_submit_button("로그인")

        if submit:
            # Secrets에서 공동 비밀번호 가져오기
            correct_pw = st.secrets.get("common_password", "2026")  # 기본값 1234
            
            if input_pw == str(correct_pw):
                st.session_state["logged_in"] = True
                st.session_state["user_name"] = user_name
                st.success(f"반갑습니다, {user_name}님! 시스템에 접속합니다.")
                st.rerun()
            else:
                st.error("비밀번호가 올바르지 않습니다. 다시 확인해 주세요.")

    st.stop()  # 로그인되지 않은 경우 아래 코드를 실행하지 않음

# -------------------------------------------------------------------
# 👤 사이드바 (접속자 정보 및 로그아웃)
# -------------------------------------------------------------------
st.sidebar.markdown(f"### 👤 **접속자 정보**")
st.sidebar.info(f"현재 접속자: **{st.session_state['user_name']}** 님")

if st.sidebar.button("🚪 로그아웃", type="secondary"):
    st.session_state["logged_in"] = False
    st.session_state["user_name"] = None
    st.rerun()

st.title("⚡ PLC S/W 역량 진단 평가 시스템")

# -------------------------------------------------------------------
# 구글 시트 연동 설정 (gspread + google.oauth2)
# -------------------------------------------------------------------
@st.cache_resource
def get_gspread_client():
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    creds_dict = dict(st.secrets["gcp_service_account"])
    
    if "\\n" in creds_dict["private_key"]:
        creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n")
        
    creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
    client = gspread.authorize(creds)
    return client

def get_worksheet():
    client = get_gspread_client()
    sheet_url = st.secrets["private_gsheets_url"]
    sheet = client.open_by_url(sheet_url).sheet1
    return sheet

# 데이터 불러오기 함수
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

# 등급 산출 함수
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

# 탭 구성
tab1, tab2, tab3 = st.tabs([
    "📝 평가 입력", 
    "📊 종합 평가 결과 대시보드", 
    "🔍 평가자별/대상자별 상세 조회"
])

# -------------------------------------------------------------------
# TAB 1: 평가 점수 입력
# -------------------------------------------------------------------
with tab1:
    st.subheader("평가 점수 제출")

    # 로그인한 사용자 이름으로 평가자 자동 고정
    evaluator = st.session_state["user_name"]

    col1, col2 = st.columns(2)
    with col1:
        st.text_input("평가자", value=f"{evaluator} (본인 로그인 완료)", disabled=True)
    with col2:
        target = st.selectbox("평가 대상자 선택", TARGETS)

    st.markdown("---")
    st.write("각 항목별 점수를 입력하세요 (0점 ~ 10점)")

    scores = {}
    cols = st.columns(len(ITEMS))
    for i, item in enumerate(ITEMS):
        with cols[i]:
            scores[item] = st.slider(f"{item}", 0, 10, 5, key=f"slide_{item}")

    if st.button("점수 저장 및 제출", type="primary"):
        try:
            df = load_data()
            
            existing_idx = df[(df["evaluator"] == evaluator) & (df["target"] == target)].index
            new_row = {"evaluator": evaluator, "target": target, **scores}

            if len(existing_idx) > 0:
                for key, val in new_row.items():
                    df.loc[existing_idx[0], key] = val
            else:
                df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)

            sheet = get_worksheet()
            sheet.clear()
            sheet.update([df.columns.values.tolist()] + df.values.tolist())
            
            st.success(f"[{evaluator}] 평가자의 [{target}] 대상자에 대한 평가가 성공적으로 저장되었습니다!")
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
            df[item] = pd.to_numeric(df[item], errors='coerce').fillna(0)

        summary_list = []
        for target_person in df["target"].unique():
            sub_df = df[df["target"] == target_person]
            eval_count = len(sub_df)
            item_means = sub_df[ITEMS].mean()
            total_avg = item_means.mean()
            grade = calculate_grade(total_avg)

            row = {
                "피평가자": target_person,
                "평가인원": eval_count,
                "종합 평균점수": round(total_avg, 2),
                "기술 평가 등급": grade
            }
            for item in ITEMS:
                row[item] = round(item_means[item], 2)
            summary_list.append(row)

        summary_df = pd.DataFrame(summary_list)

        st.dataframe(summary_df, use_container_width=True)

        st.markdown("### 🏆 등급 현황 통계")
        grade_counts = summary_df["기술 평가 등급"].value_counts().reindex(["S", "A", "B", "C", "D"], fill_value=0)

        c1, c2, c3, c4, c5 = st.columns(5)
        for i, g in enumerate(["S", "A", "B", "C", "D"]):
            eval(f"c{i+1}").metric(f"{g} 등급", f"{grade_counts[g]} 명")

        st.markdown("### 📈 피평가자별 역량 방사형 차트")
        selected_target = st.selectbox("분석할 대상자 선택", summary_df["피평가자"].unique())

        target_info = summary_df[summary_df["피평가자"] == selected_target].iloc[0]

        radar_df = pd.DataFrame({
            "항목": ITEMS,
            "점수": [target_info[item] for item in ITEMS]
        })

        fig = px.line_polar(radar_df, r='점수', theta='항목', line_close=True, range_r=[0, 10])
        fig.update_traces(fill='toself')
        st.plotly_chart(fig, use_container_width=True)

        st.download_button(
            label="📥 평가 집계 결과 엑셀(CSV) 다운로드",
            data=summary_df.to_csv(index=False).encode('utf-8-sig'),
            file_name="PLC_Software_역량진단_결과.csv",
            mime="text/csv"
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

    # 기본적으로 로그인한 사용자가 기본 선택되도록 설정
    default_eval_idx = evaluator_list.index(st.session_state["user_name"]) if st.session_state["user_name"] in evaluator_list else 0

    with filter_col1:
        sel_evaluator = st.selectbox("👤 평가자 필터", evaluator_list, index=default_eval_idx)
    with filter_col2:
        sel_target = st.selectbox("🎯 평가 대상자 필터", target_list)

    # 📌 특정 평가자를 선택한 경우: 미평가 대상자 현황 표시
    if sel_evaluator != "전체":
        evaluated_targets = df[df["evaluator"] == sel_evaluator]["target"].tolist() if not df.empty else []
        not_evaluated_targets = [t for t in TARGETS if t not in evaluated_targets]
        
        st.markdown("---")
        m_col1, m_col2 = st.columns(2)
        m_col1.metric("진행한 평가 건수", f"{len(evaluated_targets)} / {len(TARGETS)} 명")
        m_col2.metric("남은 미평가 인원", f"{len(not_evaluated_targets)} 명")
        
        if not_evaluated_targets:
            with st.expander(f"⚠️ [{sel_evaluator}] 평가자가 아직 평가하지 않은 대상자 목록 ({len(not_evaluated_targets)}명)", expanded=True):
                cols_per_row = 4
                for i in range(0, len(not_evaluated_targets), cols_per_row):
                    cols = st.columns(cols_per_row)
                    for j, target_name in enumerate(not_evaluated_targets[i:i+cols_per_row]):
                        cols[j].write(f"• {target_name}")
        else:
            st.success(f"🎉 [{sel_evaluator}] 평가자는 모든 대상자에 대한 평가를 완료했습니다!")
        st.markdown("---")

    # 평가 내역 테이블 출력
    if df.empty or len(df) == 0:
        st.info("아직 입력된 평가 데이터가 없습니다.")
    else:
        for item in ITEMS:
            df[item] = pd.to_numeric(df[item], errors='coerce').fillna(0)

        display_df = df.copy()
        display_df.rename(columns={"evaluator": "평가자", "target": "평가 대상자"}, inplace=True)
        display_df["평균 점수"] = display_df[ITEMS].mean(axis=1).round(2)

        filtered_df = display_df.copy()

        if sel_evaluator != "전체":
            filtered_df = filtered_df[filtered_df["평가자"] == sel_evaluator]

        if sel_target != "전체":
            filtered_df = filtered_df[filtered_df["평가 대상자"] == sel_target]

        st.markdown(f"**총 {len(filtered_df)}건의 완료된 평가 데이터가 검색되었습니다.**")
        st.dataframe(filtered_df, use_container_width=True)
