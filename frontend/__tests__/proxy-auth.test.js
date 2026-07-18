jest.mock("next/server", () => ({
  NextResponse: {
    redirect: jest.fn((url) => ({ kind: "redirect", url: String(url) })),
    next: jest.fn(() => ({ kind: "next" })),
  },
}));

const { NextResponse } = require("next/server");
const { proxy } = require("../proxy");

function createRequest({ pathname = "/dashboard", token, cookieHeader } = {}) {
  return {
    url: `https://www.cealeg.shop${pathname}`,
    nextUrl: { pathname },
    cookies: {
      get: jest.fn((name) =>
        name === "cealeg_session" && token ? { value: token } : undefined
      ),
    },
    headers: {
      get: jest.fn((name) =>
        name === "cookie"
          ? cookieHeader || (token ? `cealeg_session=${token}` : "")
          : ""
      ),
    },
  };
}

describe("authentication proxy", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    global.fetch = jest.fn();
  });

  test("redirects a signed-out visitor to login with the intended destination", async () => {
    const result = await proxy(createRequest({ pathname: "/missions" }));

    expect(result).toEqual({
      kind: "redirect",
      url: "https://www.cealeg.shop/login?next=%2Fmissions",
    });
    expect(global.fetch).not.toHaveBeenCalled();
  });

  test("allows a verified session and forwards the complete cookie header", async () => {
    global.fetch.mockResolvedValue({
      ok: true,
      json: async () => ({ user: { id: 7, isAdmin: false } }),
    });
    const request = createRequest({
      token: "member-session-1",
      cookieHeader: "cealeg_session=member-session-1; locale=en",
    });

    const result = await proxy(request);

    expect(result).toEqual({ kind: "next" });
    expect(global.fetch).toHaveBeenCalledWith(
      "http://127.0.0.1:5001/auth/me",
      {
        headers: {
          cookie: "cealeg_session=member-session-1; locale=en",
        },
        cache: "no-store",
      }
    );
  });

  test("redirects when the backend rejects or cannot validate the session", async () => {
    global.fetch.mockResolvedValueOnce({ ok: false });
    global.fetch.mockRejectedValueOnce(new Error("backend unavailable"));

    const rejected = await proxy(
      createRequest({ pathname: "/cart", token: "rejected-session-1" })
    );
    const unavailable = await proxy(
      createRequest({ pathname: "/history", token: "offline-session-1" })
    );

    expect(rejected.url).toContain("/login?next=%2Fcart");
    expect(unavailable.url).toContain("/login?next=%2Fhistory");
    expect(NextResponse.next).not.toHaveBeenCalled();
  });

  test("keeps non-admin users out of admin and allows administrators", async () => {
    global.fetch
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({ user: { id: 8, isAdmin: false } }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({ user: { id: 9, isAdmin: true } }),
      });

    const member = await proxy(
      createRequest({ pathname: "/admin", token: "member-admin-attempt-1" })
    );
    const admin = await proxy(
      createRequest({ pathname: "/admin", token: "admin-session-1" })
    );

    expect(member).toEqual({
      kind: "redirect",
      url: "https://www.cealeg.shop/dashboard",
    });
    expect(admin).toEqual({ kind: "next" });
  });

  test("reuses a recent session validation without another backend request", async () => {
    global.fetch.mockResolvedValue({
      ok: true,
      json: async () => ({ user: { id: 10, isAdmin: false } }),
    });
    const firstRequest = createRequest({ token: "cached-session-1" });
    const secondRequest = createRequest({ token: "cached-session-1" });

    await proxy(firstRequest);
    await proxy(secondRequest);

    expect(global.fetch).toHaveBeenCalledTimes(1);
    expect(NextResponse.next).toHaveBeenCalledTimes(2);
  });
});
