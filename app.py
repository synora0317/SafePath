# app.py
# 실행: streamlit run app.py
# 데이터·API 키 모두 필요 없습니다 (data.py에 전부 내장).

import streamlit as st
import pandas as pd
import pydeck as pdk

from data import LOCATIONS
from risk_engine import (
    DISASTER_TYPES, MOBILITY_RADIUS, INSTITUTION_TYPES, EVAC_MEANS_RADIUS,
    analyze_individual, analyze_institution,
)
from ui_components import (
    shelter_cards_html, monitoring_box_html, default_monitoring_bullets,
    no_shelter_html, masthead_html, tier_banner_html,
)
from theme import GLOBAL_CSS

st.set_page_config(page_title="SafePath", page_icon="🧭", layout="centered")
st.markdown(GLOBAL_CSS, unsafe_allow_html=True)
st.markdown(masthead_html(), unsafe_allow_html=True)

st.markdown('<div class="sp-role-label">역할을 선택하세요</div>', unsafe_allow_html=True)
role = st.radio("역할을 선택하세요", ["개인", "기관"], horizontal=True, label_visibility="collapsed")
st.markdown("---")

loc_names = [l["name"] for l in LOCATIONS]


from theme import PRIMARY, SLATE, TIER_COLORS


def _hex_to_rgb(hex_color: str):
    hex_color = hex_color.lstrip("#")
    return [int(hex_color[i:i+2], 16) for i in (0, 2, 4)]


USER_COLOR = _hex_to_rgb(TIER_COLORS["심각"])       # 브랜드 위험색(레드) 재사용
SHELTER_PRIMARY_COLOR = _hex_to_rgb(PRIMARY)        # 브랜드 세이프티 그린
SHELTER_SECONDARY_COLOR = _hex_to_rgb(SLATE)        # 브랜드 슬레이트


def render_map(result, label):
    user_lat, user_lon = result["lat"], result["lon"]
    shelters = result["shelters"]

    # ---------- 마커 (반응형 크기: 실제 미터 반경 + 화면 최소/최대 픽셀 보장) ----------
    points = [{
        "lat": user_lat, "lon": user_lon, "name": label,
        "color": USER_COLOR, "radius_m": 32,
    }]
    for i, (d, s) in enumerate(shelters):
        is_primary = (i == 0)
        points.append({
            "lat": s["위도"], "lon": s["경도"],
            "name": f"{s['대피소명']} ({d*1000:.0f}m)",
            "color": SHELTER_PRIMARY_COLOR if is_primary else SHELTER_SECONDARY_COLOR,
            "radius_m": 40 if is_primary else 26,
        })
    point_df = pd.DataFrame(points)

    point_layer = pdk.Layer(
        "ScatterplotLayer",
        data=point_df,
        get_position="[lon, lat]",
        get_fill_color="color",
        get_radius="radius_m",
        radius_units="meters",
        radius_min_pixels=5,   # 축소해도 안 사라지도록 최소 크기 보장
        radius_max_pixels=26,  # 확대해도 과하게 커지지 않도록 최대 크기 제한
        stroked=True,
        get_line_color=[255, 255, 255],
        line_width_min_pixels=1.5,
        pickable=True,
    )

    layers = [point_layer]

    # 대피소가 멀수록 살짝 축소해서 마커가 화면 안에 다 들어오게
    max_dist = max((d for d, s in shelters), default=0.0)
    zoom = 16 if max_dist <= 0.3 else 15 if max_dist <= 0.8 else 14 if max_dist <= 1.5 else 13
    view_state = pdk.ViewState(latitude=user_lat, longitude=user_lon, zoom=zoom)

    st.pydeck_chart(pdk.Deck(
        layers=layers,
        initial_view_state=view_state,
        tooltip={"text": "{name}"},
        map_provider="carto",
        map_style=pdk.map_styles.LIGHT,
    ))
    if shelters:
        st.caption("🔴 나의 위치 · 🟢 최우선 대피소 · ⚪ 차선안 대피소")


def render_shelter_section(result, disaster_type):
    if result["shelters"]:
        st.markdown(shelter_cards_html(result["shelters"], result["move_mode"]), unsafe_allow_html=True)
        bullets = default_monitoring_bullets(result["shelters"], disaster_type)
        st.markdown(monitoring_box_html(bullets), unsafe_allow_html=True)
    else:
        st.markdown(no_shelter_html(result["no_shelter_message"]), unsafe_allow_html=True)


if role == "개인":
    st.subheader("개인 대피 안내")
    loc_name = st.selectbox("① 현재 위치", loc_names)
    disaster_type = st.selectbox("② 재난 유형", DISASTER_TYPES)
    move_mode = st.selectbox("③ 이동수단", list(MOBILITY_RADIUS.keys()))
    companion = st.selectbox("④ 동행자", ["없음", "어린이", "노약자", "반려동물"])

    location = next(l for l in LOCATIONS if l["name"] == loc_name)

    if st.button("분석하기", type="primary"):
        result = analyze_individual(location, disaster_type, move_mode, companion)

        st.subheader("📍 위치 및 대피소")
        render_map(result, "나의 위치")

        st.subheader("🤖 AI 분석 결과 (개인용)")
        st.markdown(tier_banner_html(disaster_type, result["tier"]), unsafe_allow_html=True)
        st.markdown(result["text"])
        render_shelter_section(result, disaster_type)

else:
    st.subheader("기관 대피 안내")
    loc_name = st.selectbox("① 현재 위치", loc_names)
    institution_type = st.selectbox("② 기관 유형", INSTITUTION_TYPES)
    disaster_type = st.selectbox("③ 재난 유형", DISASTER_TYPES)
    evac_count = st.number_input("④ 대피 인원", min_value=1, max_value=2000, value=30)
    evac_means = st.selectbox("⑤ 대피 수단", list(EVAC_MEANS_RADIUS.keys()))

    location = next(l for l in LOCATIONS if l["name"] == loc_name)

    if st.button("분석하기", type="primary"):
        result = analyze_institution(location, institution_type, disaster_type, evac_count, evac_means)

        st.subheader("📍 위치 및 대피소")
        render_map(result, "기관 위치")

        st.subheader("🤖 AI 분석 결과 (기관용)")
        st.markdown(tier_banner_html(disaster_type, result["tier"]), unsafe_allow_html=True)
        st.markdown(result["text"])
        render_shelter_section(result, disaster_type)
