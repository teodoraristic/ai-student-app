import { useState } from 'react'
import { AdminSurface } from '../../components/admin/AdminSurface'
import { useAdminUsers, type AdminUserRow, type CreateUserRole } from '../../hooks/useAdminUsers'

const STUDY_YEAR_OPTIONS: { value: number; label: string }[] = [
  { value: 1, label: 'Godina I' },
  { value: 2, label: 'Godina II' },
  { value: 3, label: 'Godina III' },
  { value: 4, label: 'Godina IV (završna — diplomski / teza)' },
  { value: 5, label: 'Master — godina I' },
  { value: 6, label: 'Master — godina II' },
]

const field =
  'mt-1 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 shadow-sm outline-none focus:border-blue-700 focus:ring-2 focus:ring-blue-700/20'
const labelCls = 'block text-sm font-medium text-slate-700'

function roleBadge(role: string) {
  const base = 'inline-flex items-center rounded-md border px-2 py-0.5 text-xs font-semibold'
  if (role === 'admin') return `${base} border-violet-200 bg-violet-50 text-violet-900`
  if (role === 'professor') return `${base} border-amber-200 bg-amber-50 text-amber-950`
  return `${base} border-slate-200 bg-slate-50 text-slate-800`
}

function RoleCell({ row }: { row: AdminUserRow }) {
  return (
    <span className={roleBadge(row.role)} title={`Role: ${row.role}`}>
      {row.role}
    </span>
  )
}

export default function Users() {
  const { rows, loading, error, actionError, createUser, deactivateUser } = useAdminUsers()
  const [otp, setOtp] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)

  const [firstName, setFirstName] = useState('')
  const [lastName, setLastName] = useState('')
  const [email, setEmail] = useState('')
  const [role, setRole] = useState<CreateUserRole>('student')
  const [studyYear, setStudyYear] = useState<number>(1)

  async function onCreateUser(e: React.FormEvent) {
    e.preventDefault()
    setSubmitting(true)
    setOtp(null)
    const pwd = await createUser({
      email,
      first_name: firstName,
      last_name: lastName,
      role,
      study_year: role === 'student' ? studyYear : undefined,
    })
    if (pwd) {
      setOtp(pwd)
      setFirstName('')
      setLastName('')
      setEmail('')
      setRole('student')
      setStudyYear(1)
    }
    setSubmitting(false)
  }

  return (
    <AdminSurface
      title="Directory"
      subtitle="Kreiranje naloga: unesite stvarne podatke. Za studenta obavezna je godina studija; OTP se prikaže jednom nakon uspeha."
    >
      {error ? (
        <p className="mb-4 rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-800" role="alert">
          {error}
        </p>
      ) : null}
      {actionError ? (
        <p className="mb-4 rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-950" role="status">
          {actionError}
        </p>
      ) : null}

      <section className="mb-8 rounded-xl border border-slate-200/90 bg-white p-5 shadow-[0_1px_0_rgba(15,23,42,0.04)]" aria-labelledby="new-user-heading">
        <h2 id="new-user-heading" className="text-lg font-semibold text-slate-900">
          Novi korisnik
        </h2>
        <p className="mt-1 text-sm text-slate-600">Uloga: student, profesor ili administrator. Student mora imati godinu studija.</p>
        <form className="mt-5 grid gap-4 sm:grid-cols-2 lg:grid-cols-3" onSubmit={(ev) => void onCreateUser(ev)}>
          <div>
            <label htmlFor="nu-first" className={labelCls}>
              Ime
            </label>
            <input id="nu-first" className={field} value={firstName} onChange={(e) => setFirstName(e.target.value)} required maxLength={120} autoComplete="off" />
          </div>
          <div>
            <label htmlFor="nu-last" className={labelCls}>
              Prezime
            </label>
            <input id="nu-last" className={field} value={lastName} onChange={(e) => setLastName(e.target.value)} required maxLength={120} autoComplete="off" />
          </div>
          <div className="sm:col-span-2 lg:col-span-1">
            <label htmlFor="nu-email" className={labelCls}>
              Email
            </label>
            <input id="nu-email" type="email" className={field} value={email} onChange={(e) => setEmail(e.target.value)} required autoComplete="off" />
          </div>
          <div>
            <label htmlFor="nu-role" className={labelCls}>
              Uloga
            </label>
            <select
              id="nu-role"
              className={field}
              value={role}
              onChange={(e) => setRole(e.target.value as CreateUserRole)}
            >
              <option value="student">Student</option>
              <option value="professor">Profesor</option>
              <option value="admin">Administrator</option>
            </select>
          </div>
          {role === 'student' ? (
            <div>
              <label htmlFor="nu-year" className={labelCls}>
                Godina studija
              </label>
              <select id="nu-year" className={field} value={studyYear} onChange={(e) => setStudyYear(Number(e.target.value))}>
                {STUDY_YEAR_OPTIONS.map((o) => (
                  <option key={o.value} value={o.value}>
                    {o.label}
                  </option>
                ))}
              </select>
              <p className="mt-1 text-xs text-slate-500">Godine IV–VI automatski označavaju završnu godinu za pravila diplomskog / konsultacija.</p>
            </div>
          ) : null}
          <div className="flex items-end sm:col-span-2 lg:col-span-1">
            <button
              type="submit"
              disabled={submitting}
              className="w-full rounded-lg bg-slate-900 px-4 py-2.5 text-sm font-medium text-white shadow-sm outline-none transition hover:bg-slate-800 disabled:opacity-60 focus-visible:ring-2 focus-visible:ring-blue-700 focus-visible:ring-offset-2 sm:w-auto"
            >
              {submitting ? 'Kreiranje…' : 'Kreiraj korisnika'}
            </button>
          </div>
        </form>
      </section>

      {otp ? (
        <div
          className="mb-6 rounded-xl border border-amber-300/80 bg-gradient-to-br from-amber-50 to-orange-50/80 p-4 shadow-sm"
          role="status"
          aria-live="polite"
        >
          <p className="text-sm font-semibold text-amber-950">Jednokratna lozinka (OTP) — kopirajte odmah</p>
          <code className="mt-2 block rounded-md bg-white/80 px-3 py-2 font-mono text-sm text-slate-900 ring-1 ring-amber-200/60">
            {otp}
          </code>
          <button
            type="button"
            className="mt-3 rounded-md border border-amber-400/60 bg-white px-3 py-1.5 text-sm font-medium text-amber-950 outline-none transition hover:bg-amber-50 focus-visible:ring-2 focus-visible:ring-blue-700/40"
            onClick={() => void navigator.clipboard.writeText(otp)}
            aria-label="Kopiraj OTP u clipboard"
          >
            Kopiraj u clipboard
          </button>
        </div>
      ) : null}

      {loading ? <p className="text-sm text-slate-500">Loading users…</p> : null}

      {!loading && rows.length === 0 ? (
        <p className="rounded-xl border border-dashed border-slate-200 bg-slate-50/80 px-4 py-8 text-center text-sm text-slate-600">No users returned.</p>
      ) : null}

      {!loading && rows.length > 0 ? (
        <div className="overflow-hidden rounded-xl border border-slate-200/90 bg-white shadow-[0_1px_0_rgba(15,23,42,0.04)]">
          <div className="overflow-x-auto">
            <table className="min-w-full text-left text-sm">
              <thead className="border-b border-slate-200 bg-slate-50/90 text-xs font-semibold uppercase tracking-wide text-slate-500">
                <tr>
                  <th scope="col" className="whitespace-nowrap px-4 py-3 font-semibold">
                    Name
                  </th>
                  <th scope="col" className="whitespace-nowrap px-4 py-3 font-semibold">
                    Email
                  </th>
                  <th scope="col" className="whitespace-nowrap px-4 py-3 font-semibold">
                    Role
                  </th>
                  <th scope="col" className="whitespace-nowrap px-4 py-3 font-semibold">
                    Study year
                  </th>
                  <th scope="col" className="whitespace-nowrap px-4 py-3 font-semibold">
                    Status
                  </th>
                  <th scope="col" className="px-4 py-3 text-right font-semibold">
                    Actions
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {rows.map((u) => (
                  <tr key={u.id} className="hover:bg-slate-50/80">
                    <td className="whitespace-nowrap px-4 py-3 font-medium text-slate-900">
                      {u.first_name} {u.last_name}
                    </td>
                    <td className="max-w-[220px] truncate px-4 py-3 text-slate-700" title={u.email}>
                      {u.email}
                    </td>
                    <td className="px-4 py-3">
                      <RoleCell row={u} />
                    </td>
                    <td className="whitespace-nowrap px-4 py-3 text-slate-700">
                      {u.role === 'student' ? (
                        <span title={u.is_final_year ? 'Tretirano kao završna godina' : undefined}>
                          {u.study_year != null ? `${u.study_year}` : '—'}
                          {u.is_final_year ? <span className="ml-1 text-xs font-medium text-blue-800">(final)</span> : null}
                        </span>
                      ) : (
                        <span className="text-slate-400">—</span>
                      )}
                    </td>
                    <td className="px-4 py-3">
                      {u.is_active ? (
                        <span className="inline-flex items-center gap-1 text-emerald-800">
                          <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" aria-hidden />
                          Active
                        </span>
                      ) : (
                        <span className="inline-flex items-center gap-1 text-slate-500">
                          <span className="h-1.5 w-1.5 rounded-full bg-slate-300" aria-hidden />
                          Inactive
                        </span>
                      )}
                    </td>
                    <td className="px-4 py-3 text-right">
                      {u.is_active ? (
                        <button
                          type="button"
                          className="rounded-sm text-sm font-medium text-rose-700 underline-offset-2 outline-none hover:underline focus-visible:ring-2 focus-visible:ring-rose-400/60"
                          onClick={() => void deactivateUser(u.id)}
                        >
                          Deactivate
                        </button>
                      ) : (
                        <span className="text-sm text-slate-400">—</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      ) : null}
    </AdminSurface>
  )
}
