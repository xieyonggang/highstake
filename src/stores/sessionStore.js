import { create } from 'zustand';

export const useSessionStore = create((set) => ({
  phase: 'setup',
  sessionId: null,
  config: {
    interaction: '',
    intensity: '',
    agents: ['skeptic', 'analyst', 'contrarian'],
  },
  deckManifest: null,

  setConfig: (config) => set({ config }),
  updateConfig: (partial) =>
    set((state) => ({ config: { ...state.config, ...partial } })),
  setDeckManifest: (manifest) => set({ deckManifest: manifest }),
  setSessionId: (id) => set({ sessionId: id }),
  setPhase: (phase) => set({ phase }),

  reset: () =>
    set({
      phase: 'setup',
      sessionId: null,
      config: { interaction: '', intensity: '', agents: ['skeptic', 'analyst', 'contrarian'] },
      deckManifest: null,
    }),
}));
