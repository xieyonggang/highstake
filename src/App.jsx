import React, { useState } from 'react';
import SetupPhase from './components/SetupPhase';
import MeetingPhase from './components/MeetingPhase';
import ReviewPhase from './components/ReviewPhase';

export default function App() {
  const [phase, setPhase] = useState('setup');
  const [config, setConfig] = useState({
    interaction: '',
    intensity: '',
    focuses: [],
  });
  const [sessionData, setSessionData] = useState(null);

  if (phase === 'setup') {
    return (
      <SetupPhase
        config={config}
        setConfig={setConfig}
        onStart={() => setPhase('meeting')}
      />
    );
  }

  if (phase === 'meeting') {
    return (
      <MeetingPhase
        config={config}
        onEnd={(data) => {
          setSessionData(data);
          setPhase('review');
        }}
      />
    );
  }

  return (
    <ReviewPhase
      sessionData={sessionData}
      onRestart={() => {
        setPhase('setup');
        setConfig({ interaction: '', intensity: '', focuses: [] });
        setSessionData(null);
      }}
    />
  );
}
