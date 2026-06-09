"use client";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api/v1";

const ACCESS_KEY = "miq.access_token";
const REFRESH_KEY = "miq.refresh_token";

export class ApiError extends Error {
  status: number;
  code: string;
  detail: string;
  constructor(opts: { status: number; code: string; title: string; detail: string }) {
    super(opts.title || opts.detail);
    this.status = opts.status;
    this.code = opts.code;
    this.detail = opts.detail;
  }
}

export function getAccessToken(): string | null {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem(ACCESS_KEY);
}

export function setTokens(access: string, refresh: string): void {
  if (typeof window === "undefined") return;
  window.localStorage.setItem(ACCESS_KEY, access);
  window.localStorage.setItem(REFRESH_KEY, refresh);
}

export function clearTokens(): void {
  if (typeof window === "undefined") return;
  window.localStorage.removeItem(ACCESS_KEY);
  window.localStorage.removeItem(REFRESH_KEY);
}

export function getRefreshToken(): string | null {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem(REFRESH_KEY);
}

interface RequestOptions {
  method?: string;
  body?: unknown;
  formData?: FormData;
  headers?: Record<string, string>;
  signal?: AbortSignal;
}

export async function apiRequest<T>(path: string, opts: RequestOptions = {}): Promise<T> {
  const headers: Record<string, string> = { Accept: "application/json", ...opts.headers };
  const token = getAccessToken();
  if (token) headers.Authorization = `Bearer ${token}`;
  let body: BodyInit | undefined;
  if (opts.formData) {
    body = opts.formData;
  } else if (opts.body !== undefined) {
    headers["Content-Type"] = "application/json";
    body = JSON.stringify(opts.body);
  }
  const resp = await fetch(`${API_BASE}${path}`, {
    method: opts.method ?? (opts.body || opts.formData ? "POST" : "GET"),
    headers,
    body,
    signal: opts.signal,
    cache: "no-store",
  });
  if (resp.status === 204) return undefined as unknown as T;
  const text = await resp.text();
  const data = text ? JSON.parse(text) : null;
  if (!resp.ok) {
    throw new ApiError({
      status: resp.status,
      code: data?.code ?? `http.${resp.status}`,
      title: data?.title ?? "Request failed",
      detail: data?.detail ?? text,
    });
  }
  return data as T;
}
