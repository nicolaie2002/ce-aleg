"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import {
  Activity,
  AlertTriangle,
  Bell,
  CheckCircle2,
  CreditCard,
  Database,
  Download,
  Mail,
  Pencil,
  RefreshCw,
  Save,
  Search,
  SearchX,
  Server,
  ShieldCheck,
  Trash2,
  Users,
  Wrench,
  XCircle,
} from "lucide-react";
import { API_URL } from "../config";
import { AppHeader } from "../components/AppHeader";
import { ProductImage } from "../components/ProductImage";
import { readApiJson } from "../utils/apiResponse";

const CONTACT_EMAIL = "contact@cealeg.shop";

const submissionStatusMeta = {
  pending: {
    label: "In verificare",
    priority: 0,
    tone: "warning",
  },
  ai_approved: {
    label: "Gata de publicat",
    priority: 1,
    tone: "default",
  },
  needs_review: {
    label: "Necesita revizie",
    priority: 2,
    tone: "danger",
  },
  approved: {
    label: "Aprobat",
    priority: 3,
    tone: "default",
  },
};

function getSubmissionStatusMeta(status) {
  return submissionStatusMeta[status] || {
    label: status || "In verificare",
    priority: 4,
    tone: "warning",
  };
}

function getSubmissionImageUrl(path) {
  if (!path) return "";
  if (path.startsWith("http")) return path;
  return `${API_URL}${path}`;
}

const statLabels = {
  users: "Conturi",
  products: "Produse în catalog",
  pendingSubmissions: "Propuneri de verificat",
  searches: "Căutări salvate",
  missingProducts: "Produse negăsite",
  uncategorizedProducts: "Produse Altele",
  priceObservations: "Prețuri raportate",
  proUsers: "Utilizatori plătitori",
};

function formatDate(value) {
  if (!value) return "-";

  try {
    return new Date(value).toLocaleString("ro-RO", {
      dateStyle: "short",
      timeStyle: "short",
    });
  } catch {
    return "-";
  }
}

function compactNumber(value) {
  return new Intl.NumberFormat("ro-RO").format(Number(value || 0));
}

function monitorTone(status) {
  if (status === "danger") return "border-red-400/35 bg-red-400/10 text-red-100";
  if (status === "warning") return "border-yellow-300/35 bg-yellow-300/10 text-yellow-100";
  return "border-cyan-300/25 bg-cyan-300/10 text-cyan-100";
}

function StatCard({ label, value, icon: Icon, tone = "default", detail }) {
  const toneClass =
    tone === "danger"
      ? "border-red-400/25 bg-red-400/8"
      : tone === "warning"
        ? "border-yellow-300/25 bg-yellow-300/8"
        : "border-white/10 bg-white/[0.045]";

  return (
    <article className={`rounded-xl border p-4 ${toneClass}`}>
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-xs font-black uppercase tracking-wide text-gray-400">{label}</p>
          <p className="mt-2 text-3xl font-black text-white">{value}</p>
        </div>
        {Icon && (
          <span className="flex h-10 w-10 items-center justify-center rounded-lg bg-white/8 text-cyan-200">
            <Icon size={19} />
          </span>
        )}
      </div>
      {detail && <p className="mt-2 text-sm leading-6 text-gray-400">{detail}</p>}
    </article>
  );
}

function EmptyState({ children }) {
  return (
    <p className="rounded-lg border border-white/10 bg-black/20 p-4 text-sm text-gray-400">
      {children}
    </p>
  );
}

function EventPill({ children, tone = "default" }) {
  return (
    <span className={`inline-flex rounded-full border px-2.5 py-1 text-xs font-black ${monitorTone(tone)}`}>
      {children}
    </span>
  );
}

function ExportLink({ href, children }) {
  return (
    <a
      href={href}
      className="inline-flex items-center justify-center gap-2 rounded-lg border border-white/15 bg-white/[0.045] px-3 py-2 text-sm font-black text-white transition hover:bg-white/10"
    >
      <Download size={15} />
      {children}
    </a>
  );
}

export default function AdminPage() {
  const [overview, setOverview] = useState({});
  const [monitoring, setMonitoring] = useState(null);
  const [submissions, setSubmissions] = useState([]);
  const [misses, setMisses] = useState([]);
  const [users, setUsers] = useState([]);
  const [message, setMessage] = useState("");
  const [userSearch, setUserSearch] = useState("");
  const [emailBusy, setEmailBusy] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [emailTestAddress, setEmailTestAddress] = useState(CONTACT_EMAIL);
  const [catalogBusy, setCatalogBusy] = useState("");
  const [catalogPreview, setCatalogPreview] = useState(null);
  const [catalogSearchTerm, setCatalogSearchTerm] = useState("");
  const [catalogSearchBusy, setCatalogSearchBusy] = useState(false);
  const [catalogResults, setCatalogResults] = useState([]);
  const [productEdit, setProductEdit] = useState(null);
  const [productSaveBusy, setProductSaveBusy] = useState(false);
  const [reportFixBusyId, setReportFixBusyId] = useState(null);
  const [reportCategoryEdits, setReportCategoryEdits] = useState({});
  const [missionDigestBusy, setMissionDigestBusy] = useState("");
  const [missionDigestPreview, setMissionDigestPreview] = useState(null);

  async function loadAdmin() {
    setIsLoading(true);
    setMessage("");

    try {
      const [
        overviewResponse,
        monitoringResponse,
        submissionsResponse,
        missesResponse,
        usersResponse,
      ] = await Promise.all([
        fetch(`${API_URL}/admin/overview`),
        fetch(`${API_URL}/admin/monitoring?days=7&limit=16`),
        fetch(`${API_URL}/admin/submissions`),
        fetch(`${API_URL}/admin/search-misses?days=30&limit=40`),
        fetch(`${API_URL}/users`),
      ]);

      if (overviewResponse.status === 401) {
        window.location.assign("/login?next=/admin");
        return;
      }

      if (!overviewResponse.ok || !submissionsResponse.ok || !usersResponse.ok) {
        setMessage("Acest spațiu este disponibil doar administratorului.");
        return;
      }

      setOverview(await readApiJson(overviewResponse));
      setMonitoring(monitoringResponse.ok ? await readApiJson(monitoringResponse) : null);
      setSubmissions(await readApiJson(submissionsResponse));
      setMisses(missesResponse.ok ? await readApiJson(missesResponse) : []);
      setUsers(await readApiJson(usersResponse));
    } catch {
      setMessage("Datele de administrare nu au putut fi încărcate.");
    } finally {
      setIsLoading(false);
    }
  }

  useEffect(() => {
    queueMicrotask(loadAdmin);
  }, []);

  async function review(submissionId) {
    setMessage("Verific propunerea...");
    const response = await fetch(`${API_URL}/submissions/ai-review/${submissionId}`, {
      method: "POST",
    });
    const data = await readApiJson(response);
    setMessage(data.message || data.error);
    await loadAdmin();
  }

  async function approve(submissionId) {
    const response = await fetch(`${API_URL}/submissions/approve/${submissionId}`, {
      method: "POST",
    });
    const data = await readApiJson(response);
    const reward = data.reward || {};
    const rewardText = response.ok && reward
      ? ` Bonus: +${reward.bonusScans || 0} scanari, +${reward.coins || 0} CeCoins.`
      : "";
    setMessage(`${data.message || data.error || ""}${rewardText}`);
    await loadAdmin();
  }

  async function remove(submissionId) {
    if (!window.confirm("Ștergi propunerea?")) return;
    const response = await fetch(`${API_URL}/submissions/item/${submissionId}`, {
      method: "DELETE",
    });
    const data = await readApiJson(response);
    setMessage(data.message || data.error);
    await loadAdmin();
  }

  async function updateUserPlan(userId, plan) {
    const response = await fetch(`${API_URL}/admin/users/${userId}/plan`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ plan, status: "active" }),
    });
    const data = await readApiJson(response);
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
          (response.ok ? "Test email finalizat." : "Emailul de test nu a putut fi trimis.")
      );
      await loadAdmin();
    } catch {
      setMessage("Emailul de test nu a putut fi trimis.");
    } finally {
      setEmailBusy(false);
    }
  }

  async function runMissionDigest(apply = false) {
    setMissionDigestBusy(apply ? "send" : "preview");
    setMessage(apply ? "Trimit emailurile pentru misiuni..." : "Caut misiuni aproape gata...");

    try {
      const response = await fetch(
        `${API_URL}/admin/missions/digest?limit=150&apply=${apply ? "true" : "false"}`,
        {
          method: apply ? "POST" : "GET",
          headers: { "Content-Type": "application/json" },
          body: apply ? JSON.stringify({ apply: true, limit: 150 }) : undefined,
        }
      );
      const data = await readApiJson(response);

      if (!response.ok) {
        throw new Error(data.error || "Digest-ul de misiuni nu a putut fi procesat.");
      }

      setMissionDigestPreview(data);
      setMessage(data.message || "Digest-ul de misiuni a fost verificat.");
      await loadAdmin();
    } catch (error) {
      setMessage(error.message || "Digest-ul de misiuni nu a putut fi procesat.");
    } finally {
      setMissionDigestBusy("");
    }
  }

  async function recategorizeCatalog(apply = false, nextBatch = false) {
    const minId = nextBatch ? catalogPreview?.nextMinId : catalogPreview?.minId;
    const params = new URLSearchParams({
      limit: "500",
      apply: apply ? "true" : "false",
    });

    if (minId) {
      params.set("min_id", String(minId));
    }

    setCatalogBusy(apply ? "apply" : "preview");
    setMessage(
      apply
        ? "Actualizez categoriile produselor..."
        : nextBatch
          ? "Caut următorul batch de produse..."
          : "Caut produse care pot fi recategorizate..."
    );

    try {
      const response = await fetch(`${API_URL}/admin/catalog/recategorize?${params.toString()}`, {
        method: apply ? "POST" : "GET",
        headers: { "Content-Type": "application/json" },
        body: apply
          ? JSON.stringify({ apply: true, limit: 500, minId: minId || undefined })
          : undefined,
      });
      const data = await readApiJson(response);

      if (!response.ok) {
        throw new Error(data.error || "Catalogul nu a putut fi verificat.");
      }

      setCatalogPreview(data);
      setMessage(data.message || "Verificarea catalogului s-a terminat.");
      await loadAdmin();
    } catch (error) {
      setMessage(error.message || "Catalogul nu a putut fi verificat.");
    } finally {
      setCatalogBusy("");
    }
  }

  function productToEdit(product) {
    return {
      id: product.id,
      name: product.name || "",
      store: product.store || "",
      category: product.category || "",
      barcode: product.barcode || "",
      image: product.image || "",
      price: product.price ?? "",
      priceText: product.priceText || "",
      calories: product.calories ?? "",
      protein: product.protein ?? "",
      sugar: product.sugar ?? "",
      fat: product.fat ?? "",
      score: product.score ?? "",
      tag: product.tag || "",
      reason: product.reason || "",
      ingredients: product.ingredients || "",
      vegan: Boolean(product.vegan),
      lactoseFree: Boolean(product.lactoseFree),
      natural: Boolean(product.natural),
      notifyUsers: true,
    };
  }

  function updateProductEdit(key, value) {
    setProductEdit((current) => (current ? { ...current, [key]: value } : current));
  }

  async function searchCatalogProducts(event) {
    event?.preventDefault();
    setCatalogSearchBusy(true);
    setMessage("Caut produse in catalog...");

    try {
      const params = new URLSearchParams({
        q: catalogSearchTerm.trim(),
        limit: "20",
      });
      const response = await fetch(`${API_URL}/admin/products/search?${params.toString()}`);
      const data = await readApiJson(response);

      if (!response.ok) {
        throw new Error(data.error || "Produsele nu au putut fi cautate.");
      }

      const items = Array.isArray(data) ? data : [];
      setCatalogResults(items);
      setProductEdit(items[0] ? productToEdit(items[0]) : null);
      setMessage(items.length ? `Am gasit ${items.length} produse.` : "Nu am gasit produse pentru cautarea asta.");
    } catch (error) {
      setMessage(error.message || "Produsele nu au putut fi cautate.");
    } finally {
      setCatalogSearchBusy(false);
    }
  }

  async function saveCatalogProduct(recalculate = true) {
    if (!productEdit?.id) return;

    setProductSaveBusy(true);
    setMessage(recalculate ? "Salvez si recalculez produsul..." : "Salvez produsul...");

    try {
      const response = await fetch(`${API_URL}/admin/products/${productEdit.id}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          ...productEdit,
          recalculate,
        }),
      });
      const data = await readApiJson(response);

      if (!response.ok) {
        throw new Error(data.error || "Produsul nu a putut fi salvat.");
      }

      const updatedProduct = data.product;
      setProductEdit(productToEdit(updatedProduct));
      setCatalogResults((current) =>
        current.map((item) => (item.id === updatedProduct.id ? updatedProduct : item))
      );
      setMessage(data.message || "Produs actualizat.");
      await loadAdmin();
    } catch (error) {
      setMessage(error.message || "Produsul nu a putut fi salvat.");
    } finally {
      setProductSaveBusy(false);
    }
  }

  async function resolveAlternativeReport(eventId, category = "") {
    setReportFixBusyId(eventId);
    setMessage(category ? "Aplic categoria pentru alternativa raportată..." : "Verific alternativa raportată...");

    try {
      const response = await fetch(`${API_URL}/admin/alternative-reports/${eventId}/resolve`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(category ? { category } : {}),
      });
      const data = await readApiJson(response);

      if (!response.ok) {
        throw new Error(data.error || "Raportarea nu a putut fi rezolvată.");
      }

      setMessage(data.message || "Raportarea a fost rezolvată.");
      setReportCategoryEdits((current) => {
        const next = { ...current };
        delete next[eventId];
        return next;
      });
      await loadAdmin();
    } catch (error) {
      setMessage(error.message || "Raportarea nu a putut fi rezolvată.");
    } finally {
      setReportFixBusyId(null);
    }
  }

  async function openReportedProductInCatalog(product = {}) {
    const query = String(product.barcode || product.name || "").trim();

    if (!query) {
      setMessage("Raportarea nu are nume sau cod de bare pentru cautare.");
      return;
    }

    setCatalogSearchTerm(query);
    setCatalogSearchBusy(true);
    setMessage(`Caut produs raportat: ${query}`);

    try {
      const params = new URLSearchParams({
        q: query,
        limit: "20",
      });
      const response = await fetch(`${API_URL}/admin/products/search?${params.toString()}`);
      const data = await readApiJson(response);

      if (!response.ok) {
        throw new Error(data.error || "Produsul raportat nu a putut fi cautat.");
      }

      const items = Array.isArray(data) ? data : [];
      setCatalogResults(items);
      setProductEdit(items[0] ? productToEdit(items[0]) : null);
      setMessage(items.length ? `Am gasit ${items.length} produse pentru raportare.` : "Nu am gasit produsul raportat in catalog.");
      document.getElementById("catalog-editor")?.scrollIntoView({ behavior: "smooth", block: "start" });
    } catch (error) {
      setMessage(error.message || "Produsul raportat nu a putut fi cautat.");
    } finally {
      setCatalogSearchBusy(false);
    }
  }

  const readiness = monitoring?.backend;
  const readinessTone = readiness?.ready
    ? "default"
    : readiness?.blockers?.length
      ? "danger"
      : "warning";
  const scanIssues = monitoring?.scanIssues || {};
  const reportedAlternativeReports = scanIssues.reportedAlternatives || [];
  const reportedProductReports = scanIssues.reportedProducts || [];
  const payments = monitoring?.payments || {};
  const email = monitoring?.email || {};
  const catalog = monitoring?.catalog || {};
  const filteredUsers = useMemo(() => {
    const term = userSearch.trim().toLowerCase();
    if (!term) return users;

    return users.filter((item) => item.email?.toLowerCase().includes(term));
  }, [users, userSearch]);
  const sortedSubmissions = useMemo(() => (
    [...submissions].sort((left, right) => {
      const leftMeta = getSubmissionStatusMeta(left.status);
      const rightMeta = getSubmissionStatusMeta(right.status);

      if (leftMeta.priority !== rightMeta.priority) {
        return leftMeta.priority - rightMeta.priority;
      }

      return new Date(right.created_at || 0) - new Date(left.created_at || 0);
    })
  ), [submissions]);
  const pendingSubmissionCount = submissions.filter((item) => item.status !== "approved").length;
  const publishableSubmissionCount = submissions.filter((item) => item.status === "ai_approved").length;

  return (
    <main className="min-h-screen bg-[#080c10] text-white">
      <AppHeader actionHref="/dashboard" actionLabel="Dashboard" />
      <section className="ce-shell ce-page">
        <div className="flex flex-col gap-5 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <p className="flex items-center gap-2 text-sm font-bold text-cyan-200">
              <ShieldCheck size={16} /> Administrare platformă
            </p>
            <h1 className="mt-3 text-4xl font-black md:text-5xl">
              Monitorizare după lansare.
            </h1>
            <p className="mt-3 max-w-3xl text-gray-300">
              Urmărește produsele negăsite, scanările eșuate, alternativele slabe,
              plățile, emailurile și starea backend-ului.
            </p>
          </div>
          <button
            onClick={loadAdmin}
            disabled={isLoading}
            className="inline-flex items-center justify-center gap-2 rounded-lg border border-white/15 bg-white/[0.045] px-4 py-3 font-black text-white hover:bg-white/10 disabled:opacity-60"
          >
            <RefreshCw size={17} className={isLoading ? "animate-spin" : ""} />
            Reîncarcă datele
          </button>
        </div>

        {message && (
          <p className="mt-5 rounded-lg border border-cyan-300/25 bg-cyan-400/10 p-4 text-sm text-cyan-100">
            {message}
          </p>
        )}

        <div className="mt-7 grid gap-3 sm:grid-cols-2 lg:grid-cols-4 xl:grid-cols-7">
          {Object.entries(statLabels).map(([key, label]) => (
            <StatCard key={key} label={label} value={overview[key] ?? "-"} />
          ))}
        </div>

        <section className="mt-8 grid gap-4 xl:grid-cols-[minmax(0,1.35fr)_minmax(360px,0.65fr)]">
          <div className="rounded-2xl border border-white/10 bg-white/[0.045] p-5">
            <div className="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
              <div>
                <p className="flex items-center gap-2 text-sm font-black text-cyan-200">
                  <Activity size={16} /> Ultimele 7 zile
                </p>
                <h2 className="mt-2 text-2xl font-black">Semnale importante</h2>
              </div>
              <EventPill tone={readinessTone}>
                {readiness?.ready ? "Backend pregătit" : "Necesită atenție"}
              </EventPill>
            </div>

            <div className="mt-5 grid gap-3 md:grid-cols-2 xl:grid-cols-3">
              <StatCard
                icon={SearchX}
                label="Produse / scanări problemă"
                value={compactNumber(scanIssues.total)}
                tone={scanIssues.total ? "warning" : "default"}
                detail={`${compactNumber(scanIssues.barcodeNotFound)} coduri negăsite, ${compactNumber(scanIssues.analysisNotFound)} analize fără rezultat`}
              />
              <StatCard
                icon={AlertTriangle}
                label="Alternative slabe"
                value={compactNumber(scanIssues.alternativesLow)}
                tone={scanIssues.alternativesLow ? "warning" : "default"}
                detail="Cazuri cu prea puține alternative bune pentru produsul scanat."
              />
              <StatCard
                icon={Bell}
                label="Alternative raportate"
                value={compactNumber(scanIssues.alternativeReports)}
                tone={scanIssues.alternativeReports ? "warning" : "default"}
                detail="Recomandări marcate de utilizatori ca nepotrivite."
              />
              <StatCard
                icon={AlertTriangle}
                label="Produse raportate"
                value={compactNumber(scanIssues.productReports)}
                tone={scanIssues.productReports ? "warning" : "default"}
                detail="Date, preturi, imagini sau scoruri semnalate din pagina de rezultat."
              />
              <StatCard
                icon={CreditCard}
                label="Checkout-uri"
                value={compactNumber(payments.checkoutStarted)}
                tone={payments.checkoutErrors ? "danger" : "default"}
                detail={`${compactNumber(payments.checkoutErrors)} erori checkout`}
              />
              <StatCard
                icon={Database}
                label="Catalog"
                value={compactNumber(catalog.products)}
                detail={`${compactNumber(catalog.pendingSubmissions)} propuneri de verificat`}
              />
              <StatCard
                icon={Mail}
                label="Email"
                value={email.configured ? "Activ" : "Oprit"}
                tone={email.configured ? "default" : "danger"}
                detail={`${email.provider || "-"} · ${email.from || "-"}`}
              />
              <StatCard
                icon={Users}
                label="Abonamente active"
                value={compactNumber(payments.activeSubscriptions)}
                detail={`${compactNumber(payments.proUsers)} Pro, ${compactNumber(payments.familyUsers)} Family`}
              />
            </div>
          </div>

          <aside className="rounded-2xl border border-white/10 bg-white/[0.045] p-5">
            <p className="flex items-center gap-2 text-sm font-black text-cyan-200">
              <Server size={16} /> Backend și Render
            </p>
            <h2 className="mt-2 text-2xl font-black">
              {readiness?.ready ? "Totul arată bine" : "Verifică blocajele"}
            </h2>
            <p className="mt-2 text-sm leading-6 text-gray-400">
              Mediu: {readiness?.environment || "-"} · DB: {readiness?.database || "-"}
            </p>

            <p className="mt-1 text-xs font-bold uppercase tracking-wide text-gray-500">
              API version: {readiness?.version?.shortCommit || "-"}
            </p>

            <div className="mt-4 space-y-3">
              {(readiness?.blockers || []).map((item) => (
                <p key={item} className="rounded-lg border border-red-400/25 bg-red-400/10 p-3 text-sm text-red-100">
                  {item}
                </p>
              ))}
              {(readiness?.warnings || []).map((item) => (
                <p key={item} className="rounded-lg border border-yellow-300/25 bg-yellow-300/10 p-3 text-sm text-yellow-100">
                  {item}
                </p>
              ))}
              {readiness?.ready && !(readiness?.warnings || []).length && (
                <p className="rounded-lg border border-cyan-300/25 bg-cyan-300/10 p-3 text-sm text-cyan-100">
                  Readiness este verde. Dacă Render raportează timeout, verifică Logs/Metrics pentru cold start sau query-uri lente.
                </p>
              )}
              {readiness?.renderNote && (
                <p className="text-xs leading-5 text-gray-500">{readiness.renderNote}</p>
              )}
            </div>
          </aside>
        </section>

        <section className="mt-8 grid gap-4 xl:grid-cols-2">
          <div className="rounded-2xl border border-white/10 bg-white/[0.045] p-5">
            <div className="flex items-center justify-between gap-4">
              <div>
                <p className="flex items-center gap-2 text-sm font-black text-amber-200">
                  <SearchX size={16} /> Probleme de scanare și recomandări
                </p>
                <h2 className="mt-2 text-2xl font-black">Cele mai recente semnale</h2>
              </div>
              <div className="flex flex-wrap justify-end gap-2">
                <ExportLink href={`${API_URL}/admin/export/search-misses.csv`}>
                  Export lipsuri
                </ExportLink>
                <ExportLink href={`${API_URL}/admin/export/alternative-reports.csv`}>
                  Export rapoarte
                </ExportLink>
              </div>
            </div>
            <div className="mt-4 overflow-x-auto">
              <table className="w-full min-w-[760px] text-left text-sm">
                <thead className="text-gray-400">
                  <tr>
                    <th className="border-b border-white/10 py-3">Semnal</th>
                    <th className="border-b border-white/10 py-3">Sursă</th>
                    <th className="border-b border-white/10 py-3">Magazin</th>
                    <th className="border-b border-white/10 py-3">Rezultate</th>
                    <th className="border-b border-white/10 py-3">Dată</th>
                  </tr>
                </thead>
                <tbody>
                  {(scanIssues.recent || []).map((item) => (
                    <tr key={item.id}>
                      <td className="border-b border-white/5 py-3 font-bold text-white">{item.query}</td>
                      <td className="border-b border-white/5 py-3 text-gray-300">{item.source}</td>
                      <td className="border-b border-white/5 py-3 text-gray-400">{item.store}</td>
                      <td className="border-b border-white/5 py-3 text-amber-200">{item.resultCount}</td>
                      <td className="border-b border-white/5 py-3 text-gray-400">{formatDate(item.createdAt)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
              {!(scanIssues.recent || []).length && (
                <EmptyState>Nu există semnale recente de scanare sau alternative slabe.</EmptyState>
              )}
            </div>

            <div className="mt-6 border-t border-white/10 pt-5">
              <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
                <div>
                  <p className="flex items-center gap-2 text-sm font-black text-yellow-100">
                    <Wrench size={16} /> Alternative raportate
                  </p>
                  <p className="mt-1 text-sm text-gray-400">
                    Repară rapid categoria unei alternative nepotrivite.
                  </p>
                </div>
                <EventPill tone={reportedAlternativeReports.length ? "warning" : "default"}>
                  {compactNumber(reportedAlternativeReports.length)} rapoarte
                </EventPill>
              </div>

              <div className="mt-4 space-y-3">
                {reportedAlternativeReports.map((event) => {
                  const metadata = event.metadata || {};
                  const scannedProduct = metadata.scannedProduct || {};
                  const alternativeProduct = metadata.alternativeProduct || {};
                  const review = metadata.adminReview || metadata.autoFix || null;
                  const categoryValue =
                    reportCategoryEdits[event.id] ?? alternativeProduct.category ?? "";

                  return (
                    <article key={event.id} className="rounded-xl border border-white/10 bg-black/20 p-4">
                      <div className="flex flex-col gap-3 xl:flex-row xl:items-start xl:justify-between">
                        <div className="min-w-0">
                          <div className="flex flex-wrap items-center gap-2">
                            <p className="font-black text-white">
                              {alternativeProduct.name || "Alternativă fără nume"}
                            </p>
                            {review && (
                              <EventPill tone={review.fixed ? "default" : "warning"}>
                                {review.fixed ? "rezolvat" : "verificat"}
                              </EventPill>
                            )}
                          </div>
                          <p className="mt-1 text-sm leading-6 text-gray-400">
                            Pentru: {scannedProduct.name || scannedProduct.barcode || "-"} · {event.userEmail} · {formatDate(event.createdAt)}
                          </p>
                          <p className="mt-1 text-sm text-gray-500">
                            Magazin: {metadata.store || "-"} · Cerință: {metadata.request || "-"}
                          </p>
                        </div>

                        <div className="flex w-full flex-col gap-2 xl:w-[27rem]">
                          <label className="text-xs font-black uppercase text-gray-400" htmlFor={`alternative-category-${event.id}`}>
                            Categoria corectă
                          </label>
                          <div className="flex flex-col gap-2 sm:flex-row">
                            <input
                              id={`alternative-category-${event.id}`}
                              value={categoryValue}
                              onChange={(inputEvent) =>
                                setReportCategoryEdits((current) => ({
                                  ...current,
                                  [event.id]: inputEvent.target.value,
                                }))
                              }
                              className="min-h-11 min-w-0 flex-1 rounded-lg border border-white/10 bg-black/30 px-3 text-sm font-semibold text-white outline-none placeholder:text-gray-500 focus:border-cyan-300"
                              placeholder="ex: Iaurturi, Bere, Mezeluri"
                            />
                            <button
                              type="button"
                              onClick={() => resolveAlternativeReport(event.id)}
                              disabled={reportFixBusyId === event.id}
                              className="inline-flex items-center justify-center gap-2 rounded-lg border border-white/15 px-3 py-2 text-sm font-black text-white hover:bg-white/10 disabled:opacity-60"
                            >
                              <RefreshCw size={15} className={reportFixBusyId === event.id ? "animate-spin" : ""} />
                              Auto
                            </button>
                            <button
                              type="button"
                              onClick={() => resolveAlternativeReport(event.id, categoryValue.trim())}
                              disabled={reportFixBusyId === event.id || !categoryValue.trim()}
                              className="inline-flex items-center justify-center gap-2 rounded-lg bg-cyan-200 px-3 py-2 text-sm font-black text-black hover:bg-white disabled:opacity-60"
                            >
                              <CheckCircle2 size={15} />
                              Aplică
                            </button>
                          </div>
                        </div>
                      </div>
                    </article>
                  );
                })}
                {!reportedAlternativeReports.length && (
                  <EmptyState>Nu există alternative raportate în intervalul selectat.</EmptyState>
                )}
              </div>
            </div>

            <div className="mt-6 border-t border-white/10 pt-5">
              <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
                <div>
                  <p className="flex items-center gap-2 text-sm font-black text-yellow-100">
                    <AlertTriangle size={16} /> Produse raportate
                  </p>
                  <p className="mt-1 text-sm text-gray-400">
                    Date gresite semnalate direct din pagina de rezultat.
                  </p>
                </div>
                <EventPill tone={reportedProductReports.length ? "warning" : "default"}>
                  {compactNumber(reportedProductReports.length)} rapoarte
                </EventPill>
              </div>

              <div className="mt-4 space-y-3">
                {reportedProductReports.map((event) => {
                  const metadata = event.metadata || {};
                  const product = metadata.product || {};

                  return (
                    <article key={event.id} className="rounded-xl border border-white/10 bg-black/20 p-4">
                      <div className="flex flex-col gap-3 xl:flex-row xl:items-start xl:justify-between">
                        <div className="min-w-0">
                          <div className="flex flex-wrap items-center gap-2">
                            <p className="font-black text-white">
                              {product.name || product.barcode || "Produs fara nume"}
                            </p>
                            <EventPill tone="warning">
                              {metadata.reasonLabel || metadata.reason || "raport"}
                            </EventPill>
                          </div>
                          <p className="mt-1 text-sm leading-6 text-gray-400">
                            {event.userEmail} · {formatDate(event.createdAt)} · {metadata.store || "-"}
                          </p>
                          <p className="mt-1 text-sm text-gray-500">
                            {product.category || "fara categorie"} · {product.barcode || "fara barcode"} · scor {product.score || "-"}
                          </p>
                          {metadata.details && (
                            <p className="mt-3 rounded-lg border border-yellow-300/15 bg-yellow-300/8 p-3 text-sm leading-6 text-yellow-50">
                              {metadata.details}
                            </p>
                          )}
                        </div>

                        <button
                          type="button"
                          onClick={() => openReportedProductInCatalog(product)}
                          className="inline-flex items-center justify-center gap-2 rounded-lg bg-cyan-200 px-3 py-2 text-sm font-black text-black hover:bg-white"
                        >
                          <Pencil size={15} />
                          Deschide in editor
                        </button>
                      </div>
                    </article>
                  );
                })}
                {!reportedProductReports.length && (
                  <EmptyState>Nu exista produse raportate in intervalul selectat.</EmptyState>
                )}
              </div>
            </div>
          </div>

          <div className="rounded-2xl border border-white/10 bg-white/[0.045] p-5">
            <p className="flex items-center gap-2 text-sm font-black text-cyan-200">
              <Bell size={16} /> Plăți și emailuri
            </p>
            <div className="flex items-center justify-between gap-4">
              <h2 className="mt-2 text-2xl font-black">Evenimente recente</h2>
              <ExportLink href={`${API_URL}/admin/export/payment-events.csv`}>
                Export plăți
              </ExportLink>
            </div>
            <div className="mt-4 space-y-3">
              {(payments.recentEvents || []).map((event) => {
                const isError = event.type === "payment_error";
                return (
                  <article key={event.id} className="rounded-lg border border-white/10 bg-black/20 p-4">
                    <div className="flex items-start justify-between gap-3">
                      <div>
                        <p className="font-black text-white">{event.userEmail}</p>
                        <p className="mt-1 text-sm text-gray-400">
                          {event.source} · {formatDate(event.createdAt)}
                        </p>
                      </div>
                      <EventPill tone={isError ? "danger" : "default"}>
                        {isError ? "eroare" : event.type}
                      </EventPill>
                    </div>
                    {event.metadata?.error && (
                      <p className="mt-3 text-sm leading-6 text-red-100">{event.metadata.error}</p>
                    )}
                    {event.metadata?.coins && (
                      <p className="mt-3 text-sm font-bold text-yellow-100">
                        {event.metadata.coins} CeCoins
                      </p>
                    )}
                  </article>
                );
              })}
              {!(payments.recentEvents || []).length && (
                <EmptyState>Nu există evenimente recente de plată în intervalul selectat.</EmptyState>
              )}
            </div>
          </div>
        </section>

        <section className="mt-8 rounded-2xl border border-white/10 bg-white/[0.045] p-5">
          <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
            <div>
              <p className="flex items-center gap-2 text-sm font-black text-cyan-200">
                <Database size={16} /> Catalog România
              </p>
              <h2 className="mt-2 text-2xl font-black">Calitate și recategorizare</h2>
              <p className="mt-2 max-w-3xl text-sm leading-6 text-gray-400">
                Folosește recategorizarea pentru produsele importate ca `Altele`.
                Algoritmul aplică taxonomia curentă, recalculează scorul și păstrează
                recomandările în aceeași familie de produs.
              </p>
            </div>
            <div className="flex flex-wrap gap-2">
              <button
                type="button"
                onClick={() => recategorizeCatalog(false)}
                disabled={Boolean(catalogBusy)}
                className="inline-flex items-center justify-center gap-2 rounded-lg border border-white/15 px-4 py-3 text-sm font-black text-white hover:bg-white/10 disabled:opacity-60"
              >
                <Search size={16} />
                {catalogBusy === "preview" ? "Verific..." : "Preview"}
              </button>
              <button
                type="button"
                onClick={() => recategorizeCatalog(true)}
                disabled={Boolean(catalogBusy)}
                className="inline-flex items-center justify-center gap-2 rounded-lg bg-cyan-200 px-4 py-3 text-sm font-black text-black hover:bg-white disabled:opacity-60"
              >
                <CheckCircle2 size={16} />
                {catalogBusy === "apply" ? "Aplic..." : "Aplică recategorizarea"}
              </button>
              <button
                type="button"
                onClick={() => recategorizeCatalog(false, true)}
                disabled={Boolean(catalogBusy) || !catalogPreview?.nextMinId}
                className="inline-flex items-center justify-center gap-2 rounded-lg border border-white/15 px-4 py-3 text-sm font-black text-white hover:bg-white/10 disabled:opacity-50"
              >
                <RefreshCw size={16} />
                Urmatorul batch
              </button>
            </div>
          </div>

          <div className="mt-5 grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
            <StatCard
              label="Produse"
              value={compactNumber(catalog.products)}
              detail="Total în baza curentă"
            />
            <StatCard
              label="Altele"
              value={compactNumber(catalog.uncategorizedProducts)}
              tone={catalog.uncategorizedProducts ? "warning" : "default"}
              detail={`${catalog.uncategorizedRate ?? 0}% din catalog`}
            />
            <StatCard
              label="Barcode"
              value={`${catalog.barcodeCoverage ?? 0}%`}
              detail={`${compactNumber(catalog.withBarcode)} produse`}
            />
            <StatCard
              label="Imagini"
              value={`${catalog.imageCoverage ?? 0}%`}
              detail={`${compactNumber(catalog.withImage)} produse`}
            />
            <StatCard
              label="Nutriție"
              value={`${catalog.nutritionCoverage ?? 0}%`}
              detail={`${compactNumber(catalog.withNutrition)} produse`}
            />
          </div>

          {catalogPreview && (
            <div className="mt-5 rounded-xl border border-white/10 bg-black/20 p-4">
              <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
                <p className="font-black text-white">
                  {catalogPreview.applied ? "Actualizare aplicată" : "Preview recategorizare"}
                </p>
                <EventPill tone={catalogPreview.changed ? "warning" : "default"}>
                  {compactNumber(catalogPreview.changed)} schimbări din {compactNumber(catalogPreview.scanned)} verificate
                </EventPill>
              </div>
              <div className="mt-3 flex flex-wrap gap-2 text-xs font-bold uppercase tracking-wide text-gray-500">
                <span>ID start {catalogPreview.minId || 1}</span>
                <span>Ultimul ID {catalogPreview.lastScannedId || "-"}</span>
                <span>{catalogPreview.hasMore ? "Mai exista batch-uri" : "Batch final"}</span>
              </div>
              <div className="mt-3 grid gap-2 lg:grid-cols-2">
                {(catalogPreview.changes || []).slice(0, 8).map((item) => (
                  <article key={`${item.id}-${item.newCategory}`} className="rounded-lg border border-white/10 bg-white/[0.035] p-3">
                    <p className="font-bold text-white">{item.name}</p>
                    <p className="mt-1 text-sm text-gray-400">
                      {item.oldCategory} → <span className="text-cyan-100">{item.newCategory}</span>
                    </p>
                  </article>
                ))}
              </div>
              {!(catalogPreview.changes || []).length && (
                <p className="mt-3 text-sm text-gray-400">
                  Nu am găsit produse care pot fi recategorizate în batch-ul verificat.
                </p>
              )}
            </div>
          )}

          <div id="catalog-editor" className="mt-6 scroll-mt-6 border-t border-white/10 pt-5">
            <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
              <div>
                <p className="flex items-center gap-2 text-sm font-black text-cyan-200">
                  <Pencil size={16} /> Editare rapida produs
                </p>
                <h3 className="mt-2 text-xl font-black text-white">Corecteaza catalogul fara SQL</h3>
                <p className="mt-2 max-w-3xl text-sm leading-6 text-gray-400">
                  Cauta dupa nume, cod de bare, categorie sau magazin. Salveaza cu recalculare ca scorul,
                  eticheta si motivul sa ramana aliniate cu taxonomia curenta.
                </p>
              </div>
              <form onSubmit={searchCatalogProducts} className="flex w-full flex-col gap-2 sm:flex-row lg:max-w-xl">
                <input
                  value={catalogSearchTerm}
                  onChange={(event) => setCatalogSearchTerm(event.target.value)}
                  className="min-h-12 flex-1 rounded-lg border border-white/10 bg-black/30 px-4 text-white outline-none placeholder:text-gray-500 focus:border-cyan-300"
                  placeholder="Nume produs, barcode, categorie..."
                />
                <button
                  type="submit"
                  disabled={catalogSearchBusy}
                  className="inline-flex items-center justify-center gap-2 rounded-lg border border-white/15 px-4 py-3 text-sm font-black text-white hover:bg-white/10 disabled:opacity-60"
                >
                  <Search size={16} />
                  {catalogSearchBusy ? "Caut..." : "Cauta"}
                </button>
              </form>
            </div>

            <div className="mt-5 grid gap-5 xl:grid-cols-[minmax(260px,0.65fr)_minmax(0,1.35fr)]">
              <div className="space-y-2">
                {catalogResults.map((product) => (
                  <button
                    key={product.id}
                    type="button"
                    onClick={() => setProductEdit(productToEdit(product))}
                    className={`w-full rounded-lg border px-3 py-3 text-left transition ${
                      productEdit?.id === product.id
                        ? "border-cyan-300/50 bg-cyan-300/10"
                        : "border-white/10 bg-white/[0.035] hover:bg-white/10"
                    }`}
                  >
                    <span className="block font-bold text-white">{product.name}</span>
                    <span className="mt-1 block text-xs text-gray-400">
                      #{product.id} · {product.category || "fara categorie"} · {product.store || "fara magazin"}
                    </span>
                    <span className="mt-1 block text-xs text-gray-500">{product.barcode || "fara barcode"}</span>
                  </button>
                ))}
                {!catalogResults.length && (
                  <EmptyState>Cauta un produs sau lasa campul gol pentru produse cu categoria Altele.</EmptyState>
                )}
              </div>

              {productEdit ? (
                <div className="grid gap-3 md:grid-cols-2">
                  <label className="text-sm font-bold text-gray-300">
                    Nume
                    <input
                      value={productEdit.name}
                      onChange={(event) => updateProductEdit("name", event.target.value)}
                      className="mt-1 min-h-11 w-full rounded-lg border border-white/10 bg-black/30 px-3 text-white outline-none focus:border-cyan-300"
                    />
                  </label>
                  <label className="text-sm font-bold text-gray-300">
                    Barcode
                    <input
                      value={productEdit.barcode}
                      onChange={(event) => updateProductEdit("barcode", event.target.value)}
                      className="mt-1 min-h-11 w-full rounded-lg border border-white/10 bg-black/30 px-3 text-white outline-none focus:border-cyan-300"
                    />
                  </label>
                  <label className="text-sm font-bold text-gray-300">
                    Magazin
                    <input
                      value={productEdit.store}
                      onChange={(event) => updateProductEdit("store", event.target.value)}
                      className="mt-1 min-h-11 w-full rounded-lg border border-white/10 bg-black/30 px-3 text-white outline-none focus:border-cyan-300"
                    />
                  </label>
                  <label className="text-sm font-bold text-gray-300">
                    Categorie
                    <input
                      value={productEdit.category}
                      onChange={(event) => updateProductEdit("category", event.target.value)}
                      className="mt-1 min-h-11 w-full rounded-lg border border-white/10 bg-black/30 px-3 text-white outline-none focus:border-cyan-300"
                    />
                  </label>
                  {["calories", "protein", "sugar", "fat", "score"].map((field) => (
                    <label key={field} className="text-sm font-bold text-gray-300">
                      {field === "calories" ? "Calorii" : field === "protein" ? "Proteina" : field === "sugar" ? "Zahar" : field === "fat" ? "Grasimi" : "Scor"}
                      <input
                        value={productEdit[field]}
                        onChange={(event) => updateProductEdit(field, event.target.value)}
                        className="mt-1 min-h-11 w-full rounded-lg border border-white/10 bg-black/30 px-3 text-white outline-none focus:border-cyan-300"
                        inputMode="decimal"
                      />
                    </label>
                  ))}
                  <label className="text-sm font-bold text-gray-300 md:col-span-2">
                    Ingrediente
                    <textarea
                      value={productEdit.ingredients}
                      onChange={(event) => updateProductEdit("ingredients", event.target.value)}
                      rows={3}
                      className="mt-1 w-full rounded-lg border border-white/10 bg-black/30 px-3 py-2 text-white outline-none focus:border-cyan-300"
                    />
                  </label>
                  <label className="text-sm font-bold text-gray-300 md:col-span-2">
                    Motiv
                    <textarea
                      value={productEdit.reason}
                      onChange={(event) => updateProductEdit("reason", event.target.value)}
                      rows={3}
                      className="mt-1 w-full rounded-lg border border-white/10 bg-black/30 px-3 py-2 text-white outline-none focus:border-cyan-300"
                    />
                  </label>
                  <div className="flex flex-wrap gap-3 md:col-span-2">
                    {[
                      ["vegan", "Vegan"],
                      ["lactoseFree", "Fara lactoza"],
                      ["natural", "Natural"],
                    ].map(([field, label]) => (
                      <label key={field} className="inline-flex items-center gap-2 text-sm font-bold text-gray-300">
                        <input
                          type="checkbox"
                          checked={Boolean(productEdit[field])}
                          onChange={(event) => updateProductEdit(field, event.target.checked)}
                          className="h-4 w-4 accent-cyan-300"
                        />
                        {label}
                      </label>
                    ))}
                  </div>
                  <label className="flex items-start gap-3 rounded-lg border border-cyan-300/20 bg-cyan-300/10 p-3 text-sm font-bold text-cyan-50 md:col-span-2">
                    <input
                      type="checkbox"
                      checked={Boolean(productEdit.notifyUsers)}
                      onChange={(event) => updateProductEdit("notifyUsers", event.target.checked)}
                      className="mt-1 h-4 w-4 shrink-0 accent-cyan-300"
                    />
                    <span>
                      Anunta utilizatorii care au scanat sau raportat produsul
                      <span className="mt-1 block text-xs font-semibold leading-5 text-cyan-100/75">
                        Se trimite doar daca exista o modificare vizibila si fiecare utilizator are cooldown anti-dublare.
                      </span>
                    </span>
                  </label>
                  <div className="flex flex-wrap gap-2 md:col-span-2">
                    <button
                      type="button"
                      onClick={() => saveCatalogProduct(true)}
                      disabled={productSaveBusy}
                      className="inline-flex items-center justify-center gap-2 rounded-lg bg-cyan-200 px-4 py-3 text-sm font-black text-black hover:bg-white disabled:opacity-60"
                    >
                      <RefreshCw size={16} />
                      {productSaveBusy ? "Salvez..." : "Salveaza + recalculeaza"}
                    </button>
                    <button
                      type="button"
                      onClick={() => saveCatalogProduct(false)}
                      disabled={productSaveBusy}
                      className="inline-flex items-center justify-center gap-2 rounded-lg border border-white/15 px-4 py-3 text-sm font-black text-white hover:bg-white/10 disabled:opacity-60"
                    >
                      <Save size={16} />
                      Salveaza manual
                    </button>
                  </div>
                </div>
              ) : (
                <EmptyState>Selecteaza un produs pentru editare.</EmptyState>
              )}
            </div>
          </div>
        </section>

        <section className="mt-8 rounded-2xl border border-white/10 bg-white/[0.045] p-5">
          <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
            <div>
              <h2 className="text-2xl font-black">Sistem email</h2>
              <p className="mt-2 text-sm text-gray-400">
                Trimite un email de test către adresa profesională a site-ului. Testele apar apoi în monitorizare.
              </p>
              {email.lastProviderError && (
                <p className="mt-3 rounded-lg border border-red-400/25 bg-red-400/10 p-3 text-sm text-red-100">
                  Ultima eroare provider: {email.lastProviderError}
                </p>
              )}
            </div>
            <div className="flex w-full flex-col gap-2 md:w-auto md:min-w-[420px]">
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
                  className="inline-flex items-center justify-center gap-2 rounded-lg bg-cyan-200 px-5 py-3 font-black text-black hover:bg-white disabled:cursor-not-allowed disabled:opacity-60"
                >
                  <Mail size={17} /> {emailBusy ? "Se trimite..." : "Testează email"}
                </button>
              </div>
            </div>
          </div>

          <div className="mt-5 grid gap-4 lg:grid-cols-[minmax(0,1fr)_minmax(320px,0.8fr)]">
            <div className="rounded-xl border border-white/10 bg-black/20 p-4">
              <p className="flex items-center gap-2 text-sm font-black text-cyan-200">
                <Bell size={16} /> Misiuni aproape gata
              </p>
              <h3 className="mt-2 text-xl font-black text-white">Digest saptamanal controlat</h3>
              <p className="mt-2 text-sm leading-6 text-gray-400">
                Gaseste utilizatori cu misiuni peste 60% progres si trimite un email scurt
                catre pagina /missions. Fiecare cont este protejat de cooldown de 6 zile.
              </p>
              <div className="mt-4 flex flex-wrap gap-2">
                <button
                  type="button"
                  onClick={() => runMissionDigest(false)}
                  disabled={Boolean(missionDigestBusy)}
                  className="inline-flex items-center justify-center gap-2 rounded-lg border border-white/15 px-4 py-3 text-sm font-black text-white hover:bg-white/10 disabled:opacity-60"
                >
                  <Search size={16} />
                  {missionDigestBusy === "preview" ? "Caut..." : "Preview digest"}
                </button>
                <button
                  type="button"
                  onClick={() => runMissionDigest(true)}
                  disabled={Boolean(missionDigestBusy) || !missionDigestPreview?.eligible || !email.configured}
                  className="inline-flex items-center justify-center gap-2 rounded-lg bg-cyan-200 px-4 py-3 text-sm font-black text-black hover:bg-white disabled:opacity-50"
                >
                  <Mail size={16} />
                  {missionDigestBusy === "send" ? "Trimit..." : "Trimite digest"}
                </button>
              </div>
            </div>

            <div className="rounded-xl border border-white/10 bg-black/20 p-4">
              <div className="flex flex-wrap gap-2">
                <EventPill tone={email.configured ? "default" : "danger"}>
                  {email.configured ? "email activ" : "email oprit"}
                </EventPill>
                <EventPill tone="default">
                  {compactNumber(email.missionDigests)} trimise in fereastra
                </EventPill>
              </div>
              {missionDigestPreview ? (
                <div className="mt-4 space-y-3">
                  <p className="text-sm font-bold text-gray-300">
                    {compactNumber(missionDigestPreview.eligible)} eligibili din {compactNumber(missionDigestPreview.scanned)} verificati.
                    {missionDigestPreview.applied ? ` Trimise: ${compactNumber(missionDigestPreview.sent)}.` : ""}
                  </p>
                  {(missionDigestPreview.recipients || []).slice(0, 4).map((recipient) => (
                    <article key={recipient.userId} className="rounded-lg border border-white/10 bg-white/[0.035] p-3">
                      <p className="font-bold text-white">{recipient.name || recipient.email}</p>
                      <p className="mt-1 text-sm text-gray-400">
                        {recipient.topMission} · {recipient.topProgress}% progres
                      </p>
                    </article>
                  ))}
                  {!(missionDigestPreview.recipients || []).length && (
                    <p className="text-sm text-gray-400">Nu exista destinatari eligibili in batch-ul verificat.</p>
                  )}
                </div>
              ) : (
                <p className="mt-4 text-sm leading-6 text-gray-400">
                  Ruleaza preview inainte de trimitere. Butonul de trimitere ramane blocat pana exista destinatari eligibili.
                </p>
              )}
            </div>
          </div>
        </section>

        <section className="mt-8 rounded-2xl border border-white/10 bg-white/[0.045] p-5">
          <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
            <div>
              <p className="flex items-center gap-2 text-sm font-black text-amber-200">
                <SearchX size={16} /> Produse negăsite
              </p>
              <h2 className="mt-2 text-2xl font-black">Ce caută oamenii și lipsește</h2>
              <p className="mt-2 text-sm text-gray-400">
                Interogări cu zero rezultate în ultimele 30 de zile. Prioritizează-le pentru import sau verificare manuală.
              </p>
            </div>
          </div>

          <div className="mt-5 overflow-x-auto">
            <table className="w-full min-w-[760px] text-left text-sm">
              <thead className="text-gray-400">
                <tr>
                  <th className="border-b border-white/10 py-3">Căutare</th>
                  <th className="border-b border-white/10 py-3">Magazin</th>
                  <th className="border-b border-white/10 py-3">Sursa</th>
                  <th className="border-b border-white/10 py-3">Apariții</th>
                  <th className="border-b border-white/10 py-3">Ultima dată</th>
                </tr>
              </thead>
              <tbody>
                {misses.map((item) => (
                  <tr key={`${item.query}-${item.store}-${item.source}`}>
                    <td className="border-b border-white/5 py-3 font-bold text-white">{item.query}</td>
                    <td className="border-b border-white/5 py-3 text-gray-300">{item.store}</td>
                    <td className="border-b border-white/5 py-3 text-gray-400">{item.source}</td>
                    <td className="border-b border-white/5 py-3 font-black text-amber-200">{item.count}</td>
                    <td className="border-b border-white/5 py-3 text-gray-400">{formatDate(item.lastSeen)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            {!misses.length && <EmptyState>Nu există încă produse negăsite în perioada selectată.</EmptyState>}
          </div>
        </section>

        <section className="mt-8 rounded-2xl border border-white/10 bg-white/[0.045] p-5">
          <div className="flex flex-col justify-between gap-4 lg:flex-row lg:items-end">
            <div className="order-2 w-full lg:max-w-sm">
              <label className="text-xs font-black uppercase text-gray-400" htmlFor="admin-user-search">
                Caută utilizator după email
              </label>
              <div className="mt-2 flex items-center gap-2 rounded-xl border border-white/10 bg-black/25 px-3 py-2 focus-within:border-cyan-300/50">
                <Search size={17} className="text-cyan-200" />
                <input
                  id="admin-user-search"
                  value={userSearch}
                  onChange={(event) => setUserSearch(event.target.value)}
                  type="search"
                  placeholder="ex: contact@cealeg.shop"
                  className="min-w-0 flex-1 bg-transparent text-sm font-semibold text-white outline-none placeholder:text-gray-500"
                />
                {userSearch && (
                  <button
                    type="button"
                    onClick={() => setUserSearch("")}
                    className="rounded-lg p-1 text-gray-400 hover:bg-white/10 hover:text-white"
                    aria-label="Șterge căutarea"
                  >
                    <XCircle size={16} />
                  </button>
                )}
              </div>
              <p className="mt-2 text-xs text-gray-500">
                {filteredUsers.length} din {users.length} conturi afișate
              </p>
            </div>
            <div>
              <h2 className="text-2xl font-black">Planuri utilizatori</h2>
              <p className="mt-2 text-sm text-gray-400">
                Folosește activarea manuală doar pentru suport punctual sau testare internă.
              </p>
            </div>
          </div>
          <div className="mt-4 overflow-x-auto">
            <table className="w-full min-w-[760px] text-left text-sm">
              <thead className="text-gray-400">
                <tr>
                  <th className="border-b border-white/10 py-3">Email</th>
                  <th className="border-b border-white/10 py-3">Admin</th>
                  <th className="border-b border-white/10 py-3">Plan</th>
                  <th className="border-b border-white/10 py-3">Acțiuni</th>
                </tr>
              </thead>
              <tbody>
                {filteredUsers.map((item) => (
                  <tr key={item.id}>
                    <td className="border-b border-white/5 py-3">{item.email}</td>
                    <td className="border-b border-white/5 py-3">{item.is_admin ? "da" : "nu"}</td>
                    <td className="border-b border-white/5 py-3 font-bold text-cyan-200">{item.plan || "free"}</td>
                    <td className="border-b border-white/5 py-3">
                      <div className="flex flex-wrap gap-2">
                        {["free", "pro", "family"].map((plan) => (
                          <button
                            key={plan}
                            onClick={() => updateUserPlan(item.id, plan)}
                            className="rounded-md border border-white/15 px-3 py-1.5 font-bold hover:bg-white/10"
                          >
                            {plan}
                          </button>
                        ))}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            {!filteredUsers.length && (
              <EmptyState>
                Nu am găsit niciun utilizator pentru emailul introdus.
              </EmptyState>
            )}
          </div>
        </section>

        <section className="mt-8">
          <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
            <div>
              <p className="flex items-center gap-2 text-sm font-black text-cyan-200">
                <Database size={16} /> Coada catalog
              </p>
              <h2 className="mt-2 text-2xl font-black">Propuneri recente</h2>
            </div>
            <div className="flex flex-wrap gap-2">
              <EventPill tone={pendingSubmissionCount ? "warning" : "default"}>
                {compactNumber(pendingSubmissionCount)} in lucru
              </EventPill>
              <EventPill tone={publishableSubmissionCount ? "default" : "warning"}>
                {compactNumber(publishableSubmissionCount)} gata
              </EventPill>
            </div>
          </div>
          <div className="mt-4 space-y-3">
            {sortedSubmissions.map((item) => {
              const statusMeta = getSubmissionStatusMeta(item.status);
              const canPublish = item.status === "ai_approved";

              return (
              <article key={item.id} className="rounded-2xl border border-white/10 bg-white/[0.045] p-5">
                <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
                  <ProductImage
                    src={getSubmissionImageUrl(item.front_image)}
                    alt={item.product_name}
                    containerClassName="h-20 w-20 shrink-0 rounded-xl"
                  />
                  <div>
                    <EventPill tone={statusMeta.tone}>{statusMeta.label}</EventPill>
                    <h3 className="mt-1 text-xl font-black">{item.product_name}</h3>
                    <p className="mt-1 text-sm text-gray-400">
                      {item.brand || "Brand nespecificat"} - {item.store}
                    </p>
                    <p className="mt-2 text-xs font-bold text-gray-500">
                      {item.barcode || "fara barcode"} - {item.category || "fara categorie"} - Kcal {item.calories ?? "-"} / Zahar {item.sugar ?? "-"}g
                    </p>
                  </div>
                  <div className="flex flex-wrap gap-2">
                    <button
                      onClick={() => review(item.id)}
                      className="inline-flex items-center gap-2 rounded-lg border border-white/15 px-3 py-2 text-sm font-bold hover:bg-white/10"
                    >
                      <RefreshCw size={15} /> Verifica
                    </button>
                    <button
                      onClick={() => approve(item.id)}
                      disabled={!canPublish}
                      className="inline-flex items-center gap-2 rounded-lg bg-cyan-200 px-3 py-2 text-sm font-black text-black hover:bg-white disabled:cursor-not-allowed disabled:bg-white/10 disabled:text-gray-500"
                    >
                      <CheckCircle2 size={15} /> Publica
                    </button>
                    <button
                      onClick={() => remove(item.id)}
                      title="Sterge propunerea"
                      className="inline-flex h-9 w-9 items-center justify-center rounded-lg border border-red-400/30 text-red-300 hover:bg-red-400/10"
                    >
                      <Trash2 size={15} />
                    </button>
                  </div>
                </div>
              </article>
              );
            })}
            {!sortedSubmissions.length && <EmptyState>Nu exista propuneri de verificat.</EmptyState>}
          </div>
        </section>

        <div className="mt-8 flex flex-wrap gap-4 text-sm font-bold">
          <Link href="/support" className="text-cyan-200 hover:text-white">
            Suport
          </Link>
          <Link href="/privacy" className="text-cyan-200 hover:text-white">
            Politica de confidențialitate
          </Link>
          <Link href="/terms" className="text-cyan-200 hover:text-white">
            Termeni
          </Link>
        </div>
      </section>
    </main>
  );
}
