"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { ArrowLeft, FileClock, Heart, ScanLine, ShoppingCart } from "lucide-react";
import { API_URL } from "../config";
import { getImageUrl } from "../utils/getImageUrl";
import { getActiveProfilePayload } from "../utils/profilePreferences";
import { ExpandableText } from "../components/ExpandableText";
import { ProductImage } from "../components/ProductImage";
import { ConfirmModal } from "../components/ConfirmModal";
import { AppHeader } from "../components/AppHeader";

export default function HistoryPage() {
  const [user, setUser] = useState(null);
  const [history, setHistory] = useState([]);
  const [message, setMessage] = useState("");
  const [isClearModalOpen, setIsClearModalOpen] = useState(false);

  async function loadHistory(userId) {
    try {
      const response = await fetch(`${API_URL}/history/${userId}`);
      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.error || "Nu s-a putut încărca istoricul.");
      }

      setHistory(data);
    } catch (error) {
      setMessage(error.message);
    }
  }

  useEffect(() => {
    queueMicrotask(() => {
      const savedUser = localStorage.getItem("cealeg_user");

      if (!savedUser) {
        window.location.assign("/login");
        return;
      }

      const parsedUser = JSON.parse(savedUser);
      setUser(parsedUser);
      loadHistory(parsedUser.id);
    });
  }, []);

  async function clearHistory() {
    if (!user) return;

    try {
      const response = await fetch(`${API_URL}/history/clear/${user.id}`, {
        method: "DELETE",
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.error || "Nu s-a putut șterge istoricul.");
      }

      setHistory([]);
      setMessage("Istoricul a fost șters.");
      setIsClearModalOpen(false);

      setTimeout(() => setMessage(""), 2500);
    } catch (error) {
      setMessage(error.message);
    }
  }

  async function deleteHistoryItem(id) {
    try {
      const response = await fetch(`${API_URL}/history/item/${id}`, {
        method: "DELETE",
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.error || "Nu s-a putut șterge scanarea.");
      }

      setHistory(history.filter((item) => item.id !== id));
      setMessage("Scanare ștearsă din istoric.");

      setTimeout(() => setMessage(""), 2500);
    } catch (error) {
      setMessage(error.message);
    }
  }

  async function addToCart(item) {
    if (!user) {
      window.location.assign("/login");
      return;
    }

    try {
      const response = await fetch(`${API_URL}/cart/add`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          user_id: user.id,
          name: item.name,
          store: item.store,
          score: item.score,
          price: item.price,
          image: item.image,
          reason: item.verdict || item.shortAdvice,
          quantity: 1,
          ...getActiveProfilePayload(),
        }),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.error || "Nu s-a putut adăuga produsul în coș.");
      }

      setMessage(`Produs adăugat în coș: ${item.name}`);
      setTimeout(() => setMessage(""), 2500);
    } catch (error) {
      setMessage(error.message);
    }
  }

  async function addToFavorites(item) {
    if (!user) {
      window.location.assign("/login");
      return;
    }

    try {
      const response = await fetch(`${API_URL}/favorites/add`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          user_id: user.id,
          name: item.name,
          store: item.store,
          category: item.category,
          score: item.score,
          price: item.price,
          image: item.image,
          reason: item.verdict || item.shortAdvice,
        }),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.error || "Nu s-a putut salva la favorite.");
      }

      setMessage(data.message || `Produs salvat la favorite: ${item.name}`);
      setTimeout(() => setMessage(""), 2500);
    } catch (error) {
      setMessage(error.message);
    }
  }

  function formatDate(dateString) {
    const date = new Date(dateString);

    return date.toLocaleString("ro-RO", {
      day: "2-digit",
      month: "2-digit",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  }

  if (!user) {
    return (
      <main className="flex min-h-screen items-center justify-center bg-[#0b0f14] text-white">
        <p className="text-gray-300">Se încarcă istoricul...</p>
      </main>
    );
  }

  return (
    <main className="min-h-screen bg-[#0b0f14] text-white">
      <AppHeader actionHref="/barcode-scan" actionLabel="Scanează produs" />
      <section className="ce-shell-lg ce-page">
        <div className="mb-8 flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <Link
            href="/dashboard"
            className="inline-flex items-center gap-2 text-sm font-bold text-cyan-200 hover:text-white"
          >
            <ArrowLeft size={16} /> Înapoi la dashboard
          </Link>

          <div className="flex flex-col gap-3 sm:flex-row">
            <Link
              href="/store"
              className="inline-flex items-center justify-center gap-2 rounded-2xl border border-white/10 px-5 py-3 text-center font-semibold hover:bg-white/10"
            >
              <ScanLine size={17} />
              Scanează produs
            </Link>

            <Link
              href="/favorites"
              className="inline-flex items-center justify-center gap-2 rounded-2xl border border-yellow-300/30 px-5 py-3 text-center font-semibold text-yellow-300 hover:bg-yellow-300/10"
            >
              <Heart size={17} />
              Favorite
            </Link>

            <Link
              href="/cart"
              className="inline-flex items-center justify-center gap-2 rounded-2xl border border-white/10 px-5 py-3 text-center font-semibold hover:bg-white/10"
            >
              <ShoppingCart size={17} />
              Vezi coșul
            </Link>
          </div>
        </div>

        {message && (
          <div className="mb-6 rounded-2xl border border-emerald-400/30 bg-emerald-400/10 p-4 text-emerald-300">
            {message}
          </div>
        )}

        <div className="rounded-3xl border border-white/10 bg-white/5 p-6 shadow-2xl">
          <p className="mb-3 inline-flex rounded-full border border-emerald-400/30 bg-emerald-400/10 px-4 py-2 text-sm text-emerald-300">
            Istoric scanări
          </p>

          <h1 className="text-4xl font-bold md:text-5xl">
            Scanările lui {user.name}
          </h1>

          <p className="mt-4 max-w-2xl text-gray-300">
            Istoricul este salvat acum în baza de date pentru contul tău.
          </p>

          <div className="mt-6 grid gap-4 sm:grid-cols-3">
            <div className="rounded-2xl border border-white/10 bg-black/30 p-4">
              <p className="text-sm text-gray-400">Scanări salvate</p>
              <p className="mt-1 text-3xl font-black text-emerald-300">
                {history.length}
              </p>
            </div>

            <div className="rounded-2xl border border-white/10 bg-black/30 p-4">
              <p className="text-sm text-gray-400">Ultimul magazin</p>
              <p className="mt-1 text-xl font-bold text-emerald-300">
                {history[0]?.store || "-"}
              </p>
            </div>

            <div className="rounded-2xl border border-white/10 bg-black/30 p-4">
              <p className="text-sm text-gray-400">Ultimul scor</p>
              <p className="mt-1 text-3xl font-black text-emerald-300">
                {history[0]?.score || "-"}
              </p>
            </div>
          </div>

          {history.length === 0 ? (
            <div className="mt-8 rounded-3xl border border-white/10 bg-black/30 p-8 text-center">
              <span className="mx-auto flex h-16 w-16 items-center justify-center rounded-2xl border border-cyan-300/25 bg-cyan-300/10 text-cyan-200">
                <FileClock size={32} />
              </span>
              <h2 className="mt-4 text-2xl font-bold">
                Nu există scanări încă
              </h2>
              <p className="mt-3 text-gray-400">
                Scanează primul produs și va apărea automat aici.
              </p>

              <Link
                href="/store"
                className="mt-6 inline-flex items-center justify-center gap-2 rounded-2xl bg-white px-6 py-3 font-black text-black hover:bg-cyan-100"
              >
                <ScanLine size={18} />
                Scanează primul produs
              </Link>
            </div>
          ) : (
            <div className="mt-8 space-y-4">
              {history.map((item) => (
                <div
                  key={item.id}
                  className="grid gap-4 rounded-3xl border border-white/10 bg-black/30 p-5 md:grid-cols-[auto_1fr_auto]"
                >
                  <ProductImage
                    src={getImageUrl(item.image)}
                    alt={item.name}
                    containerClassName="h-24 w-24 rounded-2xl"
                  />

                  <div>
                    <div className="flex flex-wrap gap-2">
                      <span className="rounded-full bg-emerald-400 px-3 py-1 text-sm font-bold text-black">
                        {item.score}/10
                      </span>

                      <span className="rounded-full border border-white/10 px-3 py-1 text-sm text-gray-300">
                        {item.store}
                      </span>

                      <span className="rounded-full border border-white/10 px-3 py-1 text-sm text-gray-300">
                        {item.category}
                      </span>
                    </div>

                    <h2 className="mt-3 text-2xl font-bold">{item.name}</h2>

                    <p className="mt-1 text-sm text-emerald-300">
                      {item.price}
                    </p>

                    <ExpandableText
                      text={item.shortAdvice || item.verdict}
                      className="mt-3 text-sm leading-6 text-gray-300"
                    />

                    <p className="mt-3 text-xs text-gray-500">
                      Scanat la: {formatDate(item.scanned_at)}
                    </p>
                  </div>

                  <div className="flex flex-col gap-2">
                    <button
                      onClick={() => addToCart(item)}
                      className="inline-flex items-center justify-center gap-2 rounded-2xl bg-white px-5 py-3 font-black text-black hover:bg-cyan-100"
                    >
                      <ShoppingCart size={18} />
                      Adaugă în coș
                    </button>

                    <button
                      onClick={() => addToFavorites(item)}
                      className="inline-flex items-center justify-center gap-2 rounded-2xl border border-yellow-300/30 px-5 py-3 font-semibold text-yellow-300 hover:bg-yellow-300/10"
                    >
                      <Heart size={18} />
                      Favorite
                    </button>

                    <button
                      onClick={() => deleteHistoryItem(item.id)}
                      className="rounded-2xl border border-red-400/30 px-5 py-3 font-semibold text-red-300 hover:bg-red-400/10"
                    >
                      Șterge
                    </button>
                  </div>
                </div>
              ))}

              <button
                onClick={() => setIsClearModalOpen(true)}
                className="w-full rounded-2xl border border-red-400/30 px-5 py-4 font-semibold text-red-300 hover:bg-red-400/10"
              >
                Șterge istoricul
              </button>
            </div>
          )}
        </div>
      </section>

      <ConfirmModal
        isOpen={isClearModalOpen}
        title="Ștergi istoricul?"
        message="Toate scanările salvate vor fi șterse. Acțiunea nu poate fi anulată."
        confirmLabel="Șterge istoricul"
        onCancel={() => setIsClearModalOpen(false)}
        onConfirm={clearHistory}
      />
    </main>
  );
}
