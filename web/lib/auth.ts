"use client";

import { API_BASE } from "./api";

export interface AuthUser {
  id: number;
  name: string;
  email: string;
  specialty: string;
}

const TOKEN_KEY = "oncoflow_token";
const USER_KEY = "oncoflow_user";

export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(TOKEN_KEY);
}

export function getUser(): AuthUser | null {
  if (typeof window === "undefined") return null;
  const raw = localStorage.getItem(USER_KEY);
  return raw ? (JSON.parse(raw) as AuthUser) : null;
}

export function isAuthed(): boolean {
  return !!getToken();
}

function persist(token: string, user: AuthUser) {
  localStorage.setItem(TOKEN_KEY, token);
  localStorage.setItem(USER_KEY, JSON.stringify(user));
}

async function post(path: string, body: unknown) {
  const res = await fetch(`${API_BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    throw new Error(data?.detail || "Request failed");
  }
  return data as { token: string; user: AuthUser };
}

export async function login(email: string, password: string): Promise<AuthUser> {
  const { token, user } = await post("/api/auth/login", { email, password });
  persist(token, user);
  return user;
}

export async function register(
  name: string,
  email: string,
  password: string,
  specialty: string
): Promise<AuthUser> {
  const { token, user } = await post("/api/auth/register", {
    name,
    email,
    password,
    specialty,
  });
  persist(token, user);
  return user;
}

export function logout() {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(USER_KEY);
}

export const DEMO_EMAIL = "kiran@oncoflow.health";
export const DEMO_PASSWORD = "oncoflow";
