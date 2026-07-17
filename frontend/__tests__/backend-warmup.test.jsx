import { act, render, waitFor } from "@testing-library/react";
import { BackendWarmup } from "@/app/components/BackendWarmup";


describe("BackendWarmup", () => {
  beforeEach(() => {
    jest.useFakeTimers();
    localStorage.clear();
    global.fetch = jest.fn(() => Promise.resolve({ ok: true }));
    delete window.requestIdleCallback;
    delete window.cancelIdleCallback;
  });

  afterEach(() => {
    jest.runOnlyPendingTimers();
    jest.useRealTimers();
    jest.restoreAllMocks();
  });

  it("does not contact the backend again during the cooldown", () => {
    localStorage.setItem("cealeg_backend_warmup_at", String(Date.now()));

    render(<BackendWarmup />);
    act(() => jest.advanceTimersByTime(20_000));

    expect(fetch).not.toHaveBeenCalled();
  });

  it("waits until after critical rendering before using the fallback timer", async () => {
    render(<BackendWarmup />);

    act(() => jest.advanceTimersByTime(7_999));
    expect(fetch).not.toHaveBeenCalled();

    act(() => jest.advanceTimersByTime(1));
    expect(fetch).toHaveBeenCalledWith("/api/backend/health", {
      cache: "no-store",
      keepalive: true,
    });
    await waitFor(() => {
      expect(Number(localStorage.getItem("cealeg_backend_warmup_at"))).toBeGreaterThan(0);
    });
  });

  it("uses idle time when the browser provides requestIdleCallback", () => {
    let idleCallback;
    window.requestIdleCallback = jest.fn((callback) => {
      idleCallback = callback;
      return 17;
    });
    window.cancelIdleCallback = jest.fn();

    const { unmount } = render(<BackendWarmup />);
    act(() => jest.advanceTimersByTime(8_000));

    expect(window.requestIdleCallback).toHaveBeenCalledWith(
      expect.any(Function),
      { timeout: 2000 }
    );
    expect(fetch).not.toHaveBeenCalled();

    act(() => idleCallback());
    expect(fetch).toHaveBeenCalledTimes(1);
    unmount();
    expect(window.cancelIdleCallback).toHaveBeenCalledWith(17);
  });
});
