const BASE = '/api';

async function request(path, options = {}) {
  const url = `${BASE}${path}`;
  const res = await fetch(url, {
    headers: { 'Content-Type': 'application/json', ...options.headers },
    ...options,
  });
  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(error.detail || `Request failed: ${res.status}`);
  }
  if (res.status === 204) return null;
  return res.json();
}

// Sessions
export async function createSession(config) {
  return request('/sessions/', {
    method: 'POST',
    body: JSON.stringify({
      interaction_mode: config.interaction,
      intensity: config.intensity,
      agents: config.agents,
      deck_id: config.deckId || null,
    }),
  });
}

export async function getSession(sessionId) {
  return request(`/sessions/${sessionId}`);
}

export async function updateSession(sessionId, data) {
  return request(`/sessions/${sessionId}`, {
    method: 'PATCH',
    body: JSON.stringify(data),
  });
}

export async function uploadRecording(sessionId, blob) {
  const formData = new FormData();
  formData.append('recording', blob, `session_${sessionId}.webm`);
  const res = await fetch(`${BASE}/sessions/${sessionId}/recording`, {
    method: 'POST',
    body: formData,
  });
  if (!res.ok) throw new Error('Failed to upload recording');
  return res.json();
}

// Decks
export async function uploadDeck(file, sessionId) {
  const formData = new FormData();
  formData.append('file', file);
  const url = sessionId
    ? `${BASE}/decks/upload?session_id=${sessionId}`
    : `${BASE}/decks/upload`;
  const res = await fetch(url, {
    method: 'POST',
    body: formData,
  });
  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(error.detail || 'Failed to upload deck');
  }
  return res.json();
}

export async function getDeck(deckId) {
  return request(`/decks/${deckId}`);
}

// Debrief
export async function getDebrief(sessionId) {
  return request(`/sessions/${sessionId}/debrief`);
}

export async function getTranscript(sessionId) {
  return request(`/sessions/${sessionId}/transcript`);
}

export async function getRecordingUrl(sessionId) {
  return request(`/sessions/${sessionId}/recording`);
}
