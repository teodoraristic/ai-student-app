export type UserRole = 'student' | 'professor' | 'admin'

export type AuthUser = {
  id: number
  email: string
  first_name: string
  last_name: string
  role: UserRole
  password_change_required: boolean
  consent_accepted_at: string | null
  /** Students only; used for thesis-related UI. */
  is_final_year: boolean
}
