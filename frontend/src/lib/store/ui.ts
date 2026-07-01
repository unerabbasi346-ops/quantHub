// Governing specification: Doc 08 — Frontend Architecture (QH-008 v1.0)
// State Management: Zustand for lightweight client state — Doc 08 §State Management
// Doc 08 §State Management: keep local UI state isolated; avoid global state unless required
// Per Doc 00 §14.11
import { create } from 'zustand'

interface UIState {
  sidebarOpen: boolean
  toggleSidebar: () => void
  setSidebarOpen: (open: boolean) => void
}

// Zustand store: UI-only state, no server data — Doc 08 §State Management
export const useUIStore = create<UIState>((set) => ({
  sidebarOpen: true,
  toggleSidebar: () => set((state) => ({ sidebarOpen: !state.sidebarOpen })),
  setSidebarOpen: (open) => set({ sidebarOpen: open }),
}))
