#!/usr/bin/env python3
"""
위키백과 '오늘의 역사' 크롤링 → historyEvents.ts 자동 삽입 스크립트

사용법: python3 crawl_wiki_history.py <월(1-12)>
        python3 crawl_wiki_history.py all          # 1~12월 전체
예시: python3 crawl_wiki_history.py 2
"""

import os
import sys
import re
import urllib.request
import urllib.parse

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
TS_FILE = os.path.join(SCRIPT_DIR, "..", "src", "lib", "historyEvents.ts")

# ── 국가 매핑 (역사적 국명/왕조 → 현대 국가명) ──
COUNTRY_MAP = {
    # 한국
    "한국": "한국", "조선": "한국", "대한민국": "한국", "고려": "한국",
    "백제": "한국", "신라": "한국", "고구려": "한국", "발해": "한국",
    "대한제국": "한국", "가야": "한국",
    # 동아시아
    "미국": "미국", "미합중국": "미국", "하와이": "미국",
    "일본": "일본", "에도": "일본", "도쿠가와": "일본", "메이지": "일본",
    "중국": "중국", "중화인민공화국": "중국", "중화민국": "중국",
    "청나라": "중국", "명나라": "중국", "송나라": "중국", "원나라": "중국",
    "금나라": "중국", "당나라": "중국", "한나라": "중국", "수나라": "중국",
    "진나라": "중국", "주나라": "중국", "상나라": "중국", "하나라": "중국",
    "위나라": "중국", "촉나라": "중국", "오나라": "중국",
    "대만": "대만", "타이완": "대만",
    "몽골": "몽골",
    # 유럽
    "영국": "영국", "잉글랜드": "영국", "스코틀랜드": "영국", "브리튼": "영국",
    "웨일스": "영국", "아일랜드": "아일랜드", "북아일랜드": "영국",
    "프랑스": "프랑스", "프랑크": "프랑스", "갈리아": "프랑스",
    "독일": "독일", "프로이센": "독일", "바이마르": "독일", "나치": "독일",
    "서독": "독일", "동독": "독일",
    "러시아": "러시아", "소련": "러시아", "소비에트": "러시아", "모스크바": "러시아",
    "이탈리아": "이탈리아", "로마": "이탈리아", "베네치아": "이탈리아",
    "피렌체": "이탈리아", "바티칸": "이탈리아",
    "스페인": "스페인", "카스티야": "스페인",
    "포르투갈": "포르투갈",
    "네덜란드": "네덜란드",
    "벨기에": "벨기에",
    "스위스": "스위스",
    "오스트리아": "오스트리아", "합스부르크": "오스트리아",
    "덴마크": "덴마크",
    "스웨덴": "스웨덴",
    "노르웨이": "노르웨이",
    "핀란드": "핀란드",
    "폴란드": "폴란드",
    "그리스": "그리스", "비잔티움": "그리스", "비잔틴": "그리스", "아테네": "그리스",
    "체코": "체코", "체코슬로바키아": "체코",
    "헝가리": "헝가리",
    "루마니아": "루마니아",
    "불가리아": "불가리아",
    "세르비아": "세르비아", "유고슬라비아": "세르비아",
    "크로아티아": "크로아티아",
    "우크라이나": "우크라이나",
    # 아시아
    "인도": "인도", "무굴": "인도",
    "베트남": "베트남",
    "태국": "태국", "시암": "태국",
    "필리핀": "필리핀",
    "인도네시아": "인도네시아",
    "말레이시아": "말레이시아",
    "싱가포르": "싱가포르",
    "미얀마": "미얀마", "버마": "미얀마",
    "캄보디아": "캄보디아", "크메르": "캄보디아",
    "파키스탄": "파키스탄",
    "방글라데시": "방글라데시",
    "스리랑카": "스리랑카",
    "네팔": "네팔",
    "아프가니스탄": "아프가니스탄",
    # 중동
    "터키": "터키", "오스만": "터키",
    "이란": "이란", "페르시아": "이란",
    "이라크": "이라크", "바빌론": "이라크", "메소포타미아": "이라크",
    "이스라엘": "이스라엘", "팔레스타인": "팔레스타인",
    "사우디아라비아": "사우디아라비아", "사우디": "사우디아라비아",
    "시리아": "시리아",
    "레바논": "레바논",
    "요르단": "요르단",
    "쿠웨이트": "쿠웨이트",
    "아랍에미리트": "아랍에미리트", "UAE": "아랍에미리트",
    "카타르": "카타르",
    # 아프리카
    "이집트": "이집트", "파라오": "이집트",
    "남아프리카": "남아프리카공화국", "남아공": "남아프리카공화국",
    "나이지리아": "나이지리아",
    "케냐": "케냐",
    "에티오피아": "에티오피아",
    "가나": "가나",
    "콩고": "콩고",
    "탄자니아": "탄자니아",
    "알제리": "알제리",
    "모로코": "모로코",
    "튀니지": "튀니지",
    "리비아": "리비아",
    "수단": "수단",
    # 아메리카
    "캐나다": "캐나다",
    "멕시코": "멕시코", "아즈텍": "멕시코",
    "브라질": "브라질",
    "아르헨티나": "아르헨티나",
    "칠레": "칠레",
    "콜롬비아": "콜롬비아",
    "페루": "페루", "잉카": "페루",
    "베네수엘라": "베네수엘라",
    "쿠바": "쿠바",
    "파나마": "파나마",
    "푸에르토리코": "푸에르토리코",
    # 오세아니아
    "호주": "호주", "오스트레일리아": "호주",
    "뉴질랜드": "뉴질랜드",
    # 국제기구 / 기타
    "유엔": "세계", "UN": "세계", "국제연합": "세계",
    "NATO": "세계", "나토": "세계",
    "올림픽": "세계", "월드컵": "세계",
}

# ── 카테고리 세분화 키워드 ──
CATEGORY_KEYWORDS = {
    "war": ["전쟁", "전투", "침공", "공격", "폭격", "항복", "휴전", "정전", "선전포고",
            "반란", "봉기", "혁명", "쿠데타", "내전", "학살", "독립전쟁"],
    "politics": ["선거", "대통령", "국왕", "총리", "황제", "즉위", "퇴위", "조약",
                 "헌법", "독립", "건국", "수립", "선포", "합병", "통일", "분단",
                 "식민", "해방", "국교", "외교", "정부"],
    "science": ["발명", "발견", "발사", "착륙", "우주", "위성", "탐사", "실험",
                "노벨", "특허", "과학", "원자", "핵", "DNA", "컴퓨터", "인터넷"],
    "culture": ["올림픽", "월드컵", "영화", "음악", "문학", "예술", "축제",
                "박물관", "유네스코", "공연", "방송"],
    "disaster": ["지진", "태풍", "홍수", "화산", "쓰나미", "폭발", "사고",
                 "침몰", "추락", "붕괴", "전염병", "역병"],
}


def strip_html(text: str) -> str:
    """HTML 태그 제거"""
    return re.sub(r"<[^>]+>", "", text).strip()


def classify_subcategory(text: str) -> str | None:
    """이벤트 텍스트에서 세부 카테고리 태그 반환"""
    for tag, keywords in CATEGORY_KEYWORDS.items():
        for kw in keywords:
            if kw in text:
                return tag
    return None


def guess_country(text: str) -> str:
    """텍스트에서 국가 추측 — 더 긴 키워드를 우선 매칭"""
    found = []
    for keyword, country in COUNTRY_MAP.items():
        idx = text.find(keyword)
        if idx != -1:
            found.append((idx, len(keyword), country))
    if not found:
        return "세계"
    # 더 긴 키워드를 우선, 같으면 더 앞에 나온 것 우선
    found.sort(key=lambda x: (-x[1], x[0]))
    return found[0][2]


def make_id(month: int, day: int, year: int, suffix: str = "") -> str:
    m = str(month).zfill(2)
    d = str(day).zfill(2)
    if year < 0:
        base = f"wiki-{m}{d}-{abs(year)}bc"
    else:
        base = f"wiki-{m}{d}-{year}"
    return base + suffix


def is_country_name(text: str) -> bool:
    """텍스트가 나라 이름(들)인지 판별"""
    names = re.split(r"[·]", text)
    for name in names:
        name = name.strip()
        if not name:
            continue
        if len(name) > 15:
            return False
        non_country = ["천주", "서방", "동방", "국제", "세계", "가톨릭", "정교회", "기독교"]
        if any(nc in name for nc in non_country):
            return False
    return True


def parse_holidays(header_html: str, header_text: str, month: int, day: int) -> list[dict]:
    """날짜 헤더의 기념일 텍스트를 파싱하여 holiday 이벤트 리스트로 반환"""
    holidays = []
    date_str = f"{str(month).zfill(2)}-{str(day).zfill(2)}"

    parts = [p.strip() for p in header_text.split(",") if p.strip()]

    for idx, part in enumerate(parts):
        country_match = re.match(r"(.+)의\s+(.+)", part)

        is_country_pattern = False
        if country_match:
            candidate_countries = country_match.group(1).strip()
            if is_country_name(candidate_countries):
                is_country_pattern = True

        if is_country_pattern:
            countries_str = country_match.group(1).strip()
            holiday_name = country_match.group(2).strip()
            country_names = re.split(r"[·]", countries_str)

            for cn in country_names:
                cn = cn.strip()
                if not cn:
                    continue
                hol_id = f"wiki-hol-{date_str}-{idx}-{cn}"
                url = extract_holiday_url(header_html, holiday_name)

                holiday = {
                    "id": hol_id,
                    "country": cn,
                    "date": date_str,
                    "year": 2024,
                    "title": holiday_name,
                    "description": f"{cn}의 {holiday_name}.",
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


def extract_holiday_url(header_html: str, keyword: str) -> str | None:
    """헤더 HTML에서 키워드와 관련된 <b><a> 볼드 링크 URL 추출"""
    pattern = re.compile(
        r'<b><a[^>]*href="([^"]*)"[^>]*>[^<]*' + re.escape(keyword[:5]),
        re.DOTALL
    )
    match = pattern.search(header_html)
    if match:
        href = match.group(1)
        if href.startswith("//"):
            return "https:" + href
        elif href.startswith("/"):
            return "https://ko.wikipedia.org" + href
    return None


def fetch_wiki_page(month: int) -> str:
    url = f"https://ko.wikipedia.org/wiki/위키백과:오늘의_역사/{month}월"
    encoded_url = urllib.parse.quote(url, safe=":/?=&")
    req = urllib.request.Request(encoded_url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req) as resp:
        return resp.read().decode("utf-8")


def parse_events(html: str, month: int) -> list[dict]:
    """HTML에서 직접 날짜 섹션과 이벤트를 파싱"""
    events = []
    seen_ids = set()

    date_pattern = re.compile(
        rf'<b><a[^>]*>({month}월\s*(\d+)일)</a></b>'
    )

    matches = list(date_pattern.finditer(html))

    for i, m in enumerate(matches):
        day = int(m.group(2))
        start_pos = m.end()
        end_pos = matches[i + 1].start() if i + 1 < len(matches) else start_pos + 5000
        section = html[start_pos:end_pos]

        # --- 기념일 파싱 ---
        ul_start = section.find("<ul")
        if ul_start > 0:
            header_html = section[:ul_start]
            header_text = strip_html(header_html).strip(": \n\t")
            if header_text:
                events.extend(parse_holidays(header_html, header_text, month, day))

        # --- 역사 이벤트 파싱 ---
        ul_match = re.search(r"<ul[^>]*>(.*?)</ul>", section, re.DOTALL)
        if not ul_match:
            continue

        li_items = re.findall(r"<li>(.*?)</li>", ul_match.group(1), re.DOTALL)

        for li_idx, li in enumerate(li_items):
            # URL 추출
            bold_link = re.search(r'<b><a[^>]*href="([^"]*)"[^>]*>', li)
            url = None
            if bold_link:
                href = bold_link.group(1)
                if href.startswith("//"):
                    url = "https:" + href
                elif href.startswith("/"):
                    url = "https://ko.wikipedia.org" + href

            text = strip_html(li).strip()
            text = re.sub(r"\(그림\)|\(사진\)", "", text).strip()

            bc_match = re.match(r"기원전\s*(\d+)년\s*-\s*(.+)", text)
            year_match = re.match(r"(\d+)년\s*-\s*(.+)", text)

            if bc_match:
                year = -int(bc_match.group(1))
                desc = bc_match.group(2).strip()
            elif year_match:
                year = int(year_match.group(1))
                desc = year_match.group(2).strip()
            else:
                continue

            title = desc
            country = guess_country(desc)
            subcategory = classify_subcategory(desc)
            date_str = f"{str(month).zfill(2)}-{str(day).zfill(2)}"

            # 같은 날 같은 연도 중복 방지
            event_id = make_id(month, day, year)
            if event_id in seen_ids:
                event_id = make_id(month, day, year, suffix=f"-{li_idx}")
            seen_ids.add(event_id)

            event = {
                "id": event_id,
                "country": country,
                "date": date_str,
                "year": year,
                "title": title,
                "description": desc,
                "category": "history",
            }
            if subcategory:
                event["subcategory"] = subcategory
            if url:
                event["url"] = url

            events.append(event)

    return events


def format_ts(events: list[dict], month: int) -> str:
    lines = [f"  // --- 위키백과 오늘의 역사: {month}월 ---"]
    for e in events:
        title = e["title"].replace('"', '\\"')
        desc = e["description"].replace('"', '\\"')
        lines.append("  {")
        lines.append(f'    id: "{e["id"]}",')
        lines.append(f'    country: "{e["country"]}",')
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


def main():
    if len(sys.argv) < 2:
        print("사용법: python3 crawl_wiki_history.py <월(1-12) | all>")
        print("예시: python3 crawl_wiki_history.py 2")
        print("      python3 crawl_wiki_history.py all")
        sys.exit(1)

    arg = sys.argv[1]
    if arg.lower() == "all":
        months = list(range(1, 13))
    else:
        months = [int(arg)]
        if not 1 <= months[0] <= 12:
            print("월은 1-12 사이여야 합니다.")
            sys.exit(1)

    total_count = 0

    for month in months:
        print(f"\n{'='*40}")
        print(f"{month}월 데이터 크롤링 중...")

        html = fetch_wiki_page(month)
        events = parse_events(html, month)

        history_count = sum(1 for e in events if e["category"] == "history")
        holiday_count = sum(1 for e in events if e["category"] == "holiday")
        print(f"  역사: {history_count}건, 공휴일: {holiday_count}건 (총 {len(events)}건)")

        # 국가별 상위 5개
        country_counts: dict[str, int] = {}
        for e in events:
            c = e["country"]
            country_counts[c] = country_counts.get(c, 0) + 1
        top_countries = sorted(country_counts.items(), key=lambda x: -x[1])[:5]
        country_str = ", ".join(f"{k}: {v}" for k, v in top_countries)
        print(f"  국가 TOP5: {country_str}")

        ts_data = format_ts(events, month)
        total_count += len(events)

        # historyEvents.ts 파일에 자동 삽입
        ts_path = os.path.normpath(TS_FILE)
        if not os.path.exists(ts_path):
            print(f"오류: {ts_path} 파일을 찾을 수 없습니다.")
            print("stdout으로 출력합니다:\n")
            print(ts_data)
            continue

        with open(ts_path, "r", encoding="utf-8") as f:
            content = f.read()

        # 기존 같은 월 위키 데이터가 있으면 제거
        marker = f"  // --- 위키백과 오늘의 역사: {month}월 ---"
        if marker in content:
            start_idx = content.index(marker)
            rest = content[start_idx + len(marker):]
            next_match = re.search(r"  // --- 위키백과 오늘의 역사: \d+월 ---", rest)
            bracket_pos = rest.find("];")

            if next_match and next_match.start() < bracket_pos:
                end_idx = start_idx + len(marker) + next_match.start()
            else:
                end_idx = start_idx + len(marker) + bracket_pos

            content = content[:start_idx] + content[end_idx:]
            print(f"  기존 {month}월 위키 데이터를 교체합니다.")

        # ]; 바로 앞에 삽입
        bracket_idx = content.rfind("];")
        new_content = content[:bracket_idx] + ts_data + "\n" + content[bracket_idx:]

        with open(ts_path, "w", encoding="utf-8") as f:
            f.write(new_content)

        print(f"  → {ts_path} 에 {len(events)}건 삽입 완료")

    print(f"\n{'='*40}")
    print(f"전체 완료! 총 {total_count}건 처리됨")


if __name__ == "__main__":
    main()
