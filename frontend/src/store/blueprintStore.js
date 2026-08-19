import { create } from 'zustand'

export const useBlueprintStore = create((set) => ({
  // Current blueprint output
  current:     null,
  // Generation state
  generating:  false,
  progress:    0,
  currentStep: '',
  currentNode: '',
  error:       null,
  // Abort controller for cancellation
  abortCtrl:   null,

  setGenerating: (generating) => set({ generating }),
  setProgress:   (progress, step, node) => set({ progress, currentStep: step, currentNode: node }),
  setError:      (error)      => set({ error, generating: false }),
  setBlueprint:  (blueprint)  => set({ current: blueprint, generating: false, progress: 100, error: null }),
  setAbortCtrl:  (ctrl)       => set({ abortCtrl: ctrl }),

  reset: () => set({
    generating: false, progress: 0,
    currentStep: '', currentNode: '', error: null,
  }),

  abort: () => set((s) => {
    s.abortCtrl?.abort()
    return { generating: false, progress: 0, currentStep: '', error: 'Cancelled' }
  }),
}))