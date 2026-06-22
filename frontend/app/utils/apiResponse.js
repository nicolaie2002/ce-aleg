export async function readApiJson(response) {
  const contentType = response.headers.get("content-type") || "";

  if (contentType.includes("application/json")) {
    return response.json();
  }

  const body = await response.text().catch(() => "");
  return {
    error:
      body && body.trim().startsWith("<")
    ? "Serverul a răspuns cu o pagină în loc de date. Reîncarcă pagina și încearcă din nou."
        : "Raspunsul serverului nu a putut fi citit.",
  };
}
