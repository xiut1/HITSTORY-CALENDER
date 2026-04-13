#!/usr/bin/env python3
"""
위키백과 '오늘의 역사' 크롤링 → historyEvents.ts 자동 삽입 스크립트

사용법: python3 crawl_wiki_history.py <월(1-12)>
        python3 crawl_wiki_history.py all          # 1~12월 전체
        python3 crawl_wiki_history.py 2 --dry-run  # 파일 변경 없이 미리보기
예시: python3 crawl_wiki_history.py 2
"""

import os
import re
import sys
import urllib.parse
import urllib.request

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
TS_FILE = os.path.join(SCRIPT_DIR, "..", "src", "lib", "historyEvents.ts")

# ══════════════════════════════════════════════════════════
# 국가 매핑
# 우선순위: 키가 긴 항목이 먼저 매칭되므로
# 복합 국명(신성로마제국, 오스트리아-헝가리 등)을 짧은 것보다 먼저 처리.
# COUNTRY_MAP 딕셔너리 자체는 정렬 불필요 — guess_country() 내부에서 정렬.
# ══════════════════════════════════════════════════════════
COUNTRY_MAP: dict[str, str] = {
    # ── 한국 ──
    "대한민국": "한국", "한국": "한국", "조선": "한국", "고려": "한국",
    "백제": "한국", "신라": "한국", "고구려": "한국", "발해": "한국",
    "대한제국": "한국", "가야": "한국", "삼한": "한국",

    # ── 북한 ──
    "조선민주주의인민공화국": "북한", "북한": "북한",

    # ── 일본 ──
    "일본": "일본", "에도": "일본", "도쿠가와": "일본", "메이지": "일본",
    "야마토": "일본", "막부": "일본",

    # ── 중국 ──
    "중화인민공화국": "중국", "중화민국": "중국", "중국": "중국",
    "청나라": "중국", "명나라": "중국", "송나라": "중국", "원나라": "중국",
    "금나라": "중국", "당나라": "중국", "한나라": "중국", "수나라": "중국",
    "진나라": "중국", "주나라": "중국", "상나라": "중국", "하나라": "중국",
    "위나라": "중국", "촉나라": "중국", "오나라": "중국", "춘추": "중국",

    # ── 대만 ──
    "대만": "대만", "타이완": "대만",

    # ── 홍콩 ──
    "홍콩": "홍콩",

    # ── 몽골 ──
    "몽골": "몽골", "몽골 제국": "몽골",

    # ── 미국 ──
    "미합중국": "미국", "미국": "미국", "하와이": "미국", "알래스카": "미국",

    # ── 캐나다 ──
    "캐나다": "캐나다",

    # ── 영국 ──
    "그레이트브리튼": "영국", "브리튼": "영국", "잉글랜드": "영국",
    "스코틀랜드": "영국", "웨일스": "영국", "북아일랜드": "영국", "영국": "영국",

    # ── 아일랜드 ──
    "아일랜드": "아일랜드",

    # ── 프랑스 ──
    "프랑스": "프랑스", "프랑크": "프랑스", "갈리아": "프랑스",

    # ── 독일 ──
    "신성 로마 제국": "독일", "신성로마제국": "독일",
    "프로이센": "독일", "바이마르": "독일", "나치 독일": "독일",
    "나치독일": "독일", "서독": "독일", "동독": "독일", "독일": "독일",

    # ── 이탈리아 ──
    "로마 제국": "이탈리아", "로마제국": "이탈리아",
    "이탈리아": "이탈리아", "베네치아": "이탈리아",
    "피렌체": "이탈리아", "바티칸": "이탈리아", "시칠리아": "이탈리아",

    # ── 러시아 ──
    "소비에트 연방": "러시아", "소비에트연방": "러시아",
    "소련": "러시아", "소비에트": "러시아",
    "러시아 제국": "러시아", "러시아": "러시아",

    # ── 스페인 ──
    "카스티야": "스페인", "아라곤": "스페인", "스페인": "스페인",

    # ── 포르투갈 ──
    "포르투갈": "포르투갈",

    # ── 네덜란드 ──
    "네덜란드": "네덜란드",

    # ── 벨기에 ──
    "벨기에": "벨기에",

    # ── 스위스 ──
    "스위스": "스위스",

    # ── 오스트리아 ──
    "오스트리아-헝가리": "오스트리아", "오스트리아 헝가리": "오스트리아",
    "합스부르크": "오스트리아", "오스트리아": "오스트리아",

    # ── 헝가리 ──
    "헝가리": "헝가리",

    # ── 덴마크 ──
    "덴마크": "덴마크",

    # ── 스웨덴 ──
    "스웨덴": "스웨덴",

    # ── 노르웨이 ──
    "노르웨이": "노르웨이",

    # ── 핀란드 ──
    "핀란드": "핀란드",

    # ── 폴란드 ──
    "폴란드": "폴란드",

    # ── 그리스 ──
    "비잔티움 제국": "그리스", "비잔틴 제국": "그리스",
    "비잔티움": "그리스", "비잔틴": "그리스",
    "그리스": "그리스",

    # ── 체코 ──
    "체코슬로바키아": "체코", "체코": "체코",

    # ── 루마니아 ──
    "루마니아": "루마니아",

    # ── 불가리아 ──
    "불가리아": "불가리아",

    # ── 세르비아 ──
    "유고슬라비아": "세르비아", "세르비아": "세르비아",

    # ── 크로아티아 ──
    "크로아티아": "크로아티아",

    # ── 우크라이나 ──
    "우크라이나": "우크라이나",

    # ── 기타 유럽 ──
    "슬로바키아": "슬로바키아", "알바니아": "알바니아",
    "북마케도니아": "북마케도니아", "마케도니아": "북마케도니아",
    "몰도바": "몰도바", "라트비아": "라트비아",
    "리투아니아": "리투아니아", "에스토니아": "에스토니아",
    "아이슬란드": "아이슬란드", "보스니아": "보스니아",
    "슬로베니아": "슬로베니아", "룩셈부르크": "룩셈부르크",
    "몰타": "몰타", "안도라": "안도라", "모나코": "모나코",
    "리히텐슈타인": "리히텐슈타인", "산마리노": "산마리노",

    # ── 터키 / 오스만 ──
    "오스만 제국": "터키", "오스만제국": "터키",
    "오스만": "터키", "튀르키예": "터키", "터키": "터키",

    # ── 이란 / 페르시아 ──
    "아케메네스": "이란", "사산": "이란",
    "페르시아": "이란", "이란": "이란",

    # ── 이라크 ──
    "바빌로니아": "이라크", "바빌론": "이라크",
    "메소포타미아": "이라크", "이라크": "이라크",

    # ── 이스라엘 ──
    "이스라엘": "이스라엘",

    # ── 팔레스타인 ──
    "팔레스타인": "팔레스타인",

    # ── 사우디 ──
    "사우디아라비아": "사우디아라비아", "사우디": "사우디아라비아",

    # ── 기타 중동 ──
    "시리아": "시리아", "레바논": "레바논", "요르단": "요르단",
    "쿠웨이트": "쿠웨이트", "아랍에미리트": "아랍에미리트", "UAE": "아랍에미리트",
    "카타르": "카타르", "바레인": "바레인", "오만": "오만", "예멘": "예멘",

    # ── 아프가니스탄 ──
    "아프가니스탄": "아프가니스탄",

    # ── 인도 / 남아시아 ──
    "무굴 제국": "인도", "무굴제국": "인도", "무굴": "인도",
    "인도": "인도",
    "파키스탄": "파키스탄", "방글라데시": "방글라데시",
    "스리랑카": "스리랑카", "네팔": "네팔", "부탄": "부탄",
    "몰디브": "몰디브",

    # ── 동남아시아 ──
    "베트남": "베트남", "시암": "태국", "태국": "태국",
    "필리핀": "필리핀", "인도네시아": "인도네시아",
    "말레이시아": "말레이시아", "싱가포르": "싱가포르",
    "미얀마": "미얀마", "버마": "미얀마",
    "캄보디아": "캄보디아", "크메르": "캄보디아",
    "라오스": "라오스", "브루나이": "브루나이", "동티모르": "동티모르",

    # ── 중앙아시아 ──
    "카자흐스탄": "카자흐스탄", "키르기스스탄": "키르기스스탄",
    "타지키스탄": "타지키스탄", "투르크메니스탄": "투르크메니스탄",
    "우즈베키스탄": "우즈베키스탄",

    # ── 코카서스 ──
    "아제르바이잔": "아제르바이잔", "아르메니아": "아르메니아",
    "조지아": "조지아",

    # ── 기타 아시아 ──
    "키프로스": "키프로스",

    # ── 이집트 ──
    "파라오": "이집트", "이집트": "이집트",

    # ── 아프리카 ──
    "남아프리카공화국": "남아프리카공화국", "남아프리카": "남아프리카공화국",
    "남아공": "남아프리카공화국",
    "나이지리아": "나이지리아", "케냐": "케냐", "에티오피아": "에티오피아",
    "가나": "가나", "콩고 민주 공화국": "콩고민주공화국",
    "콩고민주공화국": "콩고민주공화국", "콩고": "콩고",
    "탄자니아": "탄자니아", "알제리": "알제리", "모로코": "모로코",
    "튀니지": "튀니지", "리비아": "리비아", "수단": "수단",
    "남수단": "남수단", "르완다": "르완다", "우간다": "우간다",
    "앙골라": "앙골라", "모잠비크": "모잠비크", "마다가스카르": "마다가스카르",
    "말리": "말리", "니제르": "니제르", "차드": "차드",
    "기니비사우": "기니비사우", "기니": "기니",
    "부르키나파소": "부르키나파소", "코트디부아르": "코트디부아르",
    "라이베리아": "라이베리아", "시에라리온": "시에라리온",
    "토고": "토고", "에리트레아": "에리트레아", "가봉": "가봉",
    "보츠와나": "보츠와나", "레소토": "레소토", "에스와티니": "에스와티니",
    "나미비아": "나미비아", "모리셔스": "모리셔스",
    "적도기니": "적도기니", "적도 기니": "적도기니",
    "중앙아프리카공화국": "중앙아프리카공화국",
    "중앙아프리카 공화국": "중앙아프리카공화국",
    "소말리아": "소말리아", "지부티": "지부티",
    "카보베르데": "카보베르데", "상투메프린시페": "상투메프린시페",
    "코모로": "코모로", "세이셸": "세이셸",
    "부룬디": "부룬디", "잠비아": "잠비아", "짐바브웨": "짐바브웨",
    "말라위": "말라위",

    # ── 남아메리카 ──
    "브라질": "브라질", "아르헨티나": "아르헨티나",
    "칠레": "칠레", "콜롬비아": "콜롬비아",
    "잉카": "페루", "페루": "페루",
    "베네수엘라": "베네수엘라", "에콰도르": "에콰도르",
    "볼리비아": "볼리비아", "파라과이": "파라과이",
    "우루과이": "우루과이", "수리남": "수리남", "가이아나": "가이아나",

    # ── 중앙아메리카 / 카리브 ──
    "아즈텍": "멕시코", "멕시코": "멕시코",
    "쿠바": "쿠바", "파나마": "파나마", "코스타리카": "코스타리카",
    "과테말라": "과테말라", "온두라스": "온두라스", "니카라과": "니카라과",
    "엘살바도르": "엘살바도르", "벨리즈": "벨리즈",
    "아이티": "아이티", "도미니카공화국": "도미니카공화국",
    "도미니카 공화국": "도미니카공화국",
    "푸에르토리코": "푸에르토리코", "자메이카": "자메이카",
    "바하마": "바하마", "바베이도스": "바베이도스",
    "트리니다드토바고": "트리니다드토바고", "트리니다드 토바고": "트리니다드토바고",
    "그레나다": "그레나다", "세인트루시아": "세인트루시아",
    "도미니카연방": "도미니카연방", "도미니카 연방": "도미니카연방",
    "세인트키츠네비스": "세인트키츠네비스",
    "앤티가바부다": "앤티가바부다",

    # ── 오세아니아 ──
    "오스트레일리아": "호주", "호주": "호주",
    "뉴질랜드": "뉴질랜드", "파푸아뉴기니": "파푸아뉴기니",
    "피지": "피지", "팔라우": "팔라우", "투발루": "투발루",
    "바누아투": "바누아투", "사모아": "사모아", "나우루": "나우루",
    "마샬 제도": "마샬제도", "마샬제도": "마샬제도",
    "솔로몬 제도": "솔로몬제도", "솔로몬제도": "솔로몬제도",
    "미크로네시아연방": "미크로네시아연방",
    "미크로네시아 연방": "미크로네시아연방",
    "키리바시": "키리바시", "통가": "통가",

    # ── 국제기구 / 범지구 ──
    "국제연합": "세계", "유엔": "세계", "UN": "세계",
    "NATO": "세계", "나토": "세계",
    "올림픽": "세계", "월드컵": "세계",
    "유럽 연합": "세계", "유럽연합": "세계", "EU": "세계",
}

# ── 단어 경계 없이 매칭하면 안 되는 키워드 (부분문자열 오매칭 방지) ──
# 예: "로마" → "로마자", "이란" → "이란성"
BOUNDARY_REQUIRED: set[str] = {
    "로마", "이란", "나치", "한국", "가나",
    "마케도니아", "조지아", "오만", "통가",
}

# ── 카테고리 세분화 키워드 ──
CATEGORY_KEYWORDS: dict[str, list[str]] = {
    "war": ["전쟁", "전투", "침공", "공격", "폭격", "항복", "휴전", "정전", "선전포고",
            "반란", "봉기", "혁명", "쿠데타", "내전", "학살", "독립전쟁", "포위"],
    "politics": ["선거", "대통령", "국왕", "총리", "황제", "즉위", "퇴위", "조약",
                 "헌법", "독립", "건국", "수립", "선포", "합병", "통일", "분단",
                 "식민", "해방", "국교", "외교", "정부", "의회"],
    "science": ["발명", "발견", "발사", "착륙", "우주", "위성", "탐사", "실험",
                "노벨", "특허", "과학", "원자", "핵", "DNA", "컴퓨터", "인터넷",
                "백신", "항생제", "물리학", "천문"],
    "culture": ["올림픽", "월드컵", "영화", "음악", "문학", "예술", "축제",
                "박물관", "유네스코", "공연", "방송", "출판"],
    "disaster": ["지진", "태풍", "홍수", "화산", "쓰나미", "폭발", "사고",
                 "침몰", "추락", "붕괴", "전염병", "역병", "허리케인"],
}


# ══════════════════════════════════════════════════════════
# 유틸리티
# ══════════════════════════════════════════════════════════

def strip_html(text: str) -> str:
    """HTML 태그 제거"""
    return re.sub(r"<[^>]+>", "", text).strip()


def normalize_wiki_url(href: str) -> str:
    """상대/프로토콜 상대 경로를 절대 URL로 변환"""
    if href.startswith("//"):
        return "https:" + href
    if href.startswith("/"):
        return "https://ko.wikipedia.org" + href
    return href


def classify_subcategory(text: str) -> str | None:
    """이벤트 텍스트에서 세부 카테고리 태그 반환"""
    for tag, keywords in CATEGORY_KEYWORDS.items():
        for kw in keywords:
            if kw in text:
                return tag
    return None


def _find_keyword(text: str, keyword: str) -> int:
    """
    키워드를 텍스트에서 찾아 시작 인덱스를 반환.
    BOUNDARY_REQUIRED에 등록된 키워드는 단어 경계(공백·구두점·문자열 끝)를 요구.
    매칭 실패 시 -1 반환.
    """
    if keyword not in BOUNDARY_REQUIRED:
        return text.find(keyword)
    # 한국어 단어 경계: 키워드 앞뒤가 한글 음절이 아닌 경우에만 매칭
    pattern = r"(?<![가-힣])(" + re.escape(keyword) + r")(?![가-힣])"
    m = re.search(pattern, text)
    return m.start(1) if m else -1


def guess_country(text: str) -> str | list[str]:
    """
    텍스트에서 국가를 추측.
    - 긴 키워드 우선 매칭 (신성로마제국 > 로마)
    - BOUNDARY_REQUIRED 키워드는 단어 경계 확인
    - 복수 국가 발견 시 리스트 반환
    """
    found: list[tuple[int, int, str]] = []  # (position, keyword_len, country)

    for keyword, country in COUNTRY_MAP.items():
        idx = _find_keyword(text, keyword)
        if idx != -1:
            found.append((idx, len(keyword), country))

    if not found:
        return "세계"

    # 1차: 키워드 길이 내림차순 (긴 키워드 우선)
    # 2차: 등장 위치 오름차순 (앞에 나온 것 우선)
    found.sort(key=lambda x: (-x[1], x[0]))

    # 겹치는 범위 제거: 이미 소비된 위치 범위에 속하는 키워드는 제외
    consumed: list[tuple[int, int]] = []  # (start, end)
    unique_countries: list[str] = []
    seen_countries: set[str] = set()

    for pos, klen, country in found:
        # 이미 더 긴 키워드가 이 위치를 포함하고 있으면 스킵
        end = pos + klen
        overlapping = any(s <= pos < e or s < end <= e for s, e in consumed)
        if overlapping:
            continue
        consumed.append((pos, end))
        if country not in seen_countries:
            seen_countries.add(country)
            unique_countries.append(country)

    if not unique_countries:
        return "세계"
    if len(unique_countries) == 1:
        return unique_countries[0]
    return unique_countries


def is_known_country(name: str) -> bool:
    """COUNTRY_MAP에 등록된 키 또는 값인지 확인"""
    name = name.strip()
    return name in COUNTRY_MAP or name in COUNTRY_MAP.values()


def split_country_names(text: str) -> list[str]:
    """'·', '와', '과'로 구분된 국가명을 분리"""
    return [n.strip() for n in re.split(r"[·]|와\s|과\s", text) if n.strip()]


def is_country_name(text: str) -> bool:
    """텍스트가 나라 이름(들)인지 판별"""
    names = split_country_names(text)
    if not names:
        return False
    return all(is_known_country(n) for n in names)


def make_id(month: int, day: int, year: int, suffix: str = "") -> str:
    m = str(month).zfill(2)
    d = str(day).zfill(2)
    base = f"wiki-{m}{d}-{abs(year)}bc" if year < 0 else f"wiki-{m}{d}-{year}"
    return base + suffix


# ══════════════════════════════════════════════════════════
# HTML 파싱
# ══════════════════════════════════════════════════════════

def extract_bold_link_url(li_html: str) -> str | None:
    """<li> HTML에서 <b><a> 볼드 링크 URL 추출"""
    match = re.search(r'<b><a[^>]*href="([^"]*)"[^>]*>', li_html)
    if match:
        return normalize_wiki_url(match.group(1))
    return None


def extract_holiday_url(header_html: str, keyword: str) -> str | None:
    """헤더 HTML에서 키워드와 관련된 <b><a> 볼드 링크 URL 추출"""
    safe_kw = re.escape(keyword[:5]) if len(keyword) >= 5 else re.escape(keyword)
    pattern = re.compile(r'<b><a[^>]*href="([^"]*)"[^>]*>[^<]*' + safe_kw, re.DOTALL)
    match = pattern.search(header_html)
    if match:
        return normalize_wiki_url(match.group(1))
    return None


def parse_year_and_desc(text: str) -> tuple[int, str] | None:
    """'기원전 XXX년 - ...' 또는 'XXX년 - ...' 형식에서 연도와 설명 추출"""
    bc_match = re.match(r"기원전\s*(\d+)년\s*[-–]\s*(.+)", text)
    if bc_match:
        return -int(bc_match.group(1)), bc_match.group(2).strip()
    year_match = re.match(r"(\d{1,4})년\s*[-–]\s*(.+)", text)
    if year_match:
        return int(year_match.group(1)), year_match.group(2).strip()
    return None


def parse_holidays(header_html: str, header_text: str, month: int, day: int) -> list[dict]:
    """날짜 헤더의 기념일 텍스트를 파싱하여 holiday 이벤트 리스트로 반환"""
    holidays = []
    date_str = f"{str(month).zfill(2)}-{str(day).zfill(2)}"
    parts = [p.strip() for p in header_text.split(",") if p.strip()]

    for idx, part in enumerate(parts):
        country_match = re.match(r"(.+?)의\s+(.+)", part)
        is_country_pattern = False
        if country_match:
            candidate = country_match.group(1).strip()
            if is_country_name(candidate):
                is_country_pattern = True

        if is_country_pattern:
            countries_str = country_match.group(1).strip()
            holiday_name = country_match.group(2).strip()
            country_names = split_country_names(countries_str)

            for cn in country_names:
                cn = cn.strip()
                if not cn:
                    continue
                mapped = COUNTRY_MAP.get(cn, cn)
                hol_id = f"wiki-hol-{date_str}-{idx}-{mapped}"
                url = extract_holiday_url(header_html, holiday_name)
                holiday: dict = {
                    "id": hol_id,
                    "country": mapped,
                    "date": date_str,
                    "year": 2024,
                    "title": holiday_name,
                    "description": f"{mapped}의 {holiday_name}.",
                    "category": "holiday",
                }
                if url:
                    holiday["url"] = url
                holidays.append(holiday)
        else:
            hol_id = f"wiki-hol-{date_str}-{idx}"
            url = extract_holiday_url(header_html, part)
            holiday = {
                "id": hol_id,
                "country": "세계",
                "date": date_str,
                "year": 2024,
                "title": part,
                "description": part,
                "category": "holiday",
            }
            if url:
                holiday["url"] = url
            holidays.append(holiday)

    return holidays


def parse_history_items(section: str, month: int, day: int, seen_ids: set[str]) -> list[dict]:
    """날짜 섹션의 <ul> 안 <li> 항목들을 역사 이벤트로 파싱"""
    ul_match = re.search(r"<ul[^>]*>(.*?)</ul>", section, re.DOTALL)
    if not ul_match:
        return []

    events = []
    date_str = f"{str(month).zfill(2)}-{str(day).zfill(2)}"
    li_items = re.findall(r"<li>(.*?)</li>", ul_match.group(1), re.DOTALL)

    for li_idx, li in enumerate(li_items):
        url = extract_bold_link_url(li)
        text = strip_html(li).strip()
        text = re.sub(r"\(그림\)|\(사진\)|\(동영상\)", "", text).strip()

        parsed = parse_year_and_desc(text)
        if not parsed:
            continue
        year, desc = parsed

        event_id = make_id(month, day, year)
        if event_id in seen_ids:
            event_id = make_id(month, day, year, suffix=f"-{li_idx}")
        seen_ids.add(event_id)

        event: dict = {
            "id": event_id,
            "country": guess_country(desc),
            "date": date_str,
            "year": year,
            "title": desc,
            "description": desc,
            "category": "history",
        }
        subcategory = classify_subcategory(desc)
        if subcategory:
            event["subcategory"] = subcategory
        if url:
            event["url"] = url

        events.append(event)

    return events


def parse_events(html: str, month: int) -> list[dict]:
    """HTML에서 날짜 섹션과 이벤트를 파싱"""
    events = []
    seen_ids: set[str] = set()

    date_pattern = re.compile(rf'<b><a[^>]*>({month}월\s*(\d+)일)</a></b>')
    matches = list(date_pattern.finditer(html))

    for i, m in enumerate(matches):
        day = int(m.group(2))
        start_pos = m.end()
        end_pos = matches[i + 1].start() if i + 1 < len(matches) else start_pos + 5000
        section = html[start_pos:end_pos]

        # 기념일 파싱
        ul_start = section.find("<ul")
        if ul_start > 0:
            header_html = section[:ul_start]
            header_text = strip_html(header_html).strip(": \n\t")
            if header_text:
                events.extend(parse_holidays(header_html, header_text, month, day))

        # 역사 이벤트 파싱
        events.extend(parse_history_items(section, month, day, seen_ids))

    return events


# ══════════════════════════════════════════════════════════
# 출력 / 파일 업데이트
# ══════════════════════════════════════════════════════════

def format_ts(events: list[dict], month: int) -> str:
    lines = [f"  // --- 위키백과 오늘의 역사: {month}월 ---"]
    for e in events:
        title = e["title"].replace('"', '\\"')
        desc = e["description"].replace('"', '\\"')
        lines.append("  {")
        lines.append(f'    id: "{e["id"]}",')
        country = e["country"]
        if isinstance(country, list):
            items = ", ".join(f'"{c}"' for c in country)
            lines.append(f'    country: [{items}],')
        else:
            lines.append(f'    country: "{country}",')
        lines.append(f'    date: "{e["date"]}",')
        lines.append(f'    year: {e["year"]},')
        lines.append(f'    title: "{title}",')
        lines.append(f'    description: "{desc}",')
        lines.append(f'    category: "{e["category"]}",')
        if e.get("subcategory"):
            lines.append(f'    subcategory: "{e["subcategory"]}",')
        if "url" in e:
            url = e["url"].replace('"', '\\"')
            lines.append(f'    url: "{url}",')
        lines.append("  },")
    return "\n".join(lines)


def print_stats(events: list[dict]) -> None:
    """크롤링 결과 통계 출력"""
    history_count = sum(1 for e in events if e["category"] == "history")
    holiday_count = sum(1 for e in events if e["category"] == "holiday")
    world_count = sum(1 for e in events if e["country"] == "세계")
    print(f"  역사: {history_count}건, 공휴일: {holiday_count}건 (총 {len(events)}건)")
    print(f"  '세계'로 분류됨(미매칭): {world_count}건")

    country_counts: dict[str, int] = {}
    for e in events:
        c = e["country"]
        keys = c if isinstance(c, list) else [c]
        for k in keys:
            country_counts[k] = country_counts.get(k, 0) + 1
    top = sorted(country_counts.items(), key=lambda x: -x[1])[:7]
    print(f"  국가 TOP7: {', '.join(f'{k}({v})' for k, v in top)}")


def remove_existing_month_data(content: str, month: int) -> str:
    """TS 파일 내용에서 기존 월별 위키 데이터 블록 제거"""
    marker = f"  // --- 위키백과 오늘의 역사: {month}월 ---"
    if marker not in content:
        return content

    start_idx = content.index(marker)
    rest = content[start_idx + len(marker):]
    next_match = re.search(r"  // --- 위키백과 오늘의 역사: \d+월 ---", rest)
    bracket_pos = rest.find("];")

    if next_match and next_match.start() < bracket_pos:
        end_idx = start_idx + len(marker) + next_match.start()
    else:
        end_idx = start_idx + len(marker) + bracket_pos

    print(f"  기존 {month}월 위키 데이터를 교체합니다.")
    return content[:start_idx] + content[end_idx:]


def update_ts_file(ts_data: str, month: int, event_count: int, dry_run: bool = False) -> None:
    """historyEvents.ts 파일에 월별 데이터 삽입/교체"""
    ts_path = os.path.normpath(TS_FILE)

    if dry_run:
        print(f"  [dry-run] {event_count}건 — 파일 변경 없음")
        print(ts_data[:500] + ("..." if len(ts_data) > 500 else ""))
        return

    if not os.path.exists(ts_path):
        print(f"오류: {ts_path} 파일을 찾을 수 없습니다. stdout으로 출력합니다:\n")
        print(ts_data)
        return

    with open(ts_path, "r", encoding="utf-8") as f:
        content = f.read()

    content = remove_existing_month_data(content, month)
    bracket_idx = content.rfind("];")
    new_content = content[:bracket_idx] + ts_data + "\n" + content[bracket_idx:]

    with open(ts_path, "w", encoding="utf-8") as f:
        f.write(new_content)

    print(f"  → {ts_path} 에 {event_count}건 삽입 완료")


def fetch_wiki_page(month: int) -> str:
    url = f"https://ko.wikipedia.org/wiki/위키백과:오늘의_역사/{month}월"
    encoded_url = urllib.parse.quote(url, safe=":/?=&")
    req = urllib.request.Request(encoded_url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req) as resp:
        return resp.read().decode("utf-8")


def parse_months_arg(arg: str) -> list[int]:
    """CLI 인자를 월 리스트로 변환"""
    if arg.lower() == "all":
        return list(range(1, 13))
    month = int(arg)
    if not 1 <= month <= 12:
        print("월은 1-12 사이여야 합니다.")
        sys.exit(1)
    return [month]


# ══════════════════════════════════════════════════════════
# 진입점
# ══════════════════════════════════════════════════════════

def main() -> None:
    if len(sys.argv) < 2:
        print("사용법: python3 crawl_wiki_history.py <월(1-12) | all> [--dry-run]")
        print("예시: python3 crawl_wiki_history.py 2")
        print("      python3 crawl_wiki_history.py all")
        print("      python3 crawl_wiki_history.py 3 --dry-run")
        sys.exit(1)

    dry_run = "--dry-run" in sys.argv
    months = parse_months_arg(sys.argv[1])
    total_count = 0

    for month in months:
        print(f"\n{'='*44}")
        print(f"{month}월 데이터 크롤링 중{'  [dry-run]' if dry_run else ''}...")

        try:
            html = fetch_wiki_page(month)
        except Exception as e:
            print(f"  오류: {e}")
            continue

        events = parse_events(html, month)
        print_stats(events)
        update_ts_file(format_ts(events, month), month, len(events), dry_run=dry_run)
        total_count += len(events)

    print(f"\n{'='*44}")
    print(f"전체 완료! 총 {total_count}건 처리됨")


if __name__ == "__main__":
    main()
