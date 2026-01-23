import { useState } from 'react'
import {
  Undo2,
  Save,
  Trash2,
  Clock,
  Check,
  Sun,
  Moon,
  Monitor,
  Palette,
  Layout,
  MessageSquare,
} from 'lucide-react'
import { useTheme, Theme, AccentColor } from '../hooks/useTheme'
import { useLayout, LayoutStyle, MascotPosition } from '../hooks/useLayout'
import { LloydMascot } from './LloydMascot'

export function Appearance() {
  const { theme, accentColor, setTheme, setAccentColor } = useTheme()
  const {
    config,
    versions,
    activeVersionId,
    setConfig,
    saveVersion,
    loadVersion,
    deleteVersion,
    rollback,
    canRollback,
  } = useLayout()

  const [saveDialogOpen, setSaveDialogOpen] = useState(false)
  const [saveName, setSaveName] = useState('')
  const [saveNotes, setSaveNotes] = useState('')

  const themeOptions: { value: Theme; label: string; icon: typeof Sun }[] = [
    { value: 'light', label: 'Light', icon: Sun },
    { value: 'dark', label: 'Dark', icon: Moon },
    { value: 'system', label: 'System', icon: Monitor },
  ]

  const accentOptions: { value: AccentColor; color: string }[] = [
    { value: 'blue', color: 'bg-blue-500' },
    { value: 'purple', color: 'bg-purple-500' },
    { value: 'green', color: 'bg-green-500' },
    { value: 'orange', color: 'bg-orange-500' },
    { value: 'pink', color: 'bg-pink-500' },
  ]

  const layoutOptions: { value: LayoutStyle; label: string; description: string }[] = [
    { value: 'default', label: 'Default', description: 'Standard sidebar layout' },
    { value: 'minimal-sidebar', label: 'Minimal Sidebar', description: 'Clean, focused sidebar with mascot' },
    { value: 'focus', label: 'Focus Mode', description: 'Maximum content area, minimal chrome' },
  ]

  const mascotOptions: { value: MascotPosition; label: string; description: string }[] = [
    { value: 'sidebar', label: 'Sidebar', description: 'Show in sidebar bottom' },
    { value: 'corner', label: 'Corner', description: 'Float in bottom-right corner' },
    { value: 'header', label: 'Header', description: 'Small icon in header' },
    { value: 'none', label: 'Hidden', description: 'No mascot visible' },
  ]

  const handleSaveVersion = () => {
    if (saveName.trim()) {
      saveVersion(saveName.trim(), saveNotes.trim() || undefined)
      setSaveName('')
      setSaveNotes('')
      setSaveDialogOpen(false)
    }
  }

  const formatDate = (timestamp: number) => {
    return new Date(timestamp).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    })
  }

  return (
    <div className="animate-fade-in space-y-8 max-w-4xl">
      {/* Header */}
      <div className="flex items-end justify-between">
        <div>
          <p className="text-[var(--text-tertiary)] text-xs uppercase tracking-widest mb-1">Customize</p>
          <h2 className="text-2xl font-semibold text-[var(--text-primary)] tracking-tight">Appearance</h2>
        </div>
        <div className="flex gap-2">
          {canRollback && (
            <button
              onClick={rollback}
              className="flex items-center gap-2 px-4 py-2 text-sm text-amber-500 hover:bg-amber-500/10 rounded-lg transition-all"
            >
              <Undo2 className="w-4 h-4" />
              Undo Last Change
            </button>
          )}
          <button
            onClick={() => setSaveDialogOpen(true)}
            className="flex items-center gap-2 px-4 py-2 text-sm bg-accent-500 text-white rounded-lg hover:bg-accent-600 transition-all"
          >
            <Save className="w-4 h-4" />
            Save Layout
          </button>
        </div>
      </div>

      {/* Theme Section */}
      <section className="glass rounded-xl p-6">
        <div className="flex items-center gap-3 mb-6">
          <div className="w-10 h-10 rounded-lg bg-accent-500/10 flex items-center justify-center">
            <Sun className="w-5 h-5 text-accent-500" />
          </div>
          <div>
            <h3 className="font-medium text-[var(--text-primary)]">Theme</h3>
            <p className="text-sm text-[var(--text-tertiary)]">Choose your preferred color scheme</p>
          </div>
        </div>

        <div className="grid grid-cols-3 gap-3 mb-6">
          {themeOptions.map((option) => {
            const Icon = option.icon
            return (
              <button
                key={option.value}
                onClick={() => setTheme(option.value)}
                className={`flex items-center justify-center gap-2 p-4 rounded-lg border transition-all ${
                  theme === option.value
                    ? 'border-accent-500 bg-accent-500/10 text-accent-500'
                    : 'border-[var(--border-color)] text-[var(--text-secondary)] hover:border-[var(--border-hover)]'
                }`}
              >
                <Icon className="w-4 h-4" />
                <span className="text-sm font-medium">{option.label}</span>
              </button>
            )
          })}
        </div>

        <div className="flex items-center gap-3 mb-3">
          <Palette className="w-4 h-4 text-[var(--text-tertiary)]" />
          <span className="text-sm text-[var(--text-secondary)]">Accent Color</span>
        </div>
        <div className="flex gap-2">
          {accentOptions.map((option) => (
            <button
              key={option.value}
              onClick={() => setAccentColor(option.value)}
              className={`w-10 h-10 rounded-lg ${option.color} transition-all ${
                accentColor === option.value
                  ? 'ring-2 ring-offset-2 ring-offset-[var(--bg-base)] ring-[var(--text-primary)]'
                  : 'hover:scale-110'
              }`}
              title={option.value}
            />
          ))}
        </div>
      </section>

      {/* Layout Section */}
      <section className="glass rounded-xl p-6">
        <div className="flex items-center gap-3 mb-6">
          <div className="w-10 h-10 rounded-lg bg-accent-500/10 flex items-center justify-center">
            <Layout className="w-5 h-5 text-accent-500" />
          </div>
          <div>
            <h3 className="font-medium text-[var(--text-primary)]">Layout Style</h3>
            <p className="text-sm text-[var(--text-tertiary)]">Choose how the interface is organized</p>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
          {layoutOptions.map((option) => (
            <button
              key={option.value}
              onClick={() => setConfig({ style: option.value })}
              className={`text-left p-4 rounded-lg border transition-all ${
                config.style === option.value
                  ? 'border-accent-500 bg-accent-500/10'
                  : 'border-[var(--border-color)] hover:border-[var(--border-hover)]'
              }`}
            >
              <div className="flex items-center gap-2 mb-1">
                {config.style === option.value && <Check className="w-4 h-4 text-accent-500" />}
                <span className={`font-medium ${config.style === option.value ? 'text-accent-500' : 'text-[var(--text-primary)]'}`}>
                  {option.label}
                </span>
              </div>
              <p className="text-xs text-[var(--text-tertiary)]">{option.description}</p>
            </button>
          ))}
        </div>
      </section>

      {/* Mascot Section */}
      <section className="glass rounded-xl p-6">
        <div className="flex items-center gap-3 mb-6">
          <div className="w-10 h-10 rounded-lg bg-accent-500/10 flex items-center justify-center">
            <MessageSquare className="w-5 h-5 text-accent-500" />
          </div>
          <div>
            <h3 className="font-medium text-[var(--text-primary)]">Lloyd Mascot</h3>
            <p className="text-sm text-[var(--text-tertiary)]">Configure your AI companion display</p>
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <div>
            <p className="text-sm text-[var(--text-secondary)] mb-3">Position</p>
            <div className="grid grid-cols-2 gap-2">
              {mascotOptions.map((option) => (
                <button
                  key={option.value}
                  onClick={() => setConfig({ mascotPosition: option.value })}
                  className={`text-left p-3 rounded-lg border transition-all ${
                    config.mascotPosition === option.value
                      ? 'border-accent-500 bg-accent-500/10'
                      : 'border-[var(--border-color)] hover:border-[var(--border-hover)]'
                  }`}
                >
                  <span className={`text-sm font-medium ${config.mascotPosition === option.value ? 'text-accent-500' : 'text-[var(--text-primary)]'}`}>
                    {option.label}
                  </span>
                  <p className="text-xs text-[var(--text-tertiary)]">{option.description}</p>
                </button>
              ))}
            </div>

            <div className="mt-4">
              <p className="text-sm text-[var(--text-secondary)] mb-2">Size: {config.mascotSize}px</p>
              <input
                type="range"
                min="60"
                max="200"
                value={config.mascotSize}
                onChange={(e) => setConfig({ mascotSize: parseInt(e.target.value) })}
                className="w-full accent-accent-500"
              />
              <div className="flex justify-between text-xs text-[var(--text-tertiary)]">
                <span>Small</span>
                <span>Large</span>
              </div>
            </div>
          </div>

          <div className="flex items-center justify-center">
            <div className="glass rounded-xl p-4">
              <LloydMascot size={config.mascotSize} status="idle" />
            </div>
          </div>
        </div>
      </section>

      {/* Saved Layouts Section */}
      <section className="glass rounded-xl p-6">
        <div className="flex items-center gap-3 mb-6">
          <div className="w-10 h-10 rounded-lg bg-accent-500/10 flex items-center justify-center">
            <Clock className="w-5 h-5 text-accent-500" />
          </div>
          <div>
            <h3 className="font-medium text-[var(--text-primary)]">Saved Layouts</h3>
            <p className="text-sm text-[var(--text-tertiary)]">Switch between saved configurations</p>
          </div>
        </div>

        {versions.length === 0 ? (
          <p className="text-sm text-[var(--text-tertiary)] text-center py-8">
            No saved layouts yet. Save your current layout to enable quick switching.
          </p>
        ) : (
          <div className="space-y-2">
            {versions.map((version) => (
              <div
                key={version.id}
                className={`flex items-center justify-between p-4 rounded-lg border transition-all ${
                  activeVersionId === version.id
                    ? 'border-accent-500 bg-accent-500/5'
                    : 'border-[var(--border-color)] hover:border-[var(--border-hover)]'
                }`}
              >
                <div className="flex-1">
                  <div className="flex items-center gap-2">
                    {activeVersionId === version.id && <Check className="w-4 h-4 text-accent-500" />}
                    <span className="font-medium text-[var(--text-primary)]">{version.name}</span>
                  </div>
                  {version.notes && (
                    <p className="text-xs text-[var(--text-tertiary)] mt-1">{version.notes}</p>
                  )}
                  <p className="text-xs text-[var(--text-tertiary)] mt-1">{formatDate(version.timestamp)}</p>
                </div>
                <div className="flex gap-2">
                  {activeVersionId !== version.id && (
                    <button
                      onClick={() => loadVersion(version.id)}
                      className="px-3 py-1.5 text-sm text-accent-500 hover:bg-accent-500/10 rounded-lg transition-all"
                    >
                      Load
                    </button>
                  )}
                  <button
                    onClick={() => deleteVersion(version.id)}
                    className="p-1.5 text-[var(--text-tertiary)] hover:text-red-500 hover:bg-red-500/10 rounded-lg transition-all"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </section>

      {/* Save Dialog */}
      {saveDialogOpen && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="glass rounded-xl p-6 w-full max-w-md mx-4 animate-fade-in">
            <h3 className="text-lg font-semibold text-[var(--text-primary)] mb-4">Save Layout</h3>

            <div className="space-y-4">
              <div>
                <label className="block text-sm text-[var(--text-secondary)] mb-2">Name</label>
                <input
                  type="text"
                  value={saveName}
                  onChange={(e) => setSaveName(e.target.value)}
                  placeholder="My Custom Layout"
                  className="w-full px-4 py-2 rounded-lg bg-[var(--bg-base)] border border-[var(--border-color)] text-[var(--text-primary)] focus:border-accent-500 outline-none"
                />
              </div>

              <div>
                <label className="block text-sm text-[var(--text-secondary)] mb-2">Notes (optional)</label>
                <textarea
                  value={saveNotes}
                  onChange={(e) => setSaveNotes(e.target.value)}
                  placeholder="What makes this layout special..."
                  rows={3}
                  className="w-full px-4 py-2 rounded-lg bg-[var(--bg-base)] border border-[var(--border-color)] text-[var(--text-primary)] focus:border-accent-500 outline-none resize-none"
                />
              </div>
            </div>

            <div className="flex justify-end gap-3 mt-6">
              <button
                onClick={() => setSaveDialogOpen(false)}
                className="px-4 py-2 text-sm text-[var(--text-secondary)] hover:text-[var(--text-primary)] transition-all"
              >
                Cancel
              </button>
              <button
                onClick={handleSaveVersion}
                disabled={!saveName.trim()}
                className="px-4 py-2 text-sm bg-accent-500 text-white rounded-lg hover:bg-accent-600 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Save
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
