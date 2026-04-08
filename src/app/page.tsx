"use client";

import styles from "./page.module.css";
import { useEffect, useMemo, useRef, useState, useSyncExternalStore } from "react";
import { historyEvents } from "@/lib/historyEvents";

// useSyncExternalStore용 헬퍼 — 컴포넌트 외부에 두어야 안정적인 참조 보장
function subscribeToColorScheme(callback: () => void) {
  const mq = window.matchMedia("(prefers-color-scheme: dark)");
  mq.addEventListener("change", callback);
  return () => mq.removeEventListener("change", callback);
}
const getSystemDark = () => window.matchMedia("(prefers-color-scheme: dark)").matches;
const getServerDark = () => false;

const dayNames = ["일", "월", "화", "수", "목", "금", "토"];

type CategoryFilter = "all" | "history" | "holiday";
type SortOrder = "asc" | "desc";

function getCountries(country: string | string[]): string[] {
  return Array.isArray(country) ? country : [country];
}

function matchesCountry(country: string | string[], selected: string): boolean {
  if (selected === "전체") return true;
  return getCountries(country).includes(selected);
}

export default function Home() {
  const [selectedCountry, setSelectedCountry] = useState("전체");
  const [searchQuery, setSearchQuery] = useState("");
  const [categoryFilter, setCategoryFilter] = useState<CategoryFilter>("all");
  const [sortOrder, setSortOrder] = useState<SortOrder>("asc");
  // 시스템 다크 모드 — useSyncExternalStore로 SSR-safe하게 구독
  const systemDark = useSyncExternalStore(subscribeToColorScheme, getSystemDark, getServerDark);
  // 수동 토글 override (null = 시스템 설정 따름)
  const [manualDark, setManualDark] = useState<boolean | null>(null);
  const darkMode = manualDark ?? systemDark;

  const today = new Date();
  const currentYear = today.getFullYear();
  const todayMonth = String(today.getMonth() + 1).padStart(2, "0");
  const todayDate = String(today.getDate()).padStart(2, "0");

  const [selectedMonth, setSelectedMonth] = useState(todayMonth);
  const [selectedDate, setSelectedDate] = useState(`${todayMonth}-${todayDate}`);

  // ─── 다크 모드: data-theme 속성 동기화 ───
  useEffect(() => {
    document.documentElement.setAttribute("data-theme", darkMode ? "dark" : "light");
  }, [darkMode]);

  // ─── 초기화 ───
  const handleReset = () => {
    setSelectedCountry("전체");
    setSearchQuery("");
    setSelectedMonth(todayMonth);
    setSelectedDate(`${todayMonth}-${todayDate}`);
    setCategoryFilter("all");
    setSortOrder("asc");
  };

  // ─── 월 이동 ───
  const handleMonthChange = (direction: "prev" | "next") => {
    const currentMonthIndex = Number(selectedMonth) - 1;
    const newDate = new Date(currentYear, currentMonthIndex + (direction === "next" ? 1 : -1), 1);
    const newMonth = String(newDate.getMonth() + 1).padStart(2, "0");
    setSelectedMonth(newMonth);
    setSelectedDate(`${newMonth}-01`);
  };

  // ─── 키보드 단축키 ───
  // ← → : 날짜 이동  |  [ , : 이전 달  |  ] . : 다음 달
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      const target = e.target as HTMLElement;
      if (target.tagName === "INPUT" || target.tagName === "TEXTAREA") return;

      if (e.key === "ArrowLeft") {
        e.preventDefault();
        const [mm, dd] = selectedDate.split("-").map(Number);
        const date = new Date(currentYear, mm - 1, dd);
        date.setDate(date.getDate() - 1);
        const newMonth = String(date.getMonth() + 1).padStart(2, "0");
        const newDay = String(date.getDate()).padStart(2, "0");
        setSelectedDate(`${newMonth}-${newDay}`);
        setSelectedMonth(newMonth);
      } else if (e.key === "ArrowRight") {
        e.preventDefault();
        const [mm, dd] = selectedDate.split("-").map(Number);
        const date = new Date(currentYear, mm - 1, dd);
        date.setDate(date.getDate() + 1);
        const newMonth = String(date.getMonth() + 1).padStart(2, "0");
        const newDay = String(date.getDate()).padStart(2, "0");
        setSelectedDate(`${newMonth}-${newDay}`);
        setSelectedMonth(newMonth);
      } else if (e.key === "[" || e.key === ",") {
        e.preventDefault();
        const monthIndex = Number(selectedMonth) - 1;
        const prevDate = new Date(currentYear, monthIndex - 1, 1);
        const newMonth = String(prevDate.getMonth() + 1).padStart(2, "0");
        setSelectedMonth(newMonth);
        setSelectedDate(`${newMonth}-01`);
      } else if (e.key === "]" || e.key === ".") {
        e.preventDefault();
        const monthIndex = Number(selectedMonth) - 1;
        const nextDate = new Date(currentYear, monthIndex + 1, 1);
        const newMonth = String(nextDate.getMonth() + 1).padStart(2, "0");
        setSelectedMonth(newMonth);
        setSelectedDate(`${newMonth}-01`);
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [selectedDate, selectedMonth, currentYear]);

  // ─── 국가 목록 ───
  const countries = useMemo(() => {
    const all = historyEvents.flatMap((event) => getCountries(event.country));
    const unique = [...new Set(all)].sort((a, b) => a.localeCompare(b, "ko"));
    return ["전체", ...unique];
  }, []);

  const [countrySearch, setCountrySearch] = useState("");
  const [countryOpen, setCountryOpen] = useState(false);
  const comboRef = useRef<HTMLDivElement>(null);

  const filteredCountries = useMemo(() => {
    if (!countrySearch) return countries;
    return countries.filter((c) => c.includes(countrySearch));
  }, [countries, countrySearch]);

  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (comboRef.current && !comboRef.current.contains(e.target as Node)) {
        setCountryOpen(false);
        setCountrySearch("");
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  // ─── 이벤트 필터링 (검색 + 국가) ───
  const scopedEvents = useMemo(() => {
    return historyEvents.filter((event) => {
      if (!matchesCountry(event.country, selectedCountry)) return false;
      if (searchQuery) {
        const q = searchQuery.toLowerCase();
        return event.title.toLowerCase().includes(q) || event.description.toLowerCase().includes(q);
      }
      return true;
    });
  }, [selectedCountry, searchQuery]);

  // ─── 카테고리 필터 적용 이벤트 (달력 + 목록 공통) ───
  const categoryFilteredEvents = useMemo(() => {
    if (categoryFilter === "all") return scopedEvents;
    return scopedEvents.filter((event) => {
      if (categoryFilter === "history") return event.category !== "holiday";
      if (categoryFilter === "holiday") return event.category === "holiday";
      return true;
    });
  }, [scopedEvents, categoryFilter]);

  // ─── 달력용 날짜별 이벤트 ───
  const eventsByDate = useMemo(() => {
    return categoryFilteredEvents.reduce<Record<string, typeof categoryFilteredEvents>>((acc, event) => {
      if (!acc[event.date]) {
        acc[event.date] = [];
      }
      acc[event.date].push(event);
      return acc;
    }, {});
  }, [categoryFilteredEvents]);

  // ─── 달력 셀 데이터 ───
  const monthData = useMemo(() => {
    const monthIndex = Number(selectedMonth) - 1;
    const firstWeekday = new Date(currentYear, monthIndex, 1).getDay();
    const cells: Array<number | null> = [];
    const lastDate = new Date(currentYear, monthIndex + 1, 0).getDate();

    for (let i = 0; i < firstWeekday; i += 1) {
      cells.push(null);
    }
    for (let day = 1; day <= lastDate; day += 1) {
      cells.push(day);
    }

    return cells;
  }, [selectedMonth, currentYear]);

  // ─── 선택 날짜 이벤트 (카테고리 필터 적용 후 정렬) ───
  const filteredEvents = useMemo(() => {
    return categoryFilteredEvents
      .filter((event) => event.date === selectedDate)
      .sort((a, b) => sortOrder === "asc" ? a.year - b.year : b.year - a.year);
  }, [categoryFilteredEvents, selectedDate, sortOrder]);

  const selectedDay = Number(selectedDate.split("-")[1]);

  return (
    <div className={styles.page}>
      <main className={styles.main}>

        {/* ─── 헤더 ─── */}
        <section className={styles.header}>
          <div className={styles.titleRow}>
            <h1>역사 캘린더</h1>
            <div className={styles.titleActions}>
              <button
                type="button"
                className={styles.darkToggle}
                onClick={() => setManualDark(!darkMode)}
                aria-label={darkMode ? "라이트 모드로 전환" : "다크 모드로 전환"}
                title={darkMode ? "라이트 모드" : "다크 모드"}
              >
                {darkMode ? (
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <circle cx="12" cy="12" r="5" />
                    <line x1="12" y1="1" x2="12" y2="3" />
                    <line x1="12" y1="21" x2="12" y2="23" />
                    <line x1="4.22" y1="4.22" x2="5.64" y2="5.64" />
                    <line x1="18.36" y1="18.36" x2="19.78" y2="19.78" />
                    <line x1="1" y1="12" x2="3" y2="12" />
                    <line x1="21" y1="12" x2="23" y2="12" />
                    <line x1="4.22" y1="19.78" x2="5.64" y2="18.36" />
                    <line x1="18.36" y1="5.64" x2="19.78" y2="4.22" />
                  </svg>
                ) : (
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z" />
                  </svg>
                )}
              </button>
              <button type="button" onClick={handleReset} className={styles.resetButton} aria-label="초기화">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M1 4v6h6" />
                  <path d="M3.51 15a9 9 0 1 0 2.13-9.36L1 10" />
                </svg>
                초기화
              </button>
            </div>
          </div>
          <p className={styles.subtitle}>오늘의 역사적 사건을 확인해보세요</p>
        </section>

        {/* ─── 필터 ─── */}
        <section className={styles.filters}>
          <div className={styles.searchWrapper}>
            <svg className={styles.searchIcon} width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="var(--text-muted)" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
              <circle cx="11" cy="11" r="8" />
              <path d="M21 21l-4.35-4.35" />
            </svg>
            <input
              type="text"
              className={styles.searchInput}
              placeholder="사건 검색..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
            />
            {searchQuery && (
              <button type="button" className={styles.searchClear} onClick={() => setSearchQuery("")} aria-label="검색 초기화">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M18 6L6 18" />
                  <path d="M6 6l12 12" />
                </svg>
              </button>
            )}
          </div>

          <div className={styles.comboWrapper} ref={comboRef}>
            <button
              type="button"
              className={styles.comboButton}
              onClick={() => {
                setCountryOpen(!countryOpen);
                setCountrySearch("");
              }}
            >
              {selectedCountry}
              <svg width="10" height="6" viewBox="0 0 10 6" fill="none">
                <path d="M0 0l5 6 5-6z" fill="var(--text-muted)" />
              </svg>
            </button>
            {countryOpen && (
              <div className={styles.comboDropdown}>
                <input
                  type="text"
                  className={styles.comboSearch}
                  placeholder="국가 검색..."
                  value={countrySearch}
                  onChange={(e) => setCountrySearch(e.target.value)}
                  autoFocus
                />
                <ul className={styles.comboList}>
                  {filteredCountries.length === 0 ? (
                    <li className={styles.comboEmpty}>결과 없음</li>
                  ) : (
                    filteredCountries.map((country) => (
                      <li key={country}>
                        <button
                          type="button"
                          className={`${styles.comboOption} ${selectedCountry === country ? styles.comboOptionActive : ""}`}
                          onClick={() => {
                            setSelectedCountry(country);
                            setCountryOpen(false);
                            setCountrySearch("");
                          }}
                        >
                          {country}
                        </button>
                      </li>
                    ))
                  )}
                </ul>
              </div>
            )}
          </div>

          {/* 카테고리 토글 */}
          <div className={styles.categoryToggle}>
            <button
              type="button"
              className={`${styles.categoryButton} ${categoryFilter === "all" ? styles.categoryButtonActive : ""}`}
              onClick={() => setCategoryFilter("all")}
            >
              전체
            </button>
            <button
              type="button"
              className={`${styles.categoryButton} ${categoryFilter === "history" ? styles.categoryButtonHistory : ""}`}
              onClick={() => setCategoryFilter("history")}
            >
              역사
            </button>
            <button
              type="button"
              className={`${styles.categoryButton} ${categoryFilter === "holiday" ? styles.categoryButtonHoliday : ""}`}
              onClick={() => setCategoryFilter("holiday")}
            >
              공휴일
            </button>
          </div>
        </section>

        {/* ─── 달력 ─── */}
        <section className={styles.calendarSection}>
          <div className={styles.calendarHeader}>
            <button type="button" onClick={() => handleMonthChange("prev")} className={styles.navButton} aria-label="이전 달">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M15 18l-6-6 6-6" />
              </svg>
            </button>
            <h2 className={styles.monthTitle}>{currentYear}년 {Number(selectedMonth)}월</h2>
            <button type="button" onClick={() => handleMonthChange("next")} className={styles.navButton} aria-label="다음 달">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M9 18l6-6-6-6" />
              </svg>
            </button>
          </div>
          <div className={styles.weekHeader}>
            {dayNames.map((dayName) => (
              <span key={dayName} className={dayName === "일" ? styles.sunday : dayName === "토" ? styles.saturday : undefined}>
                {dayName}
              </span>
            ))}
          </div>
          <div className={styles.calendarGrid}>
            {monthData.map((day, index) => {
              if (day === null) {
                return <div key={`empty-${index}`} className={styles.emptyCell} />;
              }

              const dayText = String(day).padStart(2, "0");
              const dayKey = `${selectedMonth}-${dayText}`;
              const events = eventsByDate[dayKey] || [];
              const historyCount = events.filter((e) => e.category !== "holiday").length;
              const holidayCount = events.filter((e) => e.category === "holiday").length;
              const isSelected = selectedDate === dayKey;
              const isSunday = index % 7 === 0;

              return (
                <button key={dayKey} type="button" className={`${styles.dayButton} ${isSelected ? styles.selected : ""}`} onClick={() => setSelectedDate(dayKey)}>
                  <span className={`${styles.dayNumber} ${holidayCount > 0 || isSunday ? styles.holidayText : ""}`}>{day}</span>
                  <div className={styles.dotContainer}>
                    {historyCount > 0 && <span className={styles.dotHistory} />}
                    {holidayCount > 0 && <span className={styles.dotHoliday} />}
                  </div>
                </button>
              );
            })}
          </div>
          <p className={styles.keyboardHint}>← → 날짜 이동 &nbsp;·&nbsp; [ ] 월 이동</p>
        </section>

        {/* ─── 이벤트 목록 ─── */}
        <section className={styles.results}>
          <div className={styles.resultHeader}>
            <h2 className={styles.resultTitle}>
              {Number(selectedMonth)}월 {selectedDay}일의 역사
            </h2>
            <div className={styles.resultMeta}>
              <span className={styles.resultCount}>{filteredEvents.length}건</span>
              <button
                type="button"
                className={styles.sortButton}
                onClick={() => setSortOrder((s) => (s === "asc" ? "desc" : "asc"))}
                title={sortOrder === "asc" ? "오래된 순 정렬 중" : "최신 순 정렬 중"}
              >
                <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                  {sortOrder === "asc" ? (
                    <>
                      <path d="M12 5v14" />
                      <path d="M5 12l7 7 7-7" />
                    </>
                  ) : (
                    <>
                      <path d="M12 19V5" />
                      <path d="M5 12l7-7 7 7" />
                    </>
                  )}
                </svg>
                {sortOrder === "asc" ? "오래된 순" : "최신 순"}
              </button>
            </div>
          </div>

          {filteredEvents.length === 0 ? (
            <div className={styles.emptyState}>
              <p>기록된 역사적 사건이 없습니다</p>
            </div>
          ) : (
            <ul className={styles.eventList}>
              {filteredEvents.map((eventItem) => (
                <li key={eventItem.id} className={styles.card}>
                  {eventItem.url ? (
                    <a href={eventItem.url} target="_blank" rel="noopener noreferrer" className={styles.cardLink}>
                      <div className={styles.cardHeader}>
                        {eventItem.category === "holiday" ? <span className={styles.badgeHoliday}>공휴일</span> : <span className={styles.badgeHistory}>역사</span>}
                        {getCountries(eventItem.country).map((c) => (
                          <span key={c} className={styles.badgeCountry}>{c}</span>
                        ))}
                        <span className={styles.cardYear}>{eventItem.year}년</span>
                      </div>
                      <h3 className={styles.cardTitle}>{eventItem.title}</h3>
                      {eventItem.title !== eventItem.description && <p className={styles.cardDesc}>{eventItem.description}</p>}
                    </a>
                  ) : (
                    <div className={styles.cardContent}>
                      <div className={styles.cardHeader}>
                        {eventItem.category === "holiday" ? <span className={styles.badgeHoliday}>공휴일</span> : <span className={styles.badgeHistory}>역사</span>}
                        {getCountries(eventItem.country).map((c) => (
                          <span key={c} className={styles.badgeCountry}>{c}</span>
                        ))}
                        <span className={styles.cardYear}>{eventItem.year}년</span>
                      </div>
                      <h3 className={styles.cardTitle}>{eventItem.title}</h3>
                      {eventItem.title !== eventItem.description && <p className={styles.cardDesc}>{eventItem.description}</p>}
                    </div>
                  )}
                </li>
              ))}
            </ul>
          )}
        </section>

      </main>
    </div>
  );
}
