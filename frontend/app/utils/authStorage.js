import { useEffect, useRef, useState } from "react";
import { clearUserProfileStorage } from "./profilePreferences";

const USER_KEY = "cealeg_user";
const TRANSIENT_ACCOUNT_KEYS = [
  "cealeg_email_status",
  "cealeg_last_result",
  "cealeg_onboarding_completed",
  "cealeg_scan_store",
  "cealeg_stores",
];
const AUTH_QUERY_KEYS = [
  "token",
  "code",
  "access_token",
  "refresh_token",
  "id_token",
];

function parseStoredUser() {
  if (typeof window === "undefined") return null;

  try {
    const rawUser = window.localStorage.getItem(USER_KEY);
    return rawUser ? JSON.parse(rawUser) : null;
  } catch {
    return null;
  }
}

function removePrefixedSessionStorage() {
  if (typeof window === "undefined") return;

  for (let index = window.sessionStorage.length - 1; index >= 0; index -= 1) {
    const key = window.sessionStorage.key(index);

    if (key?.startsWith("cealeg_")) {
      window.sessionStorage.removeItem(key);
    }
  }
}

export function storeAuthenticatedUser(user) {
  if (typeof window === "undefined" || !user?.id) return;

  const previousUser = parseStoredUser();

  if (previousUser?.id && String(previousUser.id) !== String(user.id)) {
    clearUserProfileStorage(previousUser.id);
    TRANSIENT_ACCOUNT_KEYS.forEach((key) => window.localStorage.removeItem(key));
    removePrefixedSessionStorage();
  }

  window.localStorage.setItem(USER_KEY, JSON.stringify(user));

  const analyticsChoice = window.localStorage.getItem("cealeg_analytics_consent");
  if (analyticsChoice === "accepted" || analyticsChoice === "declined") {
    fetch("/api/backend/account/consent", {
      method: "POST",
      credentials: "include",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ analytics: analyticsChoice === "accepted" }),
      keepalive: true,
    }).catch(() => {});
  }
}

export function clearAuthenticatedSession() {
  if (typeof window === "undefined") return;

  const user = parseStoredUser();

  if (user?.id) {
    clearUserProfileStorage(user.id);
  } else {
    clearUserProfileStorage(null);
  }

  window.localStorage.removeItem(USER_KEY);
  TRANSIENT_ACCOUNT_KEYS.forEach((key) => window.localStorage.removeItem(key));
  removePrefixedSessionStorage();
}

export function consumeAuthTokenFromLocation(parameterName = "token") {
  if (typeof window === "undefined") return "";

  const url = new URL(window.location.href);
  let token = url.searchParams.get(parameterName) || "";
  let changed = false;

  AUTH_QUERY_KEYS.forEach((key) => {
    if (url.searchParams.has(key)) {
      url.searchParams.delete(key);
      changed = true;
    }
  });

  if (url.hash) {
    const hashParams = new URLSearchParams(url.hash.slice(1));
    let hashChanged = false;

    if (!token) {
      token = hashParams.get(parameterName) || "";
    }

    AUTH_QUERY_KEYS.forEach((key) => {
      if (hashParams.has(key)) {
        hashParams.delete(key);
        hashChanged = true;
      }
    });

    if (hashChanged) {
      const nextHash = hashParams.toString();
      url.hash = nextHash ? `#${nextHash}` : "";
      changed = true;
    }
  }

  if (changed) {
    const cleanUrl = `${url.pathname}${url.search}${url.hash}`;
    window.history.replaceState(window.history.state, "", cleanUrl);
  }

  return token;
}

export function useConsumedAuthToken(parameterName = "token") {
  const capturedTokenRef = useRef(undefined);
  const [token, setToken] = useState(null);

  useEffect(() => {
    let isActive = true;

    if (capturedTokenRef.current === undefined) {
      capturedTokenRef.current = consumeAuthTokenFromLocation(parameterName);
    }

    const capturedToken = capturedTokenRef.current;
    queueMicrotask(() => {
      if (isActive) setToken(capturedToken);
    });

    return () => {
      isActive = false;
    };
  }, [parameterName]);

  return token;
}
