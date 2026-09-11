const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";
const TOKEN_STORAGE_KEY = "peblo_cms_token";

// In-memory token is the source of truth for the running session; sessionStorage is only
// so a page refresh doesn't force a re-login. sessionStorage (not localStorage) clears when
// the tab closes — a reasonable middle ground given this is a take-home, not a bank.
let inMemoryToken: string | null = sessionStorage.getItem(TOKEN_STORAGE_KEY);

// setToken() is called from outside React (mutation callbacks), so plain module state
// wouldn't trigger a re-render anywhere — AuthContext subscribes here to turn a token
// change into a React state update, otherwise login/logout never propagate to the UI.
const listeners = new Set<(token: string | null) => void>();

export function getToken(): string | null {
  return inMemoryToken;
}

export function setToken(token: string | null): void {
  inMemoryToken = token;
  if (token) sessionStorage.setItem(TOKEN_STORAGE_KEY, token);
  else sessionStorage.removeItem(TOKEN_STORAGE_KEY);
  listeners.forEach((fn) => fn(token));
}

export function subscribeToken(fn: (token: string | null) => void): () => void {
  listeners.add(fn);
  return () => listeners.delete(fn);
}

export interface FieldError {
  field: string;
  code: string;
  message: string;
}

export class ApiError extends Error {
  status: number;
  fieldErrors: FieldError[];

  constructor(status: number, fieldErrors: FieldError[], message: string) {
    super(message);
    this.status = status;
    this.fieldErrors = fieldErrors;
  }
}

interface ApiFetchOptions extends RequestInit {
  skipAuth?: boolean;
}

export async function apiFetch<T>(path: string, options: ApiFetchOptions = {}): Promise<T> {
  const headers = new Headers(options.headers);
  const token = getToken();
  if (token && !options.skipAuth) headers.set("Authorization", `Bearer ${token}`);
  if (options.body && !(options.body instanceof FormData) && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }

  const resp = await fetch(`${API_BASE}${path}`, { ...options, headers });

  if (resp.status === 204) return undefined as T;

  const text = await resp.text();
  const data = text ? JSON.parse(text) : {};

  if (!resp.ok) {
    const fieldErrors: FieldError[] = data.errors ?? [];
    const message = fieldErrors[0]?.message ?? data.detail ?? `Request failed (${resp.status})`;
    throw new ApiError(resp.status, fieldErrors, message);
  }

  return data as T;
}

export function apiUrl(path: string): string {
  return `${API_BASE}${path}`;
}
