import type { ReactNode } from 'react'

type AdminSurfaceProps = {
  title: string
  subtitle?: string
  actions?: ReactNode
  children: ReactNode
}

/**
 * Shared admin content frame: typography + max width aligned to admin IA.
 */
export function AdminSurface({ title, subtitle, actions, children }: AdminSurfaceProps) {
  return (
    <div className="admin-app mx-auto max-w-6xl px-1 pb-10 pt-2 sm:px-2">
      <header className="mb-8 flex flex-col gap-4 border-b border-slate-200/90 pb-6 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight text-slate-900 sm:text-3xl">
            {title}
          </h1>
          {subtitle ? <p className="mt-1.5 max-w-2xl text-sm leading-relaxed text-slate-600">{subtitle}</p> : null}
        </div>
        {actions ? <div className="flex flex-shrink-0 flex-wrap items-center gap-2">{actions}</div> : null}
      </header>
      {children}
    </div>
  )
}
