import { useState } from 'react'
import { RefreshCw, CheckCircle2, Clock, AlertTriangle, RotateCcw, ChevronDown, ChevronRight } from 'lucide-react'
import { StatusResponse, Story } from '../types'

interface TaskQueueProps {
  status: StatusResponse | null
  onRefresh: () => void
}

export function TaskQueue({ status, onRefresh }: TaskQueueProps) {
  const [expandedStory, setExpandedStory] = useState<string | null>(null)
  const [resetting, setResetting] = useState<string | null>(null)

  const handleResetStory = async (storyId: string) => {
    setResetting(storyId)
    try {
      const res = await fetch('/api/reset-story', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ story_id: storyId }),
      })

      if (res.ok) {
        onRefresh()
      }
    } catch (err) {
      console.error('Failed to reset story:', err)
    } finally {
      setResetting(null)
    }
  }

  const getStoryStatus = (story: Story) => {
    if (story.passes) return 'complete'
    if (story.attempts >= 3) return 'blocked'
    return 'pending'
  }

  const getStatusBadge = (statusType: string) => {
    switch (statusType) {
      case 'complete':
        return (
          <span className="flex items-center gap-1.5 px-2.5 py-1 text-[10px] uppercase tracking-wider font-medium bg-emerald-500/10 text-emerald-400 rounded-full">
            <CheckCircle2 className="w-3 h-3" />
            Complete
          </span>
        )
      case 'blocked':
        return (
          <span className="flex items-center gap-1.5 px-2.5 py-1 text-[10px] uppercase tracking-wider font-medium bg-red-500/10 text-red-400 rounded-full">
            <AlertTriangle className="w-3 h-3" />
            Blocked
          </span>
        )
      default:
        return (
          <span className="flex items-center gap-1.5 px-2.5 py-1 text-[10px] uppercase tracking-wider font-medium bg-amber-500/10 text-amber-400 rounded-full">
            <Clock className="w-3 h-3" />
            Pending
          </span>
        )
    }
  }

  const completionRate = status?.total_stories
    ? Math.round((status.completed_stories / status.total_stories) * 100)
    : 0

  return (
    <div className="animate-fade-in max-w-4xl">
      {/* Header */}
      <div className="flex items-end justify-between mb-8">
        <div>
          <p className="text-[var(--text-tertiary)] text-xs uppercase tracking-widest mb-1">Queue</p>
          <h2 className="text-2xl font-semibold text-[var(--text-primary)] tracking-tight">Tasks</h2>
          <p className="text-sm text-[var(--text-tertiary)] mt-1">
            {status?.completed_stories || 0} of {status?.total_stories || 0} completed
          </p>
        </div>
        <button
          onClick={onRefresh}
          className="p-2 text-[var(--text-tertiary)] hover:text-[var(--text-primary)] hover:bg-[var(--border-color)] rounded-lg transition-all"
        >
          <RefreshCw className="w-4 h-4" />
        </button>
      </div>

      {/* Progress Bar */}
      {status && status.total_stories > 0 && (
        <div className="glass rounded-xl p-5 mb-6">
          <div className="flex items-center justify-between mb-3">
            <span className="text-xs text-[var(--text-tertiary)] uppercase tracking-wider">Progress</span>
            <span className="text-sm font-medium text-[var(--text-primary)]">{completionRate}%</span>
          </div>
          <div className="h-1.5 bg-[var(--border-color)] rounded-full overflow-hidden">
            <div
              className="h-full bg-gradient-to-r from-accent-400 to-accent-500 rounded-full transition-all duration-700"
              style={{ width: `${completionRate}%` }}
            />
          </div>
        </div>
      )}

      {/* Task List */}
      <div className="space-y-3">
        {status?.stories && status.stories.length > 0 ? (
          status.stories.map((story) => {
            const storyStatus = getStoryStatus(story)
            const isExpanded = expandedStory === story.id

            return (
              <div
                key={story.id}
                className={`glass rounded-xl transition-all duration-200 ${
                  isExpanded ? 'border-accent-500/30' : ''
                }`}
              >
                {/* Story Header */}
                <div
                  className="flex items-center gap-4 p-4 cursor-pointer hover:bg-[var(--border-color)]/50 rounded-xl transition-all"
                  onClick={() => setExpandedStory(isExpanded ? null : story.id)}
                >
                  <button className="text-[var(--text-tertiary)] hover:text-[var(--text-primary)]">
                    {isExpanded ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
                  </button>

                  <div className="flex-1 min-w-0">
                    <h3 className="font-medium text-[var(--text-primary)] truncate">{story.title}</h3>
                    <p className="text-xs text-[var(--text-tertiary)] mt-0.5">
                      Priority {story.priority} · {story.attempts} attempts
                    </p>
                  </div>

                  {getStatusBadge(storyStatus)}
                </div>

                {/* Expanded Content */}
                {isExpanded && (
                  <div className="px-4 pb-4 border-t border-[var(--border-color)]">
                    <div className="pt-4 space-y-4">
                      {/* Description */}
                      <div>
                        <h4 className="text-xs text-[var(--text-tertiary)] uppercase tracking-wider mb-2">Description</h4>
                        <p className="text-sm text-[var(--text-secondary)]">{story.description || 'No description'}</p>
                      </div>

                      {/* Acceptance Criteria */}
                      {story.acceptanceCriteria && story.acceptanceCriteria.length > 0 && (
                        <div>
                          <h4 className="text-xs text-[var(--text-tertiary)] uppercase tracking-wider mb-2">Acceptance Criteria</h4>
                          <ul className="space-y-1.5">
                            {story.acceptanceCriteria.map((criteria, index) => (
                              <li key={index} className="flex items-start gap-2 text-sm text-[var(--text-secondary)]">
                                <span className="text-accent-500 mt-0.5">•</span>
                                {criteria}
                              </li>
                            ))}
                          </ul>
                        </div>
                      )}

                      {/* Notes */}
                      {story.notes && (
                        <div>
                          <h4 className="text-xs text-[var(--text-tertiary)] uppercase tracking-wider mb-2">Notes</h4>
                          <pre className="text-sm text-[var(--text-secondary)] bg-[var(--border-color)]/50 p-3 rounded-lg whitespace-pre-wrap font-mono">
                            {story.notes}
                          </pre>
                        </div>
                      )}

                      {/* Actions */}
                      {!story.passes && (
                        <div className="flex justify-end pt-2">
                          <button
                            onClick={(e) => {
                              e.stopPropagation()
                              handleResetStory(story.id)
                            }}
                            disabled={resetting === story.id}
                            className="flex items-center gap-2 px-3 py-1.5 text-xs text-[var(--text-tertiary)] hover:text-[var(--text-primary)] hover:bg-[var(--border-color)] rounded-lg transition-all disabled:opacity-50"
                          >
                            <RotateCcw className={`w-3.5 h-3.5 ${resetting === story.id ? 'animate-spin' : ''}`} />
                            Reset
                          </button>
                        </div>
                      )}
                    </div>
                  </div>
                )}
              </div>
            )
          })
        ) : (
          <div className="glass rounded-xl p-12 text-center">
            <div className="w-12 h-12 mx-auto mb-4 bg-[var(--border-color)] rounded-full flex items-center justify-center">
              <Clock className="w-6 h-6 text-[var(--text-tertiary)]" />
            </div>
            <h3 className="font-medium text-[var(--text-primary)] mb-1">No Tasks</h3>
            <p className="text-sm text-[var(--text-tertiary)]">Submit an idea to create tasks</p>
          </div>
        )}
      </div>
    </div>
  )
}
