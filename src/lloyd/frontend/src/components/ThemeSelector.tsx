import { Sun, Moon, Monitor } from 'lucide-react'
import { useTheme, Theme, AccentColor } from '../hooks/useTheme'

const themes: { id: Theme; icon: typeof Sun }[] = [
  { id: 'light', icon: Sun },
  { id: 'dark', icon: Moon },
  { id: 'system', icon: Monitor },
]

const accentColors: { id: AccentColor; color: string }[] = [
  { id: 'blue', color: '#0ea5e9' },
  { id: 'purple', color: '#a855f7' },
  { id: 'green', color: '#22c55e' },
  { id: 'orange', color: '#f97316' },
  { id: 'pink', color: '#ec4899' },
]

export function ThemeSelector() {
  const { theme, accentColor, setTheme, setAccentColor } = useTheme()

  return (
    <div className="p-4 border-t border-[var(--border-color)]">
      {/* Theme Mode */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex gap-1 p-1 rounded-lg bg-[var(--border-color)]">
          {themes.map(({ id, icon: Icon }) => (
            <button
              key={id}
              onClick={() => setTheme(id)}
              className={`p-1.5 rounded-md transition-all ${
                theme === id
                  ? 'bg-[var(--bg-elevated)] text-accent-500 shadow-sm'
                  : 'text-[var(--text-tertiary)] hover:text-[var(--text-secondary)]'
              }`}
            >
              <Icon className="w-3.5 h-3.5" />
            </button>
          ))}
        </div>
      </div>

      {/* Accent Color */}
      <div className="flex gap-1.5">
        {accentColors.map(({ id, color }) => (
          <button
            key={id}
            onClick={() => setAccentColor(id)}
            className={`w-5 h-5 rounded-full transition-all hover:scale-110 ${
              accentColor === id ? 'ring-2 ring-offset-2 ring-offset-[var(--bg-base)] ring-[var(--text-tertiary)]' : ''
            }`}
            style={{ backgroundColor: color }}
          />
        ))}
      </div>
    </div>
  )
}
