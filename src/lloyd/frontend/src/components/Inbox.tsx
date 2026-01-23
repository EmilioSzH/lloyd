import { useEffect, useState } from 'react'
import { Inbox as InboxIcon, CheckCircle, XCircle, AlertCircle, HelpCircle, FileCheck, RefreshCw } from 'lucide-react'

interface InboxItem {
  id: string
  type: 'review' | 'blocked' | 'question' | 'failed' | 'spec_approval'
  project_id: string
  title: string
  created_at: string
  priority: 'high' | 'normal' | 'low'
  context: Record<string, unknown>
  actions: string[]
  resolved: boolean
  resolved_at: string | null
  resolution: string | null
}

const typeIcons: Record<string, typeof InboxIcon> = {
  review: FileCheck,
  blocked: XCircle,
  question: HelpCircle,
  failed: AlertCircle,
  spec_approval: CheckCircle,
}

const typeColors: Record<string, string> = {
  review: 'text-blue-400',
  blocked: 'text-red-400',
  question: 'text-yellow-400',
  failed: 'text-orange-400',
  spec_approval: 'text-green-400',
}

const priorityColors: Record<string, string> = {
  high: 'bg-red-500/20 text-red-400 border-red-500/30',
  normal: 'bg-blue-500/20 text-blue-400 border-blue-500/30',
  low: 'bg-zinc-500/20 text-zinc-400 border-zinc-500/30',
}

export function Inbox() {
  const [items, setItems] = useState<InboxItem[]>([])
  const [showResolved, setShowResolved] = useState(false)
  const [isLoading, setIsLoading] = useState(true)
  const [selectedItem, setSelectedItem] = useState<InboxItem | null>(null)

  const fetchItems = async () => {
    setIsLoading(true)
    try {
      const endpoint = showResolved ? '/api/inbox?show_resolved=true' : '/api/inbox'
      const res = await fetch(endpoint)
      if (res.ok) {
        setItems(await res.json())
      }
    } catch (err) {
      console.error('Failed to fetch inbox:', err)
    }
    setIsLoading(false)
  }

  useEffect(() => {
    fetchItems()
  }, [showResolved])

  const handleResolve = async (itemId: string, action: string) => {
    try {
      const res = await fetch(`/api/inbox/${itemId}/resolve`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action }),
      })
      if (res.ok) {
        setSelectedItem(null)
        fetchItems()
      }
    } catch (err) {
      console.error('Failed to resolve item:', err)
    }
  }

  const formatDate = (dateStr: string) => {
    const date = new Date(dateStr)
    return date.toLocaleDateString() + ' ' + date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
  }

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-2xl font-semibold text-[var(--text-primary)] flex items-center gap-2">
            <InboxIcon className="w-6 h-6 text-accent-500" />
            Inbox
          </h2>
          <p className="text-sm text-[var(--text-tertiary)] mt-1">
            Items requiring your attention
          </p>
        </div>
        <div className="flex items-center gap-3">
          <label className="flex items-center gap-2 text-sm text-[var(--text-secondary)]">
            <input
              type="checkbox"
              checked={showResolved}
              onChange={(e) => setShowResolved(e.target.checked)}
              className="w-4 h-4 rounded border-[var(--border-color)]"
            />
            Show resolved
          </label>
          <button
            onClick={fetchItems}
            className="p-2 rounded-lg hover:bg-[var(--border-color)] transition-colors"
          >
            <RefreshCw className="w-4 h-4 text-[var(--text-secondary)]" />
          </button>
        </div>
      </div>

      {/* Content */}
      {isLoading ? (
        <div className="flex items-center justify-center py-12">
          <div className="w-8 h-8 border-2 border-accent-500 border-t-transparent rounded-full animate-spin" />
        </div>
      ) : items.length === 0 ? (
        <div className="glass rounded-xl p-12 text-center">
          <InboxIcon className="w-12 h-12 mx-auto text-[var(--text-tertiary)] mb-4" />
          <p className="text-[var(--text-secondary)]">
            {showResolved ? 'No inbox items' : 'No items requiring attention'}
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 xl:grid-cols-2 gap-4">
          {items.map((item) => {
            const Icon = typeIcons[item.type] || InboxIcon
            return (
              <div
                key={item.id}
                className={`glass rounded-xl p-4 cursor-pointer transition-all hover:border-accent-500/30 ${
                  item.resolved ? 'opacity-60' : ''
                } ${selectedItem?.id === item.id ? 'border-accent-500' : ''}`}
                onClick={() => setSelectedItem(item)}
              >
                <div className="flex items-start gap-4">
                  <div className={`p-2 rounded-lg bg-[var(--border-color)] ${typeColors[item.type]}`}>
                    <Icon className="w-5 h-5" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <h3 className="font-medium text-[var(--text-primary)] truncate">
                        {item.title}
                      </h3>
                      <span className={`px-2 py-0.5 text-xs rounded-full border ${priorityColors[item.priority]}`}>
                        {item.priority}
                      </span>
                      {item.resolved && (
                        <span className="px-2 py-0.5 text-xs rounded-full bg-green-500/20 text-green-400 border border-green-500/30">
                          resolved
                        </span>
                      )}
                    </div>
                    <p className="text-sm text-[var(--text-tertiary)]">
                      {item.type} | {formatDate(item.created_at)}
                    </p>
                  </div>
                </div>

                {/* Expanded view */}
                {selectedItem?.id === item.id && (
                  <div className="mt-4 pt-4 border-t border-[var(--border-color)]">
                    {item.context && Object.keys(item.context).length > 0 && (
                      <div className="mb-4">
                        <h4 className="text-sm font-medium text-[var(--text-secondary)] mb-2">Context</h4>
                        <pre className="text-xs bg-[var(--bg-base)] p-3 rounded-lg overflow-auto text-[var(--text-tertiary)]">
                          {JSON.stringify(item.context, null, 2)}
                        </pre>
                      </div>
                    )}

                    {!item.resolved && item.actions.length > 0 && (
                      <div>
                        <h4 className="text-sm font-medium text-[var(--text-secondary)] mb-2">Actions</h4>
                        <div className="flex flex-wrap gap-2">
                          {item.actions.map((action) => (
                            <button
                              key={action}
                              onClick={(e) => {
                                e.stopPropagation()
                                handleResolve(item.id, action)
                              }}
                              className="px-3 py-1.5 text-sm bg-accent-500/10 text-accent-500 rounded-lg hover:bg-accent-500/20 transition-colors"
                            >
                              {action}
                            </button>
                          ))}
                        </div>
                      </div>
                    )}

                    {item.resolved && item.resolution && (
                      <div className="text-sm text-[var(--text-tertiary)]">
                        <span className="font-medium">Resolution:</span> {item.resolution}
                        {item.resolved_at && (
                          <span className="ml-2">at {formatDate(item.resolved_at)}</span>
                        )}
                      </div>
                    )}
                  </div>
                )}
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}
