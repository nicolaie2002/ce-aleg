export const dynamic = "force-dynamic";

const backendUrl = process.env.BACKEND_URL || "http://127.0.0.1:5001";

export async function GET(request) {
  const cronSecret = process.env.CRON_SECRET;
  const authHeader = request.headers.get("authorization") || "";

  if (!cronSecret || authHeader !== `Bearer ${cronSecret}`) {
    return Response.json({ error: "Unauthorized" }, { status: 401 });
  }

  let response;

  try {
    response = await fetch(`${backendUrl}/internal/cron/maintenance`, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${cronSecret}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        recategorize: true,
        recategorizeLimit: 300,
        sendDigest: true,
        digestLimit: 100,
      }),
      cache: "no-store",
    });
  } catch (error) {
    return Response.json(
      {
        ok: false,
        error: "Backend cron maintenance request failed",
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
