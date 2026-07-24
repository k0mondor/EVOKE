import { create } from 'zustand'

interface PageMotionStore {
  scrollProgress: number
  applicationProgress: number
  setScrollProgress: (value: number) => void
  setApplicationProgress: (value: number) => void
}

export const usePageMotionStore = create<PageMotionStore>((set) => ({
  scrollProgress: 0,
  applicationProgress: 0,
  setScrollProgress: (value) =>
    set({
      scrollProgress: Math.max(0, Math.min(1, value)),
    }),
  setApplicationProgress: (value) =>
    set({
      applicationProgress: Math.max(0, Math.min(1, value)),
    }),
}))
