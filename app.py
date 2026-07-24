st.markdown("---")
    st.write("각 항목별 점수를 입력하세요 (0점 ~ 10점)")

    # 🎨 슬라이더 스타일 및 눈금선 중첩 스타일 지정
    st.markdown(
        """
        <style>
            div[data-testid="stSlider"] {
                padding-bottom: 0px;
            }
            div[data-testid="stSlider"] [data-testid="stTickBar"] {
                display: none;
            }
            .slider-tick-container {
                display: flex;
                justify-content: space-between;
                position: relative;
                top: -18px;
                padding: 0 11px;
                pointer-events: none;
                margin-bottom: -10px;
                z-index: 1;
            }
            .slider-tick-item {
                display: flex;
                flex-direction: column;
                align-items: center;
                width: 14px;
            }
            .slider-tick-mark {
                width: 1.5px;
                height: 12px;
                background-color: #a0a0a0;
            }
            .slider-tick-label {
                font-size: 0.70rem;
                color: #777777;
                font-weight: 500;
                margin-top: 4px;
            }
        </style>
        """,
        unsafe_allow_html=True,
    )

    scores = {}
    items_per_row = 2

    # 🔥 HTML 태그 노출 방지를 위해 줄바꿈 없이 한 줄로 결합
    ticks_html = '<div class="slider-tick-container">' + "".join([f'<div class="slider-tick-item"><div class="slider-tick-mark"></div><div class="slider-tick-label">{num}</div></div>' for num in range(11)]) + '</div>'

    for i in range(0, len(ITEMS), items_per_row):
        row_items = ITEMS[i : i + items_per_row]
        cols = st.columns(len(row_items))
        
        for j, item in enumerate(row_items):
            with cols[j]:
                scores[item] = st.slider(
                    f"{item}", 
                    min_value=0, 
                    max_value=10, 
                    value=5, 
                    step=1,
                    key=f"slide_{item}"
                )
                # HTML 구조가 텍스트로 깨지지 않고 정상 렌더링되도록 처리
                st.markdown(ticks_html, unsafe_allow_html=True)
