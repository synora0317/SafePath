# app.py
# 실행: streamlit run app.py
# 데이터·API 키 모두 필요 없습니다 (data.py에 전부 내장).

import streamlit as st
from streamlit_folium import st_folium

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
from map_view import build_map

st.set_page_config(page_title="SafePath", page_icon="🧭", layout="centered")
st.markdown(GLOBAL_CSS, unsafe_allow_html=True)
st.markdown(masthead_html(), unsafe_allow_html=True)

st.markdown('<div class="sp-role-label">역할을 선택하세요</div>', unsafe_allow_html=True)
role = st.radio("역할을 선택하세요", ["개인", "기관"], horizontal=True, label_visibility="collapsed")
st.markdown("---")

loc_names = [l["name"] for l in LOCATIONS]


def render_map(result, label):
    m = build_map(result, label)
    st_folium(m, use_container_width=True, height=420, returned_objects=[])
    if result["shelters"]:
        st.caption("🔴 나의 위치 · 🟢 최우선 대피소 · ⚪ 차선안 대피소 (직선거리 기준)")


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
