# UniConsult — Project Context

## What the app does

UniConsult is a university consultation booking system for the Faculty of Electrical Engineering (ETF), Belgrade. Students book one-on-one or group consultations with their professors through a **rule-based conversational chatbot** (UniBot), instead of traditional web forms. Professors manage their availability, track attendance, and announce preparation sessions for upcoming exams. An admin manages users, courses, exam schedules, and system-wide announcements.

## User roles

| Role | Email (demo) | Password |
|---|---|---|
| Student — Ivan Horvat (final year, thesis approved with Ana Marković) | `student@university.edu` | `StudentPass123!` |
| Student — Milica Simić (final year, pending thesis with Petrović) | `milica.student@university.edu` | `StudentPass123!` |
| Student — Nikola Ilić (not final year, rejected thesis with Ana) | `nikola.student@university.edu` | `StudentPass123!` |
| Student — Sara Kovačević (not final year, no thesis) | `sara.student@university.edu` | `StudentPass123!` |
| Student — Tea Marković (not final year) | `tea.markovic.student@university.edu` | `StudentPass123!` |
| Professor — Ana Marković (Databases) | `prof.markovic@university.edu` | `ProfPass123!` |
| Professor — Petar Petrović (Algorithms, ML) | `prof.petrovic@university.edu` | `ProfPass123!` |
| Professor — Jelena Jovanović (OS, ML, Cybersecurity) | `prof.jovanovic@university.edu` | `ProfPass123!` |
| Admin | `admin@university.edu` | `AdminPass123!` |

## Consultation types

| Type | When to use | Booking channel |
|---|---|---|
| **General** | Course question, homework, topic help | Chatbot (finds available windows) |
| **Thesis** | Mentor meetings (final-year only, approved mentor required) | Chatbot |
| **Preparation** | Exam prep — professor must announce a session first | Chatbot (announced slots only) |
| **Graded work review** | Review graded exam/lab — professor announces | Chatbot (announced slots only) |

## Chatbot flow (phases)

```
collect        → gather professor + type + course
task_collect   → ask "what topic?" (GENERAL only)
pick_date      → show date chips
pick_time      → show time slot chips for chosen date
confirm_booking→ summary + Yes/No chips
done           → booking confirmed or flow ended
```

Special mid-flow branches:
- **group_join_offer** — another student already booked same professor/course/topic, offer to join
- **pick_prep_exam** — two prep sessions for same course, ask which exam
- **waitlist_offer** — all slots full, offer session waitlist or day waitlist
- **preparation_times** — collect preferred times before registering a prep vote (Phase 2, currently commented out)

Reset at any time: type `start over`.

---

## Chatbot test scenarios

Run seed first: `python -m backend.db.seed`

### Scenario 1 — Happy path, general consultation
**Login:** Ivan (`student@university.edu`)

```
"I need help with Petrovic about algorithms"
→ bot asks topic
"recurrence relations"
→ date chips appear (pick any)
→ time chips appear (pick any)
→ confirm → booked
```

### Scenario 2 — Group booking offer
**Login:** Ivan (`student@university.edu`)

Tea Marković already has a booking with Ana Marković for Databases with topic `SQL joins`. When Ivan asks for the same topic, the bot offers to join Tea's session.

```
"general consultation with Ana Markovic, databases"
→ bot asks topic
"SQL joins"
→ GROUP OFFER fires: "Another student already booked Ana Marković for Databases…"
→ chips: [Yes, join that session] [No, pick a different time]
```

### Scenario 3 — Graded work review (free slots)
**Login:** Ivan (`student@university.edu`)

A graded review session exists for Algorithms / Petrović with 3 free slots.

```
"I want to check my grade with Petrovic for algorithms"
→ date chips (today + a few days)
→ time chips → confirm → booked
```

### Scenario 4 — Graded work review (waitlist, full session)
**Login:** Ivan (`student@university.edu`)

Ana's review session is full (capacity 1, Sara booked).

```
"review my grade with Ana for databases"
→ "All listed times are full. Join the waitlist…"
→ waitlist chips appear
```

### Scenario 5 — Preparation booking (single event)
**Login:** Milica (`milica.student@university.edu`)

Jelena Jovanović has an announced prep session for OS.

```
"preparation for operating systems with Jovanovic"
→ picks date of jelena_prep_upcoming → time → confirm → booked
```

### Scenario 6 — Preparation exam disambiguation
**Login:** Ivan (`student@university.edu`)

Ana has TWO announced prep sessions for Databases, linked to two different exams (Final Exam + Midterm II). Bot must ask which exam.

```
"I want to prepare for databases with Ana"
→ "There is more than one announced preparation session for this course…"
→ chips: [Final Exam] [Midterm II — Transactions & recovery]
→ pick one → date chips → time → confirm → booked
```

### Scenario 7 — Waitlist (pick a full date)
**Login:** Ivan (`student@university.edu`)

Petar's algorithms waitlist demo session is on today+11, capacity 2, both slots taken (Dušan + Tea).

```
"general consultation with Petrovic about algorithms"
→ date chips include today+11
→ pick today+11 → "That day has no free times left"
→ waitlist chips: [Waitlist HH:MM–HH:MM] [Waitlist · any slot …]
```

### Scenario 8 — Thesis (approved mentor, auto-fill)
**Login:** Ivan (`student@university.edu`)

Ivan has an approved thesis with Ana Marković. Bot auto-fills the professor without asking.

```
"thesis consultation"
→ (no professor prompt — Ana auto-filled)
→ date chips from Ana's thesis window (Fridays 14:00–16:00)
→ pick date → pick time → confirm → booked
```

### Scenario 9 — Thesis (pending application)
**Login:** Milica (`milica.student@university.edu`)

Milica has a pending application with Petrović. Bot blocks booking.

```
"thesis consultation"
→ "Your thesis supervision request is still waiting for the professor's decision."
```

### Scenario 10 — Thesis (rejected / no application)
**Login:** Nikola (`nikola.student@university.edu`)

Nikola's application to Ana was rejected.

```
"thesis consultation with Markovic"
→ "Prof. Ana Markovic has declined thesis supervision. Choose a different professor…"
```

### Scenario 11 — Thesis (not final year)
**Login:** Sara (`sara.student@university.edu`)

Sara is not a final-year student.

```
"thesis consultation"
→ "Thesis consultations are only for final-year students."
```

### Scenario 12 — Preparation vote (no session announced yet)
**Login:** Ivan (`student@university.edu`)

Discrete Structures (Stefan Nikolić) has no prep session announced.

```
"I want to prepare for discrete structures with Stefan"
→ "No preparation session has been announced for this course yet."
```

### Scenario 13 — Reset mid-flow
At any point during a multi-step flow:

```
"start over"
→ "Starting fresh. What do you need help with?"
```

---

## Key data relationships (for understanding seed)

- **Ana Marković** teaches **Databases** (CS101). Students: Ivan, Milica, Sara, Tea, Nina.
- **Petar Petrović** teaches **Algorithms** (CS202) and **ML** (CS401). Algorithms students: Ivan, Nikola, Luka, Tea, Jovana, Dušan.
- **Jelena Jovanović** teaches **Operating Systems** (CS303). Students: Milica, Nikola, Sara, Uros.
- Ivan has **active thesis** with Ana → is_final_year=True, thesis_professor_id=Ana.
- Milica has **pending thesis** with Petrovic → thesis_professor_id=None.
- Nikola has **rejected thesis** with Ana → thesis_professor_id=None.

## Consultation windows (recurring schedule)

| Professor | Regular day | Regular hours | Thesis day | Thesis hours |
|---|---|---|---|---|
| Ana Marković | Wednesday | 10:00–12:00 | Friday | 14:00–16:00 |
| Petar Petrović | Monday | 09:00–11:00 | Thursday | 13:00–15:00 |
| Jelena Jovanović | Tuesday | 12:00–14:00 | Thursday | 10:00–12:00 |
| Radovan Đurđević | Monday | 14:00–16:00 | Wednesday | 09:00–11:00 |
| Maja Jović | Tuesday | 10:00–12:00 | Friday | 10:00–12:00 |
| Stefan Nikolić | Wednesday | 15:00–17:00 | Friday | 09:00–11:00 |
| Lazar Stanković | Monday | 13:00–15:00 | Thursday | 10:00–12:00 |
| Tanja Kostić | Tuesday | 14:00–16:00 | Friday | 13:00–15:00 |
| Marko Ilić | Wednesday | 09:00–11:00 | Monday | 16:00–18:00 |

## Architecture summary

- **Backend:** FastAPI + async SQLAlchemy (PostgreSQL). JWT auth.
- **Frontend:** React 18 + TypeScript (Vite). Inline CSS styles. No component library (Tailwind only for admin pages).
- **Chatbot:** Fully rule-based NLP. State stored in `conversations.state` (JSON). No LLM.
- **Run backend:** `python -m uvicorn backend.main:app --reload`
- **Run frontend:** `cd frontend && npm run dev`
- **Seed:** `python -m backend.db.seed`
