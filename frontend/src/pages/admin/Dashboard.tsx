import { Link } from 'react-router-dom'
import { AdminSurface } from '../../components/admin/AdminSurface'
import { useAdminDashboard } from '../../hooks/useAdminDashboard'

function StatCard({
  label,
  value,
  hint,
}: {
  label: string
  value: string
  hint?: string
}) {
  return (
    <div className="rounded-xl border border-slate-200/90 bg-white p-5 shadow-[0_1px_0_rgba(15,23,42,0.04)]">
      <p className="text-xs font-semibold uppercase tracking-wider text-slate-500">{label}</p>
      <p className="mt-2 text-3xl font-semibold tabular-nums text-slate-900">{value}</p>
      {hint ? <p className="mt-2 text-sm text-slate-600">{hint}</p> : null}
    </div>
  )
}

export default function AdminDashboard() {
  const { data, loading, error } = useAdminDashboard()

  const waitlistEntries = data ? Object.entries(data.waitlist_per_professor) : []
  const waitlistSummary =
    waitlistEntries.length === 0
      ? 'No waitlist entries by professor yet.'
      : `${waitlistEntries.length} professor${waitlistEntries.length === 1 ? '' : 's'} with queued students.`

  return (
    <AdminSurface
      title="Operations overview"
      subtitle="High-level booking volume and waitlist signals. Use the sidebar for account and schedule management."
    >
      {error ? (
        <p className="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-800" role="alert">
          {error}
        </p>
      ) : null}

      {loading && !data ? (
        <p className="text-sm text-slate-500">Loading metrics…</p>
      ) : null}

      {data ? (
        <div className="admin-stagger grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          <StatCard label="Total bookings" value={String(data.total_bookings)} hint="Across all consultation types." />
          <StatCard
            label="No-show rate"
            value={`${(data.no_show_rate * 100).toFixed(1)}%`}
            hint="Placeholder until analytics are wired through."
          />
          <StatCard label="Waitlist snapshot" value={waitlistEntries.length ? String(waitlistEntries.length) : '—'} hint={waitlistSummary} />
        </div>
      ) : null}

      <section className="mt-10" aria-labelledby="admin-shortcuts-heading">
        <h2 id="admin-shortcuts-heading" className="text-lg font-semibold text-slate-900">
          Shortcuts
        </h2>
        <div className="admin-stagger mt-4 grid gap-3 sm:grid-cols-2">
          <Link
            to="/admin/users"
            className="group rounded-xl border border-slate-200/90 bg-white p-4 shadow-[0_1px_0_rgba(15,23,42,0.04)] outline-none ring-blue-700/0 transition hover:border-blue-200 hover:shadow-md focus-visible:ring-2 focus-visible:ring-blue-700/30"
          >
            <span className="text-sm font-semibold text-slate-900 group-hover:text-blue-800">Users &amp; access</span>
            <span className="mt-1 block text-sm text-slate-600">Create accounts, OTP handoff, deactivate.</span>
          </Link>
          <Link
            to="/admin/academic"
            className="group rounded-xl border border-slate-200/90 bg-white p-4 shadow-[0_1px_0_rgba(15,23,42,0.04)] outline-none ring-blue-700/0 transition hover:border-blue-200 hover:shadow-md focus-visible:ring-2 focus-visible:ring-blue-700/30"
          >
            <span className="text-sm font-semibold text-slate-900 group-hover:text-blue-800">Academic calendar</span>
            <span className="mt-1 block text-sm text-slate-600">Exam periods, midterms, and finals.</span>
          </Link>
        </div>
      </section>

      {data && waitlistEntries.length > 0 ? (
        <section className="mt-10" aria-labelledby="waitlist-breakdown-heading">
          <h2 id="waitlist-breakdown-heading" className="text-lg font-semibold text-slate-900">
            Waitlist by professor
          </h2>
          <ul className="mt-3 divide-y divide-slate-100 rounded-xl border border-slate-200/90 bg-white text-sm">
            {waitlistEntries.map(([name, count]) => (
              <li key={name} className="flex items-center justify-between gap-3 px-4 py-3">
                <span className="font-medium text-slate-800">{name}</span>
                <span className="tabular-nums text-slate-600">
                  {count} waiting
                </span>
              </li>
            ))}
          </ul>
        </section>
      ) : null}
    </AdminSurface>
  )
}
