# routing.py
# OSRM(FOSSGIS 후원 공개 데모 서버, router.project-osrm.org)로 실제 도로를 따라가는 경로를 조회합니다.
# 주의: 이 서버는 "비상업적, 초당 1회 요청" 제한이 있는 공개 데모입니다.
#       실제 서비스로 운영할 때는 자체 OSRM 서버를 두거나 카카오/네이버 등
#       상용 길찾기 API로 교체해야 합니다. (README에도 명시)
#
# 조회 순서 (건물을 관통하는 직선을 최대한 피하기 위함):
#   1) 도보(foot) 프로필로 시도 (실패 시 1회 재시도)
#   2) 실패하거나 비정상적으로 우회하면(=주변 골목이 OSM에 보행로로 없는 경우),
#      자동차(driving) 프로필로 재시도 (마찬가지로 1회 재시도) — 큰길이라도
#      반드시 "실제 도로 위"를 지나가게 함
#   3) 그래도 실패하면 마지막 수단으로 직선
#
# 중요: 실패한 결과는 캐싱하지 않습니다. 한 번의 일시적 네트워크 오류가
#       1시간 동안 "직선"으로 고정되어버리는 것을 막기 위함입니다.
#       (성공한 결과만 세션 동안 캐싱하여 반복 호출을 줄입니다)

import math
import time
import requests
import streamlit as st

OSRM_ROOT = "https://router.project-osrm.org/route/v1"
TIMEOUT_SEC = 6          # 무료 공개 서버 지연 감안해 여유 있게
RETRY_COUNT = 2          # 프로필당 최대 시도 횟수 (최초 1회 + 재시도 1회)
RETRY_DELAY_SEC = 0.6
MAX_DETOUR_RATIO_FOOT = 2.5
MAX_DETOUR_RATIO_DRIVING = 4.0


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


def _query_osrm_once(profile, lat1, lon1, lat2, lon2, max_ratio):
    url = f"{OSRM_ROOT}/{profile}/{lon1},{lat1};{lon2},{lat2}"
    params = {"overview": "full", "geometries": "geojson"}
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


def _query_osrm(profile, lat1, lon1, lat2, lon2, max_ratio):
    """실패 시 RETRY_COUNT번까지 재시도. 마지막 시도까지 실패하면 None."""
    for attempt in range(RETRY_COUNT):
        try:
            coords = _query_osrm_once(profile, lat1, lon1, lat2, lon2, max_ratio)
            if coords is not None:
                return coords
        except (requests.RequestException, KeyError, ValueError, IndexError):
            pass
        if attempt < RETRY_COUNT - 1:
            time.sleep(RETRY_DELAY_SEC)
    return None


def get_walking_route(lat1, lon1, lat2, lon2):
    """실제 도로 위를 지나가는 [[lon, lat], ...] 좌표 리스트와, 어떤 방식으로 구했는지를 반환.
    반환값: (coords 또는 None, source)  source: "foot" | "driving" | "straight"
    성공한 결과만 세션 내 캐싱하고, 실패(직선 대체)는 캐싱하지 않아 다음 호출 때 재시도합니다.
    """
    cache = st.session_state.setdefault("_route_cache", {})
    key = (round(lat1, 6), round(lon1, 6), round(lat2, 6), round(lon2, 6))
    if key in cache:
        return cache[key]

    coords = _query_osrm("foot", lat1, lon1, lat2, lon2, MAX_DETOUR_RATIO_FOOT)
    if coords is not None:
        cache[key] = (coords, "foot")
        return cache[key]

    coords = _query_osrm("driving", lat1, lon1, lat2, lon2, MAX_DETOUR_RATIO_DRIVING)
    if coords is not None:
        cache[key] = (coords, "driving")
        return cache[key]

    return None, "straight"  # 캐싱하지 않음 — 다음 호출 때 다시 시도
