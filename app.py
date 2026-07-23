import json
import pandas as pd
import plotly.express as px
import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials

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
st.title("⚡ PLC S/W 역량 진단 평가 시스템")

# -------------------------------------------------------------------
# 구글 시트 연동 설정 (gspread)
# -------------------------------------------------------------------
@st.cache_resource
def get_gspread_client():
    scope = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/drive"
    ]
    # Secrets에 저장된 서비스 계정 정보 불러오기
    creds_dict = dict(st.secrets["gcp_service_account"])
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    client = gspread.authorize(creds)
    return client

def get_worksheet():
    client = get_gspread_client()
    # Secrets에 입력된 구글 시트 URL 또는 이름으로 연결
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

    col1, col2 = st.columns(2)
    with col1:
        evaluator = st.selectbox("평가자 선택", EVALUATORS)
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

            # 구글 시트에 업데이트 저장 (헤더 포함 전체 데이터 쓰기)
            sheet = get_worksheet()
            sheet.clear()
            sheet.update([df.columns.values.tolist()] + df.values.tolist())
            
            st.success(f"[{evaluator}] 평가자의 [{target}] 대상자에 대한 평가가 구글 시트에 저장되었습니다!")
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

    if df.empty or len(df) == 0:
        st.info("아직 입력된 평가 데이터가 없습니다.")
    else:
        for item in ITEMS:
            df[item] = pd.to_numeric(df[item], errors='coerce').fillna(0)

        display_df = df.copy()
        display_df.rename(columns={"evaluator": "평가자", "target": "평가 대상자"}, inplace=True)
        display_df["평균 점수"] = display_df[ITEMS].mean(axis=1).round(2)

        filter_col1, filter_col2 = st.columns(2)

        evaluator_list = ["전체"] + list(display_df["평가자"].unique())
        target_list = ["전체"] + list(display_df["평가 대상자"].unique())

        with filter_col1:
            sel_evaluator = st.selectbox("👤 평가자 필터", evaluator_list)
        with filter_col2:
            sel_target = st.selectbox("🎯 평가 대상자 필터", target_list)

        filtered_df = display_df.copy()

        if sel_evaluator != "전체":
            filtered_df = filtered_df[filtered_df["평가자"] == sel_evaluator]

        if sel_target != "전체":
            filtered_df = filtered_df[filtered_df["평가 대상자"] == sel_target]

        st.markdown(f"**총 {len(filtered_df)}건의 평가 데이터가 검색되었습니다.**")
        st.dataframe(filtered_df, use_container_width=True)
