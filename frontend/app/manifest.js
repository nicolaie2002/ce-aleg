export default function manifest() {
  return {
    name: "Ce aleg?",
    short_name: "Ce aleg?",
    description:
      "Scaneaza coduri de bare, vezi verdictul produsului si compara alternative mai bune la cumparaturi.",
    start_url: "/",
    scope: "/",
    display: "standalone",
    background_color: "#05080f",
    theme_color: "#05080f",
    categories: ["shopping", "food", "health"],
    lang: "ro",
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
