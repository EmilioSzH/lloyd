import { RefreshCw, FileText, Download } from 'lucide-react'
import { ProgressResponse } from '../types'

interface ProgressLogProps {
  progress: ProgressResponse | null
  onRefresh: () => void
}

export function ProgressLog({ progress, onRefresh }: ProgressLogProps) {
  const handleDownload = () => {
    if (!progress?.content) return

    const blob = new Blob([progress.content], { type: 'text/plain' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = 'lloyd-progress.txt'
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
  }

  const formatLine = (line: string) => {
    // Format headers
    if (line.startsWith('# ')) {
      return <span className="text-lg font-semibold text-[var(--text-primary)]">{line.slice(2)}</span>
    }
    if (line.startsWith('## ')) {
      return <span className="text-base font-medium text-[var(--text-primary)]">{line.slice(3)}</span>
    }
    if (line.startsWith('### ')) {
      return <span className="text-sm font-medium text-accent-400">{line.slice(4)}</span>
    }
    // Format list items
    if (line.startsWith('- ')) {
      return (
        <span className="flex items-start gap-2">
          <span className="text-accent-500 mt-0.5">•</span>
          <span>{line.slice(2)}</span>
        </span>
      )
    }
    return <span>{line}</span>
  }

  return (
    <div className="animate-fade-in">
      {/* Header */}
      <div className="flex items-end justify-between mb-8">
        <div>
          <p className="text-[var(--text-tertiary)] text-xs uppercase tracking-widest mb-1">History</p>
          <h2 className="text-2xl font-semibold text-[var(--text-primary)] tracking-tight">Progress</h2>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={handleDownload}
            disabled={!progress?.content}
            className="p-2 text-[var(--text-tertiary)] hover:text-[var(--text-primary)] hover:bg-[var(--border-color)] rounded-lg transition-all disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <Download className="w-4 h-4" />
          </button>
          <button
            onClick={onRefresh}
            className="p-2 text-[var(--text-tertiary)] hover:text-[var(--text-primary)] hover:bg-[var(--border-color)] rounded-lg transition-all"
          >
            <RefreshCw className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Stats */}
      {progress?.lines && progress.lines.length > 0 && (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-6">
          <div className="glass rounded-xl p-4 text-center">
            <p className="text-2xl font-semibold text-[var(--text-primary)]">{progress.lines.length}</p>
            <p className="text-[10px] text-[var(--text-tertiary)] uppercase tracking-wider mt-1">Lines</p>
          </div>
          <div className="glass rounded-xl p-4 text-center">
            <p className="text-2xl font-semibold text-[var(--text-primary)]">
              {progress.lines.filter(l => l.startsWith('## ')).length}
            </p>
            <p className="text-[10px] text-[var(--text-tertiary)] uppercase tracking-wider mt-1">Sections</p>
          </div>
          <div className="glass rounded-xl p-4 text-center">
            <p className="text-2xl font-semibold text-[var(--text-primary)]">
              {progress.lines.filter(l => l.startsWith('- ')).length}
            </p>
            <p className="text-[10px] text-[var(--text-tertiary)] uppercase tracking-wider mt-1">Items</p>
          </div>
          <div className="glass rounded-xl p-4 text-center">
            <p className="text-2xl font-semibold text-[var(--text-primary)]">
              {(progress.content.length / 1000).toFixed(1)}k
            </p>
            <p className="text-[10px] text-[var(--text-tertiary)] uppercase tracking-wider mt-1">Chars</p>
          </div>
        </div>
      )}

      {/* Log Content */}
      <div className="glass rounded-xl overflow-hidden">
        {progress?.lines && progress.lines.length > 0 ? (
          <div className="p-5 space-y-1 font-mono text-sm max-h-[65vh] overflow-auto">
            {progress.lines.map((line, index) => (
              <div
                key={index}
                className={`py-0.5 ${
                  line.trim() === '' ? 'h-3' : 'text-[var(--text-secondary)]'
                }`}
              >
                {formatLine(line)}
              </div>
            ))}
          </div>
        ) : (
          <div className="p-12 text-center">
            <div className="w-12 h-12 mx-auto mb-4 bg-[var(--border-color)] rounded-full flex items-center justify-center">
              <FileText className="w-6 h-6 text-[var(--text-tertiary)]" />
            </div>
            <h3 className="font-medium text-[var(--text-primary)] mb-1">No Progress</h3>
            <p className="text-sm text-[var(--text-tertiary)]">Activity will appear here as Lloyd works</p>
          </div>
        )}
      </div>
    </div>
  )
}
