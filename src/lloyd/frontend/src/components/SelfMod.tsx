import { useEffect, useState } from 'react'
import { Wrench, CheckCircle, XCircle, GitMerge, Trash2, RefreshCw, AlertTriangle } from 'lucide-react'

interface SelfModTask {
  task_id: string
  description: string
  risk_level: 'safe' | 'moderate' | 'risky'
  status: string
  clone_path: string | null
  created_at: string
  test_results: Record<string, [boolean, string]>
  error_message: string | null
}

const riskColors: Record<string, string> = {
  safe: 'bg-green-500/20 text-green-400 border-green-500/30',
  moderate: 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30',
  risky: 'bg-red-500/20 text-red-400 border-red-500/30',
}

const statusColors: Record<string, string> = {
  queued: 'text-zinc-400',
  in_progress: 'text-blue-400',
  testing: 'text-yellow-400',
  awaiting_gpu: 'text-orange-400',
  awaiting_approval: 'text-purple-400',
  merged: 'text-green-400',
  failed: 'text-red-400',
  rejected: 'text-zinc-500',
}

export function SelfMod() {
  const [tasks, setTasks] = useState<SelfModTask[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [selectedTask, setSelectedTask] = useState<SelfModTask | null>(null)

  const fetchTasks = async () => {
    setIsLoading(true)
    try {
      const res = await fetch('/api/selfmod/queue')
      if (res.ok) {
        setTasks(await res.json())
      }
    } catch (err) {
      console.error('Failed to fetch selfmod tasks:', err)
    }
    setIsLoading(false)
  }

  useEffect(() => {
    fetchTasks()
  }, [])

  const handleApprove = async (taskId: string) => {
    try {
      const res = await fetch(`/api/selfmod/${taskId}/approve`, { method: 'POST' })
      if (res.ok) {
        fetchTasks()
        setSelectedTask(null)
      }
    } catch (err) {
      console.error('Failed to approve:', err)
    }
  }

  const handleReject = async (taskId: string) => {
    try {
      const res = await fetch(`/api/selfmod/${taskId}/reject`, { method: 'POST' })
      if (res.ok) {
        fetchTasks()
        setSelectedTask(null)
      }
    } catch (err) {
      console.error('Failed to reject:', err)
    }
  }

  const formatDate = (dateStr: string) => {
    const date = new Date(dateStr)
    return date.toLocaleDateString() + ' ' + date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
  }

  const pendingApproval = tasks.filter(t => t.status === 'awaiting_approval' || t.status === 'awaiting_gpu')

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-2xl font-semibold text-[var(--text-primary)] flex items-center gap-2">
            <Wrench className="w-6 h-6 text-accent-500" />
            Self-Modifications
          </h2>
          <p className="text-sm text-[var(--text-tertiary)] mt-1">
            Safe modifications to Lloyd itself
          </p>
        </div>
        <button
          onClick={fetchTasks}
          className="p-2 rounded-lg hover:bg-[var(--border-color)] transition-colors"
        >
          <RefreshCw className="w-4 h-4 text-[var(--text-secondary)]" />
        </button>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-1 sm:grid-cols-4 gap-4">
        <div className="glass rounded-xl p-4">
          <div className="text-2xl font-semibold text-[var(--text-primary)]">{tasks.length}</div>
          <div className="text-sm text-[var(--text-tertiary)]">Total tasks</div>
        </div>
        <div className="glass rounded-xl p-4">
          <div className="text-2xl font-semibold text-purple-400">{pendingApproval.length}</div>
          <div className="text-sm text-[var(--text-tertiary)]">Awaiting approval</div>
        </div>
        <div className="glass rounded-xl p-4">
          <div className="text-2xl font-semibold text-green-400">{tasks.filter(t => t.status === 'merged').length}</div>
          <div className="text-sm text-[var(--text-tertiary)]">Merged</div>
        </div>
        <div className="glass rounded-xl p-4">
          <div className="text-2xl font-semibold text-red-400">{tasks.filter(t => t.status === 'failed').length}</div>
          <div className="text-sm text-[var(--text-tertiary)]">Failed</div>
        </div>
      </div>

      {/* Content */}
      {isLoading ? (
        <div className="flex items-center justify-center py-12">
          <div className="w-8 h-8 border-2 border-accent-500 border-t-transparent rounded-full animate-spin" />
        </div>
      ) : tasks.length === 0 ? (
        <div className="glass rounded-xl p-12 text-center">
          <Wrench className="w-12 h-12 mx-auto text-[var(--text-tertiary)] mb-4" />
          <p className="text-[var(--text-secondary)]">No self-modification tasks</p>
          <p className="text-sm text-[var(--text-tertiary)] mt-2">
            When you ask Lloyd to modify itself, tasks appear here
          </p>
        </div>
      ) : (
        <div className="space-y-6">
          {/* Pending Approval Section */}
          {pendingApproval.length > 0 && (
            <div>
              <h3 className="text-sm font-medium text-[var(--text-secondary)] mb-3 flex items-center gap-2">
                <AlertTriangle className="w-4 h-4 text-yellow-400" />
                Awaiting Action ({pendingApproval.length})
              </h3>
              <div className="grid grid-cols-1 xl:grid-cols-2 gap-4">
                {pendingApproval.map((task) => (
                  <TaskCard
                    key={task.task_id}
                    task={task}
                    selected={selectedTask?.task_id === task.task_id}
                    onSelect={() => setSelectedTask(task)}
                    onApprove={handleApprove}
                    onReject={handleReject}
                    formatDate={formatDate}
                  />
                ))}
              </div>
            </div>
          )}

          {/* All Tasks */}
          <div>
            <h3 className="text-sm font-medium text-[var(--text-secondary)] mb-3">
              All Tasks ({tasks.length})
            </h3>
            <div className="grid grid-cols-1 xl:grid-cols-2 gap-4">
              {tasks.filter(t => !pendingApproval.includes(t)).map((task) => (
                <TaskCard
                  key={task.task_id}
                  task={task}
                  selected={selectedTask?.task_id === task.task_id}
                  onSelect={() => setSelectedTask(task)}
                  onApprove={handleApprove}
                  onReject={handleReject}
                  formatDate={formatDate}
                />
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

interface TaskCardProps {
  task: SelfModTask
  selected: boolean
  onSelect: () => void
  onApprove: (id: string) => void
  onReject: (id: string) => void
  formatDate: (date: string) => string
}

function TaskCard({ task, selected, onSelect, onApprove, onReject, formatDate }: TaskCardProps) {
  return (
    <div
      className={`glass rounded-xl p-4 cursor-pointer transition-all hover:border-accent-500/30 ${
        selected ? 'border-accent-500' : ''
      }`}
      onClick={onSelect}
    >
      <div className="flex items-start justify-between gap-4">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <h3 className="font-medium text-[var(--text-primary)] truncate">
              {task.description.slice(0, 50)}
              {task.description.length > 50 ? '...' : ''}
            </h3>
          </div>
          <div className="flex items-center gap-3 text-sm">
            <span className={`px-2 py-0.5 text-xs rounded-full border ${riskColors[task.risk_level]}`}>
              {task.risk_level}
            </span>
            <span className={statusColors[task.status]}>
              {task.status.replace('_', ' ')}
            </span>
            <span className="text-[var(--text-tertiary)]">
              {formatDate(task.created_at)}
            </span>
          </div>
        </div>
      </div>

      {/* Expanded view */}
      {selected && (
        <div className="mt-4 pt-4 border-t border-[var(--border-color)] space-y-4">
          <div className="text-sm">
            <span className="text-[var(--text-tertiary)]">Task ID:</span>{' '}
            <span className="text-[var(--text-secondary)] font-mono">{task.task_id}</span>
          </div>

          {task.clone_path && (
            <div className="text-sm">
              <span className="text-[var(--text-tertiary)]">Clone:</span>{' '}
              <span className="text-[var(--text-secondary)] font-mono text-xs">{task.clone_path}</span>
            </div>
          )}

          {task.error_message && (
            <div className="p-3 bg-red-500/10 rounded-lg text-sm text-red-400">
              {task.error_message}
            </div>
          )}

          {Object.keys(task.test_results).length > 0 && (
            <div>
              <h4 className="text-sm font-medium text-[var(--text-secondary)] mb-2">Test Results</h4>
              <div className="space-y-1">
                {Object.entries(task.test_results).map(([name, [passed]]) => (
                  <div key={name} className="flex items-center gap-2 text-sm">
                    {passed ? (
                      <CheckCircle className="w-4 h-4 text-green-400" />
                    ) : (
                      <XCircle className="w-4 h-4 text-red-400" />
                    )}
                    <span className="text-[var(--text-secondary)]">{name}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Actions */}
          {(task.status === 'awaiting_approval' || task.status === 'awaiting_gpu') && (
            <div className="flex items-center gap-2 pt-2">
              <button
                onClick={(e) => {
                  e.stopPropagation()
                  onApprove(task.task_id)
                }}
                className="flex items-center gap-2 px-3 py-1.5 text-sm bg-green-500/10 text-green-400 rounded-lg hover:bg-green-500/20 transition-colors"
              >
                <GitMerge className="w-4 h-4" />
                Approve & Merge
              </button>
              <button
                onClick={(e) => {
                  e.stopPropagation()
                  onReject(task.task_id)
                }}
                className="flex items-center gap-2 px-3 py-1.5 text-sm bg-red-500/10 text-red-400 rounded-lg hover:bg-red-500/20 transition-colors"
              >
                <Trash2 className="w-4 h-4" />
                Reject
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
