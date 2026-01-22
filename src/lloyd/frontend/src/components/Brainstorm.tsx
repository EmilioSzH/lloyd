import { useEffect, useState } from 'react'
import { Sparkles, Plus, MessageCircle, FileText, Check, Trash2, RefreshCw } from 'lucide-react'

interface BrainstormSession {
  session_id: string
  initial_idea: string
  clarifications: Array<{ question: string; answer: string }>
  spec: string | null
  status: 'in_progress' | 'spec_ready' | 'approved' | 'queued'
  created_at: string
}

const statusColors: Record<string, string> = {
  in_progress: 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30',
  spec_ready: 'bg-blue-500/20 text-blue-400 border-blue-500/30',
  approved: 'bg-green-500/20 text-green-400 border-green-500/30',
  queued: 'bg-purple-500/20 text-purple-400 border-purple-500/30',
}

export function Brainstorm() {
  const [sessions, setSessions] = useState<BrainstormSession[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [selectedSession, setSelectedSession] = useState<BrainstormSession | null>(null)
  const [newIdea, setNewIdea] = useState('')
  const [showNewForm, setShowNewForm] = useState(false)

  const fetchSessions = async () => {
    setIsLoading(true)
    try {
      const res = await fetch('/api/brainstorm')
      if (res.ok) {
        setSessions(await res.json())
      }
    } catch (err) {
      console.error('Failed to fetch sessions:', err)
    }
    setIsLoading(false)
  }

  useEffect(() => {
    fetchSessions()
  }, [])

  const createSession = async () => {
    if (!newIdea.trim()) return
    try {
      const res = await fetch('/api/brainstorm', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ idea: newIdea }),
      })
      if (res.ok) {
        setNewIdea('')
        setShowNewForm(false)
        fetchSessions()
      }
    } catch (err) {
      console.error('Failed to create session:', err)
    }
  }

  const approveSession = async (sessionId: string) => {
    try {
      const res = await fetch(`/api/brainstorm/${sessionId}/approve`, {
        method: 'POST',
      })
      if (res.ok) {
        fetchSessions()
      }
    } catch (err) {
      console.error('Failed to approve session:', err)
    }
  }

  const deleteSession = async (sessionId: string) => {
    try {
      const res = await fetch(`/api/brainstorm/${sessionId}`, {
        method: 'DELETE',
      })
      if (res.ok) {
        if (selectedSession?.session_id === sessionId) {
          setSelectedSession(null)
        }
        fetchSessions()
      }
    } catch (err) {
      console.error('Failed to delete session:', err)
    }
  }

  const formatDate = (dateStr: string) => {
    const date = new Date(dateStr)
    return date.toLocaleDateString() + ' ' + date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-semibold text-[var(--text-primary)] flex items-center gap-2">
            <Sparkles className="w-6 h-6 text-accent-500" />
            Brainstorm
          </h2>
          <p className="text-sm text-[var(--text-tertiary)] mt-1">
            Refine vague ideas into detailed specs
          </p>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={() => setShowNewForm(true)}
            className="flex items-center gap-2 px-4 py-2 bg-accent-500 text-white rounded-lg hover:bg-accent-600 transition-colors"
          >
            <Plus className="w-4 h-4" />
            New Session
          </button>
          <button
            onClick={fetchSessions}
            className="p-2 rounded-lg hover:bg-[var(--border-color)] transition-colors"
          >
            <RefreshCw className="w-4 h-4 text-[var(--text-secondary)]" />
          </button>
        </div>
      </div>

      {/* New Session Form */}
      {showNewForm && (
        <div className="glass rounded-xl p-6">
          <h3 className="text-lg font-medium text-[var(--text-primary)] mb-4">
            Start a brainstorming session
          </h3>
          <textarea
            value={newIdea}
            onChange={(e) => setNewIdea(e.target.value)}
            placeholder="Describe your idea... (can be vague)"
            className="w-full h-32 px-4 py-3 bg-[var(--bg-base)] border border-[var(--border-color)] rounded-lg text-[var(--text-primary)] placeholder-[var(--text-tertiary)] resize-none focus:outline-none focus:border-accent-500"
          />
          <div className="flex justify-end gap-3 mt-4">
            <button
              onClick={() => {
                setShowNewForm(false)
                setNewIdea('')
              }}
              className="px-4 py-2 text-[var(--text-secondary)] hover:text-[var(--text-primary)] transition-colors"
            >
              Cancel
            </button>
            <button
              onClick={createSession}
              disabled={!newIdea.trim()}
              className="px-4 py-2 bg-accent-500 text-white rounded-lg hover:bg-accent-600 transition-colors disabled:opacity-50"
            >
              Start Brainstorming
            </button>
          </div>
        </div>
      )}

      {/* Sessions List */}
      {isLoading ? (
        <div className="flex items-center justify-center py-12">
          <div className="w-8 h-8 border-2 border-accent-500 border-t-transparent rounded-full animate-spin" />
        </div>
      ) : sessions.length === 0 && !showNewForm ? (
        <div className="glass rounded-xl p-12 text-center">
          <Sparkles className="w-12 h-12 mx-auto text-[var(--text-tertiary)] mb-4" />
          <p className="text-[var(--text-secondary)] mb-4">No brainstorming sessions yet</p>
          <button
            onClick={() => setShowNewForm(true)}
            className="px-4 py-2 bg-accent-500/10 text-accent-500 rounded-lg hover:bg-accent-500/20 transition-colors"
          >
            Start your first session
          </button>
        </div>
      ) : (
        <div className="space-y-3">
          {sessions.map((session) => (
            <div
              key={session.session_id}
              className={`glass rounded-xl p-4 cursor-pointer transition-all hover:border-accent-500/30 ${
                selectedSession?.session_id === session.session_id ? 'border-accent-500' : ''
              }`}
              onClick={() => setSelectedSession(session)}
            >
              <div className="flex items-start justify-between gap-4">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1">
                    <h3 className="font-medium text-[var(--text-primary)] truncate">
                      {session.initial_idea.slice(0, 60)}
                      {session.initial_idea.length > 60 ? '...' : ''}
                    </h3>
                    <span className={`px-2 py-0.5 text-xs rounded-full border ${statusColors[session.status]}`}>
                      {session.status.replace('_', ' ')}
                    </span>
                  </div>
                  <div className="flex items-center gap-4 text-sm text-[var(--text-tertiary)]">
                    <span>{formatDate(session.created_at)}</span>
                    <span className="flex items-center gap-1">
                      <MessageCircle className="w-3 h-3" />
                      {session.clarifications.length} clarifications
                    </span>
                    {session.spec && (
                      <span className="flex items-center gap-1 text-green-400">
                        <FileText className="w-3 h-3" />
                        Spec ready
                      </span>
                    )}
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  {session.status === 'spec_ready' && (
                    <button
                      onClick={(e) => {
                        e.stopPropagation()
                        approveSession(session.session_id)
                      }}
                      className="p-2 text-green-400 hover:bg-green-500/10 rounded-lg transition-colors"
                      title="Approve spec"
                    >
                      <Check className="w-4 h-4" />
                    </button>
                  )}
                  <button
                    onClick={(e) => {
                      e.stopPropagation()
                      deleteSession(session.session_id)
                    }}
                    className="p-2 text-[var(--text-tertiary)] hover:text-red-400 hover:bg-red-500/10 rounded-lg transition-colors"
                    title="Delete session"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              </div>

              {/* Expanded view */}
              {selectedSession?.session_id === session.session_id && (
                <div className="mt-4 pt-4 border-t border-[var(--border-color)] space-y-4">
                  <div>
                    <h4 className="text-sm font-medium text-[var(--text-secondary)] mb-2">Initial Idea</h4>
                    <p className="text-sm text-[var(--text-primary)] bg-[var(--bg-base)] p-3 rounded-lg">
                      {session.initial_idea}
                    </p>
                  </div>

                  {session.clarifications.length > 0 && (
                    <div>
                      <h4 className="text-sm font-medium text-[var(--text-secondary)] mb-2">Clarifications</h4>
                      <div className="space-y-2">
                        {session.clarifications.map((c, i) => (
                          <div key={i} className="bg-[var(--bg-base)] p-3 rounded-lg">
                            <p className="text-sm text-accent-400 mb-1">Q: {c.question}</p>
                            <p className="text-sm text-[var(--text-primary)]">A: {c.answer}</p>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {session.spec && (
                    <div>
                      <h4 className="text-sm font-medium text-[var(--text-secondary)] mb-2">Generated Spec</h4>
                      <pre className="text-sm text-[var(--text-primary)] bg-[var(--bg-base)] p-3 rounded-lg whitespace-pre-wrap">
                        {session.spec}
                      </pre>
                    </div>
                  )}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
