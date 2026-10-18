/**
 * simulationSocket.js — Reusable WebSocket connection manager for WareBot AI.
 * Handles auto-reconnect with bounded exponential backoff, event dispatching,
 * and clean lifecycle management.
 */

import { API_BASE_URL } from './api';

function getWebSocketUrl() {
  if (import.meta.env.VITE_WS_URL) {
    return import.meta.env.VITE_WS_URL;
  }
  const base = API_BASE_URL.replace(/^http:/, 'ws:').replace(/^https:/, 'wss:');
  return `${base}/api/simulation/stream`;
}

export class SimulationSocket {
  constructor() {
    this.url = getWebSocketUrl();
    this.ws = null;
    this.status = 'offline'; // 'connecting' | 'connected' | 'reconnecting' | 'offline'
    this.messageHandlers = new Set();
    this.statusHandlers = new Set();
    this.reconnectAttempt = 0;
    this.reconnectTimer = null;
    this.maxReconnectDelayMs = 8000;
    this.intentionalClose = false;
  }

  /**
   * Register a message callback. Returns unsubscribe function.
   */
  onMessage(callback) {
    this.messageHandlers.add(callback);
    return () => this.messageHandlers.delete(callback);
  }

  /**
   * Register a status change callback. Returns unsubscribe function.
   */
  onStatusChange(callback) {
    this.statusHandlers.add(callback);
    callback(this.status);
    return () => this.statusHandlers.delete(callback);
  }

  _setStatus(newStatus) {
    if (this.status !== newStatus) {
      this.status = newStatus;
      this.statusHandlers.forEach(cb => {
        try {
          cb(newStatus);
        } catch (e) {
          console.error('[simulationSocket] status handler error:', e);
        }
      });
    }
  }

  /**
   * Initiate WebSocket connection.
   */
  connect() {
    if (this.ws && (this.ws.readyState === WebSocket.OPEN || this.ws.readyState === WebSocket.CONNECTING)) {
      return;
    }

    this.intentionalClose = false;
    this._setStatus(this.reconnectAttempt > 0 ? 'reconnecting' : 'connecting');

    try {
      this.ws = new WebSocket(this.url);

      this.ws.onopen = () => {
        this.reconnectAttempt = 0;
        this._setStatus('connected');
        console.info('[simulationSocket] WebSocket connected to', this.url);
      };

      this.ws.onmessage = event => {
        try {
          const payload = JSON.parse(event.data);
          this.messageHandlers.forEach(handler => {
            try {
              handler(payload);
            } catch (err) {
              console.error('[simulationSocket] message handler error:', err);
            }
          });
        } catch (err) {
          console.warn('[simulationSocket] Failed to parse message JSON:', event.data);
        }
      };

      this.ws.onclose = () => {
        this.ws = null;
        if (!this.intentionalClose) {
          this._scheduleReconnect();
        } else {
          this._setStatus('offline');
        }
      };

      this.ws.onerror = err => {
        console.warn('[simulationSocket] WebSocket connection error.');
        // onclose will automatically be triggered by browser
      };
    } catch (err) {
      console.warn('[simulationSocket] Failed to create WebSocket:', err);
      this._scheduleReconnect();
    }
  }

  _scheduleReconnect() {
    if (this.intentionalClose) return;

    this.reconnectAttempt++;
    // Exponential backoff with jitter: min(1000 * 2^(n-1), maxReconnectDelayMs)
    const baseDelay = Math.min(1000 * Math.pow(2, this.reconnectAttempt - 1), this.maxReconnectDelayMs);
    const jitter = Math.random() * 300;
    const delay = baseDelay + jitter;

    this._setStatus('reconnecting');
    console.info(`[simulationSocket] Reconnecting in ${Math.round(delay)}ms (attempt ${this.reconnectAttempt})...`);

    clearTimeout(this.reconnectTimer);
    this.reconnectTimer = setTimeout(() => {
      this.connect();
    }, delay);
  }

  /**
   * Send JSON message to backend.
   */
  send(message) {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(message));
    } else {
      console.warn('[simulationSocket] Cannot send message: socket not open.');
    }
  }

  /**
   * Cleanly disconnect.
   */
  disconnect() {
    this.intentionalClose = true;
    clearTimeout(this.reconnectTimer);
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
    this._setStatus('offline');
  }
}

// Global singleton instance
export const simulationSocket = new SimulationSocket();
