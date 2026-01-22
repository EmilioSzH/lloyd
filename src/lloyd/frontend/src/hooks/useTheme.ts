import { createContext, useContext, useEffect, useState } from 'react'

export type Theme = 'light' | 'dark' | 'system'
export type AccentColor = 'blue' | 'purple' | 'green' | 'orange' | 'pink'

interface ThemeContextType {
  theme: Theme
  accentColor: AccentColor
  resolvedTheme: 'light' | 'dark'
  setTheme: (theme: Theme) => void
  setAccentColor: (color: AccentColor) => void
}

export const ThemeContext = createContext<ThemeContextType | undefined>(undefined)

export function useTheme() {
  const context = useContext(ThemeContext)
  if (!context) {
    throw new Error('useTheme must be used within a ThemeProvider')
  }
  return context
}

export function useThemeProvider() {
  const [theme, setThemeState] = useState<Theme>(() => {
    const saved = localStorage.getItem('lloyd-theme')
    return (saved as Theme) || 'system'
  })

  const [accentColor, setAccentColorState] = useState<AccentColor>(() => {
    const saved = localStorage.getItem('lloyd-accent')
    return (saved as AccentColor) || 'blue'
  })

  const [resolvedTheme, setResolvedTheme] = useState<'light' | 'dark'>('light')

  useEffect(() => {
    const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)')

    const updateResolvedTheme = () => {
      if (theme === 'system') {
        setResolvedTheme(mediaQuery.matches ? 'dark' : 'light')
      } else {
        setResolvedTheme(theme)
      }
    }

    updateResolvedTheme()
    mediaQuery.addEventListener('change', updateResolvedTheme)

    return () => mediaQuery.removeEventListener('change', updateResolvedTheme)
  }, [theme])

  useEffect(() => {
    const root = document.documentElement
    root.classList.remove('light', 'dark')
    root.classList.add(resolvedTheme)
  }, [resolvedTheme])

  useEffect(() => {
    document.documentElement.setAttribute('data-accent', accentColor)
  }, [accentColor])

  const setTheme = (newTheme: Theme) => {
    setThemeState(newTheme)
    localStorage.setItem('lloyd-theme', newTheme)
  }

  const setAccentColor = (color: AccentColor) => {
    setAccentColorState(color)
    localStorage.setItem('lloyd-accent', color)
  }

  return {
    theme,
    accentColor,
    resolvedTheme,
    setTheme,
    setAccentColor,
  }
}
