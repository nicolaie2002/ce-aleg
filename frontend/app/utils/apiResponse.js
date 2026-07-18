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
  active_subscription_exists: "You already have an active subscription.",
  admin_required: "Administrator access is required.",
  auth_required: "Sign in is required.",
  billing_portal_unavailable: "The billing portal is temporarily unavailable.",
  cecoins_checkout_failed: "CeCoins checkout could not be started.",
  cecoins_checkout_not_configured: "CeCoins checkout is not configured.",
  cecoins_price_invalid: "This CeCoins pack is not configured correctly.",
  cecoins_session_sync_failed: "CeCoins could not be synchronized from this checkout session.",
  email_already_verified: "This email address is already verified.",
  email_not_configured: "Email delivery is not configured.",
  email_not_verified: "Confirm your email before signing in.",
  external_catalog_unavailable: "The external product catalog is temporarily unavailable.",
  external_product_not_found: "The product was not found in the external catalog.",
  family_plan_required: "A Family plan is required for this feature.",
  gamification_leaderboard_failed: "The leaderboard could not be loaded right now.",
  gamification_summary_failed: "Missions could not be loaded right now.",
  invalid_email: "Enter a valid email address.",
  invalid_scan_image: "The selected image could not be processed.",
  invalid_server_response: "The server response could not be read. Refresh and try again.",
  openfoodfacts_unavailable: "Open Food Facts is temporarily unavailable.",
  paid_plan_required: "A Pro or Family plan is required for this feature.",
  processing_restricted: "This action is unavailable while account processing is restricted.",
  product_already_exists: "This product already exists in the catalog.",
  product_identity_required: "Add a product name or a valid barcode.",
  rate_limit_exceeded: "Too many requests. Try again in a few seconds.",
  route_policy_missing: "This request is temporarily unavailable.",
  scan_limit_reached: "The free scan limit has been reached.",
  stripe_checkout_failed: "Checkout could not be started.",
  stripe_customer_missing: "No billing profile was found for this account.",
  stripe_customer_stale: "The billing profile needs to be refreshed.",
  stripe_not_configured: "Payments are not configured right now.",
  stripe_payment_not_confirmed: "The payment has not been confirmed yet.",
  stripe_portal_failed: "The billing portal could not be opened.",
  stripe_session_sync_failed: "The checkout session could not be synchronized.",
  stripe_webhook_handler_failed: "The payment notification could not be processed.",
  submission_already_pending: "This product has already been submitted and is under review.",
  submission_daily_limit: "The daily product submission limit has been reached.",
  submission_pending_limit: "You have too many submissions waiting for review.",
  user_not_found: "The user account was not found.",
  validation_error: "Check the information you entered and try again.",
  verification_email_failed: "The confirmation email could not be sent.",
  verified_source_product_not_found: "A verified source product could not be found.",
  vision_not_configured: "Visual recognition is not configured.",
  vision_unavailable: "Visual recognition is temporarily unavailable.",
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
  "Contul nu a putut fi șters momentan. Încearcă din nou mai târziu.": "The account could not be deleted right now. Try again later.",
  "Contul tău și datele personale asociate au fost șterse.": "Your account and associated personal data have been deleted.",
  "Abonamentul Stripe nu a putut fi anulat momentan. Încearcă din nou sau contactează suportul.": "The Stripe subscription could not be cancelled right now. Try again or contact support.",
  "Abonamentul nu a putut fi anulat momentan. Contul nu a fost sters ca sa nu ramai taxat.": "The subscription could not be cancelled right now. The account was kept active to prevent further billing issues.",
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
  "EMAIL_FROM lipseste.": "EMAIL_FROM is missing.",
  "BREVO_API_KEY lipseste pentru providerul Brevo.": "BREVO_API_KEY is missing for the Brevo provider.",
  "RESEND_API_KEY lipseste pentru providerul Resend.": "RESEND_API_KEY is missing for the Resend provider.",
  "EMAIL_SMTP_HOST lipseste pentru providerul SMTP.": "EMAIL_SMTP_HOST is missing for the SMTP provider.",
  "Brevo poate respinge senderul Gmail. Recomandat: EMAIL_FROM=contact@cealeg.shop si domeniu/sender verificat in Brevo.": "Brevo may reject a Gmail sender. Recommended: use EMAIL_FROM=contact@cealeg.shop and verify the domain or sender in Brevo.",
  "EMAIL_FROM si CONTACT_EMAIL sunt pe domenii diferite; verifica senderul si reply-to.": "EMAIL_FROM and CONTACT_EMAIL use different domains; check the sender and reply-to address.",
  "Numele produsului este prea scurt sau lipsește.": "The product name is missing or too short.",
  "Magazinul lipsește.": "The store is missing.",
  "Categoria produsului nu este completată.": "The product category is missing.",
  "Cantitatea/gramajul nu este completată.": "The quantity or package size is missing.",
  "Lipsește poza cu fața produsului.": "The product front photo is missing.",
  "Lipsește poza cu eticheta nutrițională.": "The nutrition label photo is missing.",
  "Nu există valori nutriționale completate.": "No nutrition values were provided.",
  "Caloriile lipsesc.": "Calories are missing.",
  "Zahărul lipsește.": "Sugar is missing.",
  "Proteina lipsește.": "Protein is missing.",
  "Grăsimile lipsesc.": "Fat is missing.",
  "Caloriile nu pot fi negative.": "Calories cannot be negative.",
  "Zahărul nu poate fi negativ.": "Sugar cannot be negative.",
  "Proteina nu poate fi negativă.": "Protein cannot be negative.",
  "Grăsimile nu pot fi negative.": "Fat cannot be negative.",
  "Produsul pare energizant, dar nu este menționată cafeina în observații.": "The product appears to be an energy drink, but caffeine is not mentioned in the notes.",
  "Pentru o băutură energizantă, proteina pare neobișnuit de mare.": "Protein appears unusually high for an energy drink.",
  "Pentru o băutură energizantă, grăsimile par neobișnuit de mari.": "Fat appears unusually high for an energy drink.",
  "Zahărul este 0, dar nu apare o mențiune despre fără zahăr sau îndulcitori.": "Sugar is 0, but there is no sugar-free or sweetener note.",
  "Produsul pare corect și complet.": "The product appears correct and complete.",
  "Produsul pare posibil corect, dar are câteva informații lipsă sau neclare.": "The product may be correct, but some information is missing or unclear.",
  "Produsul pare incomplet sau incorect.": "The product appears incomplete or incorrect.",
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
  {
    pattern: /^Provider necunoscut: (.+)\. Foloseste brevo, resend sau smtp\.$/i,
    translate: (match) => `Unknown provider: ${match[1]}. Use brevo, resend or smtp.`,
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
