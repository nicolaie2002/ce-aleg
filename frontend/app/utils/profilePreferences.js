export const ACTIVE_PROFILE_KEY = "cealeg_active_profile";
export const LEGACY_PREFERENCES_KEY = "cealeg_preferences";

export function getActiveProfile() {
  if (typeof window === "undefined") return null;

  try {
    const savedProfile = window.localStorage.getItem(ACTIVE_PROFILE_KEY);
    return savedProfile ? JSON.parse(savedProfile) : null;
  } catch {
    return null;
  }
}

export function setActiveProfile(profile) {
  if (typeof window === "undefined" || !profile) return;

  window.localStorage.setItem(ACTIVE_PROFILE_KEY, JSON.stringify(profile));
  window.dispatchEvent(new CustomEvent("cealeg:profile-change", { detail: profile }));
}

export function getPreferencesKey(profileId) {
  return profileId ? `${LEGACY_PREFERENCES_KEY}:${profileId}` : LEGACY_PREFERENCES_KEY;
}

export function readProfilePreferences(profileId) {
  if (typeof window === "undefined") return null;

  const specificKey = getPreferencesKey(profileId);
  const stored = window.localStorage.getItem(specificKey) || window.localStorage.getItem(LEGACY_PREFERENCES_KEY);

  if (!stored) return null;

  try {
    return JSON.parse(stored);
  } catch {
    return null;
  }
}

export function saveProfilePreferences(profileId, preferences) {
  if (typeof window === "undefined") return;

  const payload = JSON.stringify(preferences);
  window.localStorage.setItem(getPreferencesKey(profileId), payload);
  window.localStorage.setItem(LEGACY_PREFERENCES_KEY, payload);
}

export function clearProfilePreferences(profileId) {
  if (typeof window === "undefined") return;

  window.localStorage.removeItem(getPreferencesKey(profileId));
  window.localStorage.removeItem(LEGACY_PREFERENCES_KEY);
}
