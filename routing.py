# routing.py
# OSRM(FOSSGIS 후원 공개 데모 서버, router.project-osrm.org)로 실제 도보 경로를 조회합니다.
# 주의: 이 서버는 "비상업적, 초당 1회 요청" 제한이 있는 공개 데모입니다.
#       실제 서비스로 운영할 때는 자체 OSRM 서버를 두거나 카카오/네이버 등
#       상용 길찾기 API로 교체해야 합니다. (README에도 명시)

import math
import requests
import streamlit as st

OSRM_BASE_URL = "https://router.project-osrm.org/route/v1/foot"
TIMEOUT_SEC = 3
MAX_DETOUR_RATIO = 2.5  # 직선거리 대비 이 배수를 넘는 경로는 지도 데이터 공백으로 보고 폐기


def _haversine_km(lat1, lon1, lat2, lon2):
    R = 6371
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlmb = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlmb / 2) ** 2
    return R * 2 * math.asin(math.sqrt(a))


def _route_length_km(coords):
    """[[lon, lat], ...] 경로의 총 길이(km)를 각 구간 직선거리 합으로 근사."""
    total = 0.0
    for (lon1, lat1), (lon2, lat2) in zip(coords, coords[1:]):
        total += _haversine_km(lat1, lon1, lat2, lon2)
    return total


@st.cache_data(ttl=3600, show_spinner=False)
def get_walking_route(lat1, lon1, lat2, lon2):
    """도보 경로의 실제 도로/보행로를 따라가는 [[lon, lat], ...] 좌표 리스트를 반환.
    다음의 경우 None을 반환하며, 호출 측에서 None이면 직선 경로로 대체 처리해야 합니다:
      - 네트워크/서버 오류, 타임아웃
      - 경로 길이가 직선거리 대비 MAX_DETOUR_RATIO배를 초과 (건물 내부 통로 등이
        OpenStreetMap에 보행로로 태그되지 않아 큰길로 우회하는, 비정상적으로
        먼 경로로 판단되는 경우 — 이 경우 직선이 오히려 실제 이동감에 더 가깝습니다)
    """
    url = f"{OSRM_BASE_URL}/{lon1},{lat1};{lon2},{lat2}"
    params = {"overview": "full", "geometries": "geojson"}
    try:
        resp = requests.get(url, params=params, timeout=TIMEOUT_SEC)
        if resp.status_code != 200:
            return None
        data = resp.json()
        if data.get("code") != "Ok" or not data.get("routes"):
            return None
        coords = data["routes"][0]["geometry"]["coordinates"]  # 이미 [lon, lat] 순서

        straight_km = _haversine_km(lat1, lon1, lat2, lon2)
        route_km = _route_length_km(coords)
        if straight_km > 0 and route_km > straight_km * MAX_DETOUR_RATIO:
            return None  # 비정상적 우회로 판단 → 직선 대체로 넘김

        return coords
    except (requests.RequestException, KeyError, ValueError, IndexError):
        return None
