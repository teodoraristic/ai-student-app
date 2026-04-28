import { createContext, useContext, type ReactNode } from 'react'

export type ShellLayoutValue = {
  sidebarCollapsed: boolean
}

const ShellLayoutContext = createContext<ShellLayoutValue>({ sidebarCollapsed: false })

export function ShellLayoutProvider({
  sidebarCollapsed,
  children,
}: {
  sidebarCollapsed: boolean
  children: ReactNode
}) {
  return (
    <ShellLayoutContext.Provider value={{ sidebarCollapsed }}>
      {children}
    </ShellLayoutContext.Provider>
  )
}

export function useShellLayout(): ShellLayoutValue {
  return useContext(ShellLayoutContext)
}
