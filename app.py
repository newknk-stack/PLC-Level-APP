import streamlit as st
import pandas as pd
import plotly.express as px
import os

# 파일 저장 경로
DATA_FILE = "evaluation_data.csv"

# 평가 항목 및 기본 정보 정의
ITEMS = ["S/W 분석 및 이해", "발표 자료 완성도", "발표력", "활용도", "S/W 난이도"]
EVALUATORS = ["정준영", "차영진", "김태환", "김남권", "최치웅"]
TARGETS = ["박상규", "이영표", "이윤열", "임성민", "김용남", "왕종표", "이동민", "이준식", "이진호", "길지훈", "이창배", "채경용", "하운기", "박광윤", "안상윤", "오성균", "이동준", "임채환", "권준성", "서창성", "유승우", "이도윤", "박시후", "손병효", "이준혁", "장정윤", "한정훈"]



# 데이터 불러오기 함수
def load_data():
    if os.path.exists(DATA_FILE):
        return pd.read_csv(DATA_FILE)
    else:
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


# 페이지 기본 설정
st.set_page_config(page_title="PLC S/W 역량 진단 평가 툴", layout="wide")
st.title("⚡ PLC S/W 역량 진단 평가 시스템")

# 탭 구성
tab1, tab2 = st.tabs(["📝 평가 입력", "📊 종합 평가 결과 대시보드"])

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
    st.write(" 각 항목별 점수를 입력하세요 (0점 ~ 10점)")

    scores = {}
    cols = st.columns(len(ITEMS))
    for i, item in enumerate(ITEMS):
        with cols[i]:
            scores[item] = st.slider(f"{item}", 0, 10, 5, key=f"slide_{item}")

    if st.button("점수 저장 및 제출", type="primary"):
        df = load_data()

        # 기존에 입력된 평가가 있다면 덮어쓰기, 없으면 추가
        existing_idx = df[(df["evaluator"] == evaluator) & (df["target"] == target)].index

        new_row = {"evaluator": evaluator, "target": target, **scores}
        if len(existing_idx) > 0:
            df.loc[existing_idx[0]] = new_row
        else:
            df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)

        df.to_csv(DATA_FILE, index=False)
        st.success(f"[{evaluator}] 평가자의 [{target}] 대상자에 대한 평가가 저장되었습니다!")

# -------------------------------------------------------------------
# TAB 2: 결과 및 대시보드
# -------------------------------------------------------------------
with tab2:
    st.subheader("종합 평가 현황")
    df = load_data()

    if df.empty:
        st.info("아직 입력된 평가 데이터가 없습니다.")
    else:
        # 대상자별 집계 계산
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
                "기술 평가 등급": grade,
            }
            for item in ITEMS:
                row[item] = round(item_means[item], 2)
            summary_list.append(row)

        summary_df = pd.DataFrame(summary_list)

        # 1. 요약 데이터 테이블 출력
        st.dataframe(summary_df, use_container_width=True)

        # 2. 등급 분포 요약
        st.markdown("### 🏆 등급 현황 통계")
        grade_counts = summary_df["기술 평가 등급"].value_counts().reindex(["S", "A", "B", "C", "D"], fill_value=0)

        c1, c2, c3, c4, c5 = st.columns(5)
        for i, g in enumerate(["S", "A", "B", "C", "D"]):
            eval(f"c{i + 1}").metric(f"{g} 등급", f"{grade_counts[g]} 명")

        # 3. 방사형 차트 (Radar Chart) 시각화
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

        # 4. 엑셀 다운로드 기능
        st.download_button(
            label="📥 평가 집계 결과 엑셀(CSV) 다운로드",
            data=summary_df.to_csv(index=False).encode('utf-8-sig'),
            file_name="PLC_Software_역량진단_결과.csv",
            mime="text/csv"
        )
