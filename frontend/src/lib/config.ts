/**
 * Centralized API & WebSocket Configuration
 * Solves hardcoded localhost references across all frontend routes (Fix #3).
 */

export const API_URL =
  process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";

export const WS_URL =
  process.env.NEXT_PUBLIC_WS_URL ||
  (API_URL.startsWith("https")
    ? API_URL.replace(/^https/, "wss")
    : API_URL.replace(/^http/, "ws")) + "/ws/telemetry";

export const VFD_SETPOINT_TOKEN =
  process.env.NEXT_PUBLIC_SETPOINT_TOKEN || "sih-26120-sec-token-baghewala";
