#!/usr/bin/env python3
"""
위키백과 '오늘의 역사' 크롤링 → historyEvents.ts 자동 삽입 스크립트

사용법:
  python3 crawl_wiki_history.py 2              # 2월만
  python3 crawl_wiki_history.py all            # 1~12월 전체
  python3 crawl_wiki_history.py 1-3,7          # 1,2,3,7월
  python3 crawl_wiki_history.py 2 --dry-run    # 파일 변경 없이 미리보기
  python3 crawl_wiki_history.py 2 --verbose    # 국가 미매칭 항목까지 출력

환경변수:
  WIKI_CRAWLER_CONTACT  User-Agent에 넣을 연락처(이메일/URL).
                        위키미디어 UA 정책상 지정을 권장합니다.
"""

import argparse
import calendar
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter
from datetime import date
from html import unescape

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
TS_FILE = os.path.normpath(os.path.join(SCRIPT_DIR, "..", "src", "lib", "historyEvents.ts"))

# 위키미디어 UA 정책: 식별 가능한 이름 + 연락처를 요구한다.
# 연락처는 커밋에 개인정보를 남기지 않도록 환경변수로 주입한다.
# HTTP 헤더는 latin-1만 허용하므로 비ASCII 문자는 제거한다.
CONTACT = os.environ.get("WIKI_CRAWLER_CONTACT", "https://github.com/history-calendar")
USER_AGENT = f"history-calendar-crawler/2.0 ({CONTACT}) python-urllib".encode(
    "ascii", "ignore"
).decode("ascii")

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
    "나치독일": "독일", "나치": "독일", "서독": "독일", "동독": "독일", "독일": "독일",

    # ── 이탈리아 ──
    "로마 제국": "이탈리아", "로마제국": "이탈리아", "로마 공화국": "이탈리아",
    "로마": "이탈리아",
    "이탈리아": "이탈리아", "베네치아": "이탈리아",
    "피렌체": "이탈리아", "시칠리아": "이탈리아",

    # ── 바티칸 ──
    "바티칸": "바티칸", "교황청": "바티칸",

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
    "벨라루스": "벨라루스", "몬테네그로": "몬테네그로", "코소보": "코소보",

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
    "감비아": "감비아", "세네갈": "세네갈", "베냉": "베냉",
    "모리타니": "모리타니", "카메룬": "카메룬", "서사하라": "서사하라",
    "콩고 공화국": "콩고", "다호메이": "베냉",

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

# ══════════════════════════════════════════════════════════
# 보조 매핑 — 도시·지명·인물·기관 → 국가
# COUNTRY_MAP보다 우선순위가 낮다(겹치면 국명이 이긴다).
# 위키 본문은 국명 없이 지명/인명만 쓰는 경우가 많아 미매칭의 주원인.
# ══════════════════════════════════════════════════════════
REGION_MAP: dict[str, str] = {
    # ── 한국 ──
    "서울": "한국", "부산": "한국", "인천": "한국", "대구": "한국",
    "광주": "한국", "대전": "한국", "울산": "한국", "제주": "한국",
    "경상": "한국", "전라": "한국", "충청": "한국", "강원": "한국",
    "경기도": "한국", "한양": "한국", "경성": "한국", "판문점": "한국",
    "세종대왕": "한국", "이순신": "한국", "안중근": "한국", "윤봉길": "한국",
    "김구": "한국", "이승만": "한국", "박정희": "한국", "임진왜란": "한국",
    "삼일운동": "한국", "3·1 운동": "한국", "광복절": "한국", "새마을": "한국",
    "평양": "북한", "김일성": "북한", "김정일": "북한", "김정은": "북한",

    # ── 일본 ──
    "도쿄": "일본", "오사카": "일본", "교토": "일본", "히로시마": "일본",
    "나가사키": "일본", "후쿠시마": "일본", "오키나와": "일본",
    "요코하마": "일본", "고베": "일본", "천황": "일본", "쇼군": "일본",

    # ── 중국 ──
    "베이징": "중국", "북경": "중국", "상하이": "중국", "상해": "중국",
    "난징": "중국", "남경": "중국", "톈안먼": "중국", "천안문": "중국",
    "마오쩌둥": "중국", "덩샤오핑": "중국", "만리장성": "중국", "자금성": "중국",

    # ── 미국 ──
    "뉴욕": "미국", "워싱턴": "미국", "로스앤젤레스": "미국", "샌프란시스코": "미국",
    "시카고": "미국", "보스턴": "미국", "필라델피아": "미국", "휴스턴": "미국",
    "시애틀": "미국", "디트로이트": "미국", "애틀랜타": "미국", "라스베이거스": "미국",
    "텍사스": "미국", "캘리포니아": "미국", "플로리다": "미국", "버지니아": "미국",
    "사우스캐롤라이나": "미국", "노스캐롤라이나": "미국", "매사추세츠": "미국",
    "펜실베이니아": "미국", "미시시피": "미국", "미주리": "미국", "오하이오": "미국",
    "조지아주": "미국", "할리우드": "미국", "실리콘밸리": "미국", "브로드웨이": "미국",
    "나스닥": "미국", "월스트리트": "미국", "백악관": "미국", "펜타곤": "미국",
    "NASA": "미국", "아폴로": "미국", "스페이스X": "미국", "보이저": "미국",
    "IBM": "미국", "애플": "미국", "마이크로소프트": "미국", "구글": "미국",
    "에디슨": "미국", "링컨": "미국", "케네디": "미국", "루스벨트": "미국",
    "트루먼": "미국", "아이젠하워": "미국", "닉슨": "미국", "레이건": "미국",
    "마틴 루서 킹": "미국", "마틴 루터 킹": "미국", "맬컴 엑스": "미국",
    "라이트 형제": "미국", "마크 트웨인": "미국", "디즈니": "미국",
    "그래미": "미국", "아카데미상": "미국", "메이저리그": "미국", "슈퍼볼": "미국",
    "에니악": "미국", "듀폰": "미국", "게티즈버그": "미국", "알라모": "미국",
    "진주만": "미국", "세계 무역 센터": "미국", "남북 전쟁": "미국",
    "연합규약": "미국", "잭 킬비": "미국", "그레이엄 벨": "미국",

    # ── 영국 ──
    "런던": "영국", "옥스퍼드": "영국", "케임브리지": "영국", "리버풀": "영국",
    "맨체스터": "영국", "에든버러": "영국", "글래스고": "영국",
    "셰익스피어": "영국", "처칠": "영국", "뉴턴": "영국", "다윈": "영국",
    "비틀즈": "영국", "버킹엄": "영국", "웨스트민스터": "영국", "BBC": "영국",
    "빅토리아 여왕": "영국", "대처": "영국", "복제 양 돌리": "영국",

    # ── 프랑스 ──
    "파리": "프랑스", "마르세유": "프랑스", "노르망디": "프랑스",
    "베르사유": "프랑스", "나폴레옹": "프랑스", "드골": "프랑스",
    "루브르": "프랑스", "에펠": "프랑스", "바스티유": "프랑스",
    "잔 다르크": "프랑스", "루이 14세": "프랑스", "칸 영화제": "프랑스",

    # ── 독일 ──
    "베를린": "독일", "뮌헨": "독일", "함부르크": "독일", "프랑크푸르트": "독일",
    "드레스덴": "독일", "히틀러": "독일", "비스마르크": "독일",
    "괴테": "독일", "베토벤": "독일", "바흐": "독일", "브람스": "독일",
    "마르크스": "독일", "엥겔스": "독일", "아인슈타인": "독일",
    "루터": "독일", "코페르니슘": "독일", "게슈타포": "독일",

    # ── 이탈리아 ──
    "밀라노": "이탈리아", "나폴리": "이탈리아", "토리노": "이탈리아",
    "폼페이": "이탈리아", "무솔리니": "이탈리아", "다빈치": "이탈리아",
    "미켈란젤로": "이탈리아", "베르디": "이탈리아", "갈릴레이": "이탈리아",
    "콜로세움": "이탈리아", "엘바섬": "이탈리아",

    # ── 바티칸 ──
    "교황": "바티칸", "성 베드로 대성당": "바티칸",

    # ── 러시아 ──
    "모스크바": "러시아", "상트페테르부르크": "러시아", "레닌그라드": "러시아",
    "스탈린그라드": "러시아", "크렘린": "러시아", "시베리아": "러시아",
    "레닌": "러시아", "스탈린": "러시아", "푸틴": "러시아", "고르바초프": "러시아",
    "톨스토이": "러시아", "차이콥스키": "러시아", "도스토옙스키": "러시아",
    "가가린": "러시아", "스푸트니크": "러시아", "표트르 대제": "러시아",

    # ── 유럽 기타 ──
    "마드리드": "스페인", "바르셀로나": "스페인", "프랑코": "스페인", "피카소": "스페인",
    "리스본": "포르투갈",
    "암스테르담": "네덜란드", "로테르담": "네덜란드", "고흐": "네덜란드", "렘브란트": "네덜란드",
    "브뤼셀": "벨기에",
    "제네바": "스위스", "취리히": "스위스", "베른": "스위스",
    "모차르트": "오스트리아", "프로이트": "오스트리아", "슈베르트": "오스트리아",
    "부다페스트": "헝가리",
    "코펜하겐": "덴마크", "안데르센": "덴마크",
    "스톡홀름": "스웨덴", "오슬로": "노르웨이", "헬싱키": "핀란드", "칼레발라": "핀란드",
    "바르샤바": "폴란드", "아우슈비츠": "폴란드", "쇼팽": "폴란드", "코페르니쿠스": "폴란드",
    "프라하": "체코",
    "아테네": "그리스", "스파르타": "그리스", "올림피아": "그리스",
    "키이우": "우크라이나", "키예프": "우크라이나", "체르노빌": "우크라이나",
    "더블린": "아일랜드", "제임스 조이스": "아일랜드",

    # ── 중동 / 아프리카 ──
    "이스탄불": "터키", "앙카라": "터키", "콘스탄티노폴리스": "터키",
    "테헤란": "이란", "호메이니": "이란",
    "바그다드": "이라크", "사담 후세인": "이라크",
    "예루살렘": "이스라엘", "텔아비브": "이스라엘",
    "가자 지구": "팔레스타인",
    "카불": "아프가니스탄", "탈레반": "아프가니스탄",
    "카이로": "이집트", "피라미드": "이집트", "수에즈": "이집트", "나일강": "이집트",
    "다르푸르": "수단", "카세린": "튀니지",
    "만델라": "남아프리카공화국", "요하네스버그": "남아프리카공화국",
    "케이프타운": "남아프리카공화국", "아파르트헤이트": "남아프리카공화국",
    "데즈먼드 투투": "남아프리카공화국",

    # ── 아시아 / 오세아니아 / 아메리카 ──
    "간디": "인도", "뉴델리": "인도", "뭄바이": "인도", "타지마할": "인도",
    "이슬라마바드": "파키스탄",
    "하노이": "베트남", "사이공": "베트남", "호찌민": "베트남",
    "방콕": "태국", "마닐라": "필리핀", "자카르타": "인도네시아",
    "시드니": "호주", "멜버른": "호주", "캔버라": "호주",
    "웰링턴": "뉴질랜드", "오클랜드": "뉴질랜드", "와이탕기": "뉴질랜드",
    "토론토": "캐나다", "몬트리올": "캐나다", "오타와": "캐나다", "밴쿠버": "캐나다",
    "리우데자네이루": "브라질", "상파울루": "브라질", "브라질리아": "브라질",
    "부에노스아이레스": "아르헨티나", "페론": "아르헨티나",
    "멕시코시티": "멕시코",
    "아바나": "쿠바", "카스트로": "쿠바", "체 게바라": "쿠바",
    "마추픽추": "페루",

    # ── 국제기구 ──
    "유네스코": "세계", "세계보건기구": "세계", "WHO": "세계",
    "국제 적십자": "세계", "적십자": "세계", "IMF": "세계",
    "국제사법재판소": "세계", "국제 표준화 기구": "세계", "ISO": "세계",
    "그린피스": "세계", "국제올림픽위원회": "세계", "IOC": "세계",
    "FIFA": "세계", "노벨상": "세계", "국제앰네스티": "세계",
}

# ── 단어 경계 없이 매칭하면 안 되는 키워드 (부분문자열 오매칭 방지) ──
# 예: "로마" → "로마자", "이란" → "이란성", "대구" → "대구탕"
BOUNDARY_REQUIRED: set[str] = {
    "로마", "이란", "나치", "한국", "가나", "인도", "수단",
    "마케도니아", "조지아", "오만", "통가", "기니", "칠레",
    "대구", "광주", "제주", "경상", "전라", "충청", "강원",
    "루터", "링컨", "파리", "교황", "적십자", "베른", "고베",
}

# ── 한국어 조사·접미사 허용 목록 ──
# "한국의", "이란은", "가나가"처럼 명사 뒤에 조사가 붙어도 매칭되어야 한다.
# 반대로 "이란성", "로마자"처럼 다른 단어가 되는 경우는 걸러야 하므로 화이트리스트로 관리.
_ALLOWED_SUFFIXES: list[str] = sorted(
    [
        # 조사
        "의", "은", "는", "이", "가", "을", "를", "에", "와", "과", "도", "로", "만",
        "께", "라", "에서", "에게", "으로", "이나", "부터", "까지", "처럼", "보다",
        "이라", "이며", "이자", "와의", "과의", "에는", "에서는", "으로는", "로는",
        # 국가명에 흔히 붙는 접미사(의미 유지)
        "인", "어", "계", "산", "군", "측", "식", "제", "풍", "즘", "형", "령",
    ],
    key=len,
    reverse=True,
)

# ── 카테고리 세분화 키워드 ──
CATEGORY_KEYWORDS: dict[str, list[str]] = {
    "war": ["전쟁", "전투", "침공", "공격", "폭격", "항복", "휴전", "정전", "선전포고",
            "반란", "봉기", "혁명", "쿠데타", "내전", "학살", "독립전쟁", "포위",
            "테러", "십자군", "원정", "점령", "함락", "군대", "병력", "무장", "핵실험"],
    "politics": ["선거", "대통령", "국왕", "총리", "황제", "즉위", "퇴위", "조약",
                 "헌법", "독립", "건국", "수립", "선포", "합병", "통일", "분단",
                 "식민", "해방", "국교", "외교", "정부", "의회",
                 "취임", "사임", "암살", "선언", "협정", "서명", "가입", "발효",
                 "비준", "제정", "공포", "시위", "항거", "회담", "정상", "주지사",
                 "총독", "수상", "장관", "조인", "재판", "판결"],
    "science": ["발명", "발견", "발사", "착륙", "우주", "위성", "탐사", "실험",
                "노벨", "특허", "과학", "원자", "핵", "DNA", "컴퓨터", "인터넷",
                "백신", "항생제", "물리학", "천문",
                "탐사선", "우주선", "로켓", "화성", "행성", "소행성", "천문학자",
                "전화", "전신", "의학", "수학", "공학", "방사능", "진화", "원소",
                "명명", "집적 회로", "복제", "귀환", "궤도"],
    "culture": ["올림픽", "월드컵", "영화", "음악", "문학", "예술", "축제",
                "박물관", "유네스코", "공연", "방송", "출판",
                "개봉", "초연", "출간", "앨범", "소설", "가극", "오페라", "교향곡",
                "미술관", "전시", "애니메이션", "드라마", "연극", "수상", "그래미",
                "아카데미상", "경기", "우승", "리그", "선수", "구단", "신문", "잡지",
                "창간", "만화", "노래", "밴드"],
    "disaster": ["지진", "태풍", "홍수", "화산", "쓰나미", "폭발", "사고",
                 "침몰", "추락", "붕괴", "전염병", "역병", "허리케인",
                 "참사", "화재", "좌초", "산사태", "가뭄", "기근", "대유행"],
}

# ── 위키 원문의 알려진 오류 교정 ──
# 예) 2월 18일은 '감비아' 독립기념일(1965)이나 위키 원문이 '잠비아'로 표기.
#     (잠비아 독립일은 10월 24일)
WIKI_TEXT_FIXES: dict[str, list[tuple[str, str]]] = {
    "02-18": [("잠비아의 독립기념일", "감비아의 독립기념일")],
}

# 위키 월별 문서는 하루 5건을 싣는다. 검증 임계값의 기준.
NOMINAL_ITEMS_PER_DAY = 5


# ══════════════════════════════════════════════════════════
# 유틸리티
# ══════════════════════════════════════════════════════════

def strip_html(text: str) -> str:
    """HTML 태그 제거 + 엔티티 디코드 + 공백 정규화"""
    text = re.sub(r"<[^>]+>", "", text)
    text = unescape(text)
    text = re.sub(r"\[\d+\]|\[편집\]", "", text)      # 각주/편집 링크 잔여물
    return re.sub(r"\s+", " ", text).strip()          # 개행 → 공백 (TS 문자열 깨짐 방지)


def normalize_wiki_url(href: str) -> str:
    """상대/프로토콜 상대 경로를 절대 URL로 변환"""
    href = unescape(href.strip())
    if href.startswith("//"):
        return "https:" + href
    if href.startswith("/"):
        return "https://ko.wikipedia.org" + href
    return href


def classify_subcategory(text: str) -> str | None:
    """
    이벤트 텍스트의 세부 카테고리 태그 반환.
    첫 매칭이 아니라 태그별 히트 수로 점수를 매겨 가장 많이 걸린 태그를 고른다.
    동점이면 CATEGORY_KEYWORDS 선언 순서(war > politics > ...)를 따른다.
    """
    best_tag: str | None = None
    best_score = 0
    for tag, keywords in CATEGORY_KEYWORDS.items():
        score = sum(1 for kw in keywords if kw in text)
        if score > best_score:
            best_tag, best_score = tag, score
    return best_tag


_boundary_cache: dict[str, re.Pattern[str]] = {}


def _boundary_pattern(keyword: str) -> re.Pattern[str]:
    """키워드 앞뒤로 한글 단어 경계(조사 허용)를 요구하는 정규식"""
    if keyword not in _boundary_cache:
        suffixes = "|".join(re.escape(s) for s in _ALLOWED_SUFFIXES)
        _boundary_cache[keyword] = re.compile(
            r"(?<![가-힣])"
            + re.escape(keyword)
            + rf"(?=$|[^가-힣]|(?:{suffixes})(?![가-힣]))"
        )
    return _boundary_cache[keyword]


def _iter_keyword_matches(text: str, keyword: str):
    """텍스트에서 키워드가 등장하는 모든 시작 인덱스를 반환"""
    if keyword in BOUNDARY_REQUIRED:
        for m in _boundary_pattern(keyword).finditer(text):
            yield m.start()
        return
    start = 0
    while (idx := text.find(keyword, start)) != -1:
        yield idx
        start = idx + 1


# (키워드, 국가, 우선순위) — 0=정식 국명, 1=지명/인물/기관
_KEYWORD_TABLE: list[tuple[str, str, int]] = (
    [(k, v, 0) for k, v in COUNTRY_MAP.items()]
    + [(k, v, 1) for k, v in REGION_MAP.items()]
)


def guess_country(text: str) -> str | list[str]:
    """
    텍스트에서 국가를 추측.
    - 겹치는 구간은 (국명 우선 → 긴 키워드 우선)으로 해결 (신성 로마 제국 > 로마)
    - BOUNDARY_REQUIRED 키워드는 조사를 허용하는 단어 경계 확인
    - 복수 국가 발견 시 본문 등장 순서대로 리스트 반환
    """
    candidates: list[tuple[int, int, int, str]] = []  # (우선순위, -길이, 위치, 국가)
    for keyword, country, priority in _KEYWORD_TABLE:
        for pos in _iter_keyword_matches(text, keyword):
            candidates.append((priority, -len(keyword), pos, country))

    if not candidates:
        return "세계"

    candidates.sort()

    consumed: list[tuple[int, int]] = []
    hits: list[tuple[int, str]] = []  # (위치, 국가)
    for _, neg_len, pos, country in candidates:
        end = pos - neg_len
        if any(pos < e and s < end for s, e in consumed):
            continue
        consumed.append((pos, end))
        hits.append((pos, country))

    if not hits:
        return "세계"

    hits.sort()
    ordered: list[str] = []
    for _, country in hits:
        if country not in ordered:
            ordered.append(country)

    return ordered[0] if len(ordered) == 1 else ordered


def is_known_country(name: str) -> bool:
    """COUNTRY_MAP에 등록된 키 또는 값인지 확인"""
    name = name.strip()
    return name in COUNTRY_MAP or name in COUNTRY_MAP.values()


def split_country_names(text: str) -> list[str]:
    """'·', '와', '과'로 구분된 국가명을 분리"""
    return [n.strip() for n in re.split(r"[·,]|와\s|과\s", text) if n.strip()]


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


def days_in_month(month: int) -> int:
    """윤년 기준(2월=29일) 해당 월의 일수"""
    return calendar.monthrange(2024, month)[1]


# ══════════════════════════════════════════════════════════
# HTML 파싱
# ══════════════════════════════════════════════════════════

_ANCHOR_RE = re.compile(r'<a[^>]*\shref="([^"]*)"[^>]*>(.*?)</a>', re.DOTALL)
_BOLD_ANCHOR_RE = re.compile(r'<b>\s*<a[^>]*\shref="([^"]*)"[^>]*>(.*?)</a>', re.DOTALL)


def extract_bold_link_url(li_html: str) -> str | None:
    """<li> HTML에서 <b><a> 볼드 링크 URL 추출"""
    match = _BOLD_ANCHOR_RE.search(li_html)
    return normalize_wiki_url(match.group(1)) if match else None


def extract_holiday_url(header_html: str, holiday_name: str) -> str | None:
    """
    헤더 HTML의 <a> 중 링크 텍스트가 기념일 이름과 가장 많이 겹치는 링크를 반환.
    (기존의 '앞 5글자 부분일치' 방식은 엉뚱한 링크를 잡는 경우가 있어 교체)
    """
    best_url: str | None = None
    best_len = 0
    for bold in (True, False):
        pattern = _BOLD_ANCHOR_RE if bold else _ANCHOR_RE
        for href, label in pattern.findall(header_html):
            label = strip_html(label)
            if not label or "파일:" in href:
                continue
            if label in holiday_name or holiday_name in label:
                if len(label) > best_len:
                    best_url, best_len = normalize_wiki_url(href), len(label)
        if best_url:  # 볼드 링크가 있으면 그것을 우선한다
            break
    return best_url


def parse_year_and_desc(text: str) -> tuple[int, str] | None:
    """'기원전 XXX년 - ...' 또는 'XXX년 - ...' 형식에서 연도와 설명 추출"""
    sep = r"\s*[-–—~:]\s*"
    bc_match = re.match(rf"기원전\s*(\d{{1,4}})년{sep}(.+)", text)
    if bc_match:
        year, desc = -int(bc_match.group(1)), bc_match.group(2).strip()
    else:
        year_match = re.match(rf"(\d{{1,4}})년{sep}(.+)", text)
        if not year_match:
            return None
        year, desc = int(year_match.group(1)), year_match.group(2).strip()

    if not desc or not -3000 <= year <= date.today().year + 1:
        return None
    return year, desc


def apply_wiki_fixes(text: str, date_str: str) -> str:
    """위키 원문의 알려진 오류를 교정"""
    for wrong, right in WIKI_TEXT_FIXES.get(date_str, []):
        text = text.replace(wrong, right)
    return text


def parse_holidays(
    header_html: str, header_text: str, month: int, day: int, holiday_year: int
) -> list[dict]:
    """날짜 헤더의 기념일 텍스트를 파싱하여 holiday 이벤트 리스트로 반환"""
    holidays = []
    date_str = f"{str(month).zfill(2)}-{str(day).zfill(2)}"
    header_text = apply_wiki_fixes(header_text, date_str)
    header_html = apply_wiki_fixes(header_html, date_str)
    parts = [p.strip(" .·") for p in header_text.split(",") if p.strip(" .·")]

    for idx, part in enumerate(parts):
        # "<국가>의 <기념일>" 패턴 — '의'가 여러 번 나올 수 있으므로 모두 시도
        countries_str: str | None = None
        holiday_name = part
        for sep in re.finditer(r"의\s+", part):
            candidate = part[: sep.start()].strip()
            rest = part[sep.end():].strip()
            if candidate and rest and is_country_name(candidate):
                countries_str, holiday_name = candidate, rest
                break

        url = extract_holiday_url(header_html, holiday_name)

        if countries_str is None:
            holiday: dict = {
                "id": f"wiki-hol-{date_str}-{idx}",
                "country": "세계",
                "date": date_str,
                "year": holiday_year,
                "title": part,
                "description": part,
                "category": "holiday",
            }
            if url:
                holiday["url"] = url
            holidays.append(holiday)
            continue

        for cn in split_country_names(countries_str):
            mapped = COUNTRY_MAP.get(cn, cn)
            holiday = {
                "id": f"wiki-hol-{date_str}-{idx}-{mapped}",
                "country": mapped,
                "date": date_str,
                "year": holiday_year,
                "title": holiday_name,
                "description": f"{mapped}의 {holiday_name}.",
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
    li_items = re.findall(r"<li[^>]*>(.*?)</li>", ul_match.group(1), re.DOTALL)

    for li_idx, li in enumerate(li_items):
        url = extract_bold_link_url(li)
        text = strip_html(li)
        text = re.sub(r"\((?:그림|사진|동영상|영상)\)", "", text).strip()
        text = apply_wiki_fixes(text, date_str)

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


def parse_events(html: str, month: int, holiday_year: int) -> list[dict]:
    """HTML에서 날짜 섹션과 이벤트를 파싱"""
    events = []
    seen_ids: set[str] = set()
    last_day = days_in_month(month)

    date_pattern = re.compile(rf'<b><a[^>]*>({month}월\s*(\d+)일)</a></b>')
    matches = list(date_pattern.finditer(html))

    for i, m in enumerate(matches):
        day = int(m.group(2))
        if not 1 <= day <= last_day:
            print(f"  경고: {month}월 {day}일 — 존재하지 않는 날짜, 건너뜁니다.")
            continue

        start_pos = m.end()
        # 마지막 섹션은 다음 날짜 헤더가 없으므로 문서 끝까지. 이벤트 목록은
        # 어차피 섹션의 첫 <ul>만 쓰므로 넉넉히 잡아도 무방하다.
        end_pos = matches[i + 1].start() if i + 1 < len(matches) else len(html)
        section = html[start_pos:end_pos]

        # 기념일 파싱
        ul_start = section.find("<ul")
        if ul_start > 0:
            header_html = section[:ul_start]
            header_text = strip_html(header_html).strip(": \n\t")
            # 헤더가 비정상적으로 길면 날짜 섹션이 아니라 문서 꼬리표일 가능성이 높다
            if header_text and len(header_text) <= 200:
                events.extend(parse_holidays(header_html, header_text, month, day, holiday_year))

        # 역사 이벤트 파싱
        events.extend(parse_history_items(section, month, day, seen_ids))

    return events


# ══════════════════════════════════════════════════════════
# 검증
# ══════════════════════════════════════════════════════════

def validate_events(events: list[dict], month: int) -> list[str]:
    """월별 크롤링 결과의 온전성 검사. 문제 메시지 리스트를 반환(빈 리스트=정상)"""
    problems: list[str] = []
    expected_days = days_in_month(month)
    history = [e for e in events if e["category"] == "history"]

    if not events:
        return [f"{month}월 파싱 결과가 0건입니다 (위키 마크업 변경 가능성)."]

    min_history = expected_days * NOMINAL_ITEMS_PER_DAY // 2
    if len(history) < min_history:
        problems.append(
            f"역사 이벤트가 {len(history)}건뿐입니다 (최소 기대치 {min_history}건)."
        )

    covered = {e["date"] for e in history}
    if len(covered) < expected_days:
        missing = sorted(
            f"{month}/{d}"
            for d in range(1, expected_days + 1)
            if f"{str(month).zfill(2)}-{str(d).zfill(2)}" not in covered
        )
        problems.append(f"역사 이벤트가 없는 날 {len(missing)}일: {', '.join(missing[:10])}")

    dups = [i for i, n in Counter(e["id"] for e in events).items() if n > 1]
    if dups:
        problems.append(f"중복 ID {len(dups)}건: {', '.join(dups[:5])}")

    return problems


# ══════════════════════════════════════════════════════════
# 출력 / 파일 업데이트
# ══════════════════════════════════════════════════════════

def js(value: str) -> str:
    """문자열을 안전한 TS 리터럴로 변환 (따옴표·백슬래시·개행 모두 이스케이프)"""
    return json.dumps(value, ensure_ascii=False)


def format_ts(events: list[dict], month: int) -> str:
    """월별 이벤트를 TS 배열 요소들로 직렬화. 개행으로 끝난다."""
    lines = [f"  // --- 위키백과 오늘의 역사: {month}월 ---"]
    for e in events:
        lines.append("  {")
        lines.append(f"    id: {js(e['id'])},")
        country = e["country"]
        if isinstance(country, list):
            items = ", ".join(js(c) for c in country)
            lines.append(f"    country: [{items}],")
        else:
            lines.append(f"    country: {js(country)},")
        lines.append(f"    date: {js(e['date'])},")
        lines.append(f"    year: {e['year']},")
        lines.append(f"    title: {js(e['title'])},")
        lines.append(f"    description: {js(e['description'])},")
        lines.append(f"    category: {js(e['category'])},")
        if e.get("subcategory"):
            lines.append(f"    subcategory: {js(e['subcategory'])},")
        if "url" in e:
            lines.append(f"    url: {js(e['url'])},")
        lines.append("  },")
    return "\n".join(lines) + "\n"


def print_stats(events: list[dict], verbose: bool = False) -> None:
    """크롤링 결과 통계 출력"""
    history = [e for e in events if e["category"] == "history"]
    holidays = [e for e in events if e["category"] == "holiday"]
    unmatched = [e for e in events if e["country"] == "세계"]

    ratio = (len(unmatched) / len(events) * 100) if events else 0
    print(f"  역사: {len(history)}건, 공휴일: {len(holidays)}건 (총 {len(events)}건)")
    print(f"  '세계'로 분류됨(미매칭): {len(unmatched)}건 ({ratio:.1f}%)")

    uncategorized = sum(1 for e in history if not e.get("subcategory"))
    print(f"  subcategory 미분류: {uncategorized}/{len(history)}건")

    country_counts: Counter[str] = Counter()
    for e in events:
        c = e["country"]
        country_counts.update(c if isinstance(c, list) else [c])
    top = country_counts.most_common(7)
    print(f"  국가 TOP7: {', '.join(f'{k}({v})' for k, v in top)}")

    if verbose and unmatched:
        print("  ── 미매칭 항목 ──")
        for e in unmatched:
            print(f"    · {e['title'][:90]}")


MARKER_RE = re.compile(r"^[ \t]*// --- 위키백과 오늘의 역사: (\d+)월 ---[ \t]*$", re.M)


def upsert_month_block(content: str, month: int, block: str) -> str:
    """
    TS 파일 내용에 월별 블록을 삽입/교체.
    기존 블록이 있으면 '그 자리에' 교체하고, 없으면 월 순서에 맞는 위치에 삽입한다.
    (기존 구현은 항상 배열 끝에 붙여서 재크롤링 시 월 순서가 깨졌다)
    """
    tail = content.rfind("];")
    if tail == -1:
        raise ValueError("historyEvents.ts에서 배열 종료 지점('];')을 찾을 수 없습니다.")

    markers = [(int(m.group(1)), m.start()) for m in MARKER_RE.finditer(content)]
    existing = next((pos for mm, pos in markers if mm == month), None)

    if existing is not None:
        later = [pos for _, pos in markers if pos > existing]
        end = min(later) if later else tail
        return content[:existing] + block + content[end:]

    later = [pos for mm, pos in markers if mm > month]
    insert_at = min(later) if later else tail
    return content[:insert_at] + block + content[insert_at:]


def write_ts_file(path: str, content: str) -> None:
    """원자적 쓰기 — 중간에 실패해도 원본이 남는다"""
    tmp = f"{path}.tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(content)
    os.replace(tmp, path)


def fetch_wiki_page(month: int, timeout: float, retries: int) -> str:
    url = f"https://ko.wikipedia.org/wiki/위키백과:오늘의_역사/{month}월"
    encoded_url = urllib.parse.quote(url, safe=":/?=&")
    req = urllib.request.Request(encoded_url, headers={"User-Agent": USER_AGENT})

    last_error: Exception | None = None
    for attempt in range(1, retries + 1):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return resp.read().decode("utf-8")
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            last_error = e
            if attempt < retries:
                backoff = 2 ** (attempt - 1)
                print(f"  요청 실패({attempt}/{retries}): {e} — {backoff}초 후 재시도")
                time.sleep(backoff)
    raise RuntimeError(f"{month}월 페이지를 가져오지 못했습니다: {last_error}")


def parse_months_arg(arg: str) -> list[int]:
    """
    CLI 인자를 월 리스트로 변환.
    'all' | '3' | '1-6' | '1,3,5' | '1-3,7' 지원.
    """
    if arg.strip().lower() == "all":
        return list(range(1, 13))

    months: set[int] = set()
    for token in arg.split(","):
        token = token.strip()
        if not token:
            continue
        match = re.fullmatch(r"(\d{1,2})(?:\s*-\s*(\d{1,2}))?", token)
        if not match:
            raise argparse.ArgumentTypeError(f"월 형식이 잘못되었습니다: {token!r}")
        lo = int(match.group(1))
        hi = int(match.group(2) or lo)
        if not (1 <= lo <= 12 and 1 <= hi <= 12) or lo > hi:
            raise argparse.ArgumentTypeError(f"월은 1-12 범위여야 합니다: {token!r}")
        months.update(range(lo, hi + 1))

    if not months:
        raise argparse.ArgumentTypeError("처리할 월이 없습니다.")
    return sorted(months)


# ══════════════════════════════════════════════════════════
# 진입점
# ══════════════════════════════════════════════════════════

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="위키백과 '오늘의 역사'를 크롤링해 historyEvents.ts에 삽입합니다.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="예시:\n"
               "  python3 crawl_wiki_history.py 2\n"
               "  python3 crawl_wiki_history.py all\n"
               "  python3 crawl_wiki_history.py 1-3,7 --dry-run\n",
    )
    parser.add_argument("months", type=parse_months_arg,
                        help="대상 월: all | 3 | 1-6 | 1,3,5")
    parser.add_argument("--dry-run", action="store_true",
                        help="파일을 변경하지 않고 결과만 출력")
    parser.add_argument("--verbose", "-v", action="store_true",
                        help="국가 미매칭 항목을 모두 출력")
    parser.add_argument("--force", action="store_true",
                        help="검증에 실패해도 파일에 반영 (데이터 유실 위험)")
    parser.add_argument("--out", default=TS_FILE,
                        help=f"대상 TS 파일 (기본: {TS_FILE})")
    parser.add_argument("--holiday-year", type=int, default=date.today().year,
                        help="공휴일 이벤트에 넣을 연도 (기본: 올해)")
    parser.add_argument("--timeout", type=float, default=20.0,
                        help="HTTP 타임아웃 초 (기본: 20)")
    parser.add_argument("--retries", type=int, default=3,
                        help="요청 재시도 횟수 (기본: 3)")
    parser.add_argument("--delay", type=float, default=1.0,
                        help="요청 간 대기 초 (기본: 1.0)")
    return parser


def main() -> int:
    args = build_parser().parse_args()

    blocks: dict[int, str] = {}
    total_count = 0
    failed: list[int] = []

    for i, month in enumerate(args.months):
        if i > 0 and args.delay > 0:
            time.sleep(args.delay)

        print(f"\n{'='*44}")
        print(f"{month}월 데이터 크롤링 중{'  [dry-run]' if args.dry_run else ''}...")

        try:
            html = fetch_wiki_page(month, args.timeout, args.retries)
        except Exception as e:
            print(f"  오류: {e}")
            failed.append(month)
            continue

        events = parse_events(html, month, args.holiday_year)
        print_stats(events, verbose=args.verbose)

        problems = validate_events(events, month)
        if problems:
            for p in problems:
                print(f"  ⚠️  {p}")
            if not args.force:
                print(f"  → {month}월은 반영하지 않습니다 (강행하려면 --force).")
                failed.append(month)
                continue
            print("  → --force 지정됨: 검증 실패에도 반영합니다.")

        blocks[month] = format_ts(events, month)
        total_count += len(events)

    if args.dry_run:
        for month in sorted(blocks):
            preview = blocks[month]
            print(f"\n[dry-run] {month}월 — 파일 변경 없음")
            print(preview[:500] + ("..." if len(preview) > 500 else ""))
    elif blocks:
        if not os.path.exists(args.out):
            print(f"\n오류: {args.out} 파일을 찾을 수 없습니다. stdout으로 출력합니다:\n")
            for month in sorted(blocks):
                print(blocks[month])
        else:
            # 전체 월을 메모리에서 반영한 뒤 한 번만 기록한다
            with open(args.out, "r", encoding="utf-8") as f:
                content = f.read()
            for month in sorted(blocks):
                action = "교체" if f"오늘의 역사: {month}월" in content else "삽입"
                content = upsert_month_block(content, month, blocks[month])
                print(f"  {month}월 데이터를 {action}했습니다.")
            write_ts_file(args.out, content)
            print(f"  → {args.out} 에 {total_count}건 반영 완료")

    print(f"\n{'='*44}")
    print(f"전체 완료! 총 {total_count}건 처리됨")
    if failed:
        print(f"실패/건너뜀: {', '.join(f'{m}월' for m in failed)}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
