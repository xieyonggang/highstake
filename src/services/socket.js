import { io } from 'socket.io-client';

let socket = null;

export function getSocket() {
  if (!socket) {
    socket = io('/', {
      transports: ['websocket'],
      autoConnect: false,
    });
  }
  return socket;
}

export function connectSocket(sessionId) {
  const s = getSocket();
  s.auth = { sessionId };
  s.connect();
  return s;
}

export function disconnectSocket() {
  if (socket) {
    socket.disconnect();
    socket = null;
  }
}
