# routing.py
# OSRM(FOSSGIS 후원 공개 데모 서버, router.project-osrm.org)로 실제 도로를 따라가는 경로를 조회합니다.
# 주의: 이 서버는 "비상업적, 초당 1회 요청" 제한이 있는 공개 데모입니다.
#       실제 서비스로 운영할 때는 자체 OSRM 서버를 두거나 카카오/네이버 등
#       상용 길찾기 API로 교체해야 합니다. (README에도 명시)
#
# 조회 순서 (건물을 관통하는 직선을 최대한 피하기 위함):
#   1) 도보(foot) 프로필로 시도
#   2) 실패하거나 비정상적으로 우회하면(=주변 골목이 OSM에 보행로로 없는 경우),
#      자동차(driving) 프로필로 재시도 — 큰길이라도 반드시 "실제 도로 위"를 지나가게 함
#   3) 그래도 실패하면 마지막 수단으로 직선(그리고 결과에 실패 사실을 표시)

import math
import requests
import streamlit as st

OSRM_ROOT = "https://router.project-osrm.org/route/v1"
TIMEOUT_SEC = 3
MAX_DETOUR_RATIO_FOOT = 2.5     # 도보 경로: 직선 대비 이 배수 넘으면 지도 데이터 공백으로 판단
MAX_DETOUR_RATIO_DRIVING = 4.0  # 차도 경로: 일방통행 등으로 더 돌아갈 수 있어 여유를 더 둠


def _haversine_km(lat1, lon1, lat2, lon2):
    R = 6371
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlmb = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlmb / 2) ** 2
    return R * 2 * math.asin(math.sqrt(a))


def _route_length_km(coords):
    total = 0.0
    for (lon1, lat1), (lon2, lat2) in zip(coords, coords[1:]):
        total += _haversine_km(lat1, lon1, lat2, lon2)
    return total


def _query_osrm(profile, lat1, lon1, lat2, lon2, max_ratio):
    """OSRM에 profile(foot/driving)로 경로를 물어보고, 성공 시 좌표 리스트를 반환.
    비정상 우회이거나 실패하면 None."""
    url = f"{OSRM_ROOT}/{profile}/{lon1},{lat1};{lon2},{lat2}"
    params = {"overview": "full", "geometries": "geojson"}
    try:
        resp = requests.get(url, params=params, timeout=TIMEOUT_SEC)
        if resp.status_code != 200:
            return None
        data = resp.json()
        if data.get("code") != "Ok" or not data.get("routes"):
            return None
        coords = data["routes"][0]["geometry"]["coordinates"]

        straight_km = _haversine_km(lat1, lon1, lat2, lon2)
        route_km = _route_length_km(coords)
        if straight_km > 0 and route_km > straight_km * max_ratio:
            return None
        return coords
    except (requests.RequestException, KeyError, ValueError, IndexError):
        return None


@st.cache_data(ttl=3600, show_spinner=False)
def get_walking_route(lat1, lon1, lat2, lon2):
    """실제 도로 위를 지나가는 [[lon, lat], ...] 좌표 리스트와, 어떤 방식으로 구했는지를 반환.
    반환값: (coords 또는 None, source)
      source: "foot" | "driving" | "straight"
    coords가 None이면 호출 측에서 직선으로 대체해야 합니다(마지막 수단).
    """
    coords = _query_osrm("foot", lat1, lon1, lat2, lon2, MAX_DETOUR_RATIO_FOOT)
    if coords is not None:
        return coords, "foot"

    # 도보 경로 실패 → 자동차 도로망으로 재시도 (건물 관통 대신 실제 큰길이라도 따라가게)
    coords = _query_osrm("driving", lat1, lon1, lat2, lon2, MAX_DETOUR_RATIO_DRIVING)
    if coords is not None:
        return coords, "driving"

    return None, "straight"
