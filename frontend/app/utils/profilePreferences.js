export const ACTIVE_PROFILE_KEY = "cealeg_active_profile";
export const LEGACY_PREFERENCES_KEY = "cealeg_preferences";

function getStoredUserId() {
  if (typeof window === "undefined") return null;

  try {
    const savedUser = window.localStorage.getItem("cealeg_user");
    const user = savedUser ? JSON.parse(savedUser) : null;
    return user?.id ? String(user.id) : null;
  } catch {
    return null;
  }
}

function normalizeStorageSegment(value) {
  return encodeURIComponent(String(value));
}

function getActiveProfileKey(userId = getStoredUserId()) {
  return userId ? `${ACTIVE_PROFILE_KEY}:${normalizeStorageSegment(userId)}` : null;
}

export function getActiveProfile() {
  if (typeof window === "undefined") return null;

  try {
    const storageKey = getActiveProfileKey();
    if (!storageKey) return null;

    const savedProfile = window.localStorage.getItem(storageKey);
    return savedProfile ? JSON.parse(savedProfile) : null;
  } catch {
    return null;
  }
}

export function getActiveProfileId() {
  return getActiveProfile()?.id || null;
}

export function getActiveProfilePayload() {
  const profileId = getActiveProfileId();
  return profileId ? { family_profile_id: profileId } : {};
}

export function setActiveProfile(profile) {
  if (typeof window === "undefined" || !profile) return;

  const storageKey = getActiveProfileKey();
  if (!storageKey) return;

  window.localStorage.setItem(storageKey, JSON.stringify(profile));
  window.dispatchEvent(new CustomEvent("cealeg:profile-change", { detail: profile }));
}

export function getPreferencesKey(profileId, userId = getStoredUserId()) {
  if (!userId) return null;

  const profileSegment = profileId ? normalizeStorageSegment(profileId) : "primary";
  return `${LEGACY_PREFERENCES_KEY}:${normalizeStorageSegment(userId)}:${profileSegment}`;
}

export function readProfilePreferences(profileId) {
  if (typeof window === "undefined") return null;

  const specificKey = getPreferencesKey(profileId);
  if (!specificKey) return null;

  const stored = window.localStorage.getItem(specificKey);

  if (!stored) return null;

  try {
    return JSON.parse(stored);
  } catch {
    return null;
  }
}

export function saveProfilePreferences(profileId, preferences) {
  if (typeof window === "undefined") return;

  const storageKey = getPreferencesKey(profileId);
  if (!storageKey) return;

  const payload = JSON.stringify(preferences);
  window.localStorage.setItem(storageKey, payload);
}

export function clearProfilePreferences(profileId) {
  if (typeof window === "undefined") return;

  const storageKey = getPreferencesKey(profileId);
  if (storageKey) window.localStorage.removeItem(storageKey);
}

export function clearUserProfileStorage(userId = getStoredUserId()) {
  if (typeof window === "undefined") return;

  if (userId) {
    const normalizedUserId = normalizeStorageSegment(userId);
    window.localStorage.removeItem(`${ACTIVE_PROFILE_KEY}:${normalizedUserId}`);

    const preferencesPrefix = `${LEGACY_PREFERENCES_KEY}:${normalizedUserId}:`;

    for (let index = window.localStorage.length - 1; index >= 0; index -= 1) {
      const key = window.localStorage.key(index);

      if (key?.startsWith(preferencesPrefix)) {
        window.localStorage.removeItem(key);
      }
    }
  }

  // Remove the pre-namespace keys left by older builds. They have no owner
  // information and therefore cannot be safely associated with a new login.
  const legacyPrefix = `${LEGACY_PREFERENCES_KEY}:`;

  for (let index = window.localStorage.length - 1; index >= 0; index -= 1) {
    const key = window.localStorage.key(index);
    const suffix = key?.startsWith(legacyPrefix) ? key.slice(legacyPrefix.length) : "";

    if (suffix && !suffix.includes(":")) {
      window.localStorage.removeItem(key);
    }
  }

  window.localStorage.removeItem(ACTIVE_PROFILE_KEY);
  window.localStorage.removeItem(LEGACY_PREFERENCES_KEY);
}
