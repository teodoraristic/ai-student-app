import { useState } from 'react'
import { api } from '../api/client'

export function FeedbackModal({ bookingId, onClose }: { bookingId: number; onClose: () => void }) {
  const [rating, setRating] = useState(5)
  const [comment, setComment] = useState('')
  const [err, setErr] = useState<string | null>(null)

  return (
    <div className="fixed inset-0 z-[90] flex items-center justify-center bg-black/40 p-4">
      <div className="w-full max-w-md rounded-2xl bg-white p-5 shadow-xl">
        <h3 className="font-semibold text-slate-900">How was your consultation?</h3>
        <label className="mt-3 block text-sm text-slate-700">
          Rating (1–5)
          <input
            type="number"
            min={1}
            max={5}
            className="mt-1 w-full rounded-lg border border-slate-300 px-2 py-2"
            value={rating}
            onChange={(e) => setRating(Number(e.target.value))}
          />
        </label>
        <label className="mt-3 block text-sm text-slate-700">
          Comment (optional)
          <textarea className="mt-1 w-full rounded-lg border border-slate-300 px-2 py-2" rows={3} value={comment} onChange={(e) => setComment(e.target.value)} />
        </label>
        {err ? <p className="mt-2 text-xs text-rose-600">{err}</p> : null}
        <div className="mt-4 flex gap-2">
          <button type="button" className="flex-1 rounded-lg border border-slate-300 py-2 text-sm" onClick={onClose}>
            Dismiss
          </button>
          <button
            type="button"
            className="flex-1 rounded-lg bg-slate-900 py-2 text-sm text-white"
            onClick={async () => {
              try {
                await api.post(`/feedback/${bookingId}`, { rating, comment: comment || null })
                onClose()
              } catch (ex: unknown) {
                const msg = (ex as { response?: { data?: { detail?: string } } }).response?.data?.detail
                setErr(msg ?? 'Submit failed')
              }
            }}
          >
            Submit
          </button>
        </div>
      </div>
    </div>
  )
}
