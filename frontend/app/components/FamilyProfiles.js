"use client";

import { useCallback, useEffect, useId, useMemo, useState } from "react";
import Link from "next/link";
import { Crown, Plus, Trash2, UserRound, UsersRound } from "lucide-react";
import { API_URL } from "../config";
import { readApiJson } from "../utils/apiResponse";
import { getActiveProfile, setActiveProfile } from "../utils/profilePreferences";
import { InteractiveSurface } from "./InteractiveSurface";
import { useLocale } from "./LocaleProvider";

const PROFILE_COLORS = {
  teal: "from-teal-300 to-cyan-500",
  amber: "from-amber-200 to-orange-500",
  violet: "from-violet-300 to-fuchsia-500",
  rose: "from-rose-300 to-red-500",
  blue: "from-sky-300 to-blue-600",
};

const COLOR_OPTIONS = Object.keys(PROFILE_COLORS);

function profileInitials(name) {
  return String(name || "?")
    .trim()
    .split(/\s+/)
    .slice(0, 2)
    .map((part) => part[0])
    .join("")
    .toUpperCase();
}

export function FamilyProfiles({ compact = false }) {
  const { pick } = useLocale();
  const newNameId = useId();
  const colorGroupId = useId();
  const [profiles, setProfiles] = useState([]);
  const [activeProfile, setActiveProfileState] = useState(null);
  const [enabled, setEnabled] = useState(false);
  const [plan, setPlan] = useState("free");
  const [newName, setNewName] = useState("");
  const [newColor, setNewColor] = useState("teal");
  const [message, setMessage] = useState("");
  const [isLoading, setIsLoading] = useState(true);
  const [isCreating, setIsCreating] = useState(false);

  const canAddProfile = enabled && profiles.length < 5;
  const activeId = activeProfile?.id;

  const subtitle = useMemo(() => {
    if (enabled) {
      return pick(
        "Alege cine cumpără acum. Preferințele se păstrează separat pentru fiecare membru.",
        "Choose who is shopping now. Preferences stay separate for every member."
      );
    }

    return pick(
      "Planul Family deblocheaza profiluri separate pentru casa ta.",
      "Family unlocks separate profiles for your household."
    );
  }, [enabled, pick]);

  const loadProfiles = useCallback(async () => {
    try {
      const response = await fetch(`${API_URL}/family/profiles`);
      const data = await readApiJson(response);

      if (!response.ok) {
        throw new Error(data.error || pick("Profilurile nu au putut fi încărcate.", "Profiles could not be loaded."));
      }

      const loadedProfiles = data.profiles || [];
      const savedActiveProfile = getActiveProfile();
      const nextActive =
        loadedProfiles.find((profile) => profile.id === savedActiveProfile?.id) ||
        loadedProfiles.find((profile) => profile.isPrimary) ||
        loadedProfiles[0] ||
        null;

      setProfiles(loadedProfiles);
      setEnabled(Boolean(data.enabled));
      setPlan(data.plan || "free");

      if (nextActive) {
        setActiveProfileState(nextActive);
        setActiveProfile(nextActive);
      }
    } catch (error) {
      setMessage(error.message);
    } finally {
      setIsLoading(false);
    }
  }, [pick]);

  useEffect(() => {
    // Family profiles are external account state and must be loaded on mount.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void loadProfiles();
  }, [loadProfiles]);

  function selectProfile(profile) {
    setActiveProfileState(profile);
    setActiveProfile(profile);
  }

  async function createProfile(event) {
    event.preventDefault();
    if (!newName.trim()) return;

    setIsCreating(true);
    setMessage("");

    try {
      const response = await fetch(`${API_URL}/family/profiles`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name: newName, color: newColor, avatar: "user" }),
      });
      const data = await readApiJson(response);

      if (!response.ok) {
        throw new Error(data.error || pick("Profilul nu a putut fi creat.", "Profile could not be created."));
      }

      const createdProfile = data.profile;
      const nextProfiles = [...profiles, createdProfile];
      setProfiles(nextProfiles);
      selectProfile(createdProfile);
      setNewName("");
      setNewColor(COLOR_OPTIONS[nextProfiles.length % COLOR_OPTIONS.length]);
    } catch (error) {
      setMessage(error.message);
    } finally {
      setIsCreating(false);
    }
  }

  async function deleteProfile(profile) {
    if (!enabled || profile.isPrimary) return;

    setMessage("");

    try {
      const response = await fetch(`${API_URL}/family/profiles/${profile.id}`, {
        method: "DELETE",
      });
      const data = await readApiJson(response);

      if (!response.ok) {
        throw new Error(data.error || pick("Profilul nu a putut fi sters.", "Profile could not be deleted."));
      }

      const nextProfiles = profiles.filter((item) => item.id !== profile.id);
      setProfiles(nextProfiles);

      if (activeId === profile.id) {
        selectProfile(nextProfiles.find((item) => item.isPrimary) || nextProfiles[0]);
      }
    } catch (error) {
      setMessage(error.message);
    }
  }

  return (
    <InteractiveSurface
      as="section"
      aria-busy={isLoading || isCreating}
      className={`ce-family-panel rounded-2xl border p-5 shadow-2xl ${compact ? "" : "md:p-6"}`}
    >
      <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
        <div>
          <p className="flex items-center gap-2 text-sm font-black text-cyan-200">
            <UsersRound size={17} />
            {pick("Profiluri Family", "Family profiles")}
          </p>
          <h2 className="mt-2 text-2xl font-black">
            {pick("Cine face cumpărăturile?", "Who is shopping?")}
          </h2>
          <p className="mt-2 max-w-3xl text-sm leading-6 text-gray-300">{subtitle}</p>
        </div>

        <span className="inline-flex w-fit items-center gap-2 rounded-full border border-white/12 bg-white/[0.06] px-3 py-1.5 text-xs font-black uppercase text-gray-200">
          <Crown size={14} className={enabled ? "text-yellow-200" : "text-gray-500"} />
          {enabled ? "Family" : plan}
        </span>
      </div>

      <div
        className="mt-5 flex gap-3 overflow-x-auto pb-2"
        role="group"
        aria-label={pick("Alege profilul activ", "Choose the active profile")}
      >
        {isLoading ? (
          <div
            className="rounded-xl border border-white/10 bg-white/[0.04] px-4 py-5 text-sm text-gray-300"
            role="status"
            aria-live="polite"
          >
            {pick("Se încarcă profilurile...", "Loading profiles...")}
          </div>
        ) : (
          profiles.map((profile) => {
            const selected = activeId === profile.id;
            const gradient = PROFILE_COLORS[profile.color] || PROFILE_COLORS.teal;

            return (
              <div key={profile.id} className="group relative shrink-0">
                <button
                  type="button"
                  onClick={() => selectProfile(profile)}
                  aria-pressed={selected}
                  aria-label={`${profile.name}${selected ? `, ${pick("profil activ", "active profile")}` : ""}`}
                  className={`flex w-28 flex-col items-center gap-3 rounded-2xl border p-3 text-center transition hover:-translate-y-1 ${
                    selected
                      ? "border-cyan-200 bg-cyan-300/12 shadow-[0_0_32px_rgba(103,232,249,.18)]"
                      : "border-white/10 bg-white/[0.035] hover:border-white/25"
                  }`}
                >
                  <span className={`flex h-16 w-16 items-center justify-center rounded-2xl bg-gradient-to-br ${gradient} text-xl font-black text-black shadow-xl`}>
                    {profileInitials(profile.name)}
                  </span>
                  <span className="max-w-full truncate text-sm font-black">{profile.name}</span>
                  {selected && (
                    <span className="rounded-full bg-cyan-200 px-2 py-0.5 text-[10px] font-black uppercase text-black">
                      {pick("activ", "active")}
                    </span>
                  )}
                </button>

                {enabled && !profile.isPrimary && (
                  <button
                    type="button"
                    onClick={() => deleteProfile(profile)}
                    className="absolute -right-1 -top-1 inline-flex h-11 w-11 items-center justify-center rounded-full border border-red-300/35 bg-[#180b0b] text-red-200 opacity-70 shadow-xl hover:bg-red-400 hover:text-black focus:opacity-100 sm:opacity-0 sm:group-hover:opacity-100 sm:group-focus-within:opacity-100"
                    aria-label={`${pick("Șterge profilul", "Delete profile")} ${profile.name}`}
                  >
                    <Trash2 size={14} />
                  </button>
                )}
              </div>
            );
          })
        )}
      </div>

      {enabled ? (
        <form onSubmit={createProfile} className="mt-4 grid gap-3 rounded-xl border border-white/10 bg-black/18 p-3 md:grid-cols-[minmax(0,1fr)_auto_auto]">
          <label htmlFor={newNameId} className="sr-only">
            {pick("Numele membrului nou", "New member name")}
          </label>
          <input
            id={newNameId}
            name="family-profile-name"
            value={newName}
            onChange={(event) => setNewName(event.target.value)}
            disabled={!canAddProfile}
            placeholder={canAddProfile ? pick("Nume membru nou", "New member name") : pick("Limita de profiluri atinsă", "Profile limit reached")}
            className="min-h-11 rounded-lg border border-white/10 bg-black/30 px-4 text-white outline-none placeholder:text-gray-500 focus:border-cyan-300 disabled:cursor-not-allowed disabled:opacity-50"
            maxLength={80}
          />
          <div className="flex gap-2" role="group" aria-labelledby={colorGroupId}>
            <span id={colorGroupId} className="sr-only">
              {pick("Culoarea profilului", "Profile color")}
            </span>
            {COLOR_OPTIONS.map((color) => (
              <button
                key={color}
                type="button"
                onClick={() => setNewColor(color)}
                className={`h-11 w-11 rounded-lg bg-gradient-to-br ${PROFILE_COLORS[color]} ${
                  newColor === color ? "ring-2 ring-white" : "opacity-75 hover:opacity-100"
                }`}
                aria-label={`${pick("Culoare", "Color")}: ${color}`}
                aria-pressed={newColor === color}
              />
            ))}
          </div>
          <button
            type="submit"
            disabled={!canAddProfile || isCreating || !newName.trim()}
            className="inline-flex min-h-11 items-center justify-center gap-2 rounded-lg bg-white px-4 font-black text-black hover:bg-cyan-100 disabled:cursor-not-allowed disabled:bg-white/10 disabled:text-gray-500"
          >
            <Plus size={17} />
            {isCreating ? pick("Se adaugă...", "Adding...") : pick("Adaugă", "Add")}
          </button>
        </form>
      ) : (
        <div className="mt-4 flex flex-col gap-3 rounded-xl border border-yellow-300/25 bg-yellow-300/8 p-4 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex items-start gap-3">
            <span className="rounded-lg bg-yellow-300/15 p-2 text-yellow-200">
              <UserRound size={18} />
            </span>
            <p className="text-sm leading-6 text-gray-300">
              {pick(
                "Cu Family poți crea profiluri pentru fiecare persoană și recomandări separate.",
                "With Family you can create a profile for each person and keep recommendations separate."
              )}
            </p>
          </div>
          <Link href="/pricing" className="inline-flex shrink-0 justify-center rounded-lg border border-yellow-300/35 px-4 py-2.5 text-sm font-black text-yellow-100 hover:bg-yellow-300/12">
            {pick("Vezi Family", "See Family")}
          </Link>
        </div>
      )}

      {message && (
        <p
          className="mt-3 rounded-lg border border-red-300/30 bg-red-400/10 p-3 text-sm text-red-100"
          role="alert"
        >
          {message}
        </p>
      )}
    </InteractiveSurface>
  );
}
