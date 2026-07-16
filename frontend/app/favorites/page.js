"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { ArrowLeft, Heart, ScanLine, ShoppingCart } from "lucide-react";
import { API_URL } from "../config";
import { getActiveProfilePayload } from "../utils/profilePreferences";
import { ExpandableText } from "../components/ExpandableText";
import { ProductImage } from "../components/ProductImage";
import { ConfirmModal } from "../components/ConfirmModal";
import { AppHeader } from "../components/AppHeader";
import { useLocale } from "../components/LocaleProvider";
import { getApiErrorMessage, readApiJson } from "../utils/apiResponse";
import { localizeCatalogLabel } from "../catalog-romania/seo-data";

function getImageUrl(path) {
  if (!path) return "";

  if (path.startsWith("http")) {
    return path;
  }

  if (path.startsWith("/uploads")) {
    return `${API_URL}${path}`;
  }

  return path;
}

export default function FavoritesPage() {
  const { locale, pick } = useLocale();
  const [user, setUser] = useState(null);
  const [favorites, setFavorites] = useState([]);
  const [message, setMessage] = useState("");
  const [isClearModalOpen, setIsClearModalOpen] = useState(false);

  const loadFavorites = useCallback(async (userId) => {
    try {
      const response = await fetch(`${API_URL}/favorites/${userId}`);
      const data = await readApiJson(response);

      if (!response.ok) {
        throw new Error(getApiErrorMessage(data, pick, "Nu s-au putut încărca favoritele.", "Favorites could not be loaded."));
      }

      setFavorites(data);
    } catch (error) {
      setMessage(error.message);
    }
  }, [pick]);

  useEffect(() => {
    queueMicrotask(() => {
      const savedUser = localStorage.getItem("cealeg_user");

      if (!savedUser) {
        window.location.assign("/login");
        return;
      }

      const parsedUser = JSON.parse(savedUser);
      setUser(parsedUser);
      loadFavorites(parsedUser.id);
    });
  }, [loadFavorites]);

  async function removeFavorite(id) {
    try {
      const response = await fetch(`${API_URL}/favorites/item/${id}`, {
        method: "DELETE",
      });

      const data = await readApiJson(response);

      if (!response.ok) {
        throw new Error(getApiErrorMessage(data, pick, "Nu s-a putut șterge produsul favorit.", "The favorite product could not be removed."));
      }

      setFavorites(favorites.filter((item) => item.id !== id));
      setMessage(pick("Produs șters din favorite.", "Product removed from favorites."));

      setTimeout(() => {
        setMessage("");
      }, 2500);
    } catch (error) {
      setMessage(error.message);
    }
  }

  async function clearFavorites() {
    if (!user) return;

    try {
      const response = await fetch(`${API_URL}/favorites/clear/${user.id}`, {
        method: "DELETE",
      });

      const data = await readApiJson(response);

      if (!response.ok) {
        throw new Error(getApiErrorMessage(data, pick, "Nu s-au putut șterge favoritele.", "Favorites could not be cleared."));
      }

      setFavorites([]);
      setMessage(pick("Toate favoritele au fost șterse.", "All favorites were cleared."));
      setIsClearModalOpen(false);

      setTimeout(() => {
        setMessage("");
      }, 2500);
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
          store: item.store || "Fără magazin ales",
          score: item.score,
          price: item.price,
          image: item.image,
          reason: item.reason || "Produs salvat la favorite.",
          quantity: 1,
          ...getActiveProfilePayload(),
        }),
      });

      const data = await readApiJson(response);

      if (!response.ok) {
        throw new Error(getApiErrorMessage(data, pick, "Nu s-a putut adăuga produsul în coș.", "The product could not be added to the cart."));
      }

      setMessage(pick(`Produs adăugat în coș: ${item.name}`, `Added to cart: ${item.name}`));

      setTimeout(() => {
        setMessage("");
      }, 2500);
    } catch (error) {
      setMessage(error.message);
    }
  }

  if (!user) {
    return (
      <main className="flex min-h-screen items-center justify-center bg-[#0b0f14] text-white">
        <p className="text-gray-300" role="status">{pick("Se încarcă favoritele...", "Loading favorites...")}</p>
      </main>
    );
  }

  return (
    <main className="min-h-screen bg-[#0b0f14] text-white">
      <AppHeader actionHref="/barcode-scan" actionLabel={pick("Scanează produs", "Scan product")} />
      <section className="ce-shell-lg ce-page">
        <div className="mb-8 flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <Link
            href="/dashboard"
            className="inline-flex items-center gap-2 text-sm font-bold text-cyan-200 hover:text-white"
          >
            <ArrowLeft size={16} /> {pick("Înapoi la dashboard", "Back to dashboard")}
          </Link>

          <div className="flex flex-col gap-3 sm:flex-row">
            <Link
              href="/store"
              className="inline-flex items-center justify-center gap-2 rounded-2xl border border-white/10 px-5 py-3 text-center font-semibold hover:bg-white/10"
            >
              <ScanLine size={17} />
              {pick("Scanează produs", "Scan product")}
            </Link>

            <Link
              href="/cart"
              className="inline-flex items-center justify-center gap-2 rounded-2xl border border-white/10 px-5 py-3 text-center font-semibold hover:bg-white/10"
            >
              <ShoppingCart size={17} />
              {pick("Vezi coșul", "View cart")}
            </Link>
          </div>
        </div>

        {message && (
          <div role="status" className="mb-6 rounded-2xl border border-emerald-400/30 bg-emerald-400/10 p-4 text-emerald-300">
            {message}
          </div>
        )}

        <div className="rounded-3xl border border-white/10 bg-white/5 p-6 shadow-2xl">
          <p className="mb-3 inline-flex rounded-full border border-yellow-300/30 bg-yellow-300/10 px-4 py-2 text-sm text-yellow-300">
            {pick("Produse favorite", "Favorite products")}
          </p>

          <h1 className="text-4xl font-bold md:text-5xl">
            {pick(`Favoritele lui ${user.name}`, `${user.name}'s favorites`)}
          </h1>

          <p className="mt-4 max-w-2xl text-gray-300">
            {pick(
              "Păstrează produsele pe care vrei să le găsești ușor la următoarea cumpărătură.",
              "Keep the products you want to find easily on your next shopping trip."
            )}
          </p>

          <div className="mt-6 grid gap-4 sm:grid-cols-3">
            <div className="rounded-2xl border border-white/10 bg-black/30 p-4">
              <p className="text-sm text-gray-400">{pick("Produse favorite", "Favorite products")}</p>
              <p className="mt-1 text-3xl font-black text-yellow-300">
                {favorites.length}
              </p>
            </div>

            <div className="rounded-2xl border border-white/10 bg-black/30 p-4">
              <p className="text-sm text-gray-400">{pick("Ultimul produs", "Latest product")}</p>
              <p className="mt-1 text-xl font-bold text-yellow-300">
                {favorites[0]?.name || "-"}
              </p>
            </div>

            <div className="rounded-2xl border border-white/10 bg-black/30 p-4">
              <p className="text-sm text-gray-400">{pick("Ultimul scor", "Latest score")}</p>
              <p className="mt-1 text-3xl font-black text-yellow-300">
                {favorites[0]?.score || "-"}
              </p>
            </div>
          </div>

          {favorites.length === 0 ? (
            <div className="mt-8 rounded-3xl border border-white/10 bg-black/30 p-8 text-center">
              <span className="mx-auto flex h-16 w-16 items-center justify-center rounded-2xl border border-yellow-300/25 bg-yellow-300/10 text-yellow-200">
                <Heart size={32} />
              </span>
              <h2 className="mt-4 text-2xl font-bold">
                {pick("Nu ai produse favorite încă", "You do not have any favorite products yet")}
              </h2>
              <p className="mt-3 text-gray-400">
                {pick(
                  "Scanează un produs sau alege o alternativă și apasă «Adaugă la favorite».",
                  "Scan a product or choose an alternative and select Add to favorites."
                )}
              </p>

              <Link
                href="/store"
                className="mt-6 inline-flex items-center justify-center gap-2 rounded-2xl bg-white px-6 py-3 font-black text-black hover:bg-cyan-100"
              >
                <ScanLine size={18} />
                {pick("Scanează produs", "Scan product")}
              </Link>
            </div>
          ) : (
            <div className="mt-8 space-y-4">
              {favorites.map((item) => (
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
                      <span className="rounded-full bg-yellow-300 px-3 py-1 text-sm font-bold text-black">
                        {item.score || "-"}/10
                      </span>

                      <span className="rounded-full border border-white/10 px-3 py-1 text-sm text-gray-300">
                        {item.store || pick("Fără magazin", "No store")}
                      </span>

                      {item.category && (
                        <span className="rounded-full border border-white/10 px-3 py-1 text-sm text-gray-300">
                          {localizeCatalogLabel(item.category, locale)}
                        </span>
                      )}
                    </div>

                    <h2 className="mt-3 text-2xl font-bold">{item.name}</h2>

                    <p className="mt-1 text-sm text-emerald-300">
                      {item.price === "preț necunoscut"
                        ? pick("Verifică prețul în magazin", "Check the price in store")
                        : item.price || pick("Verifică prețul în magazin", "Check the price in store")}
                    </p>

                    <ExpandableText
                      text={item.reason}
                      fallback={pick("Produs favorit.", "Favorite product.")}
                      className="mt-3 text-sm leading-6 text-gray-300"
                    />
                  </div>

                  <div className="flex flex-col gap-2">
                    <button
                      onClick={() => addToCart(item)}
                      className="inline-flex items-center justify-center gap-2 rounded-2xl bg-white px-5 py-3 font-black text-black hover:bg-cyan-100"
                    >
                      <ShoppingCart size={18} />
                      {pick("Adaugă în coș", "Add to cart")}
                    </button>

                    <button
                      onClick={() => removeFavorite(item.id)}
                      className="rounded-2xl border border-red-400/30 px-5 py-3 font-semibold text-red-300 hover:bg-red-400/10"
                    >
                      {pick("Șterge", "Remove")}
                    </button>
                  </div>
                </div>
              ))}

              <button
                onClick={() => setIsClearModalOpen(true)}
                className="w-full rounded-2xl border border-red-400/30 px-5 py-4 font-semibold text-red-300 hover:bg-red-400/10"
              >
                {pick("Șterge toate favoritele", "Clear all favorites")}
              </button>
            </div>
          )}
        </div>
      </section>

      <ConfirmModal
        isOpen={isClearModalOpen}
        title={pick("Ștergi toate favoritele?", "Clear all favorites?")}
        message={pick("Lista de produse favorite va fi golită. Acțiunea nu poate fi anulată.", "Your favorite products list will be cleared. This action cannot be undone.")}
        confirmLabel={pick("Șterge favoritele", "Clear favorites")}
        cancelLabel={pick("Anulează", "Cancel")}
        onCancel={() => setIsClearModalOpen(false)}
        onConfirm={clearFavorites}
      />
    </main>
  );
}
