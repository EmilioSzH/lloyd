import { ReactNode } from 'react'
import { LayoutContext, useLayoutProvider } from '../hooks/useLayout'

interface LayoutProviderProps {
  children: ReactNode
}

export function LayoutProvider({ children }: LayoutProviderProps) {
  const layoutValue = useLayoutProvider()

  return (
    <LayoutContext.Provider value={layoutValue}>
      {children}
    </LayoutContext.Provider>
  )
}
