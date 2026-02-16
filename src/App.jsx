import React from 'react';
import { useSessionStore } from './stores/sessionStore';
import SetupPhase from './components/SetupPhase';
import MeetingPhase from './components/MeetingPhase';
import ReviewPhase from './components/ReviewPhase';

export default function App() {
  const phase = useSessionStore((s) => s.phase);

  if (phase === 'setup') return <SetupPhase />;
  if (phase === 'meeting') return <MeetingPhase />;
  return <ReviewPhase />;
}
