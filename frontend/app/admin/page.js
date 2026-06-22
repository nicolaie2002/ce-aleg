"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { CheckCircle2, Mail, RefreshCw, SearchX, ShieldCheck, Trash2 } from "lucide-react";
import { API_URL } from "../config";
import { AppHeader } from "../components/AppHeader";
import { readApiJson } from "../utils/apiResponse";

const statLabels = {
  users: "Conturi",
  products: "Produse in catalog",
  pendingSubmissions: "Propuneri de verificat",
  searches: "Cautari salvate",
  missingProducts: "Produse negasite",
  priceObservations: "Preturi raportate",
  proUsers: "Utilizatori Pro",
};

const CONTACT_EMAIL = "contact@cealeg.shop";

export default function AdminPage() {
  const [overview, setOverview] = useState({});
  const [submissions, setSubmissions] = useState([]);
  const [misses, setMisses] = useState([]);
  const [users, setUsers] = useState([]);
  const [message, setMessage] = useState("");
  const [emailBusy, setEmailBusy] = useState(false);
  const [emailTestAddress, setEmailTestAddress] = useState(CONTACT_EMAIL);

  async function loadAdmin() {
    const [overviewResponse, submissionsResponse, missesResponse, usersResponse] = await Promise.all([
      fetch(`${API_URL}/admin/overview`),
      fetch(`${API_URL}/admin/submissions`),
      fetch(`${API_URL}/admin/search-misses?days=30&limit=40`),
      fetch(`${API_URL}/users`),
    ]);

    if (overviewResponse.status === 401) {
      window.location.assign("/login");
      return;
    }

    if (!overviewResponse.ok || !submissionsResponse.ok || !usersResponse.ok) {
      setMessage("Acest spatiu este disponibil doar administratorului.");
      return;
    }

    setOverview(await overviewResponse.json());
    setSubmissions(await submissionsResponse.json());
    setMisses(missesResponse.ok ? await missesResponse.json() : []);
    setUsers(await usersResponse.json());
  }

  useEffect(() => {
    queueMicrotask(loadAdmin);
  }, []);

  async function review(submissionId) {
    setMessage("Verific propunerea...");
    const response = await fetch(`${API_URL}/submissions/ai-review/${submissionId}`, {
      method: "POST",
    });
    const data = await response.json();
    setMessage(data.message || data.error);
    await loadAdmin();
  }

  async function approve(submissionId) {
    const response = await fetch(`${API_URL}/submissions/approve/${submissionId}`, {
      method: "POST",
    });
    const data = await response.json();
    setMessage(data.message || data.error);
    await loadAdmin();
  }

  async function remove(submissionId) {
    if (!window.confirm("Stergi propunerea?")) return;
    const response = await fetch(`${API_URL}/submissions/item/${submissionId}`, {
      method: "DELETE",
    });
    const data = await response.json();
    setMessage(data.message || data.error);
    await loadAdmin();
  }

  async function updateUserPlan(userId, plan) {
    const response = await fetch(`${API_URL}/admin/users/${userId}/plan`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ plan, status: "active" }),
    });
    const data = await response.json();
    setMessage(data.message || data.error);
    await loadAdmin();
  }

  async function sendEmailTest() {
    setEmailBusy(true);
    setMessage("Trimit emailul de test...");

    try {
      const response = await fetch(`${API_URL}/admin/email-test`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ to: emailTestAddress || CONTACT_EMAIL }),
      });
      const data = await readApiJson(response);
      setMessage(
        data.message ||
          data.error ||
          (response.ok
            ? "Test email finalizat."
            : "Emailul de test nu a putut fi trimis.")
      );
    } catch {
      setMessage("Emailul de test nu a putut fi trimis.");
    } finally {
      setEmailBusy(false);
    }
  }

  return (
    <main className="min-h-screen bg-[#080c10] text-white">
      <AppHeader actionHref="/dashboard" actionLabel="Dashboard" />
      <section className="ce-shell ce-page">
        <p className="flex items-center gap-2 text-sm font-bold text-emerald-300">
          <ShieldCheck size={16} /> Administrare platforma
        </p>
        <h1 className="mt-3 text-4xl font-black">Moderare, planuri si sanatatea platformei</h1>
        <p className="mt-3 max-w-2xl text-gray-300">
          Verifica propunerile comunitatii, planurile utilizatorilor si serviciile esentiale inainte de publicare.
        </p>

        <div className="mt-7 grid gap-3 sm:grid-cols-2 lg:grid-cols-4 xl:grid-cols-7">
          {Object.entries(statLabels).map(([key, label]) => (
            <div key={key} className="rounded-lg border border-white/10 bg-[#11171d] p-4">
              <p className="text-sm text-gray-400">{label}</p>
              <p className="mt-2 text-3xl font-black text-emerald-300">{overview[key] ?? "-"}</p>
            </div>
          ))}
        </div>

        {message && <p className="mt-5 rounded-lg border border-emerald-300/25 bg-emerald-400/10 p-4 text-sm text-emerald-100">{message}</p>}

        <section className="mt-8 rounded-lg border border-white/10 bg-[#11171d] p-5">
          <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
            <div>
              <h2 className="text-2xl font-black">Sistem si email</h2>
              <p className="mt-2 text-sm text-gray-400">
                Trimite un email de test catre adresa profesionala a site-ului.
              </p>
            </div>
            <div className="flex w-full flex-col gap-2 md:w-auto md:min-w-[380px]">
              <label className="text-xs font-black uppercase text-gray-400" htmlFor="admin-email-test">
                Destinatar test
              </label>
              <div className="flex flex-col gap-2 sm:flex-row">
                <input
                  id="admin-email-test"
                  value={emailTestAddress}
                  onChange={(event) => setEmailTestAddress(event.target.value)}
                  className="min-h-12 flex-1 rounded-lg border border-white/10 bg-black/30 px-4 text-white outline-none placeholder:text-gray-500 focus:border-cyan-300"
                  placeholder={CONTACT_EMAIL}
                  type="email"
                />
                <button
                  onClick={sendEmailTest}
                  disabled={emailBusy}
                  className="inline-flex items-center justify-center gap-2 rounded-lg bg-emerald-400 px-5 py-3 font-black text-black hover:bg-emerald-300 disabled:cursor-not-allowed disabled:opacity-60"
                >
                  <Mail size={17} /> {emailBusy ? "Se trimite..." : "Testeaza email"}
                </button>
              </div>
            </div>
          </div>
        </section>

        <section className="mt-8 rounded-lg border border-white/10 bg-[#11171d] p-5">
          <div className="flex items-center justify-between gap-4">
            <div>
              <h2 className="text-2xl font-black">Planuri utilizatori</h2>
              <p className="mt-2 text-sm text-gray-400">Activeaza manual Free, Pro sau Family.</p>
            </div>
            <button onClick={loadAdmin} title="Reincarca" className="inline-flex h-10 w-10 items-center justify-center rounded-lg border border-white/15 hover:bg-white/10">
              <RefreshCw size={17} />
            </button>
          </div>
          <div className="mt-4 overflow-x-auto">
            <table className="w-full min-w-[720px] text-left text-sm">
              <thead className="text-gray-400">
                <tr>
                  <th className="border-b border-white/10 py-3">Email</th>
                  <th className="border-b border-white/10 py-3">Admin</th>
                  <th className="border-b border-white/10 py-3">Plan</th>
                  <th className="border-b border-white/10 py-3">Actiuni</th>
                </tr>
              </thead>
              <tbody>
                {users.map((item) => (
                  <tr key={item.id}>
                    <td className="border-b border-white/5 py-3">{item.email}</td>
                    <td className="border-b border-white/5 py-3">{item.is_admin ? "da" : "nu"}</td>
                    <td className="border-b border-white/5 py-3 font-bold text-emerald-300">{item.plan || "free"}</td>
                    <td className="border-b border-white/5 py-3">
                      <div className="flex flex-wrap gap-2">
                        {["free", "pro", "family"].map((plan) => (
                          <button key={plan} onClick={() => updateUserPlan(item.id, plan)} className="rounded-md border border-white/15 px-3 py-1.5 font-bold hover:bg-white/10">
                            {plan}
                          </button>
                        ))}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>

        <section className="mt-8 rounded-lg border border-white/10 bg-[#11171d] p-5">
          <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
            <div>
              <p className="flex items-center gap-2 text-sm font-bold text-amber-200">
                <SearchX size={16} /> Produse negasite
              </p>
              <h2 className="mt-2 text-2xl font-black">Ce cauta oamenii si lipseste</h2>
              <p className="mt-2 text-sm text-gray-400">
                Interogari cu zero rezultate in ultimele 30 de zile. Prioritizeaza-le pentru import sau verificare manuala.
              </p>
            </div>
            <button onClick={loadAdmin} title="Reincarca lipsurile" className="inline-flex items-center justify-center gap-2 rounded-lg border border-white/15 px-4 py-3 text-sm font-bold hover:bg-white/10">
              <RefreshCw size={16} /> Reincarca
            </button>
          </div>

          <div className="mt-5 overflow-x-auto">
            <table className="w-full min-w-[760px] text-left text-sm">
              <thead className="text-gray-400">
                <tr>
                  <th className="border-b border-white/10 py-3">Cautare</th>
                  <th className="border-b border-white/10 py-3">Magazin</th>
                  <th className="border-b border-white/10 py-3">Sursa</th>
                  <th className="border-b border-white/10 py-3">Aparitii</th>
                  <th className="border-b border-white/10 py-3">Ultima data</th>
                </tr>
              </thead>
              <tbody>
                {misses.map((item) => (
                  <tr key={`${item.query}-${item.store}-${item.source}`}>
                    <td className="border-b border-white/5 py-3 font-bold text-white">{item.query}</td>
                    <td className="border-b border-white/5 py-3 text-gray-300">{item.store}</td>
                    <td className="border-b border-white/5 py-3 text-gray-400">{item.source}</td>
                    <td className="border-b border-white/5 py-3 font-black text-amber-200">{item.count}</td>
                    <td className="border-b border-white/5 py-3 text-gray-400">
                      {item.lastSeen ? new Date(item.lastSeen).toLocaleString("ro-RO") : "-"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            {!misses.length && (
              <p className="mt-4 rounded-lg border border-white/10 bg-black/20 p-4 text-sm text-gray-400">
                Nu exista inca produse negasite in perioada selectata.
              </p>
            )}
          </div>
        </section>

        <section className="mt-8">
          <div className="flex items-center justify-between gap-4">
            <h2 className="text-2xl font-black">Propuneri recente</h2>
          </div>
          <div className="mt-4 space-y-3">
            {submissions.map((item) => (
              <article key={item.id} className="rounded-lg border border-white/10 bg-[#11171d] p-5">
                <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
                  <div>
                    <p className="text-xs font-bold uppercase text-emerald-300">{item.status}</p>
                    <h3 className="mt-1 text-xl font-black">{item.product_name}</h3>
                    <p className="mt-1 text-sm text-gray-400">{item.brand || "Brand nespecificat"} · {item.store}</p>
                  </div>
                  <div className="flex flex-wrap gap-2">
                    <button onClick={() => review(item.id)} className="inline-flex items-center gap-2 rounded-lg border border-white/15 px-3 py-2 text-sm font-bold hover:bg-white/10">
                      <RefreshCw size={15} /> Verifica
                    </button>
                    <button onClick={() => approve(item.id)} className="inline-flex items-center gap-2 rounded-lg bg-emerald-400 px-3 py-2 text-sm font-black text-black hover:bg-emerald-300">
                      <CheckCircle2 size={15} /> Publica
                    </button>
                    <button onClick={() => remove(item.id)} title="Sterge propunerea" className="inline-flex h-9 w-9 items-center justify-center rounded-lg border border-red-400/30 text-red-300 hover:bg-red-400/10">
                      <Trash2 size={15} />
                    </button>
                  </div>
                </div>
              </article>
            ))}
            {!submissions.length && <p className="rounded-lg border border-white/10 bg-[#11171d] p-5 text-gray-400">Nu exista propuneri de verificat.</p>}
          </div>
        </section>

        <Link href="/privacy" className="mt-8 inline-block text-sm font-bold text-emerald-300 hover:text-emerald-200">
          Politica de confidentialitate
        </Link>
      </section>
    </main>
  );
}
