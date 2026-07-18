import { afterEach, describe, expect, it, vi } from 'vitest';

import { createHappyCleaningCoordinator } from './happyCleaningSync';


class FakeSocket {
  static instances = [];

  constructor(url) {
    this.url = url;
    this.readyState = 0;
    FakeSocket.instances.push(this);
  }

  open() {
    this.readyState = 1;
    this.onopen?.();
  }

  message(payload) {
    this.onmessage?.({ data: JSON.stringify(payload) });
  }

  close() {
    this.readyState = 3;
    this.onclose?.();
  }
}


describe('Happy Cleaning realtime coordinator', () => {
  afterEach(() => {
    vi.useRealTimers();
    FakeSocket.instances = [];
  });

  it('reconciles on connect and coalesces newer invalidations of the focused event', async () => {
    vi.useFakeTimers();
    let revision = 4;
    const refresh = vi.fn(async () => { revision = 8; });
    const coordinator = createHappyCleaningCoordinator({
      eventId: 7,
      getRevision: () => revision,
      refresh,
      WebSocketImpl: FakeSocket,
    });

    coordinator.start();
    FakeSocket.instances[0].open();
    await vi.runAllTicks();
    expect(refresh).toHaveBeenCalledTimes(1);

    FakeSocket.instances[0].message({ version: 1, event_id: 7, projection: 'assignments', revision: 9, invalidation_id: 'a', request_id: 'r1' });
    FakeSocket.instances[0].message({ version: 1, event_id: 7, projection: 'child_numbers', revision: 10, invalidation_id: 'b', request_id: 'r2' });
    FakeSocket.instances[0].message({ version: 1, event_id: 7, projection: 'todos', revision: 11, invalidation_id: 'todo', request_id: 'r-todo' });
    FakeSocket.instances[0].message({ version: 1, event_id: 8, projection: 'assignments', revision: 99, invalidation_id: 'c', request_id: 'r3' });
    await vi.advanceTimersByTimeAsync(0);

    expect(refresh).toHaveBeenCalledTimes(2);
    coordinator.stop();
  });

  it('reports disconnection, polls only while visible and focused, gates writes, and cleans up', async () => {
    vi.useFakeTimers();
    const documentImpl = { visibilityState: 'visible', hasFocus: () => true };
    const states = [];
    const refresh = vi.fn().mockResolvedValue(undefined);
    const coordinator = createHappyCleaningCoordinator({
      eventId: 7,
      getRevision: () => 4,
      refresh,
      onState: state => states.push(state),
      WebSocketImpl: FakeSocket,
      documentImpl,
      pollInterval: 1500,
      reconnectDelay: 5000,
    });

    coordinator.start();
    expect(coordinator.canWrite()).toBe(false);
    FakeSocket.instances[0].open();
    await vi.runAllTicks();
    expect(coordinator.canWrite()).toBe(true);
    FakeSocket.instances[0].close();
    expect(states.at(-1).connection).toBe('disconnected');
    expect(coordinator.canWrite()).toBe(false);

    await vi.advanceTimersByTimeAsync(1500);
    expect(refresh).toHaveBeenCalledTimes(2);
    expect(coordinator.state()).toMatchObject({
      connection: 'disconnected',
      httpAvailable: true,
      fresh: true,
    });
    expect(coordinator.canWrite()).toBe(true);
    documentImpl.visibilityState = 'hidden';
    await vi.advanceTimersByTimeAsync(1500);
    expect(refresh).toHaveBeenCalledTimes(2);

    coordinator.stop();
    const count = FakeSocket.instances.length;
    await vi.advanceTimersByTimeAsync(5000);
    expect(FakeSocket.instances).toHaveLength(count);
  });

  it('marks HTTP failure unavailable until a later focused snapshot succeeds', async () => {
    const refresh = vi.fn()
      .mockRejectedValueOnce(new Error('offline'))
      .mockResolvedValueOnce(undefined);
    const states = [];
    const coordinator = createHappyCleaningCoordinator({
      eventId: 7,
      getRevision: () => 4,
      refresh,
      onState: state => states.push(state),
      WebSocketImpl: FakeSocket,
    });

    coordinator.start();
    FakeSocket.instances[0].open();
    await vi.waitFor(() => expect(states.at(-1).httpAvailable).toBe(false));
    expect(coordinator.canWrite()).toBe(false);
    await coordinator.reconcile();
    expect(states.at(-1).httpAvailable).toBe(true);
    expect(coordinator.canWrite()).toBe(true);
    coordinator.stop();
  });
});
