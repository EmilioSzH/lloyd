import { useState } from 'react'
import {
  LayoutDashboard,
  Lightbulb,
  ListTodo,
  ScrollText,
  Settings as SettingsIcon,
  HelpCircle,
  Inbox,
  Sparkles,
  BookOpen,
  ChevronLeft,
  ChevronRight,
  Wrench,
  Puzzle,
  Palette,
} from 'lucide-react'
import { ThemeSelector } from './ThemeSelector'
import { LloydMascot } from './LloydMascot'

type View = 'dashboard' | 'idea' | 'tasks' | 'progress' | 'settings' | 'guide' | 'inbox' | 'brainstorm' | 'knowledge' | 'selfmod' | 'extensions' | 'appearance'

interface SidebarProps {
  currentView: View
  onViewChange: (view: View) => void
  isConnected: boolean
  currentStatus?: 'idle' | 'working' | 'thinking' | 'complete' | 'error'
}

const navItems = [
  { id: 'dashboard' as View, label: 'Dashboard', icon: LayoutDashboard },
  { id: 'idea' as View, label: 'New Idea', icon: Lightbulb },
  { id: 'inbox' as View, label: 'Inbox', icon: Inbox },
  { id: 'brainstorm' as View, label: 'Brainstorm', icon: Sparkles },
  { id: 'tasks' as View, label: 'Tasks', icon: ListTodo },
  { id: 'progress' as View, label: 'Progress', icon: ScrollText },
  { id: 'knowledge' as View, label: 'Knowledge', icon: BookOpen },
  { id: 'selfmod' as View, label: 'Self-Mod', icon: Wrench },
  { id: 'extensions' as View, label: 'Extensions', icon: Puzzle },
  { id: 'appearance' as View, label: 'Appearance', icon: Palette },
  { id: 'settings' as View, label: 'Settings', icon: SettingsIcon },
  { id: 'guide' as View, label: 'How to Use', icon: HelpCircle },
]

export function Sidebar({ currentView, onViewChange, isConnected, currentStatus = 'idle' }: SidebarProps) {
  const [collapsed, setCollapsed] = useState(false)

  return (
    <aside className={`${collapsed ? 'w-16' : 'w-64'} h-screen sticky top-0 flex flex-col glass border-r border-[var(--border-color)] transition-all duration-300`}>
      {/* Logo */}
      <div className={`p-4 ${collapsed ? 'px-3' : 'p-5'}`}>
        <div className="flex items-center gap-3">
          <div className="relative shrink-0">
            <div className="w-9 h-9 bg-gradient-to-br from-accent-400 to-accent-600 rounded-lg flex items-center justify-center animate-pulse-glow">
              <span className="text-white font-semibold text-lg">L</span>
            </div>
            {/* Connection indicator */}
            <div className={`absolute -bottom-0.5 -right-0.5 w-2.5 h-2.5 rounded-full border-2 border-[var(--bg-base)] ${
              isConnected ? 'bg-emerald-400' : 'bg-zinc-400'
            }`} />
          </div>
          {!collapsed && (
            <div className="overflow-hidden">
              <h1 className="font-semibold text-[var(--text-primary)] tracking-tight">Lloyd</h1>
              <p className="text-[10px] text-[var(--text-tertiary)] uppercase tracking-widest">AI Assistant</p>
            </div>
          )}
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 px-2 overflow-y-auto">
        <ul className="space-y-0.5">
          {navItems.map((item) => {
            const Icon = item.icon
            const isActive = currentView === item.id
            return (
              <li key={item.id}>
                <button
                  onClick={() => onViewChange(item.id)}
                  title={collapsed ? item.label : undefined}
                  className={`w-full flex items-center gap-3 px-3 py-2 rounded-lg transition-all duration-200 ${
                    isActive
                      ? 'bg-accent-500/10 text-accent-500'
                      : 'text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:bg-[var(--border-color)]'
                  } ${collapsed ? 'justify-center' : ''}`}
                >
                  <Icon className="w-4 h-4 shrink-0" strokeWidth={isActive ? 2.5 : 2} />
                  {!collapsed && (
                    <span className={`text-sm truncate ${isActive ? 'font-medium' : ''}`}>{item.label}</span>
                  )}
                </button>
              </li>
            )
          })}
        </ul>
      </nav>

      {/* Lloyd Mascot Widget */}
      {!collapsed && (
        <div className="px-3 py-2">
          <div className="glass rounded-xl p-3 bg-gradient-to-br from-[var(--bg-card)] to-transparent">
            <LloydMascot
              size={100}
              status={currentStatus}
              className="mx-auto"
            />
          </div>
        </div>
      )}

      {/* Collapse Toggle */}
      <div className="px-2 py-2 border-t border-[var(--border-color)]">
        <button
          onClick={() => setCollapsed(!collapsed)}
          className="w-full flex items-center justify-center gap-2 px-3 py-2 text-[var(--text-tertiary)] hover:text-[var(--text-primary)] hover:bg-[var(--border-color)] rounded-lg transition-all"
        >
          {collapsed ? (
            <ChevronRight className="w-4 h-4" />
          ) : (
            <>
              <ChevronLeft className="w-4 h-4" />
              <span className="text-xs">Collapse</span>
            </>
          )}
        </button>
      </div>

      {/* Theme Selector */}
      {!collapsed && <ThemeSelector />}
    </aside>
  )
}
