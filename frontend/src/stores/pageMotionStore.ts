import { create } from 'zustand'

interface PageMotionStore {
  applicationProgress: number
  setApplicationProgress: (value: number) => void
}

export const usePageMotionStore = create<PageMotionStore>((set) => ({
  applicationProgress: 0,
  setApplicationProgress: (value) =>
    set({
      applicationProgress: Math.max(0, Math.min(1, value)),
    }),
}))
