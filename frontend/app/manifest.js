export default function manifest() {
  return {
    name: "Ce aleg?",
    short_name: "Ce aleg?",
    description:
      "Scanează coduri de bare, vezi verdictul produsului și compară alternative mai bune la cumpărături.",
    start_url: "/",
    id: "/",
    scope: "/",
    display: "standalone",
    background_color: "#05080f",
    theme_color: "#05080f",
    categories: ["shopping", "food", "health"],
    lang: "ro",
    shortcuts: [
      {
        name: "Scanează produs",
        short_name: "Scanează",
        url: "/barcode-scan",
        icons: [{ src: "/icon.png", sizes: "512x512", type: "image/png" }],
      },
      {
        name: "Misiuni",
        short_name: "Misiuni",
        url: "/missions",
        icons: [{ src: "/icon.png", sizes: "512x512", type: "image/png" }],
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
      },
    ],
  };
}
