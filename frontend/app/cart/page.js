"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { ArrowLeft, ScanLine, ShoppingCart } from "lucide-react";
import { API_URL } from "../config";
import { getActiveProfile } from "../utils/profilePreferences";
import { ProductImage } from "../components/ProductImage";
import { ConfirmModal } from "../components/ConfirmModal";
import { InlineNotice } from "../components/InlineNotice";
import { AppHeader } from "../components/AppHeader";
import { FamilyProfiles } from "../components/FamilyProfiles";
import { TranslatedText } from "../components/TranslatedText";
import { useLocale } from "../components/LocaleProvider";
import { getApiErrorMessage, readApiJson } from "../utils/apiResponse";

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

function notifyCartUpdated() {
  window.dispatchEvent(new CustomEvent("cealeg:cart-updated"));
}

export default function CartPage() {
  const { pick } = useLocale();
  const [user, setUser] = useState(null);
  const [cartItems, setCartItems] = useState([]);
  const [newStoreName, setNewStoreName] = useState("");
  const [stores, setStores] = useState([]);
  const [activeProfile, setActiveProfileState] = useState(null);
  const [expandedReasons, setExpandedReasons] = useState({});
  const [message, setMessage] = useState("");
  const [messageTone, setMessageTone] = useState("success");
  const [isClearModalOpen, setIsClearModalOpen] = useState(false);

  const showError = useCallback((messageText) => {
    setMessageTone("error");
    setMessage(messageText);
  }, []);

  const loadCart = useCallback(async (userId, profile = null) => {
    try {
      const profileId = profile?.id;
      const profileQuery = profileId ? `?profile_id=${encodeURIComponent(profileId)}` : "";
      const response = await fetch(`${API_URL}/cart/${userId}${profileQuery}`);
      const data = await readApiJson(response);

      if (!response.ok) {
        throw new Error(getApiErrorMessage(data, pick, "Nu s-a putut încărca coșul.", "The cart could not be loaded."));
      }

      setCartItems(data);
      notifyCartUpdated();
    } catch (error) {
      showError(error.message);
    }
  }, [pick, showError]);

  useEffect(() => {
    let isMounted = true;
    let currentUserId = null;

    function handleProfileChange(event) {
      if (!isMounted || !currentUserId) return;
      const nextProfile = event.detail || getActiveProfile();
      setActiveProfileState(nextProfile);
      loadCart(currentUserId, nextProfile);
    }

    window.addEventListener("cealeg:profile-change", handleProfileChange);

    queueMicrotask(() => {
      if (!isMounted) return;

      const savedUser = localStorage.getItem("cealeg_user");

      if (!savedUser) {
        window.location.href = "/login";
        return;
      }

      const parsedUser = JSON.parse(savedUser);
      currentUserId = parsedUser.id;
      setUser(parsedUser);
      const profile = getActiveProfile();
      setActiveProfileState(profile);

      const savedStores = localStorage.getItem("cealeg_stores");

      if (savedStores) {
        setStores(JSON.parse(savedStores));
      } else {
        const defaultStores = [
          "Lidl",
          "Kaufland",
          "Carrefour",
          "Mega Image",
          "Profi",
          "Penny",
          pick("Magazin local", "Local store"),
        ];

        setStores(defaultStores);
        localStorage.setItem("cealeg_stores", JSON.stringify(defaultStores));
      }

      loadCart(parsedUser.id, profile);
    });

    return () => {
      isMounted = false;
      window.removeEventListener("cealeg:profile-change", handleProfileChange);
    };
  }, [loadCart, pick]);

  function toggleReason(itemId) {
    setExpandedReasons((current) => ({
      ...current,
      [itemId]: !current[itemId],
    }));
  }

  function removeExpandedReason(itemId) {
    setExpandedReasons((current) => {
      const updatedReasons = { ...current };
      delete updatedReasons[itemId];
      return updatedReasons;
    });
  }

  function addStore() {
    if (!newStoreName.trim()) return;

    const updatedStores = [...stores, newStoreName.trim()];
    setStores(updatedStores);
    localStorage.setItem("cealeg_stores", JSON.stringify(updatedStores));
    setNewStoreName("");
  }

  async function removeItem(id) {
    try {
      const response = await fetch(`${API_URL}/cart/item/${id}`, {
        method: "DELETE",
      });

      const data = await readApiJson(response);

      if (!response.ok) {
        throw new Error(getApiErrorMessage(data, pick, "Nu s-a putut șterge produsul.", "The product could not be removed."));
      }

      setCartItems((current) => current.filter((item) => item.id !== id));
      removeExpandedReason(id);
      notifyCartUpdated();
    } catch (error) {
      showError(error.message);
    }
  }

  async function toggleBought(item) {
    try {
      const response = await fetch(`${API_URL}/cart/item/${item.id}`, {
        method: "PATCH",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          bought: !item.bought,
        }),
      });

      const data = await readApiJson(response);

      if (!response.ok) {
        throw new Error(getApiErrorMessage(data, pick, "Nu s-a putut actualiza produsul.", "The product could not be updated."));
      }

      setCartItems(
        cartItems.map((cartItem) =>
          cartItem.id === item.id ? data.item : cartItem
        )
      );
      notifyCartUpdated();
    } catch (error) {
      showError(error.message);
    }
  }

  async function changeStore(item, newStore) {
    try {
      const response = await fetch(`${API_URL}/cart/item/${item.id}`, {
        method: "PATCH",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          store: newStore,
        }),
      });

      const data = await readApiJson(response);

      if (!response.ok) {
        throw new Error(getApiErrorMessage(data, pick, "Nu s-a putut schimba magazinul.", "The store could not be changed."));
      }

      setCartItems(
        cartItems.map((cartItem) =>
          cartItem.id === item.id ? data.item : cartItem
        )
      );
      notifyCartUpdated();
    } catch (error) {
      showError(error.message);
    }
  }

  async function updateQuantity(item, quantity) {
    try {
      const response = await fetch(`${API_URL}/cart/item/${item.id}`, {
        method: "PATCH",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          quantity,
        }),
      });

      const data = await readApiJson(response);

      if (!response.ok) {
        throw new Error(getApiErrorMessage(data, pick, "Nu s-a putut actualiza cantitatea.", "The quantity could not be updated."));
      }

      if (quantity <= 0) {
        setCartItems((current) =>
          current.filter((cartItem) => cartItem.id !== item.id)
        );
        removeExpandedReason(item.id);
      } else {
        setCartItems(
          cartItems.map((cartItem) =>
            cartItem.id === item.id ? data.item : cartItem
          )
        );
      }
      notifyCartUpdated();
    } catch (error) {
      showError(error.message);
    }
  }

  async function clearCart() {
    if (!user) return;

    try {
      const profileQuery = activeProfile?.id
        ? `?profile_id=${encodeURIComponent(activeProfile.id)}`
        : "";
      const response = await fetch(`${API_URL}/cart/clear/${user.id}${profileQuery}`, {
        method: "DELETE",
      });

      const data = await readApiJson(response);

      if (!response.ok) {
        throw new Error(getApiErrorMessage(data, pick, "Nu s-a putut goli coșul.", "The cart could not be cleared."));
      }

      setCartItems([]);
      setExpandedReasons({});
      setMessageTone("success");
      setMessage(pick("Coșul a fost golit.", "The cart was cleared."));
      setIsClearModalOpen(false);
      notifyCartUpdated();
    } catch (error) {
      showError(error.message);
    }
  }

  const activeProfileName = activeProfile?.name || user?.name || "";

  const groupedCart = cartItems.reduce((groups, item) => {
    const store = item.store || pick("Fără magazin", "No store");
    if (!groups[store]) groups[store] = [];
    groups[store].push(item);
    return groups;
  }, {});

  const totalItems = cartItems.reduce(
    (total, item) => total + (item.quantity || 1),
    0
  );

  const boughtItems = cartItems
    .filter((item) => item.bought)
    .reduce((total, item) => total + (item.quantity || 1), 0);

  if (!user) {
    return (
      <main className="flex min-h-screen items-center justify-center bg-[#0b0f14] text-white">
        <p className="text-gray-300" role="status">{pick("Se încarcă coșul...", "Loading cart...")}</p>
      </main>
    );
  }

  return (
    <main className="min-h-screen bg-[#0b0f14] text-white">
      <AppHeader actionHref="/barcode-scan" actionLabel={pick("Scanează produs", "Scan product")} />
      <section className="ce-shell-lg ce-page">
        <InlineNotice
          message={message}
          tone={messageTone}
          className="mb-6"
        />
        <div className="mb-8 flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <Link
            href="/dashboard"
            className="inline-flex items-center gap-2 text-sm font-bold text-cyan-200 hover:text-white"
          >
            <ArrowLeft size={16} /> {pick("Înapoi la dashboard", "Back to dashboard")}
          </Link>

          <Link
            href="/store"
            className="inline-flex items-center justify-center gap-2 rounded-2xl border border-white/10 px-5 py-3 text-center font-semibold hover:bg-white/10"
          >
            <ScanLine size={17} />
            {pick("Scanează alt produs", "Scan another product")}
          </Link>
        </div>

        <div className="rounded-3xl border border-white/10 bg-white/5 p-6 shadow-2xl">
          <p className="mb-3 inline-flex rounded-full border border-emerald-400/30 bg-emerald-400/10 px-4 py-2 text-sm text-emerald-300">
            {pick("Coș inteligent", "Smart cart")}
          </p>

          <h1 className="text-4xl font-bold md:text-5xl">
            {pick(`Lista de cumpărături a lui ${activeProfileName}`, `${activeProfileName}'s shopping list`)}
          </h1>

          <p className="mt-4 max-w-2xl text-gray-300">
            {pick(
              "Organizează produsele pe magazine și bifează-le pe măsură ce le adaugi în coș.",
              "Organize products by store and check them off as you add them to your basket."
            )}
          </p>

          <div className="mt-6">
            <FamilyProfiles compact />
          </div>

          <div className="mt-6 grid gap-4 sm:grid-cols-3">
            <div className="rounded-2xl border border-white/10 bg-black/30 p-4">
              <p className="text-sm text-gray-400">{pick("Produse în coș", "Cart products")}</p>
              <p className="mt-1 text-3xl font-black text-emerald-300">
                {totalItems}
              </p>
            </div>

            <div className="rounded-2xl border border-white/10 bg-black/30 p-4">
              <p className="text-sm text-gray-400">{pick("Bifate", "Checked")}</p>
              <p className="mt-1 text-3xl font-black text-emerald-300">
                {boughtItems}
              </p>
            </div>

            <div className="rounded-2xl border border-white/10 bg-black/30 p-4">
              <p className="text-sm text-gray-400">{pick("Magazine", "Stores")}</p>
              <p className="mt-1 text-3xl font-black text-emerald-300">
                {Object.keys(groupedCart).length}
              </p>
            </div>
          </div>

          <div className="mt-8 rounded-3xl border border-white/10 bg-black/30 p-5">
            <h2 className="text-2xl font-bold">{pick("Adaugă magazin nou", "Add a new store")}</h2>

            <div className="mt-4 flex flex-col gap-3 sm:flex-row">
              <label htmlFor="cart-new-store" className="sr-only">
                {pick("Numele magazinului", "Store name")}
              </label>
              <input
                id="cart-new-store"
                value={newStoreName}
                onChange={(e) => setNewStoreName(e.target.value)}
                placeholder={pick("Exemplu: magazin local, piață...", "Example: local shop, market...")}
                className="flex-1 rounded-2xl border border-white/10 bg-white/5 px-4 py-3 text-white outline-none placeholder:text-gray-500 focus:border-emerald-400"
              />

              <button
                onClick={addStore}
                className="rounded-2xl bg-emerald-400 px-6 py-3 font-semibold text-black hover:bg-emerald-300"
              >
                {pick("Adaugă magazin", "Add store")}
              </button>
            </div>
          </div>

          {cartItems.length === 0 ? (
            <div className="mt-8 rounded-3xl border border-white/10 bg-black/30 p-8 text-center">
              <span className="mx-auto flex h-16 w-16 items-center justify-center rounded-2xl border border-cyan-300/25 bg-cyan-300/10 text-cyan-200">
                <ShoppingCart size={32} />
              </span>
              <h2 className="mt-4 text-2xl font-bold">{pick("Coșul este gol", "Your cart is empty")}</h2>
              <p className="mt-3 text-gray-400">
                {pick(
                  "Scanează un produs, alege o alternativă și apasă «Adaugă în coș».",
                  "Scan a product, choose an alternative and select Add to cart."
                )}
              </p>

              <Link
                href="/store"
                className="mt-6 inline-flex items-center justify-center gap-2 rounded-2xl bg-white px-6 py-3 font-black text-black hover:bg-cyan-100"
              >
                <ScanLine size={18} />
                {pick("Începe scanarea", "Start scanning")}
              </Link>
            </div>
          ) : (
            <div className="mt-8 space-y-6">
              {Object.entries(groupedCart).map(([store, items]) => (
                <div
                  key={store}
                  className="rounded-3xl border border-white/10 bg-black/30 p-5"
                >
                  <div className="mb-4 flex items-center justify-between gap-3">
                    <div>
                      <h2 className="text-2xl font-bold">{store}</h2>
                      <p className="text-sm text-gray-400">
                        {items.reduce(
                          (total, item) => total + (item.quantity || 1),
                          0
                        )}{" "}
                        {pick("produse de cumpărat", "items to buy")}
                      </p>
                    </div>
                  </div>

                  <div className="space-y-3">
                    {items.map((item) => (
                      <div
                        key={item.id}
                        className="grid gap-4 rounded-2xl border border-white/10 bg-white/5 p-4 md:grid-cols-[auto_1fr_auto]"
                      >
                        <button
                          type="button"
                          onClick={() => toggleBought(item)}
                          aria-label={pick(
                            `${item.bought ? "Debifează" : "Bifează"} ${item.name}`,
                            `${item.bought ? "Uncheck" : "Check"} ${item.name}`
                          )}
                          aria-pressed={Boolean(item.bought)}
                          className={`h-7 w-7 rounded-lg border ${
                            item.bought
                              ? "border-emerald-400 bg-emerald-400 text-black"
                              : "border-white/20 bg-black/30"
                          }`}
                        >
                          {item.bought ? "✓" : ""}
                        </button>

                        <div className={item.bought ? "opacity-50" : ""}>
                          <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
                            <ProductImage
                              src={getImageUrl(item.image)}
                              alt={item.name}
                              containerClassName="h-20 w-20 rounded-2xl"
                            />

                            <div className="min-w-0">
                              <div className="flex flex-wrap items-center gap-2">
                                <h3
                                  className={`text-lg font-bold ${
                                    item.bought ? "line-through" : ""
                                  }`}
                                >
                                  {item.name}
                                </h3>

                                <span className="rounded-full bg-emerald-400 px-3 py-1 text-sm font-black text-black">
                                  x{item.quantity || 1}
                                </span>
                              </div>

                              <p className="mt-1 text-sm text-gray-400">
                                {item.price === "preț necunoscut"
                                  ? pick("Verifică prețul în magazin", "Check the price in store")
                                  : item.price || pick("Verifică prețul în magazin", "Check the price in store")}{" "}
                                · {pick("scor", "score")}{" "}
                                {item.score || "-"} / 10
                              </p>

                              {item.reason && (
                                <div className="mt-2">
                                  <p
                                    id={`cart-reason-${item.id}`}
                                    className={`text-sm leading-5 text-gray-300 ${
                                      expandedReasons[item.id]
                                        ? ""
                                        : "line-clamp-2"
                                    }`}
                                  >
                                    <TranslatedText>{item.reason}</TranslatedText>
                                  </p>

                                  {item.reason.length > 120 && (
                                    <button
                                      type="button"
                                      onClick={() => toggleReason(item.id)}
                                      aria-controls={`cart-reason-${item.id}`}
                                      aria-expanded={Boolean(
                                        expandedReasons[item.id]
                                      )}
                                      className="mt-1 text-sm font-semibold text-emerald-300 hover:text-emerald-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-emerald-300/70"
                                    >
                                      {expandedReasons[item.id]
                                        ? pick("Arată mai puțin", "Show less")
                                        : pick("Citește mai mult", "Read more")}
                                    </button>
                                  )}
                                </div>
                              )}

                              <div className="mt-3 flex items-center gap-2">
                                <button
                                  type="button"
                                  onClick={() =>
                                    updateQuantity(
                                      item,
                                      (item.quantity || 1) - 1
                                    )
                                  }
                                  aria-label={pick(`Scade cantitatea pentru ${item.name}`, `Decrease quantity for ${item.name}`)}
                                  className="rounded-xl border border-white/10 px-3 py-1 font-bold hover:bg-white/10"
                                >
                                  -
                                </button>

                                <span className="min-w-8 text-center font-bold">
                                  {item.quantity || 1}
                                </span>

                                <button
                                  type="button"
                                  onClick={() =>
                                    updateQuantity(
                                      item,
                                      (item.quantity || 1) + 1
                                    )
                                  }
                                  aria-label={pick(`Mărește cantitatea pentru ${item.name}`, `Increase quantity for ${item.name}`)}
                                  className="rounded-xl border border-white/10 px-3 py-1 font-bold hover:bg-white/10"
                                >
                                  +
                                </button>
                              </div>
                            </div>
                          </div>
                        </div>

                        <div className="flex flex-col gap-2">
                          <select
                            value={item.store}
                            onChange={(e) => changeStore(item, e.target.value)}
                            aria-label={pick(`Magazin pentru ${item.name}`, `Store for ${item.name}`)}
                            className="rounded-xl border border-white/10 bg-[#0b0f14] px-3 py-2 text-sm text-white outline-none"
                          >
                            {stores.map((storeName) => (
                              <option key={storeName} value={storeName}>
                                {storeName}
                              </option>
                            ))}
                          </select>

                          <button
                            onClick={() => removeItem(item.id)}
                            className="rounded-xl border border-red-400/30 px-3 py-2 text-sm font-semibold text-red-300 hover:bg-red-400/10"
                          >
                            {pick("Șterge", "Remove")}
                          </button>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              ))}

              <button
                onClick={() => setIsClearModalOpen(true)}
                className="w-full rounded-2xl border border-red-400/30 px-5 py-4 font-semibold text-red-300 hover:bg-red-400/10"
              >
                {pick("Golește coșul", "Clear cart")}
              </button>
            </div>
          )}
        </div>
      </section>

      <ConfirmModal
        isOpen={isClearModalOpen}
        title={pick("Golești coșul?", "Clear the cart?")}
        message={pick("Toate produsele din coș vor fi șterse. Acțiunea nu poate fi anulată.", "All products in the cart will be removed. This action cannot be undone.")}
        confirmLabel={pick("Golește coșul", "Clear cart")}
        cancelLabel={pick("Anulează", "Cancel")}
        onCancel={() => setIsClearModalOpen(false)}
        onConfirm={clearCart}
      />
    </main>
  );
}
