import { Navigate } from 'react-router-dom'

/** Former “Professors” page — directory now lives under Subjects. */
export default function Professors() {
  return <Navigate to="/student/subjects" replace />
}
