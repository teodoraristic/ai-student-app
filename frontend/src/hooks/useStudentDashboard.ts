import { useCallback, useEffect, useState } from 'react'
import { api } from '../api/client'

export type DashboardAnnouncement = { id: number; title: string; body: string }

export type DashboardBooking = {
  id: number
  status: string
  session_date: string | null
  time_from: string | null
  time_to: string | null
  consultation_type: string | null
  professor_name: string | null
  course_code: string | null
  course_name: string | null
  hall: string | null
  task: string | null
  anonymous_question: string | null
}

export function useStudentDashboardData() {
  const [announcements, setAnnouncements] = useState<DashboardAnnouncement[]>([])
  const [bookings, setBookings] = useState<DashboardBooking[]>([])
  const [loading, setLoading] = useState(true)
  const [announcementsError, setAnnouncementsError] = useState<string | null>(null)
  const [bookingsError, setBookingsError] = useState<string | null>(null)

  const reload = useCallback(async () => {
    setLoading(true)
    setAnnouncementsError(null)
    setBookingsError(null)
    const [aRes, bRes] = await Promise.allSettled([
      api.get<DashboardAnnouncement[]>('/announcements'),
      api.get<DashboardBooking[]>('/bookings/mine'),
    ])
    if (aRes.status === 'fulfilled') {
      setAnnouncements(aRes.value.data)
    } else {
      setAnnouncements([])
      setAnnouncementsError('Could not load announcements.')
    }
    if (bRes.status === 'fulfilled') {
      setBookings(bRes.value.data)
    } else {
      setBookings([])
      setBookingsError('Could not load your bookings.')
    }
    setLoading(false)
  }, [])

  useEffect(() => {
    const id = window.setTimeout(() => void reload(), 0)
    return () => window.clearTimeout(id)
  }, [reload])

  return {
    announcements,
    bookings,
    loading,
    announcementsError,
    bookingsError,
    reload,
  }
}
