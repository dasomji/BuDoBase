import { useEffect, useRef, useState } from 'react';

const allowedProjections = new Set(['assignments', 'child_numbers', 'todos']);

const initialState = {
  connection: 'connecting',
  httpAvailable: true,
  fresh: false,
};

export function createHappyCleaningCoordinator({
  eventId,
  getRevision,
  refresh,
  onState = () => {},
  WebSocketImpl = globalThis.WebSocket,
  documentImpl = globalThis.document,
  locationImpl = globalThis.location,
  pollInterval = 1500,
  reconnectDelay = 1000,
}) {
  let state = { ...initialState };
  let socket = null;
  let stopped = true;
  let pollTimer = null;
  let reconnectTimer = null;
  let coalesceTimer = null;
  const seenInvalidations = new Set();

  const emit = patch => {
    state = { ...state, ...patch };
    onState({ ...state });
  };

  const focused = () => documentImpl?.visibilityState !== 'hidden'
    && (typeof documentImpl?.hasFocus !== 'function' || documentImpl.hasFocus());

  const reconcile = async () => {
    emit({ fresh: false });
    try {
      await refresh();
      emit({ httpAvailable: true, fresh: true });
      return true;
    } catch {
      emit({ httpAvailable: false, fresh: false });
      return false;
    }
  };

  const clearDisconnectedTimers = () => {
    if (pollTimer !== null) clearInterval(pollTimer);
    if (reconnectTimer !== null) clearTimeout(reconnectTimer);
    pollTimer = null;
    reconnectTimer = null;
  };

  const socketUrl = () => {
    const secure = locationImpl?.protocol === 'https:';
    const host = locationImpl?.host || 'testserver';
    return `${secure ? 'wss' : 'ws'}://${host}/ws/happy-cleaning/events/${eventId}/`;
  };

  const connect = () => {
    if (stopped || !WebSocketImpl) return;
    emit({ connection: 'connecting' });
    socket = new WebSocketImpl(socketUrl());
    socket.onopen = () => {
      if (stopped) return;
      clearDisconnectedTimers();
      emit({ connection: 'connected' });
      void reconcile();
    };
    socket.onmessage = message => {
      if (stopped) return;
      let envelope;
      try { envelope = JSON.parse(message.data); } catch { return; }
      if (
        envelope?.version !== 1
        || envelope.event_id !== eventId
        || !allowedProjections.has(envelope.projection)
        || !Number.isInteger(envelope.revision)
        || envelope.revision <= getRevision()
        || typeof envelope.invalidation_id !== 'string'
        || seenInvalidations.has(envelope.invalidation_id)
      ) return;
      seenInvalidations.add(envelope.invalidation_id);
      emit({ fresh: false });
      if (coalesceTimer === null) {
        coalesceTimer = setTimeout(() => {
          coalesceTimer = null;
          void reconcile();
        }, 0);
      }
    };
    socket.onclose = () => {
      if (stopped) return;
      emit({ connection: 'disconnected', fresh: false });
      clearDisconnectedTimers();
      pollTimer = setInterval(() => {
        if (focused()) void reconcile();
      }, pollInterval);
      reconnectTimer = setTimeout(connect, reconnectDelay);
    };
    socket.onerror = () => {
      if (socket?.readyState < 2) socket.close();
    };
  };

  return {
    start() {
      if (!stopped) return;
      stopped = false;
      onState({ ...state });
      connect();
    },
    stop() {
      if (stopped) return;
      stopped = true;
      clearDisconnectedTimers();
      if (coalesceTimer !== null) clearTimeout(coalesceTimer);
      coalesceTimer = null;
      const current = socket;
      socket = null;
      if (current && current.readyState < 2) current.close();
    },
    reconcile,
    canWrite() {
      return state.httpAvailable && state.fresh;
    },
    state() {
      return { ...state };
    },
  };
}

export function useHappyCleaningSync({
  enabled,
  eventId,
  revision,
  refresh,
  WebSocketImpl = globalThis.WebSocket,
}) {
  const refreshRef = useRef(refresh);
  const revisionRef = useRef(revision);
  const [state, setState] = useState({
    enabled: false,
    connection: 'connected',
    httpAvailable: true,
    fresh: true,
    writesEnabled: true,
  });
  refreshRef.current = refresh;
  revisionRef.current = revision;

  useEffect(() => {
    if (!enabled || !eventId) {
      setState({
        enabled: false,
        connection: 'connected',
        httpAvailable: true,
        fresh: true,
        writesEnabled: true,
      });
      return undefined;
    }
    let coordinator;
    coordinator = createHappyCleaningCoordinator({
      eventId: Number(eventId),
      getRevision: () => revisionRef.current || 0,
      refresh: () => refreshRef.current(),
      WebSocketImpl,
      onState: next => setState({
        enabled: true,
        ...next,
        writesEnabled: coordinator?.canWrite() || false,
      }),
    });
    coordinator.start();
    return () => coordinator.stop();
  }, [WebSocketImpl, enabled, eventId]);

  return state;
}
