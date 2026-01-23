import { useEffect, useState } from 'react'
import { Puzzle, Plus, Trash2, Power, PowerOff, RefreshCw, AlertCircle } from 'lucide-react'

interface Extension {
  name: string
  display_name: string
  version: string
  description: string
  path: string
  enabled: boolean
  error: string | null
  has_tool: boolean
}

export function Extensions() {
  const [extensions, setExtensions] = useState<Extension[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [showCreateForm, setShowCreateForm] = useState(false)
  const [newExtName, setNewExtName] = useState('')
  const [newExtDesc, setNewExtDesc] = useState('')

  const fetchExtensions = async () => {
    setIsLoading(true)
    try {
      const res = await fetch('/api/extensions')
      if (res.ok) {
        setExtensions(await res.json())
      }
    } catch (err) {
      console.error('Failed to fetch extensions:', err)
    }
    setIsLoading(false)
  }

  useEffect(() => {
    fetchExtensions()
  }, [])

  const handleCreate = async () => {
    if (!newExtName.trim()) return
    try {
      const res = await fetch('/api/extensions', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: newExtName, description: newExtDesc }),
      })
      if (res.ok) {
        setNewExtName('')
        setNewExtDesc('')
        setShowCreateForm(false)
        fetchExtensions()
      }
    } catch (err) {
      console.error('Failed to create extension:', err)
    }
  }

  const handleToggle = async (name: string, enable: boolean) => {
    try {
      const res = await fetch(`/api/extensions/${name}/${enable ? 'enable' : 'disable'}`, {
        method: 'POST',
      })
      if (res.ok) {
        fetchExtensions()
      }
    } catch (err) {
      console.error('Failed to toggle extension:', err)
    }
  }

  const handleRemove = async (name: string) => {
    if (!confirm(`Remove extension "${name}"?`)) return
    try {
      const res = await fetch(`/api/extensions/${name}`, { method: 'DELETE' })
      if (res.ok) {
        fetchExtensions()
      }
    } catch (err) {
      console.error('Failed to remove extension:', err)
    }
  }

  const enabledCount = extensions.filter(e => e.enabled && !e.error).length
  const errorCount = extensions.filter(e => e.error).length

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-2xl font-semibold text-[var(--text-primary)] flex items-center gap-2">
            <Puzzle className="w-6 h-6 text-accent-500" />
            Extensions
          </h2>
          <p className="text-sm text-[var(--text-tertiary)] mt-1">
            Extend Lloyd with plugins
          </p>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={() => setShowCreateForm(true)}
            className="flex items-center gap-2 px-4 py-2 bg-accent-500 text-white rounded-lg hover:bg-accent-600 transition-colors"
          >
            <Plus className="w-4 h-4" />
            Create Extension
          </button>
          <button
            onClick={fetchExtensions}
            className="p-2 rounded-lg hover:bg-[var(--border-color)] transition-colors"
          >
            <RefreshCw className="w-4 h-4 text-[var(--text-secondary)]" />
          </button>
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <div className="glass rounded-xl p-4">
          <div className="text-2xl font-semibold text-[var(--text-primary)]">{extensions.length}</div>
          <div className="text-sm text-[var(--text-tertiary)]">Total extensions</div>
        </div>
        <div className="glass rounded-xl p-4">
          <div className="text-2xl font-semibold text-green-400">{enabledCount}</div>
          <div className="text-sm text-[var(--text-tertiary)]">Enabled</div>
        </div>
        <div className="glass rounded-xl p-4">
          <div className="text-2xl font-semibold text-red-400">{errorCount}</div>
          <div className="text-sm text-[var(--text-tertiary)]">Errors</div>
        </div>
      </div>

      {/* Create Form */}
      {showCreateForm && (
        <div className="glass rounded-xl p-6">
          <h3 className="text-lg font-medium text-[var(--text-primary)] mb-4">
            Create New Extension
          </h3>
          <div className="space-y-4">
            <div>
              <label className="block text-sm text-[var(--text-secondary)] mb-1">Name</label>
              <input
                type="text"
                value={newExtName}
                onChange={(e) => setNewExtName(e.target.value)}
                placeholder="my-extension"
                className="w-full px-4 py-2 bg-[var(--bg-base)] border border-[var(--border-color)] rounded-lg text-[var(--text-primary)] placeholder-[var(--text-tertiary)] focus:outline-none focus:border-accent-500"
              />
            </div>
            <div>
              <label className="block text-sm text-[var(--text-secondary)] mb-1">Description</label>
              <input
                type="text"
                value={newExtDesc}
                onChange={(e) => setNewExtDesc(e.target.value)}
                placeholder="What does this extension do?"
                className="w-full px-4 py-2 bg-[var(--bg-base)] border border-[var(--border-color)] rounded-lg text-[var(--text-primary)] placeholder-[var(--text-tertiary)] focus:outline-none focus:border-accent-500"
              />
            </div>
            <div className="flex justify-end gap-3">
              <button
                onClick={() => {
                  setShowCreateForm(false)
                  setNewExtName('')
                  setNewExtDesc('')
                }}
                className="px-4 py-2 text-[var(--text-secondary)] hover:text-[var(--text-primary)] transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={handleCreate}
                disabled={!newExtName.trim()}
                className="px-4 py-2 bg-accent-500 text-white rounded-lg hover:bg-accent-600 transition-colors disabled:opacity-50"
              >
                Create
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Content */}
      {isLoading ? (
        <div className="flex items-center justify-center py-12">
          <div className="w-8 h-8 border-2 border-accent-500 border-t-transparent rounded-full animate-spin" />
        </div>
      ) : extensions.length === 0 && !showCreateForm ? (
        <div className="glass rounded-xl p-12 text-center">
          <Puzzle className="w-12 h-12 mx-auto text-[var(--text-tertiary)] mb-4" />
          <p className="text-[var(--text-secondary)] mb-4">No extensions installed</p>
          <button
            onClick={() => setShowCreateForm(true)}
            className="px-4 py-2 bg-accent-500/10 text-accent-500 rounded-lg hover:bg-accent-500/20 transition-colors"
          >
            Create your first extension
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
          {extensions.map((ext) => (
            <div
              key={ext.name}
              className={`glass rounded-xl p-4 transition-all ${
                ext.error ? 'border-red-500/30' : ext.enabled ? 'border-green-500/20' : ''
              }`}
            >
              <div className="flex items-start justify-between gap-3 mb-3">
                <div>
                  <h3 className="font-medium text-[var(--text-primary)]">{ext.display_name}</h3>
                  <p className="text-xs text-[var(--text-tertiary)]">v{ext.version}</p>
                </div>
                <div className="flex items-center gap-1">
                  {ext.error ? (
                    <span className="px-2 py-0.5 text-xs rounded-full bg-red-500/20 text-red-400">
                      Error
                    </span>
                  ) : ext.enabled ? (
                    <span className="px-2 py-0.5 text-xs rounded-full bg-green-500/20 text-green-400">
                      Enabled
                    </span>
                  ) : (
                    <span className="px-2 py-0.5 text-xs rounded-full bg-zinc-500/20 text-zinc-400">
                      Disabled
                    </span>
                  )}
                </div>
              </div>

              <p className="text-sm text-[var(--text-secondary)] mb-4 line-clamp-2">
                {ext.description}
              </p>

              {ext.error && (
                <div className="flex items-start gap-2 p-2 bg-red-500/10 rounded-lg mb-4 text-xs text-red-400">
                  <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
                  <span>{ext.error}</span>
                </div>
              )}

              <div className="flex items-center gap-2">
                {!ext.error && (
                  <button
                    onClick={() => handleToggle(ext.name, !ext.enabled)}
                    className={`flex items-center gap-1.5 px-3 py-1.5 text-xs rounded-lg transition-colors ${
                      ext.enabled
                        ? 'bg-zinc-500/10 text-zinc-400 hover:bg-zinc-500/20'
                        : 'bg-green-500/10 text-green-400 hover:bg-green-500/20'
                    }`}
                  >
                    {ext.enabled ? (
                      <>
                        <PowerOff className="w-3 h-3" />
                        Disable
                      </>
                    ) : (
                      <>
                        <Power className="w-3 h-3" />
                        Enable
                      </>
                    )}
                  </button>
                )}
                <button
                  onClick={() => handleRemove(ext.name)}
                  className="flex items-center gap-1.5 px-3 py-1.5 text-xs bg-red-500/10 text-red-400 rounded-lg hover:bg-red-500/20 transition-colors"
                >
                  <Trash2 className="w-3 h-3" />
                  Remove
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
