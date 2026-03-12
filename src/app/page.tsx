"use client";

import styles from "./page.module.css";
import { useMemo, useState } from "react";
import { historyEvents } from "@/lib/historyEvents";

const dayNames = ["일", "월", "화", "수", "목", "금", "토"];

export default function Home() {
  const [selectedCountry, setSelectedCountry] = useState("전체");

  const today = new Date();
  const todayMonth = String(today.getMonth() + 1).padStart(2, "0");
  const todayDate = String(today.getDate()).padStart(2, "0");

  const [selectedMonth, setSelectedMonth] = useState(todayMonth);
  const [selectedDate, setSelectedDate] = useState(`${todayMonth}-${todayDate}`);

  const handleReset = () => {
    setSelectedCountry("전체");
    setSelectedMonth(todayMonth);
    setSelectedDate(`${todayMonth}-${todayDate}`);
  };

  const handleMonthChange = (direction: "prev" | "next") => {
    const currentMonthIndex = Number(selectedMonth) - 1;
    const newDate = new Date(2026, currentMonthIndex + (direction === "next" ? 1 : -1), 1);
    const newMonth = String(newDate.getMonth() + 1).padStart(2, "0");

    setSelectedMonth(newMonth);
    setSelectedDate(`${newMonth}-01`);
  };

  const countries = useMemo(() => {
    return ["전체", ...new Set(historyEvents.map((event) => event.country))];
  }, []);

  const scopedEvents = useMemo(() => {
    return historyEvents.filter((event) => (selectedCountry === "전체" ? true : event.country === selectedCountry));
  }, [selectedCountry]);

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
    const year = 2026;
    const monthIndex = Number(selectedMonth) - 1;
    const firstWeekday = new Date(year, monthIndex, 1).getDay();
    const cells: Array<number | null> = [];
    const lastDate = new Date(year, monthIndex + 1, 0).getDate();

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
          <div className={styles.selectWrapper}>
            <label htmlFor="country-select">국가</label>
            <select id="country-select" value={selectedCountry} onChange={(e) => setSelectedCountry(e.target.value)}>
              {countries.map((country) => (
                <option key={country} value={country}>
                  {country}
                </option>
              ))}
            </select>
          </div>
        </section>

        <section className={styles.calendarSection}>
          <div className={styles.calendarHeader}>
            <button type="button" onClick={() => handleMonthChange("prev")} className={styles.navButton} aria-label="이전 달">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M15 18l-6-6 6-6" />
              </svg>
            </button>
            <h2 className={styles.monthTitle}>{Number(selectedMonth)}월</h2>
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
                        <span className={styles.badgeCountry}>{eventItem.country}</span>
                        <span className={styles.cardYear}>{eventItem.year}년</span>
                      </div>
                      <h3 className={styles.cardTitle}>{eventItem.title}</h3>
                      {eventItem.title !== eventItem.description && <p className={styles.cardDesc}>{eventItem.description}</p>}
                    </a>
                  ) : (
                    <div className={styles.cardContent}>
                      <div className={styles.cardHeader}>
                        {eventItem.category === "holiday" ? <span className={styles.badgeHoliday}>공휴일</span> : <span className={styles.badgeHistory}>역사</span>}
                        <span className={styles.badgeCountry}>{eventItem.country}</span>
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
