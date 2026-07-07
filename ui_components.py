# ui_components.py
# "추천 대피소" 카드와 "운영 모니터링" 박스를 SafePath 브랜드 톤으로 렌더링합니다.

from theme import PRIMARY, PRIMARY_TINT, SLATE, LINE, TIER_COLORS, TIER_TINTS, clean as _clean

WALK_MIN_PER_KM = 12       # 도보 약 5km/h
WHEELCHAIR_MIN_PER_KM = 15
DRIVE_MIN_PER_KM = 2       # 차량/버스 약 30km/h


def estimate_travel(dist_km: float, move_mode: str) -> str:
    if move_mode in ("차량", "자체 차량", "버스(수송차량 필요)"):
        minutes = max(1, round(dist_km * DRIVE_MIN_PER_KM))
        label = "차량"
    elif move_mode == "휠체어":
        minutes = max(1, round(dist_km * WHEELCHAIR_MIN_PER_KM))
        label = "도보(휠체어)"
    else:
        minutes = max(1, round(dist_km * WALK_MIN_PER_KM))
        label = "도보"
    return f"{label} {minutes}분"


def flood_bypass_label(route_text: str) -> str:
    if "우회" in route_text:
        return "안전 경로 확보"
    if any(k in route_text for k in ["침수", "통제", "폐쇄", "결빙", "위험"]):
        return "경로 주의 필요"
    return "특이사항 없음"


def accessibility_label(acc_text: str) -> str:
    if "엘리베이터 O" in acc_text:
        return "엘리베이터 O"
    if "경사로 O" in acc_text:
        return "경사로 O"
    return "시설 없음"


def _metric_block(icon, label, value):
    return f"""
    <div style="flex:1;text-align:center;">
      <div style="color:#888;font-size:0.72rem;margin-bottom:4px;">{icon} {label}</div>
      <div style="font-weight:600;font-size:0.9rem;color:#222;">{value}</div>
    </div>
    """


def shelter_cards_html(shelters, move_mode, show_metrics_for_primary=True):
    """shelters: [(거리km, shelter_dict), ...] (거리순 정렬된 상태)"""
    if not shelters:
        return ""

    cards = []
    badges = ["최우선", "차선안", "차선안"]
    badge_colors = [PRIMARY, SLATE, SLATE]
    badge_bg = [PRIMARY_TINT, "#F0F0F0", "#F0F0F0"]

    for i, (dist, s) in enumerate(shelters):
        badge = badges[i] if i < len(badges) else "차선안"
        b_color = badge_colors[i] if i < len(badge_colors) else SLATE
        b_bg = badge_bg[i] if i < len(badge_bg) else "#F0F0F0"
        cap = s["현재 잔여 수용가능인원(명)"]
        status = s["개방여부"]
        check_color = PRIMARY if status == "개방" else "#bdbdbd"

        header = f"""
        <div style="display:flex;justify-content:space-between;align-items:flex-start;">
          <div style="display:flex;align-items:center;gap:8px;">
            <span style="color:{check_color};font-size:1.1rem;">●</span>
            <span style="font-weight:700;font-size:1.02rem;color:#1a1a1a;">{s['대피소명']}</span>
            <span style="background:{b_bg};color:{b_color};padding:2px 10px;border-radius:10px;font-size:0.72rem;font-weight:600;">{badge}</span>
          </div>
          <div style="text-align:right;">
            <div style="color:#888;font-size:0.7rem;">잔여 수용</div>
            <div class="sp-databox" style="font-weight:700;color:{PRIMARY};font-size:1.05rem;">👥 {cap}명</div>
          </div>
        </div>
        <div class="sp-databox" style="color:#888;font-size:0.82rem;margin:6px 0 0 26px;">직선거리 {dist*1000:.0f}m · {status} 중</div>
        """

        metrics = ""
        if i == 0 and show_metrics_for_primary:
            acc = accessibility_label(s["교통약자 접근성(경사로·엘리베이터)"])
            flood = flood_bypass_label(s["접근가능경로"])
            eta = estimate_travel(dist, move_mode)
            metrics = f"""
            <hr style="margin:12px 0;border:none;border-top:1px solid #eee;">
            <div style="display:flex;">
              {_metric_block("♿", "교통약자", acc)}
              {_metric_block("💧", "침수 우회", flood)}
              {_metric_block("🕐", "예상 이동", eta)}
            </div>
            """

        card = f"""
        <div style="border:1px solid {LINE};border-radius:14px;padding:18px 20px;margin-bottom:12px;background:#fff;">
          {header}
          {metrics}
        </div>
        """
        cards.append(card)

    return _clean(f"""
    <div style="margin-top:8px;">
      <div style="font-weight:700;font-size:1.05rem;margin-bottom:10px;">◎ 추천 대피소</div>
      {''.join(cards)}
    </div>
    """)


def monitoring_box_html(bullets):
    items = "".join(f'<li style="margin-bottom:6px;">{b}</li>' for b in bullets)
    return _clean(f"""
    <div style="margin-top:18px;">
      <div style="font-weight:700;font-size:1.02rem;margin-bottom:10px;">🗒 운영 모니터링</div>
      <div style="background:#f5f5f5;border-radius:12px;padding:16px 20px;">
        <ul style="margin:0;padding-left:18px;color:#333;font-size:0.9rem;">
          {items}
        </ul>
      </div>
    </div>
    """)


def default_monitoring_bullets(shelters, disaster_type):
    if not shelters:
        return ["대피소 미확보 상태 — 관할 기관과 대체 이송 방안 협의 필요"]
    bullets = ["대피소 개방 상태 10분 간격 확인", "잔여 수용 인원 실시간 모니터링"]
    _, top = shelters[0]
    if "우회" in top["접근가능경로"] or disaster_type in ("호우", "태풍"):
        bullets.append("침수·강풍 우회 경로 유지 여부 점검")
    if disaster_type == "대설":
        bullets.append("진입로 결빙·제설 상태 점검")
    return bullets


def no_shelter_html(message: str):
    return _clean(f"""
    <div style="border:1px solid #ffcdd2;background:#fff5f5;border-radius:12px;padding:16px 20px;margin-top:8px;">
      <span style="color:#c62828;font-weight:700;">⚠ 긴급 이송 필요</span>
      <div style="margin-top:6px;color:#333;font-size:0.9rem;">{message}</div>
    </div>
    """)


def masthead_html():
    """SafePath 브랜드 헤더. 앱 최상단에 한 번만 렌더링."""
    return _clean("""
    <div class="sp-stripe"></div>
    <div class="sp-masthead">
      <div class="sp-logomark">🧭</div>
      <div>
        <div class="sp-wordmark">SafePath</div>
        <div class="sp-subtitle">AI 기반 실시간 재난 대피소 안내 네비게이션</div>
      </div>
    </div>
    """)


def tier_banner_html(disaster_type: str, tier: str):
    """분석 결과의 위험단계를 색으로 보여주는 상태 배너.
    브랜드 컬러(세이프티 그린)가 실제 위험도에 따라 초록→황색→주황→적색으로 바뀌는
    SafePath의 시그니처 요소."""
    color = TIER_COLORS.get(tier, SLATE)
    tint = TIER_TINTS.get(tier, "#F0F0F0")
    return _clean(f"""
    <div style="height:5px;border-radius:3px;background:{color};margin-bottom:14px;"></div>
    <div style="display:flex;align-items:center;gap:10px;margin-bottom:16px;">
      <span class="sp-tier-chip" style="background:{tint};color:{color};">{disaster_type} · {tier} 단계</span>
    </div>
    """)
