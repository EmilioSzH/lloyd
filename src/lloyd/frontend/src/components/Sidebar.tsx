import {
  LayoutDashboard,
  Lightbulb,
  ListTodo,
  ScrollText,
  Settings as SettingsIcon,
  HelpCircle,
} from 'lucide-react'
import { ThemeSelector } from './ThemeSelector'

type View = 'dashboard' | 'idea' | 'tasks' | 'progress' | 'settings' | 'guide'

interface SidebarProps {
  currentView: View
  onViewChange: (view: View) => void
  isConnected: boolean
}

const navItems = [
  { id: 'dashboard' as View, label: 'Dashboard', icon: LayoutDashboard },
  { id: 'idea' as View, label: 'New Idea', icon: Lightbulb },
  { id: 'tasks' as View, label: 'Tasks', icon: ListTodo },
  { id: 'progress' as View, label: 'Progress', icon: ScrollText },
  { id: 'settings' as View, label: 'Settings', icon: SettingsIcon },
  { id: 'guide' as View, label: 'How to Use', icon: HelpCircle },
]

export function Sidebar({ currentView, onViewChange, isConnected }: SidebarProps) {
  return (
    <aside className="w-56 h-screen sticky top-0 flex flex-col glass border-r border-[var(--border-color)]">
      {/* Logo */}
      <div className="p-6">
        <div className="flex items-center gap-3">
          <div className="relative">
            <div className="w-9 h-9 bg-gradient-to-br from-accent-400 to-accent-600 rounded-lg flex items-center justify-center animate-pulse-glow">
              <span className="text-white font-semibold text-lg">L</span>
            </div>
            {/* Connection indicator */}
            <div className={`absolute -bottom-0.5 -right-0.5 w-2.5 h-2.5 rounded-full border-2 border-[var(--bg-base)] ${
              isConnected ? 'bg-emerald-400' : 'bg-zinc-400'
            }`} />
          </div>
          <div>
            <h1 className="font-semibold text-[var(--text-primary)] tracking-tight">Lloyd</h1>
            <p className="text-[10px] text-[var(--text-tertiary)] uppercase tracking-widest">AI Assistant</p>
          </div>
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 px-3">
        <ul className="space-y-1">
          {navItems.map((item) => {
            const Icon = item.icon
            const isActive = currentView === item.id
            return (
              <li key={item.id}>
                <button
                  onClick={() => onViewChange(item.id)}
                  className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg transition-all duration-200 ${
                    isActive
                      ? 'bg-accent-500/10 text-accent-500'
                      : 'text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:bg-[var(--border-color)]'
                  }`}
                >
                  <Icon className="w-4 h-4" strokeWidth={isActive ? 2.5 : 2} />
                  <span className={`text-sm ${isActive ? 'font-medium' : ''}`}>{item.label}</span>
                </button>
              </li>
            )
          })}
        </ul>
      </nav>

      {/* Theme Selector */}
      <ThemeSelector />
    </aside>
  )
}
