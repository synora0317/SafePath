# theme.py
# SafePath 브랜드 토큰 (색상/폰트) 및 전역 CSS

PRIMARY = "#1B7F4C"       # 세이프티 그린 (브랜드 메인)
PRIMARY_TINT = "#E4F2EA"  # 배지/배경용 옅은 초록
INK = "#10241C"           # 본문 텍스트
SLATE = "#5B6B63"         # 보조 텍스트
BG = "#F7F9F7"            # 전체 배경
LINE = "#E3E8E5"          # 테두리

TIER_COLORS = {
    "관심": "#1B7F4C",
    "주의": "#D89B1D",
    "경계": "#E4572E",
    "심각": "#C81E3A",
}
TIER_TINTS = {
    "관심": "#E4F2EA",
    "주의": "#FBF0DA",
    "경계": "#FBE4DB",
    "심각": "#FBE0E4",
}

GLOBAL_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@500;700&family=IBM+Plex+Sans:wght@400;500;600&family=IBM+Plex+Mono:wght@500&display=swap');

.stApp {
  background: #F7F9F7;
}
html, body, [class*="css"] {
  font-family: 'IBM Plex Sans', sans-serif;
}

.sp-stripe {
  height: 5px;
  border-radius: 3px;
  margin-bottom: 16px;
  background: #5B6B63;
}
.sp-masthead {
  display: flex;
  align-items: center;
  gap: 14px;
  margin-bottom: 22px;
}
.sp-logomark {
  width: 42px; height: 42px;
  border-radius: 11px;
  background: #1B7F4C;
  display: flex; align-items: center; justify-content: center;
  font-size: 20px;
  flex-shrink: 0;
}
.sp-wordmark {
  font-family: 'Space Grotesk', sans-serif;
  font-weight: 700;
  font-size: 1.9rem;
  color: #10241C;
  letter-spacing: -0.02em;
  line-height: 1.1;
}
.sp-subtitle {
  font-family: 'IBM Plex Sans', sans-serif;
  font-size: 0.82rem;
  color: #5B6B63;
  letter-spacing: 0.03em;
  margin-top: 2px;
}
.sp-databox, .sp-databox * {
  font-family: 'IBM Plex Mono', monospace !important;
}
.sp-tier-chip {
  display: inline-block;
  padding: 3px 12px;
  border-radius: 20px;
  font-weight: 600;
  font-size: 0.85rem;
  font-family: 'IBM Plex Sans', sans-serif;
}

.sp-role-label {
  font-family: 'IBM Plex Sans', sans-serif;
  font-size: 1.5rem;
  font-weight: 600;
  color: #10241C;
  margin: 6px 0 2px 0;
}
.sp-step-label {
  font-family: 'IBM Plex Sans', sans-serif;
  font-size: 0.8rem;
  color: #5B6B63;
  font-weight: 500;
  letter-spacing: 0.02em;
  margin: 14px 0 -6px 0;
}

button[kind="primary"] {
  background-color: #1B7F4C !important;
  border-color: #1B7F4C !important;
}
button[kind="primary"]:hover {
  background-color: #156b40 !important;
  border-color: #156b40 !important;
}
</style>
"""


def clean(html: str) -> str:
    """줄 앞 공백 제거 (마크다운이 코드블록으로 오인하는 것 방지)"""
    return "\n".join(line.lstrip() for line in html.strip().split("\n"))
