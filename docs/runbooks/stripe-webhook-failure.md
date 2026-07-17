# Runbook: esec Stripe webhook

## Actiune rapida

1. Opreste promovarea checkoutului daca planurile sau CeCoins sunt atribuite gresit.
2. Colecteaza event ID, request ID, ora UTC si user ID intern.
3. Verifica endpointul, modul test/live si signing secret fara a afisa secretele.
4. Confirma idempotenta in `stripe_webhook_events` inainte de resend.
5. Retrimite un singur eveniment din Stripe Dashboard si verifica efectul.

Procedura completa, matricea de statusuri si reconcilierea sunt in
[stripe-webhook.md](stripe-webhook.md). Nu activa manual abonamente fara dovada si
reconciliere cu sursa Stripe.
