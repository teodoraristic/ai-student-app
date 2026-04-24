import type { ReactNode } from 'react'
import { Navigate, Route, Routes } from 'react-router-dom'
import { AppLayout } from './components/AppLayout'
import { useAuth } from './contexts/AuthContext'
import Login from './pages/Login'
import ChangePassword from './pages/ChangePassword'
import Privacy from './pages/Privacy'
import StudentDashboard from './pages/student/Dashboard'
import Chat from './pages/student/Chat'
import MyBookings from './pages/student/MyBookings'
import Professors from './pages/student/Professors'
import Thesis from './pages/student/Thesis'
import Waitlist from './pages/student/Waitlist'
import ProfessorDashboard from './pages/professor/Dashboard'
import ProfessorWindows from './pages/professor/Windows'
import ProfessorBookings from './pages/professor/Bookings'
import ProfessorRequests from './pages/professor/Requests'
import ThesisApplications from './pages/professor/ThesisApplications'
import ProfessorStats from './pages/professor/Stats'
import AdminDashboard from './pages/admin/Dashboard'
import AdminUsers from './pages/admin/Users'
import AdminScheduler from './pages/admin/SchedulerLog'

function RequireAuth({
  allowPasswordChange,
  children,
}: {
  allowPasswordChange?: boolean
  children: ReactNode
}) {
  const { user, loading } = useAuth()
  if (loading) return <div className="p-8 text-center text-sm text-slate-600">Loading…</div>
  if (!user) return <Navigate to="/login" replace />
  if (user.password_change_required && !allowPasswordChange) return <Navigate to="/change-password" replace />
  return <>{children}</>
}

function RoleGate({ role, children }: { role: 'student' | 'professor' | 'admin'; children: ReactNode }) {
  const { user } = useAuth()
  if (!user || user.role !== role) return <Navigate to="/" replace />
  return <>{children}</>
}

const studentNav = [
  { to: '/student', label: 'Home' },
  { to: '/student/chat', label: 'Chat' },
  { to: '/student/bookings', label: 'Bookings' },
  { to: '/student/professors', label: 'Professors' },
  { to: '/student/thesis', label: 'Thesis' },
  { to: '/student/waitlist', label: 'Waitlist' },
]

const profNav = [
  { to: '/professor', label: 'Home' },
  { to: '/professor/windows', label: 'Windows' },
  { to: '/professor/bookings', label: 'Bookings' },
  { to: '/professor/requests', label: 'Requests' },
  { to: '/professor/thesis', label: 'Thesis apps' },
  { to: '/professor/stats', label: 'Stats' },
]

const adminNav = [
  { to: '/admin', label: 'Home' },
  { to: '/admin/users', label: 'Users' },
  { to: '/admin/scheduler', label: 'Scheduler' },
]

function HomeRedirect() {
  const { user } = useAuth()
  if (!user) return <Navigate to="/login" replace />
  if (user.password_change_required) return <Navigate to="/change-password" replace />
  if (user.role === 'student') return <Navigate to="/student" replace />
  if (user.role === 'professor') return <Navigate to="/professor" replace />
  if (user.role === 'admin') return <Navigate to="/admin" replace />
  return <Navigate to="/login" replace />
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route path="/privacy" element={<Privacy />} />
      <Route
        path="/change-password"
        element={
          <RequireAuth allowPasswordChange>
            <ChangePassword />
          </RequireAuth>
        }
      />
      <Route
        path="/"
        element={
          <RequireAuth>
            <HomeRedirect />
          </RequireAuth>
        }
      />
      <Route
        path="/student"
        element={
          <RequireAuth>
            <RoleGate role="student">
              <AppLayout nav={studentNav} />
            </RoleGate>
          </RequireAuth>
        }
      >
        <Route index element={<StudentDashboard />} />
        <Route path="chat" element={<Chat />} />
        <Route path="bookings" element={<MyBookings />} />
        <Route path="professors" element={<Professors />} />
        <Route path="thesis" element={<Thesis />} />
        <Route path="waitlist" element={<Waitlist />} />
      </Route>
      <Route
        path="/professor"
        element={
          <RequireAuth>
            <RoleGate role="professor">
              <AppLayout nav={profNav} />
            </RoleGate>
          </RequireAuth>
        }
      >
        <Route index element={<ProfessorDashboard />} />
        <Route path="windows" element={<ProfessorWindows />} />
        <Route path="bookings" element={<ProfessorBookings />} />
        <Route path="requests" element={<ProfessorRequests />} />
        <Route path="thesis" element={<ThesisApplications />} />
        <Route path="stats" element={<ProfessorStats />} />
      </Route>
      <Route
        path="/admin"
        element={
          <RequireAuth>
            <RoleGate role="admin">
              <AppLayout nav={adminNav} />
            </RoleGate>
          </RequireAuth>
        }
      >
        <Route index element={<AdminDashboard />} />
        <Route path="users" element={<AdminUsers />} />
        <Route path="scheduler" element={<AdminScheduler />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}
