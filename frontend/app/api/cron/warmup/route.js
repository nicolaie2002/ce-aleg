export const dynamic = "force-dynamic";

const backendUrl = process.env.BACKEND_URL || "http://127.0.0.1:5001";

function readSecret(value, name) {
  let secret = String(value || "").trim().replace(/^['"]|['"]$/g, "");
  const prefixedName = `${name}=`;

  if (secret.startsWith(prefixedName)) {
    secret = secret.slice(prefixedName.length).trim().replace(/^['"]|['"]$/g, "");
  }

  return secret;
}

export async function GET(request) {
  const cronSecret = readSecret(process.env.CRON_SECRET, "CRON_SECRET");
  const authHeader = request.headers.get("authorization") || "";

  if (!cronSecret || authHeader !== `Bearer ${cronSecret}`) {
    return Response.json({ error: "Unauthorized" }, { status: 401 });
  }

  let response;

  try {
    response = await fetch(`${backendUrl}/health`, {
      cache: "no-store",
      headers: {
        "User-Agent": "CeAlegWarmup/1.0",
      },
    });
  } catch (error) {
    return Response.json(
      {
        ok: false,
        error: "Backend warm-up request failed",
        detail: error instanceof Error ? error.message : "Unknown fetch error",
      },
      { status: 502 }
    );
  }

  const data = await response.json().catch(() => ({}));

  return Response.json(
    {
      ok: response.ok,
      backendStatus: response.status,
      ...data,
    },
    { status: response.ok ? 200 : response.status }
  );
}
