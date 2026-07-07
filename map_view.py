# map_view.py
# folium으로 지도를 그립니다: 나의 위치·대피소 마커 + 대피소까지의 경로선.
# 경로선은 routing.py(OSRM)로 실제 도보 경로를 시도하고, 서버 응답 실패시에만
# 직선으로 대체합니다(경로가 돌아가더라도 실제 도로 경로면 그대로 사용).

import folium
from theme import PRIMARY, SLATE, TIER_COLORS
from routing import get_walking_route

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
    fallback_used = False

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

        # ---------- 경로선: OSRM 실제 도보 경로(우회 판정 없음), 서버실패 시에만 직선 ----------
        route_coords = get_walking_route(user_lat, user_lon, s["위도"], s["경도"])
        if route_coords is None:
            line_points = [[user_lat, user_lon], [s["위도"], s["경도"]]]
            fallback_used = True
        else:
            line_points = [[lat, lon] for lon, lat in route_coords]  # OSRM은 [lon,lat] → folium은 [lat,lon]

        folium.PolyLine(
            line_points,
            color=color,
            weight=5 if is_primary else 2.5,
            opacity=0.85 if is_primary else 0.55,
        ).add_to(m)

        # 실제 경로일 때는 경로 전체가 보이도록 경유 좌표도 fit_bounds에 포함
        if route_coords is not None:
            for lon, lat in route_coords:
                bounds.append([lat, lon])

    if len(bounds) > 1:
        m.fit_bounds(bounds, padding=(30, 30))

    return m, fallback_used
