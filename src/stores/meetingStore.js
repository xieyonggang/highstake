import { create } from 'zustand';

export const useMeetingStore = create((set) => ({
  currentSlide: 0,
  transcript: [],
  messages: [],
  activeSpeaker: null,
  handsRaised: [],
  sessionState: 'ready',
  exchangeState: null, // {state: 'exchange'|'presenting'|'resolving', agentId?, exchangeId?}
  exchangeTurnInfo: null, // {turnNumber: 1, maxTurns: 3}
  thinkingAgents: [], // agentId strings currently "thinking"
  elapsedTime: 0,
  isRecording: false,
  isMuted: false,
  isCameraOn: true,

  addTranscriptSegment: (segment) =>
    set((state) => {
      if (segment.is_final || segment.isFinal) {
        return {
          transcript: [...state.transcript.filter((t) => t.isFinal || t.is_final), segment],
        };
      }
      return {
        transcript: [...state.transcript.filter((t) => t.isFinal || t.is_final), segment],
      };
    }),

  addMessage: (message) =>
    set((state) => ({
      messages: [...state.messages, message],
    })),

  setActiveSpeaker: (agentId) => set({ activeSpeaker: agentId }),
  clearActiveSpeaker: () => set({ activeSpeaker: null }),
  setHandsRaised: (hands) => set({ handsRaised: hands }),
  addHandRaised: (agentId) =>
    set((state) => ({
      handsRaised: state.handsRaised.includes(agentId)
        ? state.handsRaised
        : [...state.handsRaised, agentId],
    })),
  removeHandRaised: (agentId) =>
    set((state) => ({
      handsRaised: state.handsRaised.filter((id) => id !== agentId),
    })),
  setCurrentSlide: (index) => set({ currentSlide: index }),
  setSessionState: (sessionState) => set({ sessionState }),
  setExchangeState: (exchangeState) => set({ exchangeState }),
  setExchangeTurnInfo: (info) => set({ exchangeTurnInfo: info }),
  addThinkingAgent: (agentId) =>
    set((state) => ({
      thinkingAgents: state.thinkingAgents.includes(agentId)
        ? state.thinkingAgents
        : [...state.thinkingAgents, agentId],
    })),
  removeThinkingAgent: (agentId) =>
    set((state) => ({
      thinkingAgents: state.thinkingAgents.filter((id) => id !== agentId),
    })),
  setElapsedTime: (time) => set({ elapsedTime: time }),
  incrementTime: () => set((state) => ({ elapsedTime: state.elapsedTime + 1 })),
  setIsRecording: (val) => set({ isRecording: val }),
  setIsMuted: (val) => set({ isMuted: val }),
  setIsCameraOn: (val) => set({ isCameraOn: val }),

  reset: () =>
    set({
      currentSlide: 0,
      transcript: [],
      messages: [],
      activeSpeaker: null,
      handsRaised: [],
      sessionState: 'ready',
      exchangeState: null,
      exchangeTurnInfo: null,
      thinkingAgents: [],
      elapsedTime: 0,
      isRecording: false,
      isMuted: false,
      isCameraOn: true,
    }),
}));
