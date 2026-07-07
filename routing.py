# routing.py
# OSRM(FOSSGIS 후원 공개 데모 서버, router.project-osrm.org)로 실제 도보 경로를 조회합니다.
# 주의: 이 서버는 "비상업적, 초당 1회 요청" 제한이 있는 공개 데모입니다.
#       실제 서비스로 운영할 때는 자체 OSRM 서버를 두거나 카카오/네이버 등
#       상용 길찾기 API로 교체해야 합니다.
#
# 중요: 예전 버전에는 "직선거리 대비 너무 많이 우회하면 폐기하고 직선으로 대체"하는
#       로직이 있었는데, 이게 오히려 문제였습니다. 도로를 따라가려면 블록을 빙
#       돌아야 하는 경우가 실제로 많은데, 이걸 "비정상 우회"로 오판해서 정상적인
#       도로 경로를 버리고 건물을 관통하는 직선으로 바꿔버렸습니다.
#       그래서 이 버전은 우회 여부를 따지지 않고, OSRM이 응답을 주면(네트워크
#       실패가 아니면) 그대로 사용합니다. 직선은 정말로 서버 응답을 못 받았을
#       때만 씁니다.

import requests
import streamlit as st

OSRM_BASE_URL = "https://router.project-osrm.org/route/v1/foot"
TIMEOUT_SEC = 8
REQUEST_HEADERS = {
    "User-Agent": "SafePath-Prototype/1.0 (hackathon demo)"
}


@st.cache_data(ttl=3600, show_spinner=False)
def get_walking_route(lat1, lon1, lat2, lon2):
    """도보 경로의 실제 도로/보행로를 따라가는 [[lon, lat], ...] 좌표 리스트를 반환.
    OSRM 서버 응답 실패(네트워크 오류, 타임아웃, 서버 오류)일 때만 None을 반환하며,
    호출 측에서 None이면 직선 경로로 대체 처리해야 합니다. 경로가 얼마나 돌아가든
    OSRM이 실제로 계산해준 도로 경로라면 그대로 사용합니다(우회 여부로 폐기하지 않음)."""
    url = f"{OSRM_BASE_URL}/{lon1},{lat1};{lon2},{lat2}"
    params = {"overview": "full", "geometries": "geojson"}
    try:
        resp = requests.get(url, params=params, headers=REQUEST_HEADERS, timeout=TIMEOUT_SEC)
        if resp.status_code != 200:
            return None
        data = resp.json()
        if data.get("code") != "Ok" or not data.get("routes"):
            return None
        coords = data["routes"][0]["geometry"]["coordinates"]  # 이미 [lon, lat] 순서
        return coords
    except (requests.RequestException, KeyError, ValueError, IndexError):
        return None
