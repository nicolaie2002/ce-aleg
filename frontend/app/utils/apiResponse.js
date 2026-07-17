export async function readApiJson(response, _context = "") {
  const contentType = response.headers.get("content-type") || "";

  if (contentType.includes("application/json")) {
    return response.json();
  }

  const body = await response.text().catch(() => "");

  return {
    code: "invalid_server_response",
    error:
      body && body.trim().startsWith("<")
        ? "Serverul a răspuns cu o pagină în loc de date. Reîncarcă pagina și încearcă din nou."
        : "Răspunsul serverului nu a putut fi citit.",
  };
}

const apiCodeTranslations = {
  admin_required: "Administrator access is required.",
  auth_required: "Sign in is required.",
  invalid_scan_image: "The selected image could not be processed.",
  invalid_server_response: "The server response could not be read. Refresh and try again.",
  validation_error: "Check the information you entered and try again.",
  wrong_account: "You cannot access another account's data.",
};

const apiErrorTranslations = {
  "Autentificare necesară.": "Sign in is required.",
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
  "Cererea este prea mare.": "The request is too large.",
  "JSON invalid sau malformat.": "The request contains invalid JSON.",
  "Prea multe traduceri. Reîncearcă în câteva secunde.": "Too many translation requests. Try again in a few seconds.",
  "Nu poți modifica datele altui cont.": "You cannot change another account's data.",
  "Nu poți trimite produse pentru alt cont.": "You cannot submit products for another account.",
  "Alternativa raportată nu este validă.": "The reported alternative is invalid.",
  "Produsul raportat nu este valid.": "The reported product is invalid.",
  "Detaliile sunt prea lungi. Te rugăm să le scurtezi.": "The details are too long. Please shorten them.",
  "Mesajul a fost trimis. Îți răspundem cât mai curând.": "Your message was sent. We will reply as soon as possible.",
  "Adresa de email nu este valida.": "Enter a valid email address.",
  "Tokenul și parola nouă sunt obligatorii.": "The reset link and new password are required.",
  "Linkul de resetare este invalid sau a expirat.": "The reset link is invalid or has expired.",
  "Linkul de ștergere este invalid sau a expirat.": "The deletion link is invalid or has expired.",
  "Autentificare necesara.": "Sign in is required.",
  "Contul nu mai este disponibil.": "This account is no longer available.",
  "Plan invalid.": "Invalid plan.",
  "Status invalid.": "Invalid status.",
  "Planul Family permite pana la 5 profiluri.": "The Family plan allows up to 5 profiles.",
  "Scrie un nume de profil de cel putin 2 caractere.": "Enter a profile name with at least 2 characters.",
  "Profilul nu a fost gasit.": "The profile was not found.",
  "Profilul principal nu poate fi sters.": "The main profile cannot be deleted.",
  "Stripe SDK nu este instalat.": "The payment service is temporarily unavailable.",
  "Stripe webhook nu este configurat.": "The payment service is not fully configured.",
  "Payload Stripe invalid.": "The payment notification is invalid.",
  "Semnatura Stripe invalida.": "The payment notification signature is invalid.",
  "Recompensă invalidă.": "Invalid reward.",
  "Pachet CeCoins invalid.": "Invalid CeCoins pack.",
  "Sesiunea Stripe este invalidă.": "The checkout session is invalid.",
  "Sesiunea Stripe nu aparține unui pachet CeCoins.": "This checkout session is not for a CeCoins pack.",
  "Sesiunea Stripe aparține altui cont.": "This checkout session belongs to another account.",
  "Produsul nu exista.": "The product does not exist.",
  "Scorul trebuie sa fie intre 0 si 10.": "The score must be between 0 and 10.",
  "Raportarea nu exista.": "The report does not exist.",
  "Raportarea nu contine alternativa valida.": "The report does not contain a valid alternative.",
  "Produsul raportat nu a putut fi gasit sau creat.": "The reported product could not be found or created.",
  "Nu am putut rezolva raportarea automat.": "The report could not be resolved automatically.",
  "Produs șters din catalog.": "Product removed from the catalog.",
  "Utilizatorul nu exista.": "The user does not exist.",
  "Parametrul q este obligatoriu.": "Enter a search term.",
  "Utilizatorul nu există.": "The user does not exist.",
  "Nu ai trimis date JSON.": "No request data was provided.",
  "user_id și name sunt obligatorii.": "The user and product name are required.",
  "Produsul din coș nu există.": "The cart item does not exist.",
  "Produsul a fost eliminat din coș.": "The product was removed from the cart.",
  "Produs șters din coș.": "Product removed from the cart.",
  "Coșul a fost golit.": "The cart has been cleared.",
  "Produsul favorit nu există.": "The favorite product does not exist.",
  "Produs șters din favorite.": "Product removed from favorites.",
  "Favoritele au fost șterse.": "Favorites have been cleared.",
  "Scanarea nu există.": "The scan does not exist.",
  "Scanare ștearsă din istoric.": "Scan removed from history.",
  "Istoricul scanărilor a fost șters.": "Scan history has been cleared.",
  "Nu poți accesa această imagine.": "You cannot access this image.",
  "Storage indisponibil.": "Image storage is unavailable.",
  "Imaginea nu a putut fi încărcată.": "The image could not be loaded.",
  "user_id trebuie să fie un număr valid.": "The user identifier is invalid.",
  "Propunerea nu există.": "The submission does not exist.",
  "Propunerea a fost ștearsă.": "The submission was deleted.",
  "Textul este prea lung.": "The text is too long.",
  "Limba ceruta nu este acceptata.": "The requested language is not supported.",
  "Cadrul video lipsește.": "The camera frame is missing.",
  "Cadrul video este gol.": "The camera frame is empty.",
  "Cadrul video este prea mare.": "The camera frame is too large.",
  "Cadrul video nu conține o imagine validă.": "The camera frame does not contain a valid image.",
  "Unauthorized": "Sign in is required.",
};

const dynamicApiTranslations = [
  {
    pattern: /^Parola trebuie (?:să|sa) aibă minimum (\d+) caractere\.$/i,
    translate: (match) => `The password must have at least ${match[1]} characters.`,
  },
  {
    pattern: /^Ai nevoie de (\d+) CeCoins pentru această recompensă\.$/i,
    translate: (match) => `You need ${match[1]} CeCoins for this reward.`,
  },
  {
    pattern: /^Mai ai nevoie de (\d+) CeCoins\.$/i,
    translate: (match) => `You need ${match[1]} more CeCoins.`,
  },
  {
    pattern: /^Poți revendica cel mult (\d+) CeCoins pe zi\.$/i,
    translate: (match) => `You can claim up to ${match[1]} CeCoins per day.`,
  },
  {
    pattern: /^Fișierul (.+) este prea mare\.$/i,
    translate: (match) => `${match[1]} is too large.`,
  },
];

export function localizeApiMessage(message, pick, code = "") {
  if (!message) return "";

  const text = String(message).trim();

  if (code && apiCodeTranslations[code]) {
    return pick(text, apiCodeTranslations[code]);
  }

  for (const entry of dynamicApiTranslations) {
    const match = text.match(entry.pattern);

    if (match) {
      return pick(text, entry.translate(match));
    }
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
    const localizedMessage = localizeApiMessage(normalizedMessage, pick, data?.code);

    if (localizedMessage !== normalizedMessage) {
      return localizedMessage;
    }

    return pick(normalizedMessage, fallbackEn || normalizedMessage);
  }

  return pick(fallbackRo, fallbackEn);
}
