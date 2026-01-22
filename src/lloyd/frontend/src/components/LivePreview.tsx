import { useEffect, useRef, useState } from 'react'
import { Terminal, Activity, Cpu, Zap, Circle } from 'lucide-react'
import { WebSocketMessage, StatusResponse } from '../types'

interface LivePreviewProps {
  lastMessage: WebSocketMessage | null
  status: StatusResponse | null
  isConnected: boolean
}

interface ActivityLog {
  id: number
  timestamp: Date
  type: string
  message: string
}

export function LivePreview({ lastMessage, status, isConnected }: LivePreviewProps) {
  const [logs, setLogs] = useState<ActivityLog[]>([])
  const [currentPhase, setCurrentPhase] = useState<string | null>(null)
  const [currentIteration, setCurrentIteration] = useState<{ current: number; max: number } | null>(null)
  const [isActive, setIsActive] = useState(false)
  const logContainerRef = useRef<HTMLDivElement>(null)
  const logIdRef = useRef(0)

  // Process incoming WebSocket messages
  useEffect(() => {
    if (!lastMessage) return

    const addLog = (type: string, message: string) => {
      logIdRef.current += 1
      setLogs(prev => [...prev.slice(-50), { // Keep last 50 logs
        id: logIdRef.current,
        timestamp: new Date(),
        type,
        message
      }])
    }

    switch (lastMessage.type) {
      case 'status':
        if (lastMessage.message) {
          addLog('status', lastMessage.message)
          setIsActive(true)
        }
        break
      case 'phase':
        if (lastMessage.phase) {
          setCurrentPhase(lastMessage.phase)
          addLog('phase', `Entering ${lastMessage.phase} phase`)
          setIsActive(true)
        }
        break
      case 'iteration':
        if (lastMessage.iteration !== undefined) {
          setCurrentIteration({
            current: lastMessage.iteration,
            max: (lastMessage as any).max_iterations || 50
          })
          addLog('iteration', `Starting iteration ${lastMessage.iteration}`)
        }
        break
      case 'prd_created':
        addLog('success', `PRD created with ${(lastMessage as any).stories || 0} stories`)
        break
      case 'status_update':
        addLog('update', 'Task status updated')
        break
      case 'complete':
        addLog('complete', `Workflow complete: ${lastMessage.status || 'done'}`)
        setIsActive(false)
        setCurrentPhase(null)
        setCurrentIteration(null)
        break
      case 'error':
        addLog('error', lastMessage.message || 'An error occurred')
        setIsActive(false)
        break
    }
  }, [lastMessage])

  // Auto-scroll to bottom
  useEffect(() => {
    if (logContainerRef.current) {
      logContainerRef.current.scrollTop = logContainerRef.current.scrollHeight
    }
  }, [logs])

  const getLogColor = (type: string) => {
    switch (type) {
      case 'phase': return 'text-accent-400'
      case 'iteration': return 'text-blue-400'
      case 'success': return 'text-emerald-400'
      case 'complete': return 'text-emerald-400'
      case 'error': return 'text-red-400'
      case 'update': return 'text-amber-400'
      default: return 'text-[var(--text-secondary)]'
    }
  }

  const getLogPrefix = (type: string) => {
    switch (type) {
      case 'phase': return '▸'
      case 'iteration': return '○'
      case 'success': return '✓'
      case 'complete': return '★'
      case 'error': return '✕'
      case 'update': return '↻'
      default: return '›'
    }
  }

  const formatTime = (date: Date) => {
    return date.toLocaleTimeString('en-US', {
      hour12: false,
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit'
    })
  }

  return (
    <div className="glass rounded-xl overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-[var(--border-color)]">
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2">
            <Terminal className="w-4 h-4 text-accent-400" />
            <span className="text-sm font-medium text-[var(--text-primary)]">Live Preview</span>
          </div>
          {isActive && (
            <div className="flex items-center gap-1.5 px-2 py-0.5 bg-accent-500/10 rounded-full">
              <div className="w-1.5 h-1.5 bg-accent-400 rounded-full animate-pulse" />
              <span className="text-[10px] text-accent-400 uppercase tracking-wider">Active</span>
            </div>
          )}
        </div>
        <div className="flex items-center gap-2">
          <div className={`w-2 h-2 rounded-full ${isConnected ? 'bg-emerald-400' : 'bg-zinc-500'}`} />
          <span className="text-[10px] text-[var(--text-tertiary)] uppercase tracking-wider">
            {isConnected ? 'Connected' : 'Offline'}
          </span>
        </div>
      </div>

      {/* Status Bar */}
      {(currentPhase || currentIteration || status?.status === 'executing') && (
        <div className="flex items-center gap-4 px-4 py-2 bg-[var(--border-color)]/30 border-b border-[var(--border-color)]">
          {currentPhase && (
            <div className="flex items-center gap-2">
              <Cpu className="w-3.5 h-3.5 text-accent-400" />
              <span className="text-xs text-[var(--text-secondary)]">
                Phase: <span className="text-accent-400 capitalize">{currentPhase}</span>
              </span>
            </div>
          )}
          {currentIteration && (
            <div className="flex items-center gap-2">
              <Activity className="w-3.5 h-3.5 text-blue-400" />
              <span className="text-xs text-[var(--text-secondary)]">
                Iteration: <span className="text-blue-400">{currentIteration.current}</span>
                <span className="text-[var(--text-tertiary)]">/{currentIteration.max}</span>
              </span>
            </div>
          )}
          {status?.status === 'executing' && !currentPhase && (
            <div className="flex items-center gap-2">
              <Zap className="w-3.5 h-3.5 text-amber-400 animate-pulse" />
              <span className="text-xs text-amber-400">Executing</span>
            </div>
          )}
        </div>
      )}

      {/* Iteration Progress */}
      {currentIteration && (
        <div className="px-4 py-2 border-b border-[var(--border-color)]">
          <div className="h-1 bg-[var(--border-color)] rounded-full overflow-hidden">
            <div
              className="h-full bg-gradient-to-r from-accent-400 to-blue-400 rounded-full transition-all duration-500"
              style={{ width: `${(currentIteration.current / currentIteration.max) * 100}%` }}
            />
          </div>
        </div>
      )}

      {/* Log Output */}
      <div
        ref={logContainerRef}
        className="h-48 overflow-auto p-4 font-mono text-xs bg-[var(--bg-base)]/50"
      >
        {logs.length > 0 ? (
          <div className="space-y-1">
            {logs.map((log) => (
              <div key={log.id} className="flex gap-2 animate-fade-in">
                <span className="text-[var(--text-tertiary)] opacity-50 shrink-0">
                  {formatTime(log.timestamp)}
                </span>
                <span className={`shrink-0 ${getLogColor(log.type)}`}>
                  {getLogPrefix(log.type)}
                </span>
                <span className={getLogColor(log.type)}>
                  {log.message}
                </span>
              </div>
            ))}
          </div>
        ) : (
          <div className="h-full flex flex-col items-center justify-center text-[var(--text-tertiary)]">
            <Circle className="w-8 h-8 mb-2 opacity-30" />
            <p className="text-xs">Waiting for activity...</p>
            <p className="text-[10px] opacity-50 mt-1">Submit an idea to see live updates</p>
          </div>
        )}
      </div>

      {/* Footer */}
      <div className="px-4 py-2 border-t border-[var(--border-color)] bg-[var(--border-color)]/20">
        <div className="flex items-center justify-between text-[10px] text-[var(--text-tertiary)]">
          <span>{logs.length} events</span>
          <span className="opacity-50">Real-time WebSocket feed</span>
        </div>
      </div>
    </div>
  )
}
