import React, { createContext, useContext, useEffect, useMemo, useState } from 'react'

export type ThemeMode = 'dark' | 'light' | 'system'
export type ResolvedTheme = 'dark' | 'light'

const STORAGE_KEY = 'themeMode'

function safeGetStoredMode(): ThemeMode {
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY)
    if (raw === 'dark' || raw === 'light' || raw === 'system') return raw
  } catch {
    // ignore
  }
  return 'system'
}

function safeStoreMode(mode: ThemeMode) {
  try {
    window.localStorage.setItem(STORAGE_KEY, mode)
  } catch {
    // ignore
  }
}

function getSystemTheme(): ResolvedTheme {
  if (typeof window === 'undefined') return 'dark'
  return window.matchMedia && window.matchMedia('(prefers-color-scheme: light)').matches ? 'light' : 'dark'
}

function applyThemeAttr(resolved: ResolvedTheme) {
  document.documentElement.dataset.theme = resolved
}

type ThemeContextValue = {
  mode: ThemeMode
  resolved: ResolvedTheme
  setMode: (mode: ThemeMode) => void
}

const ThemeContext = createContext<ThemeContextValue | null>(null)

export function ThemeProvider({ children }: { children: React.ReactNode }) {
  const [mode, setModeState] = useState<ThemeMode>(() => safeGetStoredMode())
  const [resolved, setResolved] = useState<ResolvedTheme>(() => (mode === 'system' ? getSystemTheme() : mode))

  useEffect(() => {
    const nextResolved: ResolvedTheme = mode === 'system' ? getSystemTheme() : mode
    setResolved(nextResolved)
    applyThemeAttr(nextResolved)
    safeStoreMode(mode)
  }, [mode])

  useEffect(() => {
    if (mode !== 'system') return
    const mql = window.matchMedia('(prefers-color-scheme: light)')
    const onChange = () => {
      const next = getSystemTheme()
      setResolved(next)
      applyThemeAttr(next)
    }
    onChange()
    if (typeof mql.addEventListener === 'function') {
      mql.addEventListener('change', onChange)
      return () => mql.removeEventListener('change', onChange)
    }
    // eslint-disable-next-line deprecation/deprecation
    mql.addListener(onChange)
    // eslint-disable-next-line deprecation/deprecation
    return () => mql.removeListener(onChange)
  }, [mode])

  const value = useMemo<ThemeContextValue>(() => ({ mode, resolved, setMode: setModeState }), [mode, resolved])

  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>
}

export function useTheme() {
  const ctx = useContext(ThemeContext)
  if (!ctx) throw new Error('useTheme must be used within ThemeProvider')
  return ctx
}

