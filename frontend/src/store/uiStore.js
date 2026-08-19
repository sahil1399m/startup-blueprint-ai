import { create } from 'zustand'

let toastId = 0

export const useUIStore = create((set) => ({
  sidebarOpen: false,
  activeModal: null,
  toasts: [],

  toggleSidebar: () => set((s) => ({ sidebarOpen: !s.sidebarOpen })),
  setSidebar: (open) => set({ sidebarOpen: open }),

  setModal: (name) => set({ activeModal: name }),
  closeModal: () => set({ activeModal: null }),

  addToast: (message, type = 'info') => {
    const id = ++toastId
    set((s) => ({
      toasts: [...s.toasts, { id, message, type }],
    }))
    // Auto-remove after 4 seconds
    setTimeout(() => {
      set((s) => ({
        toasts: s.toasts.filter((t) => t.id !== id),
      }))
    }, 4000)
    return id
  },

  removeToast: (id) =>
    set((s) => ({
      toasts: s.toasts.filter((t) => t.id !== id),
    })),
}))
