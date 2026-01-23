import { createContext, useContext, useState, useCallback } from 'react'

export type LayoutStyle = 'default' | 'minimal-sidebar' | 'focus'
export type MascotPosition = 'sidebar' | 'corner' | 'header' | 'none'

interface LayoutConfig {
  style: LayoutStyle
  mascotPosition: MascotPosition
  mascotSize: number // pixels
  sidebarCollapsedDefault: boolean
  showTaskQueueInSidebar: boolean
  focusModeEnabled: boolean
}

interface LayoutVersion {
  id: string
  name: string
  config: LayoutConfig
  timestamp: number
  notes?: string
}

interface LayoutContextType {
  config: LayoutConfig
  versions: LayoutVersion[]
  activeVersionId: string | null
  setConfig: (config: Partial<LayoutConfig>) => void
  saveVersion: (name: string, notes?: string) => void
  loadVersion: (id: string) => void
  deleteVersion: (id: string) => void
  rollback: () => void
  canRollback: boolean
}

const defaultConfig: LayoutConfig = {
  style: 'minimal-sidebar',
  mascotPosition: 'sidebar',
  mascotSize: 120,
  sidebarCollapsedDefault: false,
  showTaskQueueInSidebar: true,
  focusModeEnabled: false,
}

export const LayoutContext = createContext<LayoutContextType | undefined>(undefined)

export function useLayout() {
  const context = useContext(LayoutContext)
  if (!context) {
    throw new Error('useLayout must be used within a LayoutProvider')
  }
  return context
}

export function useLayoutProvider() {
  const [config, setConfigState] = useState<LayoutConfig>(() => {
    const saved = localStorage.getItem('lloyd-layout-config')
    if (saved) {
      try {
        return { ...defaultConfig, ...JSON.parse(saved) }
      } catch {
        return defaultConfig
      }
    }
    return defaultConfig
  })

  const [versions, setVersions] = useState<LayoutVersion[]>(() => {
    const saved = localStorage.getItem('lloyd-layout-versions')
    if (saved) {
      try {
        return JSON.parse(saved)
      } catch {
        return []
      }
    }
    return []
  })

  const [activeVersionId, setActiveVersionId] = useState<string | null>(() => {
    return localStorage.getItem('lloyd-layout-active-version')
  })

  const [previousConfig, setPreviousConfig] = useState<LayoutConfig | null>(null)

  const setConfig = useCallback((newConfig: Partial<LayoutConfig>) => {
    setConfigState(prev => {
      setPreviousConfig(prev) // Store for rollback
      const updated = { ...prev, ...newConfig }
      localStorage.setItem('lloyd-layout-config', JSON.stringify(updated))
      return updated
    })
    setActiveVersionId(null)
    localStorage.removeItem('lloyd-layout-active-version')
  }, [])

  const saveVersion = useCallback((name: string, notes?: string) => {
    const newVersion: LayoutVersion = {
      id: `layout-${Date.now()}`,
      name,
      config: { ...config },
      timestamp: Date.now(),
      notes,
    }
    setVersions(prev => {
      const updated = [newVersion, ...prev].slice(0, 10) // Keep last 10 versions
      localStorage.setItem('lloyd-layout-versions', JSON.stringify(updated))
      return updated
    })
    setActiveVersionId(newVersion.id)
    localStorage.setItem('lloyd-layout-active-version', newVersion.id)
  }, [config])

  const loadVersion = useCallback((id: string) => {
    const version = versions.find(v => v.id === id)
    if (version) {
      setPreviousConfig(config)
      setConfigState(version.config)
      localStorage.setItem('lloyd-layout-config', JSON.stringify(version.config))
      setActiveVersionId(id)
      localStorage.setItem('lloyd-layout-active-version', id)
    }
  }, [versions, config])

  const deleteVersion = useCallback((id: string) => {
    setVersions(prev => {
      const updated = prev.filter(v => v.id !== id)
      localStorage.setItem('lloyd-layout-versions', JSON.stringify(updated))
      return updated
    })
    if (activeVersionId === id) {
      setActiveVersionId(null)
      localStorage.removeItem('lloyd-layout-active-version')
    }
  }, [activeVersionId])

  const rollback = useCallback(() => {
    if (previousConfig) {
      setConfigState(previousConfig)
      localStorage.setItem('lloyd-layout-config', JSON.stringify(previousConfig))
      setPreviousConfig(null)
      setActiveVersionId(null)
      localStorage.removeItem('lloyd-layout-active-version')
    }
  }, [previousConfig])

  return {
    config,
    versions,
    activeVersionId,
    setConfig,
    saveVersion,
    loadVersion,
    deleteVersion,
    rollback,
    canRollback: previousConfig !== null,
  }
}
