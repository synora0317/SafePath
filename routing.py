# routing.py
# OSRM(FOSSGIS 후원 공개 데모 서버, router.project-osrm.org)로 실제 도보 경로를 조회합니다.
# 주의: 이 서버는 "비상업적, 초당 1회 요청" 제한이 있는 공개 데모입니다.
#       실제 서비스로 운영할 때는 자체 OSRM 서버를 두거나 카카오/네이버 등
#       상용 길찾기 API로 교체해야 합니다. (README에도 명시)

import requests
import streamlit as st

OSRM_BASE_URL = "https://router.project-osrm.org/route/v1/foot"
TIMEOUT_SEC = 3


@st.cache_data(ttl=3600, show_spinner=False)
def get_walking_route(lat1, lon1, lat2, lon2):
    """도보 경로의 실제 도로/보행로를 따라가는 [[lon, lat], ...] 좌표 리스트를 반환.
    조회 실패(타임아웃, 네트워크 오류, 서버 오류) 시 None을 반환하며,
    호출 측에서 None이면 직선 경로로 대체 처리해야 합니다."""
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
        return coords
    except (requests.RequestException, KeyError, ValueError, IndexError):
        return None
