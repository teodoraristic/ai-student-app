import { ComingSoon } from '../../components/ComingSoon'
import * as U from './uiTokens'

export default function Stats() {
  return (
    <div style={U.shell}>
      <div style={U.pageHeader}>
        <h1 style={U.title}>Statistics</h1>
        <p style={U.subtitle}>Workload trends and feedback summaries (post-MVP).</p>
      </div>
      <ComingSoon feature="Advanced analytics and predictive model" />
    </div>
  )
}
