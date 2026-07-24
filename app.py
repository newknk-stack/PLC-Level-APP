# 기존 [1, 2] 비율에서 5:5([1, 1]) 비율로 수정
    btn_col1, btn_col2 = st.columns([1, 1])

    with btn_col1:
        st.markdown(
            f"""
            <div style="background-color: #f8f9fa; padding: 10px 12px; border-radius: 6px; border: 1px solid #e0e0e0; text-align: center;">
                <span style="font-size: 0.95rem; color: #555;">기술평가 등급(사전):</span><br>
                <span style="font-size: 1.25rem;">{colored_grade_display}</span>
                <span style="font-size: 0.9rem; color: #888;"> (평균 {current_avg:.1f}점)</span>
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
