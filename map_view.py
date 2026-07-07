# map_view.py
# folium으로 지도를 그립니다: 나의 위치·대피소 마커 + 대피소까지의 직선 경로.
# (OSRM 공개 데모 서버의 클라우드 환경 신뢰성 문제로, 실제 도로 경로 조회는
#  제거하고 직선 표시로 되돌렸습니다. 실 서비스화 시 카카오/네이버 등
#  상용 길찾기 API로 대체할 계획입니다.)

import folium
from theme import PRIMARY, SLATE, TIER_COLORS

USER_COLOR = TIER_COLORS["심각"]   # 브랜드 위험색(레드)
PRIMARY_COLOR = PRIMARY            # 브랜드 세이프티 그린
SECONDARY_COLOR = SLATE            # 브랜드 슬레이트


def build_map(result, label):
    user_lat, user_lon = result["lat"], result["lon"]
    shelters = result["shelters"]

    m = folium.Map(location=[user_lat, user_lon], zoom_start=16, tiles="cartodbpositron")

    # ---------- 나의 위치 마커 (미터 단위 Circle → 확대/축소에 반응) ----------
    folium.Circle(
        location=[user_lat, user_lon],
        radius=18,
        color=USER_COLOR,
        fill=True,
        fill_color=USER_COLOR,
        fill_opacity=0.9,
        weight=2,
        tooltip=label,
    ).add_to(m)

    bounds = [[user_lat, user_lon]]

    for i, (d, s) in enumerate(shelters):
        is_primary = (i == 0)
        color = PRIMARY_COLOR if is_primary else SECONDARY_COLOR
        radius_m = 22 if is_primary else 14

        # ---------- 대피소 마커 ----------
        folium.Circle(
            location=[s["위도"], s["경도"]],
            radius=radius_m,
            color=color,
            fill=True,
            fill_color=color,
            fill_opacity=0.85,
            weight=2,
            tooltip=f"{s['대피소명']} ({d*1000:.0f}m){' · 최우선' if is_primary else ' · 차선안'}",
        ).add_to(m)
        bounds.append([s["위도"], s["경도"]])

        # ---------- 경로선: 직선거리 기준 ----------
        line_points = [[user_lat, user_lon], [s["위도"], s["경도"]]]
        folium.PolyLine(
            line_points,
            color=color,
            weight=5 if is_primary else 2.5,
            opacity=0.85 if is_primary else 0.55,
        ).add_to(m)

    if len(bounds) > 1:
        m.fit_bounds(bounds, padding=(30, 30))

    return m
