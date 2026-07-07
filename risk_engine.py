# risk_engine.py
# 개인/기관 역할에 따라 서로 다른 입력 흐름과 출력 형식을 처리합니다.
# 위험 단계는 사용자가 직접 고르지 않고, 실시간 AWS 관측값을 시나리오 임계값과
# 비교해 자동으로 판정합니다(호우/태풍). 대설·산불·지진은 관련 실시간 관측 데이터가
# 없어 기본값(관심)과 함께 데이터 한계를 안내문에 명시합니다.

import math
from data import SCENARIO_호우, SCENARIO_태풍, SCENARIO_대설, SCENARIO_지진, SCENARIO_산불, SHELTERS, AWS_STATIONS, FACILITIES

SCENARIOS = {"호우": SCENARIO_호우, "태풍": SCENARIO_태풍, "대설": SCENARIO_대설,
             "지진": SCENARIO_지진, "산불": SCENARIO_산불}
TIER_ORDER = ["관심", "주의", "경계", "심각"]
DISASTER_TYPES = ["호우", "태풍", "대설", "산불", "지진"]

MOBILITY_RADIUS = {"도보": 1.5, "차량": 5.0, "휠체어": 0.5}
INSTITUTION_TYPES = ["병원", "요양시설", "학교", "어린이집", "장애인시설", "공장", "기타"]
EVAC_MEANS_RADIUS = {"도보": 1.5, "자체 차량": 5.0, "버스(수송차량 필요)": 8.0}

# 기관유형별 교통약자 접근성 요구 여부(다수 거동불편자 추정)
INSTITUTION_NEEDS_ACCESSIBLE = {"병원": True, "요양시설": True, "장애인시설": True,
                                 "학교": False, "어린이집": False, "공장": False, "기타": False}
INSTITUTION_NEEDS_MEDICAL = {"병원": True, "요양시설": False, "장애인시설": False,
                              "학교": False, "어린이집": False, "공장": False, "기타": False}


def haversine_km(lat1, lon1, lat2, lon2):
    R = 6371
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlmb = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlmb / 2) ** 2
    return R * 2 * math.asin(math.sqrt(a))


def nearest_aws(lat, lon):
    best = None
    for s in AWS_STATIONS:
        d = haversine_km(lat, lon, float(s["위도"]), float(s["경도"]))
        if best is None or d < best[0]:
            best = (d, s)
    return best


def determine_tier(disaster_type, station):
    """실시간 관측값을 시나리오 임계값과 비교해 4단계 위험등급을 자동 판정.
    반환: (tier, 설명문구, 데이터한계여부)"""
    if disaster_type == "호우":
        val = float(station["강수량(mm)"] or 0)
        table = SCENARIO_호우
        key = "시간당 강우량(mm/h)"
        unit = "mm/h(관측 강수량으로 근사)"
    elif disaster_type == "태풍":
        val = float(station["풍속(m/s)"] or 0)
        table = SCENARIO_태풍
        key = "풍속(m/s)"
        unit = "m/s"
    elif disaster_type == "산불":
        # 산불 시나리오의 '대피 권고 단계' 필드를 실시간 풍속으로 자동 매칭
        # (실효습도 등 다른 요인은 관측 데이터가 없어 반영하지 못하는 한계가 있음)
        val = float(station["풍속(m/s)"] or 0)
        table = SCENARIO_산불
        matched_idx = 0
        for i, row in enumerate(table):
            if val >= float(row["풍속(m/s)"]):
                matched_idx = i
        raw_tier = table[matched_idx]["대피 권고 단계"]
        tier = raw_tier.split("(")[0]  # '심각(강제대피)' → '심각'
        desc = (f"실시간 관측 풍속 {val}m/s 기준 자동 판정 (참조: {table[matched_idx]['scenario_id']} "
                f"{table[matched_idx]['시나리오명']}, 대피권고: {raw_tier}). "
                f"※ 실효습도 등 산불 확산에 영향을 주는 다른 요인은 실시간 데이터가 없어 반영되지 않았습니다.")
        return tier, desc, False
    else:
        # 대설·지진: 실시간 관측 데이터 없음 → 기본값(관심) + 한계 안내
        note = {
            "대설": "AWS 관측 데이터에 적설량 항목이 없어 실시간 자동판정이 불가합니다.",
            "지진": "지진 규모·진앙 정보를 제공하는 실시간 관측망이 연동되어 있지 않습니다.",
        }[disaster_type]
        return "관심", f"{note} (데모 기본값: 관심 단계)", True

    # 임계값 이하에서 가장 높은 단계 찾기 (없으면 관심)
    matched_idx = 0
    for i, row in enumerate(table):
        if val >= float(row[key]):
            matched_idx = i
    tier = TIER_ORDER[min(matched_idx // 3, 3)] if matched_idx < 9 else "심각"
    # 관심(0,1) 주의(2,3,4) 경계(5,6,7) 심각(8,9) 형태로 재매핑
    if matched_idx <= 1:
        tier = "관심"
    elif matched_idx <= 4:
        tier = "주의"
    elif matched_idx <= 7:
        tier = "경계"
    else:
        tier = "심각"
    desc = f"실시간 관측값 {val}{unit} 기준 자동 판정 (참조: {table[matched_idx]['scenario_id']} {table[matched_idx]['시나리오명']})"
    return tier, desc, False


def is_walk_limited(move_mode: str) -> bool:
    return move_mode == "휠체어"


def find_shelters(lat, lon, radius_km, disaster_type, require_accessible=False,
                   require_pet=False, require_medical=False, min_capacity=0, top_n=3):
    cands = []
    for s in SHELTERS:
        if disaster_type in ("호우", "태풍", "대설"):
            if disaster_type not in str(s["재난유형 적합성(호우/태풍/대설)"]):
                continue
        # 산불/지진은 대피소 유형 태그가 없으므로 재난유형 필터를 적용하지 않음(전체 후보 대상)
        if require_accessible:
            acc = s["교통약자 접근성(경사로·엘리베이터)"]
            if "경사로 O" not in acc and "엘리베이터 O" not in acc:
                continue
        if require_pet and s["반려동물 동반 가능여부"] == "불가":
            continue
        if require_medical and s.get("의료 지원 가능 여부") != "O":
            continue
        try:
            if int(s["현재 잔여 수용가능인원(명)"]) < min_capacity:
                continue
        except (ValueError, TypeError):
            pass
        d = haversine_km(lat, lon, s["위도"], s["경도"])
        if d <= radius_km:
            cands.append((d, s))
    cands.sort(key=lambda x: x[0])
    return cands[:top_n]


def nearby_hazard_note(lat, lon, disaster_type):
    """반경 내 취약시설 데이터의 '인접 재해위험지구 유형'을 빌려와
    주변 위험요소 설명으로 근사 사용(실제 서비스에서는 좌표기반 위험지구 데이터 필요).
    재난유형이 일치하는 시설을 우선 탐색하고, 없으면 최근접 시설로 대체."""
    matched, any_nearby = None, None
    for f in FACILITIES:
        d = haversine_km(lat, lon, f["위도"], f["경도"])
        if any_nearby is None or d < any_nearby[0]:
            any_nearby = (d, f)
        if f["주요 재해유형"] == disaster_type and d <= 5.0:
            if matched is None or d < matched[0]:
                matched = (d, f)
    chosen = matched or (any_nearby if any_nearby and any_nearby[0] <= 3.0 else None)
    if chosen:
        return f"{chosen[1]['인접 재해위험지구 유형']} (인근 {chosen[0]:.1f}km 지점 사례 기준 참고)"
    generic = {
        "호우": "인근 하천·저지대 침수 가능성 일반 유의",
        "태풍": "강풍에 의한 시설물·간판 낙하 가능성 일반 유의",
        "대설": "결빙 구간 발생 가능성 일반 유의",
        "산불": "산림 인접 여부 확인 필요",
        "지진": "노후 건축물·옹벽 붕괴 가능성 일반 유의",
    }
    return generic.get(disaster_type, "특이 위험요소 확인되지 않음")


# ---------- 개인 ----------
def analyze_individual(location: dict, disaster_type: str, move_mode: str, companion: str) -> dict:
    lat, lon = location["lat"], location["lon"]
    dist_aws, station = nearest_aws(lat, lon)
    tier, tier_desc, data_limited = determine_tier(disaster_type, station)

    walk_limited = is_walk_limited(move_mode)
    radius = MOBILITY_RADIUS[move_mode]
    require_pet = companion == "반려동물"

    shelters = find_shelters(lat, lon, radius, disaster_type,
                              require_accessible=walk_limited, require_pet=require_pet)

    lines = []
    lines.append(f"**현재 재난 위험도**: {disaster_type} / **'{tier}'** 단계. {tier_desc}")

    vuln = []
    if move_mode == "휠체어":
        vuln.append("휠체어 이용자 → 교통약자로 자동 분류, 경사로·엘리베이터 구비 대피소만 추천")
    if companion == "어린이":
        vuln.append("어린이 동반 → 이동 시 안전 확보 우선 필요")
    if companion == "노약자":
        vuln.append("노약자 동반 → 무리한 장거리 이동 지양 필요")
    if companion == "반려동물":
        vuln.append("반려동물 동반 → 동반 가능 대피소만 추천")
    lines.append("**대상 특성 반영**: " + ("; ".join(vuln) if vuln else "특이사항 없음") + f" (이동수단: {move_mode})")

    if data_limited:
        lines.append(f"※ 데이터 한계 안내: {disaster_type}은(는) 실시간 자동판정 데이터가 없어 기본값(관심)을 표시하고 있습니다. 실제 상황은 관할 기관 발표를 반드시 함께 확인하십시오.")

    no_shelter_message = None
    if not shelters:
        no_shelter_message = f"반경 {radius}km 이내 조건에 맞는 대피소가 없습니다. 자력 이동을 시도하지 말고 119에 연락해 이송 지원을 요청하십시오."

    return {
        "text": "\n\n".join(lines),
        "shelters": shelters,
        "lat": lat, "lon": lon, "radius_km": radius,
        "move_mode": move_mode,
        "require_accessible": walk_limited,
        "require_pet": require_pet,
        "no_shelter_message": no_shelter_message,
        "tier": tier,
    }


# ---------- 기관 ----------
def analyze_institution(location: dict, institution_type: str, disaster_type: str,
                         evac_count: int, evac_means: str) -> dict:
    lat, lon = location["lat"], location["lon"]
    dist_aws, station = nearest_aws(lat, lon)
    tier, tier_desc, data_limited = determine_tier(disaster_type, station)

    radius = EVAC_MEANS_RADIUS.get(evac_means, 3.0)
    require_accessible = INSTITUTION_NEEDS_ACCESSIBLE.get(institution_type, False)
    require_medical = INSTITUTION_NEEDS_MEDICAL.get(institution_type, False)

    shelters = find_shelters(lat, lon, radius, disaster_type,
                              require_accessible=require_accessible,
                              require_medical=require_medical,
                              min_capacity=evac_count)

    hazard = nearby_hazard_note(lat, lon, disaster_type)

    sec1 = f"**① 현재 재난 위험도**: {disaster_type} / **'{tier}'** 단계. {tier_desc}"
    if data_limited:
        sec1 += f" (※ {disaster_type} 실시간 자동판정 데이터 없음 → 기본값 표시, 관할 기관 발표 확인 필요)"

    sec2 = f"**② 기관 주변 위험 요소**: {hazard}"

    if shelters:
        d, s = shelters[0]
        sec4 = (f"**④ 단체 이동 경로 및 주의사항**: {s['접근가능경로']} (이동수단: {s['접근경로 상세(수단)']}). "
                f"{institution_type} 특성상 " +
                ("거동불편자 우선 이송 순서를 사전에 정하고, " if require_accessible else "") +
                f"단체 인솔자를 지정하여 인원 점검을 병행할 것.")
    else:
        sec4 = "**④ 단체 이동 경로 및 주의사항**: 대피소 미확보 상태이므로 관할 재난안전대책본부와 사전 이송 목적지를 즉시 협의할 것."

    text = "\n\n".join([sec1, sec2, sec4])

    no_shelter_message = None
    if not shelters:
        no_shelter_message = f"반경 {radius}km 이내 조건({evac_count}명 수용 등)에 맞는 대피소가 없습니다. 광역 이송 또는 외부 수송자원 지원이 필요합니다."

    return {
        "text": text,
        "shelters": shelters,
        "lat": lat, "lon": lon, "radius_km": radius,
        "move_mode": evac_means,
        "require_accessible": require_accessible,
        "require_pet": False,
        "no_shelter_message": no_shelter_message,
        "evac_count": evac_count,
        "tier": tier,
    }
