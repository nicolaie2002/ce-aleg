import { act, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { AiStatusPanel } from "@/app/components/AiStatusPanel";
import { LocaleProvider } from "@/app/components/LocaleProvider";
import { ServiceWorkerRegistration } from "@/app/components/ServiceWorkerRegistration";

jest.mock("@/app/config", () => ({ API_URL: "/api/backend" }));

function withLocale(component) {
  return <LocaleProvider>{component}</LocaleProvider>;
}

describe("AiStatusPanel", () => {
  beforeEach(() => {
    global.fetch = jest.fn();
  });

  it("replaces fallback entries with the live backend status", async () => {
    global.fetch.mockResolvedValue({
      ok: true,
      json: jest.fn().mockResolvedValue({
        localOcr: { enabled: true, label: "OCR" },
        cloudVision: { enabled: false, label: "Cloud vision" },
        freeMode: { enabled: true, label: "Free mode" },
      }),
    });

    render(withLocale(<AiStatusPanel />));

    expect(
      await screen.findByText("Identificare vizuală opțională")
    ).toBeInTheDocument();
    expect(screen.getByText("OCR local pentru coduri și etichete")).toBeInTheDocument();
    expect(screen.getByText("indisponibil")).toBeInTheDocument();
    expect(global.fetch).toHaveBeenCalledWith("/api/backend/ai/status");
  });

  it("keeps useful local fallback information when the backend is unavailable", async () => {
    global.fetch.mockRejectedValue(new Error("offline"));

    render(withLocale(<AiStatusPanel compact />));

    expect(screen.getByText("OCR local pentru coduri și etichete")).toBeInTheDocument();
    expect(screen.getByText("Catalog Open Food Facts")).toBeInTheDocument();
    expect(screen.queryByText("Totul este pregătit pentru scanare")).not.toBeInTheDocument();
    await waitFor(() => expect(global.fetch).toHaveBeenCalledTimes(1));
  });
});

describe("ServiceWorkerRegistration", () => {
  const originalNodeEnv = process.env.NODE_ENV;
  let serviceWorker;
  let registration;
  let waitingWorker;

  beforeEach(() => {
    process.env.NODE_ENV = "production";
    waitingWorker = { postMessage: jest.fn() };
    registration = {
      waiting: waitingWorker,
      installing: null,
      addEventListener: jest.fn(),
    };
    serviceWorker = {
      controller: {},
      register: jest.fn().mockResolvedValue(registration),
      addEventListener: jest.fn(),
      removeEventListener: jest.fn(),
    };
    Object.defineProperty(navigator, "serviceWorker", {
      configurable: true,
      value: serviceWorker,
    });
  });

  afterEach(() => {
    process.env.NODE_ENV = originalNodeEnv;
    delete navigator.serviceWorker;
  });

  it("offers and installs a waiting PWA update", async () => {
    const user = userEvent.setup();
    const { unmount } = render(withLocale(<ServiceWorkerRegistration />));

    expect(await screen.findByText("Actualizare disponibilă")).toBeInTheDocument();
    expect(serviceWorker.register).toHaveBeenCalledWith("/sw.js", {
      scope: "/",
      updateViaCache: "none",
    });

    await user.click(screen.getByRole("button", { name: "Instalează actualizarea" }));

    expect(waitingWorker.postMessage).toHaveBeenCalledWith({
      type: "SKIP_WAITING",
    });
    expect(screen.queryByText("Actualizare disponibilă")).not.toBeInTheDocument();

    unmount();
    expect(serviceWorker.removeEventListener).toHaveBeenCalledWith(
      "controllerchange",
      expect.any(Function)
    );
  });

  it("detects an update that finishes installing after registration", async () => {
    let updateFound;
    let stateChanged;
    const installingWorker = {
      state: "installing",
      addEventListener: jest.fn((event, callback) => {
        if (event === "statechange") stateChanged = callback;
      }),
    };
    registration.waiting = null;
    registration.installing = installingWorker;
    registration.addEventListener.mockImplementation((event, callback) => {
      if (event === "updatefound") updateFound = callback;
    });

    render(withLocale(<ServiceWorkerRegistration />));

    await waitFor(() => expect(serviceWorker.register).toHaveBeenCalledTimes(1));
    act(() => updateFound());
    installingWorker.state = "installed";
    act(() => stateChanged());

    expect(await screen.findByText("Actualizare disponibilă")).toBeInTheDocument();
  });

  it("fails quietly when registration is rejected", async () => {
    const warning = jest.spyOn(console, "warn").mockImplementation(() => {});
    serviceWorker.register.mockRejectedValue(new Error("registration failed"));

    render(withLocale(<ServiceWorkerRegistration />));

    await waitFor(() =>
      expect(warning).toHaveBeenCalledWith(
        "Service worker registration failed",
        expect.any(Error)
      )
    );
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
    warning.mockRestore();
  });
});
