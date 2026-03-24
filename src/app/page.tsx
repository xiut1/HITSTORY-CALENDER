"use client";

import styles from "./page.module.css";
import { useEffect, useMemo, useRef, useState } from "react";
import { historyEvents } from "@/lib/historyEvents";

const dayNames = ["일", "월", "화", "수", "목", "금", "토"];

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

  const today = new Date();
  const currentYear = today.getFullYear();
  const todayMonth = String(today.getMonth() + 1).padStart(2, "0");
  const todayDate = String(today.getDate()).padStart(2, "0");

  const [selectedMonth, setSelectedMonth] = useState(todayMonth);
  const [selectedDate, setSelectedDate] = useState(`${todayMonth}-${todayDate}`);

  const handleReset = () => {
    setSelectedCountry("전체");
    setSearchQuery("");
    setSelectedMonth(todayMonth);
    setSelectedDate(`${todayMonth}-${todayDate}`);
  };

  const handleMonthChange = (direction: "prev" | "next") => {
    const currentMonthIndex = Number(selectedMonth) - 1;
    const newDate = new Date(currentYear, currentMonthIndex + (direction === "next" ? 1 : -1), 1);
    const newMonth = String(newDate.getMonth() + 1).padStart(2, "0");

    setSelectedMonth(newMonth);
    setSelectedDate(`${newMonth}-01`);
  };

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

  const eventsByDate = useMemo(() => {
    return scopedEvents.reduce<Record<string, typeof scopedEvents>>((acc, event) => {
      if (!acc[event.date]) {
        acc[event.date] = [];
      }
      acc[event.date].push(event);
      return acc;
    }, {});
  }, [scopedEvents]);

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
  }, [selectedMonth]);

  const filteredEvents = useMemo(() => {
    return scopedEvents.filter((event) => event.date === selectedDate).sort((a, b) => a.year - b.year);
  }, [scopedEvents, selectedDate]);

  return (
    <div className={styles.page}>
      <main className={styles.main}>
        <section className={styles.header}>
          <div className={styles.titleRow}>
            <h1>역사 캘린더</h1>
            <button type="button" onClick={handleReset} className={styles.resetButton} aria-label="초기화">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                <path d="M1 4v6h6" />
                <path d="M3.51 15a9 9 0 1 0 2.13-9.36L1 10" />
              </svg>
              초기화
            </button>
          </div>
          <p className={styles.subtitle}>오늘의 역사적 사건을 확인해보세요</p>
        </section>

        <section className={styles.filters}>
          <div className={styles.searchWrapper}>
            <svg className={styles.searchIcon} width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#8b95a1" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
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
                <path d="M0 0l5 6 5-6z" fill="#8b95a1" />
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
        </section>

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
        </section>

        <section className={styles.results}>
          <h2 className={styles.resultTitle}>
            {Number(selectedMonth)}월 {Number(selectedDate.split("-")[1])}일의 역사
            <span style={{ color: "#b0b8c1", fontWeight: 500, fontSize: 14, marginLeft: 6 }}>{filteredEvents.length}건</span>
          </h2>
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
