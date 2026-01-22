import { useEffect, useState } from 'react'
import { BookOpen, Tag, TrendingUp, RefreshCw, Search, Trash2 } from 'lucide-react'

interface LearningEntry {
  id: string
  category: string
  title: string
  description: string
  context: string
  confidence: number
  frequency: number
  last_applied: string | null
  created_at: string
  tags: string[]
}

const categoryColors: Record<string, string> = {
  bug_pattern: 'bg-red-500/20 text-red-400 border-red-500/30',
  fix_strategy: 'bg-green-500/20 text-green-400 border-green-500/30',
  user_preference: 'bg-blue-500/20 text-blue-400 border-blue-500/30',
  code_pattern: 'bg-purple-500/20 text-purple-400 border-purple-500/30',
  project_structure: 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30',
  default: 'bg-zinc-500/20 text-zinc-400 border-zinc-500/30',
}

export function Knowledge() {
  const [entries, setEntries] = useState<LearningEntry[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [selectedEntry, setSelectedEntry] = useState<LearningEntry | null>(null)
  const [searchQuery, setSearchQuery] = useState('')
  const [filterCategory, setFilterCategory] = useState<string>('')

  const fetchEntries = async () => {
    setIsLoading(true)
    try {
      let url = '/api/knowledge'
      const params = new URLSearchParams()
      if (filterCategory) params.set('category', filterCategory)
      if (params.toString()) url += '?' + params.toString()

      const res = await fetch(url)
      if (res.ok) {
        setEntries(await res.json())
      }
    } catch (err) {
      console.error('Failed to fetch knowledge:', err)
    }
    setIsLoading(false)
  }

  useEffect(() => {
    fetchEntries()
  }, [filterCategory])

  const deleteEntry = async (entryId: string) => {
    try {
      const res = await fetch(`/api/knowledge/${entryId}`, {
        method: 'DELETE',
      })
      if (res.ok) {
        if (selectedEntry?.id === entryId) {
          setSelectedEntry(null)
        }
        fetchEntries()
      }
    } catch (err) {
      console.error('Failed to delete entry:', err)
    }
  }

  const formatDate = (dateStr: string | null) => {
    if (!dateStr) return 'Never'
    const date = new Date(dateStr)
    return date.toLocaleDateString() + ' ' + date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
  }

  const filteredEntries = entries.filter((entry) => {
    if (!searchQuery) return true
    const query = searchQuery.toLowerCase()
    return (
      entry.title.toLowerCase().includes(query) ||
      entry.description.toLowerCase().includes(query) ||
      entry.tags.some((t) => t.toLowerCase().includes(query))
    )
  })

  const categories = [...new Set(entries.map((e) => e.category))]

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-semibold text-[var(--text-primary)] flex items-center gap-2">
            <BookOpen className="w-6 h-6 text-accent-500" />
            Knowledge Base
          </h2>
          <p className="text-sm text-[var(--text-tertiary)] mt-1">
            Learned patterns and insights
          </p>
        </div>
        <button
          onClick={fetchEntries}
          className="p-2 rounded-lg hover:bg-[var(--border-color)] transition-colors"
        >
          <RefreshCw className="w-4 h-4 text-[var(--text-secondary)]" />
        </button>
      </div>

      {/* Filters */}
      <div className="flex items-center gap-4">
        <div className="relative flex-1 max-w-md">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-[var(--text-tertiary)]" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search knowledge..."
            className="w-full pl-10 pr-4 py-2 bg-[var(--bg-base)] border border-[var(--border-color)] rounded-lg text-[var(--text-primary)] placeholder-[var(--text-tertiary)] focus:outline-none focus:border-accent-500"
          />
        </div>
        <select
          value={filterCategory}
          onChange={(e) => setFilterCategory(e.target.value)}
          className="px-4 py-2 bg-[var(--bg-base)] border border-[var(--border-color)] rounded-lg text-[var(--text-primary)] focus:outline-none focus:border-accent-500"
        >
          <option value="">All categories</option>
          {categories.map((cat) => (
            <option key={cat} value={cat}>
              {cat.replace('_', ' ')}
            </option>
          ))}
        </select>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-3 gap-4">
        <div className="glass rounded-xl p-4">
          <div className="text-2xl font-semibold text-[var(--text-primary)]">{entries.length}</div>
          <div className="text-sm text-[var(--text-tertiary)]">Total entries</div>
        </div>
        <div className="glass rounded-xl p-4">
          <div className="text-2xl font-semibold text-[var(--text-primary)]">{categories.length}</div>
          <div className="text-sm text-[var(--text-tertiary)]">Categories</div>
        </div>
        <div className="glass rounded-xl p-4">
          <div className="text-2xl font-semibold text-[var(--text-primary)]">
            {entries.length > 0
              ? Math.round((entries.reduce((sum, e) => sum + e.confidence, 0) / entries.length) * 100)
              : 0}
            %
          </div>
          <div className="text-sm text-[var(--text-tertiary)]">Avg confidence</div>
        </div>
      </div>

      {/* Content */}
      {isLoading ? (
        <div className="flex items-center justify-center py-12">
          <div className="w-8 h-8 border-2 border-accent-500 border-t-transparent rounded-full animate-spin" />
        </div>
      ) : filteredEntries.length === 0 ? (
        <div className="glass rounded-xl p-12 text-center">
          <BookOpen className="w-12 h-12 mx-auto text-[var(--text-tertiary)] mb-4" />
          <p className="text-[var(--text-secondary)]">
            {searchQuery || filterCategory
              ? 'No matching entries found'
              : 'No knowledge entries yet. Lloyd learns as it works!'}
          </p>
        </div>
      ) : (
        <div className="space-y-3">
          {filteredEntries.map((entry) => (
            <div
              key={entry.id}
              className={`glass rounded-xl p-4 cursor-pointer transition-all hover:border-accent-500/30 ${
                selectedEntry?.id === entry.id ? 'border-accent-500' : ''
              }`}
              onClick={() => setSelectedEntry(entry)}
            >
              <div className="flex items-start justify-between gap-4">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1">
                    <h3 className="font-medium text-[var(--text-primary)] truncate">{entry.title}</h3>
                    <span
                      className={`px-2 py-0.5 text-xs rounded-full border ${
                        categoryColors[entry.category] || categoryColors.default
                      }`}
                    >
                      {entry.category.replace('_', ' ')}
                    </span>
                  </div>
                  <p className="text-sm text-[var(--text-tertiary)] line-clamp-2">{entry.description}</p>
                  <div className="flex items-center gap-4 mt-2">
                    <div className="flex items-center gap-1 text-sm">
                      <TrendingUp className="w-3 h-3 text-accent-500" />
                      <span className="text-[var(--text-secondary)]">
                        {Math.round(entry.confidence * 100)}% confidence
                      </span>
                    </div>
                    <span className="text-sm text-[var(--text-tertiary)]">Used {entry.frequency}x</span>
                  </div>
                </div>
                <button
                  onClick={(e) => {
                    e.stopPropagation()
                    deleteEntry(entry.id)
                  }}
                  className="p-2 text-[var(--text-tertiary)] hover:text-red-400 hover:bg-red-500/10 rounded-lg transition-colors"
                  title="Delete entry"
                >
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>

              {/* Expanded view */}
              {selectedEntry?.id === entry.id && (
                <div className="mt-4 pt-4 border-t border-[var(--border-color)] space-y-4">
                  {entry.context && (
                    <div>
                      <h4 className="text-sm font-medium text-[var(--text-secondary)] mb-2">Context</h4>
                      <p className="text-sm text-[var(--text-primary)] bg-[var(--bg-base)] p-3 rounded-lg">
                        {entry.context}
                      </p>
                    </div>
                  )}

                  {entry.tags.length > 0 && (
                    <div>
                      <h4 className="text-sm font-medium text-[var(--text-secondary)] mb-2">Tags</h4>
                      <div className="flex flex-wrap gap-2">
                        {entry.tags.map((tag) => (
                          <span
                            key={tag}
                            className="flex items-center gap-1 px-2 py-1 text-xs bg-[var(--border-color)] text-[var(--text-secondary)] rounded-full"
                          >
                            <Tag className="w-3 h-3" />
                            {tag}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}

                  <div className="flex items-center gap-6 text-sm text-[var(--text-tertiary)]">
                    <span>Created: {formatDate(entry.created_at)}</span>
                    <span>Last applied: {formatDate(entry.last_applied)}</span>
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
