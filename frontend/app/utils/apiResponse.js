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
        : "Răspunsul serverului nu a putut fi citit.",
  };
}

const apiErrorTranslations = {
  "Autentificare necesară.": "Sign in is required.",
  "Autentificare necesara.": "Sign in is required.",
  "Acces rezervat administratorului.": "Administrator access is required.",
  "Nu poți accesa datele altui cont.": "You cannot access another account's data.",
  "Nu poti accesa datele altui cont.": "You cannot access another account's data.",
  "Prea multe cereri. Reîncearcă în câteva secunde.": "Too many requests. Try again in a few seconds.",
  "Prea multe cereri. Reincearca in cateva secunde.": "Too many requests. Try again in a few seconds.",
  "Prea multe încercări. Așteaptă puțin.": "Too many attempts. Please wait a moment.",
  "Cererea a fost blocata din motive de securitate.": "The request was blocked for security reasons.",
  "Emailul și parola sunt obligatorii.": "Email and password are required.",
  "Emailul si parola sunt obligatorii.": "Email and password are required.",
  "Email sau parolă greșită.": "Wrong email or password.",
  "Email sau parola gresita.": "Wrong email or password.",
  "Confirma emailul inainte sa intri in cont.": "Confirm your email before signing in.",
  "Numele, emailul și parola sunt obligatorii.": "Name, email and password are required.",
  "Numele, emailul si parola sunt obligatorii.": "Name, email and password are required.",
  "Trebuie să accepți Termenii și Politica de confidențialitate.": "You must accept the Terms and Privacy Policy.",
  "Trebuie sa accepti Termenii si Politica de confidentialitate.": "You must accept the Terms and Privacy Policy.",
  "Exista deja un cont cu acest email.": "An account with this email already exists.",
  "Codul de invitație nu este valid.": "The invite code is not valid.",
  "Codul de invitatie nu este valid.": "The invite code is not valid.",
  "Emailul este obligatoriu.": "Email is required.",
  "Linkul de confirmare lipseste.": "The confirmation link is missing.",
  "Linkul de confirmare este invalid sau a expirat.": "The confirmation link is invalid or expired.",
  "Email confirmat. Contul este activ.": "Email confirmed. Your account is active.",
  "Dacă există un cont cu acest email, vei primi un link pentru resetarea parolei.": "If an account exists with this email, you will receive a password reset link.",
  "Daca exista un cont cu acest email, vei primi un link pentru resetarea parolei.": "If an account exists with this email, you will receive a password reset link.",
  "Pachetul CeCoins nu poate fi cumpărat acum.": "This CeCoins pack cannot be purchased right now.",
  "Pachetul CeCoins nu poate fi cumparat acum.": "This CeCoins pack cannot be purchased right now.",
  "Plata nu poate fi pornită acum.": "Checkout cannot start right now.",
  "Plata nu poate fi pornita acum.": "Checkout cannot start right now.",
  "Portalul de facturare nu poate fi deschis acum.": "The billing portal cannot be opened right now.",
  "Emailul de test nu a putut fi trimis.": "The test email could not be sent.",
  "Misiunile nu s-au putut încărca momentan.": "Missions could not be loaded right now.",
  "Clasamentul nu s-a putut încărca momentan.": "The leaderboard could not be loaded right now.",
  "Misiunea s-a actualizat. Reîncarcă pagina și încearcă din nou.": "The mission changed. Refresh the page and try again.",
  "Ai revendicat deja recompensa acestei misiuni azi. Revino mâine pentru următorul nivel.": "You already claimed this mission reward today. Come back tomorrow for the next level.",
  "Misiunea nu este finalizată încă.": "The mission is not complete yet.",
  "Introdu o adresă de email validă.": "Enter a valid email address.",
  "Scrie câteva detalii despre problemă.": "Add a few details about the issue.",
  "Mesajul este prea lung. Te rugăm să îl scurtezi.": "The message is too long. Please shorten it.",
  "Emailul de suport nu este configurat complet.": "Support email is not fully configured.",
  "Mesajul nu a putut fi trimis momentan.": "The message could not be sent right now.",
  "Serverul a răspuns cu o pagină în loc de date. Reîncarcă pagina și încearcă din nou.": "The server returned a page instead of data. Refresh and try again.",
  "Răspunsul serverului nu a putut fi citit.": "The server response could not be read.",
};

export function localizeApiMessage(message, pick) {
  if (!message) return "";

  const text = String(message).trim();
  const passwordMatch =
    text.match(/^Parola trebuie să aibă minimum (\d+) caractere\.$/i) ||
    text.match(/^Parola trebuie sa aiba minimum (\d+) caractere\.$/i);

  if (passwordMatch) {
    return pick(text, `The password must have at least ${passwordMatch[1]} characters.`);
  }

  if (text.startsWith("Pentru cont trebuie")) {
    return pick(
      text,
      "To create an account, confirm that you are at least 16 or have parent/guardian consent."
    );
  }

  return pick(text, apiErrorTranslations[text] || text);
}

export function getApiErrorMessage(data, pick, fallbackRo, fallbackEn) {
  const rawMessage = data?.error || data?.message;

  if (rawMessage) {
    const normalizedMessage = String(rawMessage).trim();
    const localizedMessage = localizeApiMessage(normalizedMessage, pick);

    if (localizedMessage !== normalizedMessage) {
      return localizedMessage;
    }

    return pick(normalizedMessage, fallbackEn || normalizedMessage);
  }

  return pick(fallbackRo, fallbackEn);
}
