import type { CSSProperties } from 'react'
import { useCallback, useMemo, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'
import { useShellLayout } from '../contexts/ShellLayoutContext'
import { useCalendarBookings, type CalendarBookingRow } from '../hooks/useCalendarBookings'
import { useCalendarExams, type CalendarExamRow } from '../hooks/useCalendarExams'

const WEEKDAYS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'] as const

const TYPE_LABEL: Record<string, string> = {
  GENERAL: 'General',
  PREPARATION: 'Preparation',
  GRADED_WORK_REVIEW: 'Review',
  THESIS: 'Thesis',
}

const TYPE_COLOR: Record<string, { bg: string; color: string }> = {
  GENERAL: { bg: '#e8f0fe', color: '#3b5bdb' },
  PREPARATION: { bg: '#fff0e6', color: '#c2500f' },
  GRADED_WORK_REVIEW: { bg: '#fff3cd', color: '#92570a' },
  THESIS: { bg: '#e6f7ee', color: '#1a7a4a' },
}

const EXAM_STYLE = { bg: '#ede7f6', color: '#5e35b1' }

const STATUS_STYLE: Record<string, { bg: string; color: string }> = {
  ACTIVE: { bg: '#e8f0fe', color: '#3b5bdb' },
  ATTENDED: { bg: '#f0faf4', color: '#1a7a4a' },
  NO_SHOW: { bg: '#fff5f5', color: '#c0392b' },
  CANCELLED: { bg: '#f1f3f6', color: '#6b7ea8' },
  WAITLIST: { bg: '#fffbf0', color: '#92570a' },
}

const meta: CSSProperties = {
  fontSize: '0.68rem',
  fontWeight: 600,
  color: '#8fa3c4',
  textTransform: 'uppercase',
  letterSpacing: '0.05em',
  margin: '0 0 0.25rem 0',
}

function pad2(n: number) {
  return n < 10 ? `0${n}` : String(n)
}

function monthMatrix(year: number, month: number): (number | null)[] {
  const dim = new Date(year, month, 0).getDate()
  const jsDow = new Date(year, month - 1, 1).getDay()
  const padStart = (jsDow + 6) % 7
  const cells: (number | null)[] = []
  for (let i = 0; i < padStart; i++) cells.push(null)
  for (let d = 1; d <= dim; d++) cells.push(d)
  while (cells.length % 7 !== 0) cells.push(null)
  while (cells.length < 42) cells.push(null)
  return cells
}

function isoDay(year: number, month: number, day: number) {
  return `${year}-${pad2(month)}-${pad2(day)}`
}

function bookingTitle(r: CalendarBookingRow, role: 'student' | 'professor'): string {
  if (role === 'student') {
    const p = r.professor_name ?? 'Professor'
    const t = TYPE_LABEL[r.consultation_type] ?? r.consultation_type
    return `${r.time_from} · ${t} · ${p}`
  }
  const who = r.student_name ?? 'Student (see session list)'
  const t = TYPE_LABEL[r.consultation_type] ?? r.consultation_type
  return `${r.time_from} · ${t} · ${who}`
}

function examTitle(r: CalendarExamRow): string {
  const t = r.event_type === 'MIDTERM' ? 'Midterm' : 'Final'
  return `${r.time_from.slice(0, 5)} · ${t} · ${r.course_code} · ${r.event_name}`
}

function parseStudentLayers(raw: string | null): { bookings: boolean; exams: boolean } {
  if (raw == null || raw.trim() === '') return { bookings: true, exams: true }
  const parts = raw.split(',').map((s) => s.trim().toLowerCase()).filter(Boolean)
  let bookings = parts.includes('bookings')
  let exams = parts.includes('exams')
  if (!bookings && !exams) {
    bookings = true
    exams = true
  }
  return { bookings, exams }
}

function layersQueryValue(showBookings: boolean, showExams: boolean): string | undefined {
  if (showBookings && showExams) return undefined
  if (showBookings && !showExams) return 'bookings'
  if (!showBookings && showExams) return 'exams'
  return undefined
}

type CellEntry =
  | { kind: 'booking'; sortKey: string; id: number; chipLabel: string; chipStyle: { bg: string; color: string }; title: string; booking: CalendarBookingRow }
  | { kind: 'exam'; sortKey: string; id: number; chipLabel: string; chipStyle: { bg: string; color: string }; title: string; exam: CalendarExamRow }

function mergeCalendarDay(
  bookings: CalendarBookingRow[],
  exams: CalendarExamRow[],
  role: 'student' | 'professor',
  showBookings: boolean,
  showExams: boolean,
): CellEntry[] {
  const out: CellEntry[] = []
  if (showBookings || role === 'professor') {
    for (const b of bookings) {
      const tc = TYPE_COLOR[b.consultation_type] ?? { bg: '#f1f3f6', color: '#4d6080' }
      out.push({
        kind: 'booking',
        sortKey: b.time_from,
        id: b.id,
        chipLabel: (TYPE_LABEL[b.consultation_type] ?? b.consultation_type).slice(0, 10),
        chipStyle: tc,
        title: bookingTitle(b, role),
        booking: b,
      })
    }
  }
  if (role === 'student' && showExams) {
    for (const e of exams) {
      out.push({
        kind: 'exam',
        sortKey: e.time_from,
        id: e.registration_id + 1_000_000,
        chipLabel: e.event_type === 'MIDTERM' ? 'Midterm' : 'Exam',
        chipStyle: EXAM_STYLE,
        title: examTitle(e),
        exam: e,
      })
    }
  }
  out.sort((a, b) => a.sortKey.localeCompare(b.sortKey))
  return out
}

export default function Calendar() {
  const { user } = useAuth()
  const { sidebarCollapsed } = useShellLayout()
  const role = user?.role === 'professor' ? 'professor' : 'student'
  const [searchParams, setSearchParams] = useSearchParams()
  const now = new Date()
  const [cursor, setCursor] = useState(() => ({ y: now.getFullYear(), m: now.getMonth() + 1 }))
  const [selectedIso, setSelectedIso] = useState<string | null>(null)

  const { bookings: showBookings, exams: showExams } = useMemo(() => {
    if (role !== 'student') return { bookings: true, exams: false }
    return parseStudentLayers(searchParams.get('layers'))
  }, [role, searchParams])

  const setLayers = useCallback(
    (nextBookings: boolean, nextExams: boolean) => {
      let b = nextBookings
      let e = nextExams
      if (!b && !e) {
        b = true
        e = true
      }
      const v = layersQueryValue(b, e)
      if (v === undefined) setSearchParams({}, { replace: true })
      else setSearchParams({ layers: v }, { replace: true })
    },
    [setSearchParams],
  )

  const { rows: bookingRows, loading: bookLoading, error: bookError, reload: reloadBookings } = useCalendarBookings(
    cursor.y,
    cursor.m,
    role,
    role === 'professor' || showBookings,
  )
  const { rows: examRows, loading: examLoading, error: examError, reload: reloadExams } = useCalendarExams(
    cursor.y,
    cursor.m,
    role === 'student' && showExams,
  )

  const loading = bookLoading || (role === 'student' && showExams && examLoading)
  const error = bookError || (role === 'student' && showExams ? examError : null)

  const reload = useCallback(async () => {
    await Promise.all([reloadBookings(), reloadExams()])
  }, [reloadBookings, reloadExams])

  const byDay = useMemo(() => {
    const m = new Map<string, CellEntry[]>()
    const bookingByDay = new Map<string, CalendarBookingRow[]>()
    for (const r of bookingRows) {
      const key = r.session_date.slice(0, 10)
      const arr = bookingByDay.get(key) ?? []
      arr.push(r)
      bookingByDay.set(key, arr)
    }
    const examByDay = new Map<string, CalendarExamRow[]>()
    for (const r of examRows) {
      const key = r.session_date.slice(0, 10)
      const arr = examByDay.get(key) ?? []
      arr.push(r)
      examByDay.set(key, arr)
    }
    const keys = new Set([...bookingByDay.keys(), ...examByDay.keys()])
    for (const key of keys) {
      const merged = mergeCalendarDay(
        bookingByDay.get(key) ?? [],
        examByDay.get(key) ?? [],
        role,
        showBookings,
        showExams,
      )
      if (merged.length) m.set(key, merged)
    }
    return m
  }, [bookingRows, examRows, role, showBookings, showExams])

  const cells = monthMatrix(cursor.y, cursor.m)
  const monthLabel = new Date(cursor.y, cursor.m - 1, 1).toLocaleDateString('en-GB', { month: 'long', year: 'numeric' })

  function shiftMonth(delta: number) {
    setCursor((c) => {
      let mo = c.m + delta
      let y = c.y
      while (mo > 12) {
        mo -= 12
        y += 1
      }
      while (mo < 1) {
        mo += 12
        y -= 1
      }
      return { y, m: mo }
    })
    setSelectedIso(null)
  }

  const bookingsBase = role === 'student' ? '/student/bookings' : '/professor/bookings'
  const selectedDayEntries = selectedIso ? (byDay.get(selectedIso) ?? []) : []
  const selectedBookings = selectedDayEntries.filter((x): x is Extract<CellEntry, { kind: 'booking' }> => x.kind === 'booking').map((x) => x.booking)
  const selectedExams = selectedDayEntries.filter((x): x is Extract<CellEntry, { kind: 'exam' }> => x.kind === 'exam').map((x) => x.exam)

  const asideLayout: CSSProperties = sidebarCollapsed
    ? { flex: '1 1 0', minWidth: 240, minHeight: 0 }
    : { flex: '1 1 300px', minWidth: 280 }

  const previewAside = (
    <aside
      style={{
        ...asideLayout,
        display: 'flex',
        flexDirection: 'column',
        background: '#fff',
        border: '1px solid #e8ecf0',
        borderRadius: 12,
        padding: '1rem 1.15rem',
        minHeight: 320,
        boxSizing: 'border-box',
      }}
    >
      <p style={{ fontSize: '0.72rem', fontWeight: 600, color: '#8fa3c4', textTransform: 'uppercase', letterSpacing: '0.06em', margin: '0 0 0.75rem 0' }}>
        Day preview
      </p>
      {selectedIso ? (
        <>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '0.75rem', flexWrap: 'wrap' }}>
            <p style={{ margin: 0, fontWeight: 600, fontSize: '0.95rem', color: '#0f1f3d', lineHeight: 1.35 }}>
              {new Date(selectedIso).toLocaleDateString('en-GB', { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' })}
            </p>
            <div style={{ display: 'flex', gap: '0.65rem', flexWrap: 'wrap' }}>
              {(role === 'professor' || showBookings) && (
                <Link
                  to={bookingsBase}
                  style={{ fontSize: '0.82rem', fontWeight: 600, color: '#3b5bdb', textDecoration: 'none', whiteSpace: 'nowrap' }}
                >
                  Bookings list →
                </Link>
              )}
              {role === 'student' && showExams ? (
                <Link
                  to="/student/exams"
                  style={{ fontSize: '0.82rem', fontWeight: 600, color: '#5e35b1', textDecoration: 'none', whiteSpace: 'nowrap' }}
                >
                  Exams page →
                </Link>
              ) : null}
            </div>
          </div>
          {selectedDayEntries.length === 0 ? (
            <p style={{ fontSize: '0.85rem', color: '#aab8cc', margin: '0.75rem 0 0 0' }}>Nothing on this day for the selected layers.</p>
          ) : (
            <ul
              style={{
                listStyle: 'none',
                margin: '0.75rem 0 0 0',
                padding: 0,
                display: 'flex',
                flexDirection: 'column',
                gap: '0.65rem',
                overflowY: 'auto',
                flex: 1,
                minHeight: 0,
              }}
            >
              {selectedBookings.map((r) => {
                const tc = TYPE_COLOR[r.consultation_type] ?? { bg: '#f1f3f6', color: '#4d6080' }
                const st = STATUS_STYLE[r.status] ?? { bg: '#f1f3f6', color: '#4d6080' }
                return (
                  <li
                    key={`b-${r.id}`}
                    style={{
                      border: '1px solid #eaecf0',
                      borderRadius: 8,
                      padding: '0.65rem 0.75rem',
                      background: '#fafbfc',
                      flexShrink: 0,
                    }}
                  >
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: '0.5rem', flexWrap: 'wrap' }}>
                      <p style={{ margin: 0, fontWeight: 600, fontSize: '0.88rem', color: '#0f1f3d' }}>
                        {r.time_from}
                        {' – '}
                        {r.time_to}
                      </p>
                      <div style={{ display: 'flex', gap: '0.35rem', flexWrap: 'wrap' }}>
                        <span style={{ fontSize: '0.7rem', fontWeight: 600, padding: '0.15rem 0.5rem', borderRadius: 20, background: tc.bg, color: tc.color }}>
                          {TYPE_LABEL[r.consultation_type] ?? r.consultation_type}
                        </span>
                        <span style={{ fontSize: '0.7rem', fontWeight: 600, padding: '0.15rem 0.5rem', borderRadius: 20, background: st.bg, color: st.color }}>
                          {r.status}
                        </span>
                      </div>
                    </div>
                    {role === 'student' && r.professor_name ? (
                      <p style={{ margin: '0.35rem 0 0 0', fontSize: '0.82rem', color: '#4d6080' }}>{r.professor_name}</p>
                    ) : null}
                    {role === 'professor' && r.student_name ? (
                      <p style={{ margin: '0.35rem 0 0 0', fontSize: '0.82rem', color: '#4d6080' }}>{r.student_name}</p>
                    ) : null}
                    {r.course_code || r.course_name ? (
                      <div style={{ marginTop: '0.35rem' }}>
                        <p style={meta}>Course</p>
                        <p style={{ margin: 0, fontSize: '0.8rem', color: '#4d6080' }}>
                          {[r.course_code, r.course_name].filter(Boolean).join(' · ')}
                        </p>
                      </div>
                    ) : null}
                    {r.hall ? (
                      <div style={{ marginTop: '0.35rem' }}>
                        <p style={meta}>Hall</p>
                        <p style={{ margin: 0, fontSize: '0.8rem', color: '#4d6080' }}>{r.hall}</p>
                      </div>
                    ) : null}
                    {r.task ? (
                      <div style={{ marginTop: '0.35rem' }}>
                        <p style={meta}>Task</p>
                        <p style={{ margin: 0, fontSize: '0.8rem', color: '#4d6080' }}>{r.task}</p>
                      </div>
                    ) : null}
                  </li>
                )
              })}
              {selectedExams.map((r) => (
                <li
                  key={`e-${r.registration_id}`}
                  style={{
                    border: '1px solid #d1c4e9',
                    borderRadius: 8,
                    padding: '0.65rem 0.75rem',
                    background: '#faf8fc',
                    flexShrink: 0,
                  }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: '0.5rem', flexWrap: 'wrap' }}>
                    <p style={{ margin: 0, fontWeight: 600, fontSize: '0.88rem', color: '#0f1f3d' }}>
                      {r.time_from.slice(0, 5)}
                      {' – '}
                      {r.time_to.slice(0, 5)}
                    </p>
                    <span style={{ fontSize: '0.7rem', fontWeight: 600, padding: '0.15rem 0.5rem', borderRadius: 20, background: EXAM_STYLE.bg, color: EXAM_STYLE.color }}>
                      {r.event_type === 'MIDTERM' ? 'Midterm' : 'Final exam'}
                    </span>
                  </div>
                  <p style={{ margin: '0.35rem 0 0 0', fontSize: '0.82rem', color: '#4d6080' }}>{r.event_name}</p>
                  <div style={{ marginTop: '0.35rem' }}>
                    <p style={meta}>Course</p>
                    <p style={{ margin: 0, fontSize: '0.8rem', color: '#4d6080' }}>
                      {r.course_code} · {r.course_name}
                    </p>
                  </div>
                  {r.hall ? (
                    <div style={{ marginTop: '0.35rem' }}>
                      <p style={meta}>Hall</p>
                      <p style={{ margin: 0, fontSize: '0.8rem', color: '#4d6080' }}>{r.hall}</p>
                    </div>
                  ) : null}
                </li>
              ))}
            </ul>
          )}
        </>
      ) : (
        <div style={{ flex: 1, display: 'flex', flexDirection: 'column', justifyContent: 'center', minHeight: 120 }}>
          <p style={{ fontSize: '0.88rem', color: '#6b7ea8', margin: 0, lineHeight: 1.5 }}>
            Select a date on the calendar to see bookings and exams here.
          </p>
        </div>
      )}
    </aside>
  )

  return (
    <div style={{ fontFamily: "'Segoe UI', system-ui, sans-serif", width: '100%', maxWidth: sidebarCollapsed ? 'none' : 1280 }}>
      <div style={{ marginBottom: '1.25rem' }}>
        <h1 style={{ fontSize: '1.4rem', fontWeight: 700, color: '#0f1f3d', margin: 0 }}>Calendar</h1>
        <p style={{ fontSize: '0.875rem', color: '#8fa3c4', margin: '0.25rem 0 0 0' }}>
          {role === 'student'
            ? 'Monthly view of consultations and registered exams. Use the checkboxes to show or hide each layer.'
            : 'Monthly view of your consultation bookings.'}
        </p>
      </div>

      {role === 'student' ? (
        <div
          style={{
            display: 'flex',
            flexWrap: 'wrap',
            gap: '1rem',
            alignItems: 'center',
            marginBottom: '1rem',
            fontSize: '0.84rem',
            color: '#4d6080',
          }}
        >
          <label style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', cursor: 'pointer' }}>
            <input
              type="checkbox"
              checked={showBookings}
              onChange={(ev) => setLayers(ev.target.checked, showExams)}
            />
            My bookings
          </label>
          <label style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', cursor: 'pointer' }}>
            <input
              type="checkbox"
              checked={showExams}
              onChange={(ev) => setLayers(showBookings, ev.target.checked)}
            />
            My exams
          </label>
        </div>
      ) : null}

      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          gap: '0.75rem',
          flexWrap: 'wrap',
          marginBottom: '1rem',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <button
            type="button"
            onClick={() => shiftMonth(-1)}
            style={{
              width: 36,
              height: 36,
              borderRadius: 8,
              border: '1px solid #d1d9e6',
              background: '#fff',
              cursor: 'pointer',
              fontSize: '1rem',
              color: '#0f1f3d',
            }}
            aria-label="Previous month"
          >
            ‹
          </button>
          <h2 style={{ margin: 0, fontSize: '1.1rem', fontWeight: 600, color: '#0f1f3d', minWidth: 200, textAlign: 'center' }}>
            {monthLabel}
          </h2>
          <button
            type="button"
            onClick={() => shiftMonth(1)}
            style={{
              width: 36,
              height: 36,
              borderRadius: 8,
              border: '1px solid #d1d9e6',
              background: '#fff',
              cursor: 'pointer',
              fontSize: '1rem',
              color: '#0f1f3d',
            }}
            aria-label="Next month"
          >
            ›
          </button>
        </div>
        <button
          type="button"
          onClick={() => void reload()}
          disabled={loading}
          style={{
            padding: '0.45rem 0.9rem',
            borderRadius: 8,
            border: '1px solid #d1d9e6',
            background: '#fff',
            fontSize: '0.82rem',
            fontWeight: 500,
            color: '#4d6080',
            cursor: loading ? 'wait' : 'pointer',
          }}
        >
          Refresh
        </button>
      </div>

      {loading && <p style={{ fontSize: '0.85rem', color: '#aab8cc', marginBottom: '0.75rem' }}>Loading…</p>}
      {error && <p style={{ fontSize: '0.85rem', color: '#c0392b', marginBottom: '0.75rem' }}>{error}</p>}

      {(() => {
        const calendarGrid = (
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(7, minmax(0, 1fr))',
              gap: 1,
              background: '#e8ecf0',
              border: '1px solid #e8ecf0',
              borderRadius: 10,
              overflow: 'hidden',
            }}
          >
            {WEEKDAYS.map((w) => (
              <div
                key={w}
                style={{
                  background: '#f5f7fa',
                  padding: '0.45rem 0.35rem',
                  fontSize: '0.72rem',
                  fontWeight: 600,
                  color: '#8fa3c4',
                  textAlign: 'center',
                }}
              >
                {w}
              </div>
            ))}
            {cells.map((day, idx) => {
              if (day == null) {
                return <div key={`e-${idx}`} style={{ background: '#fafbfc', minHeight: 88 }} />
              }
              const iso = isoDay(cursor.y, cursor.m, day)
              const dayRows = byDay.get(iso) ?? []
              const isSelected = selectedIso === iso
              return (
                <button
                  key={iso}
                  type="button"
                  onClick={() => setSelectedIso(iso)}
                  style={{
                    background: isSelected ? '#eef2ff' : '#fff',
                    border: 'none',
                    margin: 0,
                    padding: '0.35rem 0.3rem 0.45rem',
                    minHeight: 88,
                    textAlign: 'left',
                    cursor: 'pointer',
                    display: 'flex',
                    flexDirection: 'column',
                    alignItems: 'stretch',
                    gap: 2,
                  }}
                >
                  <span style={{ fontSize: '0.78rem', fontWeight: 700, color: '#0f1f3d' }}>{day}</span>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 2, overflow: 'hidden' }}>
                    {dayRows.slice(0, 3).map((r) => (
                      <span
                        key={r.id}
                        style={{
                          fontSize: '0.62rem',
                          fontWeight: 600,
                          lineHeight: 1.25,
                          padding: '2px 4px',
                          borderRadius: 4,
                          background: r.chipStyle.bg,
                          color: r.chipStyle.color,
                          overflow: 'hidden',
                          textOverflow: 'ellipsis',
                          whiteSpace: 'nowrap',
                        }}
                        title={r.title}
                      >
                        {r.sortKey.slice(0, 5)} {r.chipLabel}
                      </span>
                    ))}
                    {dayRows.length > 3 ? (
                      <span style={{ fontSize: '0.62rem', color: '#8fa3c4' }}>+{dayRows.length - 3} more</span>
                    ) : null}
                  </div>
                </button>
              )
            })}
          </div>
        )

        if (sidebarCollapsed) {
          return (
            <div
              style={{
                display: 'flex',
                flexDirection: 'row',
                flexWrap: 'nowrap',
                alignItems: 'stretch',
                width: '100%',
                minWidth: 0,
                gap: '1.25rem',
              }}
            >
              <div
                style={{
                  flex: '2 1 0',
                  minWidth: 280,
                  minHeight: 0,
                  overflow: 'hidden',
                }}
              >
                {calendarGrid}
              </div>
              {previewAside}
            </div>
          )
        }

        return (
          <div
            style={{
              display: 'flex',
              flexDirection: 'row',
              alignItems: 'stretch',
              gap: '1.25rem',
              flexWrap: 'wrap',
            }}
          >
            <div style={{ flex: '2 1 480px', minWidth: 0 }}>
              {calendarGrid}
            </div>
            {previewAside}
          </div>
        )
      })()}
    </div>
  )
}
