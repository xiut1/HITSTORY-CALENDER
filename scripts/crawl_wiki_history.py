#!/usr/bin/env python3
"""
위키백과 '오늘의 역사' 크롤링 → historyEvents.ts 자동 삽입 스크립트

사용법: python3 crawl_wiki_history.py <월(1-12)>
예시: python3 crawl_wiki_history.py 2
"""

import os
import sys
import re
import urllib.request
import urllib.parse

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
TS_FILE = os.path.join(SCRIPT_DIR, "..", "src", "lib", "historyEvents.ts")

COUNTRY_MAP = {
    "한국": "한국", "조선": "한국", "대한민국": "한국", "고려": "한국",
    "백제": "한국", "신라": "한국", "고구려": "한국",
    "미국": "미국", "미합중국": "미국",
    "일본": "일본",
    "중국": "중국", "중화인민공화국": "중국", "중화민국": "중국",
    "청나라": "중국", "명나라": "중국", "송나라": "중국",
    "금나라": "중국", "당나라": "중국", "한나라": "중국",
    "영국": "영국", "잉글랜드": "영국", "스코틀랜드": "영국", "브리튼": "영국",
    "프랑스": "프랑스",
    "독일": "독일", "프로이센": "독일",
    "러시아": "러시아", "소련": "러시아", "소비에트": "러시아",
    "이탈리아": "이탈리아", "로마": "이탈리아",
    "스페인": "스페인",
    "인도": "인도",
    "이집트": "이집트",
    "캐나다": "캐나다",
    "호주": "호주", "오스트레일리아": "호주",
    "브라질": "브라질",
    "멕시코": "멕시코",
    "터키": "터키", "오스만": "터키",
    "그리스": "그리스", "비잔티움": "그리스",
    "폴란드": "폴란드",
    "네덜란드": "네덜란드",
    "벨기에": "벨기에",
    "스위스": "스위스",
    "오스트리아": "오스트리아",
    "덴마크": "덴마크",
    "스웨덴": "스웨덴",
    "노르웨이": "노르웨이",
    "핀란드": "핀란드",
    "포르투갈": "포르투갈",
    "베트남": "베트남",
    "태국": "태국",
    "쿠바": "쿠바",
    "이란": "이란", "페르시아": "이란",
    "이라크": "이라크",
    "아르헨티나": "아르헨티나",
    "남아프리카": "남아프리카공화국",
}


def strip_html(text: str) -> str:
    """HTML 태그 제거"""
    return re.sub(r"<[^>]+>", "", text).strip()


def guess_country(text: str) -> str:
    for keyword, country in COUNTRY_MAP.items():
        if keyword in text:
            return country
    return "세계"


def make_id(month: int, day: int, year: int) -> str:
    m = str(month).zfill(2)
    d = str(day).zfill(2)
    if year < 0:
        return f"wiki-{m}{d}-{abs(year)}bc"
    return f"wiki-{m}{d}-{year}"


def make_title(desc: str) -> str:
    """설명 전체를 제목으로 사용"""
    return desc


def is_country_name(text: str) -> bool:
    """텍스트가 나라 이름(들)인지 판별"""
    # ·로 분리했을 때 각 항목이 짧고 나라스러운지 확인
    names = re.split(r"[·]", text)
    for name in names:
        name = name.strip()
        if not name:
            continue
        # 나라 이름은 보통 짧고 (1~15자), "의", "에서" 등을 포함하지 않음
        if len(name) > 15:
            return False
        # 알려진 비-나라 키워드
        non_country = ["천주", "서방", "동방", "국제", "세계", "가톨릭", "정교회", "기독교"]
        if any(nc in name for nc in non_country):
            return False
    return True


def parse_holidays(header_html: str, header_text: str, month: int, day: int) -> list[dict]:
    """날짜 헤더의 기념일 텍스트를 파싱하여 holiday 이벤트 리스트로 반환"""
    holidays = []
    date_str = f"{str(month).zfill(2)}-{str(day).zfill(2)}"

    # 쉼표로 기념일 항목 분리
    parts = [p.strip() for p in header_text.split(",") if p.strip()]

    for idx, part in enumerate(parts):
        # "나라·나라의 기념일" 패턴 (마지막 "의"로 분리)
        # 단, "의"가 기념일 이름 안에 있을 수도 있으므로 나라인지 검증
        country_match = re.match(r"(.+)의\s+(.+)", part)

        is_country_pattern = False
        if country_match:
            candidate_countries = country_match.group(1).strip()
            candidate_holiday = country_match.group(2).strip()
            # 후보 나라명이 실제 나라인지 확인
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
            # 나라 없는 기념일 (예: "주현절", "새해 첫날", "천주의 성모 마리아 대축일")
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
    # keyword가 포함된 <b><a> 태그 찾기
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

    # 패턴: <p ...><b><a ...>X월 Y일</a></b>...</p> 뒤에 <ul><li>...</li>...</ul>
    # 날짜 헤더 위치 찾기: <a ...>X월 Y일</a> 가 <b> 안에 있는 경우
    date_pattern = re.compile(
        rf'<b><a[^>]*>({month}월\s*(\d+)일)</a></b>'
    )

    matches = list(date_pattern.finditer(html))

    for i, m in enumerate(matches):
        day = int(m.group(2))
        start_pos = m.end()

        # 이 날짜 뒤에서 다음 날짜 헤더 전까지의 범위에서 <ul> 찾기
        end_pos = matches[i + 1].start() if i + 1 < len(matches) else start_pos + 5000

        section = html[start_pos:end_pos]

        # --- 기념일 파싱: 날짜 헤더와 <ul> 사이 텍스트 ---
        ul_start = section.find("<ul")
        if ul_start > 0:
            header_html = section[:ul_start]
            header_text = strip_html(header_html).strip(": \n\t")
            if header_text:
                events.extend(parse_holidays(header_html, header_text, month, day))

        # <ul>...</ul> 블록 찾기 (첫 번째 것만)
        ul_match = re.search(r"<ul[^>]*>(.*?)</ul>", section, re.DOTALL)
        if not ul_match:
            continue

        # <li>...</li> 각각 파싱
        li_items = re.findall(r"<li>(.*?)</li>", ul_match.group(1), re.DOTALL)

        for li in li_items:
            # <b><a href="..."> 패턴에서 첫 번째 볼드 링크를 url로 추출
            bold_link = re.search(r'<b><a[^>]*href="([^"]*)"[^>]*>', li)
            url = None
            if bold_link:
                href = bold_link.group(1)
                # //ko.wikipedia.org/... → https://ko.wikipedia.org/...
                if href.startswith("//"):
                    url = "https:" + href
                elif href.startswith("/"):
                    url = "https://ko.wikipedia.org" + href

            text = strip_html(li).strip()
            # (그림), (사진) 제거
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

            title = make_title(desc)
            country = guess_country(desc)
            date_str = f"{str(month).zfill(2)}-{str(day).zfill(2)}"
            event_id = make_id(month, day, year)

            event = {
                "id": event_id,
                "country": country,
                "date": date_str,
                "year": year,
                "title": title,
                "description": desc,
            }
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
        if e.get("category"):
            lines.append(f'    category: "{e["category"]}",')
        if "url" in e:
            url = e["url"].replace('"', '\\"')
            lines.append(f'    url: "{url}",')
        lines.append("  },")
    return "\n".join(lines)


def main():
    if len(sys.argv) < 2:
        print("사용법: python3 crawl_wiki_history.py <월(1-12)>")
        print("예시: python3 crawl_wiki_history.py 2")
        sys.exit(1)

    month = int(sys.argv[1])
    if not 1 <= month <= 12:
        print("월은 1-12 사이여야 합니다.")
        sys.exit(1)

    print(f"{month}월 데이터 크롤링 중...")

    html = fetch_wiki_page(month)
    events = parse_events(html, month)
    ts_data = format_ts(events, month)

    print(f"총 {len(events)}건 추출됨")

    # historyEvents.ts 파일에 자동 삽입
    ts_path = os.path.normpath(TS_FILE)
    if not os.path.exists(ts_path):
        print(f"오류: {ts_path} 파일을 찾을 수 없습니다.")
        print("stdout으로 출력합니다:\n")
        print(ts_data)
        sys.exit(1)

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
        print(f"기존 {month}월 위키 데이터를 교체합니다.")

    # ]; 바로 앞에 삽입
    bracket_idx = content.rfind("];")
    new_content = content[:bracket_idx] + ts_data + "\n" + content[bracket_idx:]

    with open(ts_path, "w", encoding="utf-8") as f:
        f.write(new_content)

    print(f"완료! {ts_path} 에 {len(events)}건 삽입됨")


if __name__ == "__main__":
    main()
