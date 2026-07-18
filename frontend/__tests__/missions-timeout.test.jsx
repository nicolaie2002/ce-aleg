import { act, render, screen } from "@testing-library/react";

jest.mock("next/image", () => function MockImage(props) {
  const { alt = "", ...imageProps } = props;
  // eslint-disable-next-line @next/next/no-img-element
  return <img alt={alt} {...imageProps} />;
});

jest.mock("../app/components/AppHeader", () => ({
  AppHeader: () => <header>Header</header>,
}));

jest.mock("../app/components/InteractiveSurface", () => ({
  InteractiveSurface: ({ children, ...props }) => <div {...props}>{children}</div>,
}));

jest.mock("../app/components/LocaleProvider", () => ({
  useLocale: () => ({
    locale: "en",
    pick: (_romanian, english) => english,
  }),
}));

const MissionsPage = require("../app/missions/page").default;

describe("MissionsPage request recovery", () => {
  beforeEach(() => {
    jest.useFakeTimers();
    global.fetch = jest.fn((_url, options = {}) => new Promise((_resolve, reject) => {
      options.signal?.addEventListener("abort", () => {
        const error = new Error("Request aborted");
        error.name = "AbortError";
        reject(error);
      });
    }));
  });

  afterEach(() => {
    jest.useRealTimers();
    jest.restoreAllMocks();
  });

  it("leaves the loading state and offers retry when the server hangs", async () => {
    render(<MissionsPage />);

    expect(screen.getByRole("status")).toHaveTextContent("Loading missions...");

    await act(async () => {
      jest.advanceTimersByTime(15_100);
      await Promise.resolve();
    });

    expect(await screen.findByRole("heading", { name: "Missions did not load" }))
      .toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Try again" })).toBeEnabled();
    expect(screen.getByRole("alert")).toHaveTextContent("server is taking too long");
  });
});
