import time
import extra_streamlit_components as stx
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
import streamlit as st

# -------------------------------------------------------------------
# 0. Page Config
# -------------------------------------------------------------------
st.set_page_config(
    page_title="PLC S/W Competency Assessment",
    page_icon="⚙️",
    layout="wide",
)

# -------------------------------------------------------------------
# 1. 평가 항목 20선 정의 (새 기준)
# -------------------------------------------------------------------
ITEMS = [
    "S/W 아키텍처 구조 이해도",
    "모션 및 시퀀스 제어 분석",
    "예외 처리 및 Safety 분석",
    "통신 및 상위 인터페이스 분석",
    "고급 데이터 처리 분석",
    "코드 문제점 및 개선점 발굴",
    "표준 모듈화/리팩토링 제안",
    "트러블 슈팅 대응 방안",
    "발표 자료의 논리적 구성",
    "시각화(흐름도/상태도) 활용",
    "핵심 기술 포인트 요약력",
    "분석 보고서/문서 완성도",
    "기술 내용 전달력",
    "발표 시간 및 태도",
    "감독관 질의 이해도",
    "답변의 논리성 및 깊이",
    "돌발/예외 상황 대응력",
    "현장 업무 적용 가능성",
    "기술 내재화 수준",
    "향후 개발 역량 발전성",
]

# -------------------------------------------------------------------
# 2. Google Sheets 연동
# -------------------------------------------------------------------
SCOPE = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive",
]


@st.cache_resource
def get_gsheet_client():
    creds_dict = st.secrets["gcp_service_account"]
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, SCOPE)
    client = gspread.authorize(creds)
    return client


def get_sheet():
    client = get_gsheet_client()
    # Google Sheets 이름 확인
    sheet = client.open("PLC_Assessment_DB").sheet1
    return sheet


def load_data():
    sheet = get_sheet()
    records = sheet.get_all_records()
    df = pd.DataFrame(records)

    if df.empty:
        headers = ["Target_Name", "Evaluator"] + ITEMS + ["Avg_Score", "Grade"]
        df = pd.DataFrame(columns=headers)
    else:
        # KeyError 방어 로직: 새 ITEMS 항목 중 시트에 없는 항목은 0으로 채움
        for item in ITEMS:
            if item in df.columns:
                df[item] = pd.to_numeric(df[item], errors="coerce").fillna(0)
            else:
                df[item] = 0

        if "Avg_Score" in df.columns:
            df["Avg_Score"] = pd.to_numeric(
                df["Avg_Score"], errors="coerce"
            ).fillna(0)

    return df


def save_data(row_data):
    sheet = get_sheet()
    records = sheet.get_all_records()

    # 데이터가 비어 있거나 헤더가 바뀐 경우를 대비해 스키마 재정의
    headers = ["Target_Name", "Evaluator"] + ITEMS + ["Avg_Score", "Grade"]

    if not records:
        sheet.append_row(headers)

    row_to_append = [row_data.get(h, "") for h in headers]
    sheet.append_row(row_to_append)


# -------------------------------------------------------------------
# 3. 등급 산정 로직 (10점 만점 평균 기준)
# -------------------------------------------------------------------
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
# 4. 쿠키 및 세션 상태 초기화 (로그아웃 버그 대응)
# -------------------------------------------------------------------
cookie_manager = stx.CookieManager()

if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False
if "user_name" not in st.session_state:
    st.session_state["user_name"] = None

# 쿠키 확인
saved_user = cookie_manager.get(cookie="logged_in_user")
if saved_user and not st.session_state["logged_in"]:
    st.session_state["logged_in"] = True
    st.session_state["user_name"] = saved_user

# -------------------------------------------------------------------
# 5. 로그인 화면
# -------------------------------------------------------------------
if not st.session_state["logged_in"]:
    st.title("⚙️ PLC S/W 역량 평가 시스템")
    st.subheader("감독관 로그인")

    user_name_input = st.text_input("감독관(평가자) 이름을 입력하세요:")

    if st.button("로그인", type="primary"):
        if user_name_input.strip():
            st.session_state["logged_in"] = True
            st.session_state["user_name"] = user_name_input.strip()

            # 쿠키 저장 (7일 유효)
            cookie_manager.set("logged_in_user", user_name_input.strip(), expires_at=None)
            st.success(f"{user_name_input}님 환영합니다!")
            time.sleep(0.5)
            st.rerun()
        else:
            st.warning("이름을 입력해 주세요.")
    st.stop()

# -------------------------------------------------------------------
# 6. 메인 화면 (사이드바 + 메인 콘텐츠)
# -------------------------------------------------------------------
# [사이드바 - 로그인 정보 및 안정적인 로그아웃]
st.sidebar.markdown(f"### 👤 **접속자 정보**")
st.sidebar.info(f"현재 평가자: **{st.session_state['user_name']}** 님")

if st.sidebar.button("🚪 로그아웃", type="secondary"):
    st.session_state["logged_in"] = False
    st.session_state["user_name"] = None
    cookie_manager.delete("logged_in_user")
    st.sidebar.success("로그아웃 되었습니다.")
    time.sleep(0.5)
    st.rerun()

st.title("⚙️ PLC S/W 분석 워크숍 역량 평가")

tab1, tab2 = st.tabs(["📝 평가 입력", "📊 전체 결과 조회"])

# -------------------------------------------------------------------
# TAB 1: 평가 입력
# -------------------------------------------------------------------
with tab1:
    st.subheader("워크숍 발표자 평가하기")

    target_name = st.text_input("발표자(피평가자) 이름", placeholder="예: 홍길동")

    st.markdown("---")
    st.write("📌 각 항목별 점수를 선택하세요 (0점 ~ 10점)")

    scores = {}

    # 💡 [방법 2 적용] 20개 항목을 4개씩 5줄 그리드로 나누어 가로 폭 확보
    items_per_row = 4
    for i in range(0, len(ITEMS), items_per_row):
        row_items = ITEMS[i : i + items_per_row]
        cols = st.columns(len(row_items))
        for j, item in enumerate(row_items):
            with cols[j]:
                scores[item] = st.slider(
                    label=item,
                    min_value=0,
                    max_value=10,
                    value=5,
                    key=f"slide_{item}",
                )

    st.markdown("---")

    if st.button("점수 저장 및 제출", type="primary", use_container_width=True):
        if not target_name.strip():
            st.error("발표자 이름을 입력해주세요!")
        else:
            avg_score = round(sum(scores.values()) / len(ITEMS), 2)
            grade = calculate_grade(avg_score)

            row_data = {
                "Target_Name": target_name.strip(),
                "Evaluator": st.session_state["user_name"],
                "Avg_Score": avg_score,
                "Grade": grade,
            }
            row_data.update(scores)

            try:
                save_data(row_data)
                st.success(
                    f"🎉 {target_name} 님의 평가가 완료되었습니다! (평균: {avg_score}점 / 등급: {grade})"
                )
            except Exception as e:
                st.error(f"데이터 저장 실패: {e}")

# -------------------------------------------------------------------
# TAB 2: 전체 결과 조회
# -------------------------------------------------------------------
with tab2:
    st.subheader("전체 평가 결과 현황")

    if st.button("🔄 데이터 새로고침"):
        st.cache_resource.clear()
        st.rerun()

    try:
        df = load_data()
        if not df.empty:
            st.dataframe(df, use_container_width=True)

            # 요약 통계
            st.markdown("---")
            st.write("### 📈 피평가자별 평균 점수")
            summary_df = (
                df.groupby("Target_Name")[["Avg_Score"]]
                .mean()
                .reset_index()
            )
            summary_df["Grade"] = summary_df["Avg_Score"].apply(calculate_grade)
            st.table(summary_df)
        else:
            st.info("아직 등록된 평가 데이터가 없습니다.")
    except Exception as e:
        st.error(f"데이터를 불러오는 중 오류 발생: {e}")
