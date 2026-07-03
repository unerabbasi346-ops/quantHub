// Governing specification: Doc 06 — UI/UX Design System (QH-006 v1.0) §Visual Language
//                          Doc 08 — Frontend Architecture (QH-008 v1.0)
// State Management: Zustand for lightweight client state — Doc 08 §State Management
// Doc 08 §State Management: keep local UI state isolated; avoid global state unless required
// Per Doc 00 §14.11
import { create } from 'zustand'

export type Theme = 'dark' | 'light'

const THEME_STORAGE_KEY = 'quant-hub-theme'

interface UIState {
  sidebarOpen: boolean
  toggleSidebar: () => void
  setSidebarOpen: (open: boolean) => void

  // Doc 06 §Visual Language: "Dark-first theme, optional light mode."
  theme: Theme
  toggleTheme: () => void
  setTheme: (theme: Theme) => void
}

function applyTheme(theme: Theme): void {
  if (typeof document === 'undefined') return
  document.documentElement.setAttribute('data-theme', theme)
  try {
    window.localStorage.setItem(THEME_STORAGE_KEY, theme)
  } catch {
    // localStorage unavailable (private mode, disabled) — theme still
    // applies for this session via the DOM attribute above; not persisted.
  }
}

// Zustand store: UI-only state, no server data — Doc 08 §State Management
export const useUIStore = create<UIState>((set) => ({
  sidebarOpen: true,
  toggleSidebar: () => set((state) => ({ sidebarOpen: !state.sidebarOpen })),
  setSidebarOpen: (open) => set({ sidebarOpen: open }),

  // Dark-first default (Doc 06); the blocking inline script in layout.tsx
  // sets the real initial DOM attribute from localStorage before paint —
  // this 'dark' is only the store's initial value for SSR/hydration.
  theme: 'dark',
  toggleTheme: () =>
    set((state) => {
      const next: Theme = state.theme === 'dark' ? 'light' : 'dark'
      applyTheme(next)
      return { theme: next }
    }),
  setTheme: (theme) => {
    applyTheme(theme)
    set({ theme })
  },
}))
