import { useState } from 'react'
import { FolderPlus, Play, Loader2, CheckCircle2, AlertCircle } from 'lucide-react'

interface SettingsProps {
  onInit: () => void
}

export function Settings({ onInit }: SettingsProps) {
  const [isInitializing, setIsInitializing] = useState(false)
  const [isResuming, setIsResuming] = useState(false)
  const [maxIterations, setMaxIterations] = useState(50)
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null)

  const handleInit = async () => {
    setIsInitializing(true)
    setMessage(null)

    try {
      const res = await fetch('/api/init', { method: 'POST' })
      if (res.ok) {
        setMessage({ type: 'success', text: 'Lloyd initialized successfully!' })
        onInit()
      } else {
        throw new Error('Failed to initialize')
      }
    } catch {
      setMessage({ type: 'error', text: 'Failed to initialize Lloyd' })
    } finally {
      setIsInitializing(false)
    }
  }

  const handleResume = async () => {
    setIsResuming(true)
    setMessage(null)

    try {
      const res = await fetch(`/api/resume?max_iterations=${maxIterations}`, { method: 'POST' })
      if (res.ok) {
        setMessage({ type: 'success', text: 'Execution resumed!' })
        onInit()
      } else {
        const data = await res.json()
        throw new Error(data.detail || 'Failed to resume')
      }
    } catch (err) {
      setMessage({ type: 'error', text: err instanceof Error ? err.message : 'Failed to resume' })
    } finally {
      setIsResuming(false)
    }
  }

  return (
    <div className="animate-fade-in max-w-4xl">
      {/* Header */}
      <div className="mb-8">
        <p className="text-[var(--text-tertiary)] text-xs uppercase tracking-widest mb-1">Configure</p>
        <h2 className="text-2xl font-semibold text-[var(--text-primary)] tracking-tight">Settings</h2>
      </div>

      {/* Message */}
      {message && (
        <div className={`mb-6 p-4 rounded-xl flex items-center gap-3 glass ${
          message.type === 'success'
            ? 'border-emerald-500/30 text-emerald-400'
            : 'border-red-500/30 text-red-400'
        }`}>
          {message.type === 'success' ? (
            <CheckCircle2 className="w-5 h-5 flex-shrink-0" />
          ) : (
            <AlertCircle className="w-5 h-5 flex-shrink-0" />
          )}
          <span className="text-sm">{message.text}</span>
        </div>
      )}

      {/* Cards */}
      <div className="space-y-4">
        {/* Initialize Card */}
        <div className="glass rounded-xl p-5">
          <div className="flex items-start gap-4">
            <div className="p-2.5 bg-accent-500/10 rounded-lg">
              <FolderPlus className="w-5 h-5 text-accent-400" />
            </div>
            <div className="flex-1">
              <h3 className="font-medium text-[var(--text-primary)] mb-1">Initialize Project</h3>
              <p className="text-sm text-[var(--text-tertiary)] mb-4">
                Create a new .lloyd directory with configuration files
              </p>
              <button
                onClick={handleInit}
                disabled={isInitializing}
                className="flex items-center gap-2 px-4 py-2 bg-gradient-to-r from-accent-500 to-accent-600 text-white text-sm font-medium rounded-lg hover:from-accent-600 hover:to-accent-700 disabled:opacity-50 disabled:cursor-not-allowed transition-all glow"
              >
                {isInitializing ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    Initializing...
                  </>
                ) : (
                  <>
                    <FolderPlus className="w-4 h-4" />
                    Initialize
                  </>
                )}
              </button>
            </div>
          </div>
        </div>

        {/* Resume Card */}
        <div className="glass rounded-xl p-5">
          <div className="flex items-start gap-4">
            <div className="p-2.5 bg-emerald-500/10 rounded-lg">
              <Play className="w-5 h-5 text-emerald-400" />
            </div>
            <div className="flex-1">
              <h3 className="font-medium text-[var(--text-primary)] mb-1">Resume Execution</h3>
              <p className="text-sm text-[var(--text-tertiary)] mb-4">
                Continue from the last checkpoint
              </p>
              <div className="flex items-center gap-4">
                <div className="flex items-center gap-2">
                  <label htmlFor="maxIter" className="text-xs text-[var(--text-tertiary)]">
                    Iterations
                  </label>
                  <input
                    type="number"
                    id="maxIter"
                    value={maxIterations}
                    onChange={(e) => setMaxIterations(Number(e.target.value))}
                    min={1}
                    max={100}
                    className="w-16 px-2 py-1 glass rounded-lg text-sm text-[var(--text-primary)] bg-transparent focus:outline-none focus:border-accent-500"
                  />
                </div>
                <button
                  onClick={handleResume}
                  disabled={isResuming}
                  className="flex items-center gap-2 px-4 py-2 bg-emerald-500 text-white text-sm font-medium rounded-lg hover:bg-emerald-600 disabled:opacity-50 disabled:cursor-not-allowed transition-all"
                >
                  {isResuming ? (
                    <>
                      <Loader2 className="w-4 h-4 animate-spin" />
                      Resuming...
                    </>
                  ) : (
                    <>
                      <Play className="w-4 h-4" />
                      Resume
                    </>
                  )}
                </button>
              </div>
            </div>
          </div>
        </div>

        {/* About Card */}
        <div className="glass rounded-xl p-5 bg-gradient-to-br from-[var(--bg-elevated)] to-[var(--bg-card)]">
          <h3 className="font-medium text-[var(--text-primary)] mb-4">About Lloyd</h3>
          <p className="text-sm text-[var(--text-secondary)] mb-4">
            AI Executive Assistant that takes product ideas and autonomously executes them to completion.
          </p>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
            <div>
              <p className="text-[10px] text-[var(--text-tertiary)] uppercase tracking-wider mb-1">Version</p>
              <p className="text-sm font-medium text-[var(--text-primary)]">0.1.0</p>
            </div>
            <div>
              <p className="text-[10px] text-[var(--text-tertiary)] uppercase tracking-wider mb-1">Framework</p>
              <p className="text-sm font-medium text-[var(--text-primary)]">CrewAI</p>
            </div>
            <div>
              <p className="text-[10px] text-[var(--text-tertiary)] uppercase tracking-wider mb-1">Config</p>
              <p className="text-sm font-medium text-[var(--text-primary)]">.lloyd/</p>
            </div>
            <div>
              <p className="text-[10px] text-[var(--text-tertiary)] uppercase tracking-wider mb-1">Status</p>
              <p className="text-sm font-medium text-emerald-400">Active</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
