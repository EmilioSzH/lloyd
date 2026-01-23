import { useEffect, useState, useCallback } from 'react'
import { Sidebar } from './components/Sidebar'
import { Dashboard } from './components/Dashboard'
import { IdeaForm } from './components/IdeaForm'
import { TaskQueue } from './components/TaskQueue'
import { ProgressLog } from './components/ProgressLog'
import { Settings } from './components/Settings'
import { HowToUse } from './components/HowToUse'
import { Inbox } from './components/Inbox'
import { Brainstorm } from './components/Brainstorm'
import { Knowledge } from './components/Knowledge'
import { SelfMod } from './components/SelfMod'
import { Extensions } from './components/Extensions'
import { Appearance } from './components/Appearance'
import { ThemeProvider } from './components/ThemeProvider'
import { LayoutProvider } from './components/LayoutProvider'
import { useWebSocket } from './hooks/useWebSocket'
import { StatusResponse, ProgressResponse } from './types'

type View = 'dashboard' | 'idea' | 'tasks' | 'progress' | 'settings' | 'guide' | 'inbox' | 'brainstorm' | 'knowledge' | 'selfmod' | 'extensions' | 'appearance'

function AppContent() {
  const [view, setView] = useState<View>('dashboard')
  const [status, setStatus] = useState<StatusResponse | null>(null)
  const [progress, setProgress] = useState<ProgressResponse | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [notifications, setNotifications] = useState<string[]>([])

  const addNotification = useCallback((message: string) => {
    setNotifications(prev => [...prev, message])
    setTimeout(() => {
      setNotifications(prev => prev.slice(1))
    }, 4000)
  }, [])

  const { isConnected, lastMessage } = useWebSocket('ws://localhost:8000/ws')

  useEffect(() => {
    if (lastMessage) {
      switch (lastMessage.type) {
        case 'status':
          if (lastMessage.message) addNotification(lastMessage.message)
          break
        case 'iteration':
          addNotification(`Iteration ${lastMessage.iteration ?? '?'}`)
          break
        case 'complete':
          addNotification('Workflow complete')
          fetchStatus()
          break
        case 'error':
          if (lastMessage.message) addNotification(lastMessage.message)
          break
        case 'status_update':
          fetchStatus()
          break
      }
    }
  }, [lastMessage, addNotification])

  const fetchStatus = async () => {
    try {
      const res = await fetch('/api/status')
      if (res.ok) setStatus(await res.json())
    } catch (err) {
      console.error('Failed to fetch status:', err)
    }
  }

  const fetchProgress = async () => {
    try {
      const res = await fetch('/api/progress')
      if (res.ok) setProgress(await res.json())
    } catch (err) {
      console.error('Failed to fetch progress:', err)
    }
  }

  useEffect(() => {
    const loadData = async () => {
      setIsLoading(true)
      await Promise.all([fetchStatus(), fetchProgress()])
      setIsLoading(false)
    }
    loadData()
  }, [])

  const refreshData = () => {
    fetchStatus()
    fetchProgress()
  }

  const renderView = () => {
    switch (view) {
      case 'dashboard':
        return <Dashboard status={status} progress={progress} onRefresh={refreshData} lastMessage={lastMessage} isConnected={isConnected} />
      case 'idea':
        return <IdeaForm onSubmit={refreshData} />
      case 'tasks':
        return <TaskQueue status={status} onRefresh={refreshData} />
      case 'progress':
        return <ProgressLog progress={progress} onRefresh={fetchProgress} />
      case 'settings':
        return <Settings onInit={refreshData} />
      case 'guide':
        return <HowToUse />
      case 'inbox':
        return <Inbox />
      case 'brainstorm':
        return <Brainstorm />
      case 'knowledge':
        return <Knowledge />
      case 'selfmod':
        return <SelfMod />
      case 'extensions':
        return <Extensions />
      case 'appearance':
        return <Appearance />
      default:
        return <Dashboard status={status} progress={progress} onRefresh={refreshData} lastMessage={lastMessage} isConnected={isConnected} />
    }
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center">
          <div className="w-10 h-10 mx-auto mb-4 border-2 border-accent-500 border-t-transparent rounded-full animate-spin" />
          <p className="text-sm text-[var(--text-tertiary)]">Loading</p>
        </div>
      </div>
    )
  }

  // Map Lloyd status to mascot status
  const getMascotStatus = (): 'idle' | 'working' | 'thinking' | 'complete' | 'error' => {
    if (!status) return 'idle'
    switch (status.status) {
      case 'executing':
      case 'in_progress':
        return 'working'
      case 'planning':
        return 'thinking'
      case 'complete':
        return 'complete'
      case 'error':
        return 'error'
      default:
        return 'idle'
    }
  }

  return (
    <div className="flex min-h-screen">
      <Sidebar currentView={view} onViewChange={setView} isConnected={isConnected} currentStatus={getMascotStatus()} />

      <main className="flex-1 p-4 lg:p-6 xl:p-8 overflow-auto">
        <div className="w-full max-w-[1800px] mx-auto">
          {renderView()}
        </div>
      </main>

      {/* Notifications */}
      <div className="fixed bottom-6 right-6 space-y-2 z-50">
        {notifications.map((notification, index) => (
          <div
            key={index}
            className="glass px-4 py-2.5 rounded-lg animate-fade-in text-sm text-[var(--text-primary)] border border-accent-500/20"
          >
            {notification}
          </div>
        ))}
      </div>
    </div>
  )
}

function App() {
  return (
    <ThemeProvider>
      <LayoutProvider>
        <AppContent />
      </LayoutProvider>
    </ThemeProvider>
  )
}

export default App
