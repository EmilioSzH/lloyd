import { useState } from 'react'
import { Send, Loader2 } from 'lucide-react'

interface IdeaFormProps {
  onSubmit: () => void
}

export function IdeaForm({ onSubmit }: IdeaFormProps) {
  const [idea, setIdea] = useState('')
  const [maxIterations, setMaxIterations] = useState(50)
  const [dryRun, setDryRun] = useState(false)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!idea.trim()) return

    setIsSubmitting(true)
    setMessage(null)

    try {
      const res = await fetch('/api/idea', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ description: idea, max_iterations: maxIterations, dry_run: dryRun }),
      })

      if (!res.ok) throw new Error('Failed to submit')

      const data = await res.json()
      setMessage({ type: 'success', text: data.message })
      setIdea('')
      onSubmit()
    } catch {
      setMessage({ type: 'error', text: 'Failed to submit idea' })
    } finally {
      setIsSubmitting(false)
    }
  }

  const examples = [
    'Build a REST API with FastAPI',
    'Create a CLI tool for Docker',
    'Build a web scraper',
  ]

  return (
    <div className="animate-fade-in max-w-4xl mx-auto">
      {/* Header */}
      <div className="mb-8">
        <p className="text-[var(--text-tertiary)] text-xs uppercase tracking-widest mb-1">Create</p>
        <h2 className="text-2xl font-semibold text-[var(--text-primary)] tracking-tight">New Idea</h2>
      </div>

      <form onSubmit={handleSubmit} className="space-y-6">
        {/* Idea Input */}
        <div className="glass rounded-xl p-1">
          <textarea
            value={idea}
            onChange={(e) => setIdea(e.target.value)}
            placeholder="Describe your product idea..."
            rows={5}
            className="w-full px-4 py-3 bg-transparent text-[var(--text-primary)] placeholder-[var(--text-tertiary)] resize-none focus:outline-none text-sm"
          />
        </div>

        {/* Options */}
        <div className="flex items-center gap-6">
          <div className="flex items-center gap-2">
            <span className="text-xs text-[var(--text-tertiary)]">Iterations</span>
            <input
              type="number"
              value={maxIterations}
              onChange={(e) => setMaxIterations(Number(e.target.value))}
              min={1}
              max={100}
              className="w-16 px-2 py-1 glass rounded-lg text-sm text-[var(--text-primary)] bg-transparent focus:outline-none focus:border-accent-500"
            />
          </div>

          <label className="flex items-center gap-2 cursor-pointer">
            <input
              type="checkbox"
              checked={dryRun}
              onChange={(e) => setDryRun(e.target.checked)}
              className="w-4 h-4 rounded border-[var(--border-color)] bg-transparent text-accent-500 focus:ring-0 focus:ring-offset-0"
            />
            <span className="text-xs text-[var(--text-tertiary)]">Dry run</span>
          </label>
        </div>

        {/* Message */}
        {message && (
          <div className={`text-sm ${message.type === 'success' ? 'text-emerald-400' : 'text-red-400'}`}>
            {message.text}
          </div>
        )}

        {/* Submit */}
        <button
          type="submit"
          disabled={isSubmitting || !idea.trim()}
          className="w-full flex items-center justify-center gap-2 px-4 py-3 bg-gradient-to-r from-accent-500 to-accent-600 text-white text-sm font-medium rounded-xl hover:from-accent-600 hover:to-accent-700 disabled:opacity-50 disabled:cursor-not-allowed transition-all glow"
        >
          {isSubmitting ? (
            <Loader2 className="w-4 h-4 animate-spin" />
          ) : (
            <>
              <Send className="w-4 h-4" />
              Submit
            </>
          )}
        </button>
      </form>

      {/* Examples */}
      <div className="mt-8">
        <p className="text-xs text-[var(--text-tertiary)] mb-3">Examples</p>
        <div className="flex flex-wrap gap-2">
          {examples.map((example, i) => (
            <button
              key={i}
              onClick={() => setIdea(example)}
              className="px-3 py-1.5 text-xs text-[var(--text-secondary)] glass rounded-lg hover:border-[var(--border-hover)] transition-all"
            >
              {example}
            </button>
          ))}
        </div>
      </div>
    </div>
  )
}
