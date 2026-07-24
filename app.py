st.caption("역량 수준별 분포 현황")

            # 1. 원본 데이터 값
            raw_levels = [
                ("L3", l3_p, "#00A3E0", "white"),
                ("L2", l2_p, "#702F98", "white"),
                ("L1", l1_p, "#FFEE00", "#222222"),
                ("L0", l0_p, "#00A859", "white"),
            ]

            # 2. 텍스트가 정상 표현되도록 시각적 비율(최소 폭 8%) 및 표시할 텍스트 계산
            #    0%인 항목은 아예 차트 막대에서 제외됩니다.
            active_levels = [item for item in raw_levels if item[1] > 0]

            # 텍스트 최소 너비 확보 계산
            min_width = 8.0  # 텍스트 표시에 필요한 최소 visual width (%)
            total_active_raw = sum(item[1] for item in active_levels)

            chart_data = []
            if active_levels:
                # 0%가 아닌 항목들의 시각적 비중 보정
                visual_widths = []
                for lbl, val, color, text_color in active_levels:
                    # 값이 존재하지만 너무 작을 경우 최소 8% 너비 보장
                    v_w = max(val, min_width)
                    visual_widths.append(v_w)

                sum_v_w = sum(visual_widths)
                # 전체 합을 100%로 맞추기 위한 정규화
                norm_widths = [(w / sum_v_w) * 100 for w in visual_widths]

                for (lbl, val, color, text_color), n_w in zip(
                    active_levels, norm_widths
                ):
                    # 막대 안에는 실제 % 수치가 표시됨 (예: L2 (1.2%))
                    text_str = f"<b>{lbl} ({val}%)</b>"
                    chart_data.append(
                        (lbl, val, n_w, color, text_color, text_str)
                    )

            # 3. Plotly 막대 차트 생성 (L3 -> L2 -> L1 -> L0 순서)
            fig_bar = go.Figure()

            for lbl, val, vis_w, color, text_color, text_str in chart_data:
                fig_bar.add_trace(
                    go.Bar(
                        y=["분포"],
                        x=[vis_w],  # 텍스트 가독성을 위해 조정된 가각 너비
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
                height=34,
                showlegend=False,
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
            )

            st.plotly_chart(
                fig_bar,
                use_container_width=True,
                config={"displayModeBar": False},
            )

            # 기존 텍스트 라벨 (L3 -> L2 -> L1 -> L0 순서로 일치)
            st.caption(
                f"L3(최상): {l3_p}% | L2(상): {l2_p}% | L1(중): {l1_p}% | L0(하): {l0_p}%"
            )
