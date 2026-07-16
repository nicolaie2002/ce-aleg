import * as Sentry from "@sentry/nextjs";

const dsn = process.env.NEXT_PUBLIC_SENTRY_DSN;

Sentry.init({
  dsn,
  enabled: Boolean(dsn) && process.env.NODE_ENV === "production",
  environment: process.env.NEXT_PUBLIC_APP_ENV || process.env.NODE_ENV,
  release: process.env.NEXT_PUBLIC_APP_VERSION,
  sendDefaultPii: false,
  tracesSampleRate: 0.1,
  beforeSend(event) {
    if (!event.request) return event;

    if (event.request.url) event.request.url = event.request.url.split("?")[0];
    delete event.request.cookies;
    delete event.request.data;
    delete event.request.query_string;

    return event;
  },
});

export const onRouterTransitionStart = Sentry.captureRouterTransitionStart;
