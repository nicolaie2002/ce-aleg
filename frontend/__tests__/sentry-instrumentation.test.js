const init = jest.fn();
const captureRequestError = jest.fn();
const captureRouterTransitionStart = jest.fn();

jest.mock("@sentry/nextjs", () => ({
  init,
  captureRequestError,
  captureRouterTransitionStart,
}));

describe("Sentry instrumentation", () => {
  beforeEach(() => {
    init.mockClear();
    jest.resetModules();
    process.env.NEXT_PUBLIC_SENTRY_DSN = "https://public@example.ingest.sentry.io/1";
  });

  afterEach(() => {
    delete process.env.NEXT_PUBLIC_SENTRY_DSN;
  });

  it("initializes the client without PII and removes query strings", async () => {
    const client = await import("../instrumentation-client");
    const options = init.mock.calls[0][0];
    const event = options.beforeSend({
      request: {
        url: "https://www.cealeg.shop/reset-password?token=secret",
        cookies: { auth: "secret" },
        data: { password: "secret" },
        query_string: "token=secret",
      },
    });

    expect(options.sendDefaultPii).toBe(false);
    expect(event.request.url).toBe("https://www.cealeg.shop/reset-password");
    expect(event.request).not.toHaveProperty("cookies");
    expect(event.request).not.toHaveProperty("data");
    expect(event.request).not.toHaveProperty("query_string");
    expect(client.onRouterTransitionStart).toBe(captureRouterTransitionStart);
  });

  it("exports the Next.js server error hook", async () => {
    const instrumentation = await import("../instrumentation");

    expect(instrumentation.onRequestError).toBe(captureRequestError);
  });
});
