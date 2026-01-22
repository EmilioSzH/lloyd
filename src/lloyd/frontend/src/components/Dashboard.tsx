import { RefreshCw } from 'lucide-react'
import { StatusResponse, ProgressResponse, WebSocketMessage } from '../types'
import { LivePreview } from './LivePreview'

interface DashboardProps {
  status: StatusResponse | null
  progress: ProgressResponse | null
  onRefresh: () => void
  lastMessage: WebSocketMessage | null
  isConnected: boolean
}

export function Dashboard({ status, progress: _progress, onRefresh, lastMessage, isConnected }: DashboardProps) {
  const completionRate = status?.total_stories
    ? Math.round((status.completed_stories / status.total_stories) * 100)
    : 0

  return (
    <div className="animate-fade-in space-y-6">
      {/* Header */}
      <div className="flex items-end justify-between">
        <div>
          <p className="text-[var(--text-tertiary)] text-xs uppercase tracking-widest mb-1">Overview</p>
          <h2 className="text-2xl font-semibold text-[var(--text-primary)] tracking-tight">
            {status?.project_name || 'No Project'}
          </h2>
        </div>
        <button
          onClick={onRefresh}
          className="p-2 text-[var(--text-tertiary)] hover:text-[var(--text-primary)] hover:bg-[var(--border-color)] rounded-lg transition-all"
        >
          <RefreshCw className="w-4 h-4" />
        </button>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-3 gap-4">
        <div className="glass rounded-xl p-5 transition-all hover:border-[var(--border-hover)]">
          <p className="text-[var(--text-tertiary)] text-xs uppercase tracking-wider mb-3">Status</p>
          <div className="flex items-center gap-2">
            <div className={`w-2 h-2 rounded-full ${
              status?.status === 'complete' ? 'bg-emerald-400' :
              status?.status === 'executing' || status?.status === 'in_progress' ? 'bg-accent-400 animate-pulse' :
              'bg-zinc-400'
            }`} />
            <span className="text-lg font-medium text-[var(--text-primary)] capitalize">
              {status?.status || 'Idle'}
            </span>
          </div>
        </div>

        <div className="glass rounded-xl p-5 transition-all hover:border-[var(--border-hover)]">
          <p className="text-[var(--text-tertiary)] text-xs uppercase tracking-wider mb-3">Progress</p>
          <div className="flex items-baseline gap-1">
            <span className="text-3xl font-semibold text-[var(--text-primary)]">{completionRate}</span>
            <span className="text-[var(--text-tertiary)]">%</span>
          </div>
          <div className="mt-3 h-1 bg-[var(--border-color)] rounded-full overflow-hidden">
            <div
              className="h-full bg-gradient-to-r from-accent-400 to-accent-500 rounded-full transition-all duration-700"
              style={{ width: `${completionRate}%` }}
            />
          </div>
        </div>

        <div className="glass rounded-xl p-5 transition-all hover:border-[var(--border-hover)]">
          <p className="text-[var(--text-tertiary)] text-xs uppercase tracking-wider mb-3">Tasks</p>
          <div className="flex items-baseline gap-2">
            <span className="text-3xl font-semibold text-[var(--text-primary)]">
              {status?.completed_stories || 0}
            </span>
            <span className="text-[var(--text-tertiary)]">/ {status?.total_stories || 0}</span>
          </div>
        </div>
      </div>

      {/* Live Preview - Full Width */}
      <LivePreview
        lastMessage={lastMessage}
        status={status}
        isConnected={isConnected}
      />

      {/* Tasks List */}
      <div className="glass rounded-xl p-5">
        <p className="text-[var(--text-tertiary)] text-xs uppercase tracking-wider mb-4">Recent Tasks</p>
        {status?.stories && status.stories.length > 0 ? (
          <div className="grid grid-cols-2 gap-x-6 gap-y-2">
            {status.stories.slice(0, 6).map((story) => (
              <div key={story.id} className="flex items-center gap-3 py-2">
                <div className={`w-1.5 h-1.5 rounded-full shrink-0 ${story.passes ? 'bg-emerald-400' : 'bg-[var(--text-tertiary)]'}`} />
                <span className="text-sm text-[var(--text-secondary)] truncate flex-1">{story.title}</span>
                {story.passes && (
                  <span className="text-[10px] text-emerald-400 uppercase tracking-wider shrink-0">Done</span>
                )}
              </div>
            ))}
          </div>
        ) : (
          <p className="text-sm text-[var(--text-tertiary)]">No tasks yet</p>
        )}
      </div>
    </div>
  )
}
