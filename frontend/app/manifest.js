export default function manifest() {
  return {
    name: "Ce aleg?",
    short_name: "Ce aleg?",
    description: "Scanează coduri de bare, vezi verdictul produsului și compară alternative mai bune la cumpărături.",
    start_url: "/",
    id: "/",
    scope: "/",
    display: "standalone",
    background_color: "#020617",
    theme_color: "#14b8a6",
    categories: ["shopping", "health", "food"],
    lang: "ro",
    orientation: "portrait-primary",
    shortcuts: [
      {
        name: "Scanează produs",
        short_name: "Scanează",
        url: "/barcode-scan",
        icons: [{ src: "/icon.png", sizes: "512x512", type: "image/png", purpose: "any maskable" }],
      },
      {
        name: "Misiuni",
        short_name: "Misiuni",
        url: "/missions",
        icons: [{ src: "/icon.png", sizes: "512x512", type: "image/png", purpose: "any maskable" }],
      },
    ],
    icons: [
      {
        src: "/icon.png",
        sizes: "512x512",
        type: "image/png",
        purpose: "any maskable",
      },
      {
        src: "/apple-icon.png",
        sizes: "180x180",
        type: "image/png",
        purpose: "any",
      },
    ],
    screenshots: [
      {
        src: "/opengraph-image.png",
        sizes: "1200x630",
        type: "image/png",
        form_factor: "wide",
        label: "Ce aleg? - Scan and compare products",
      },
    ],
  };
}