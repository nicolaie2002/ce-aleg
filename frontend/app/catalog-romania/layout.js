export const metadata = {
  title: "Catalog România pentru scanare produse",
  description:
    "Catalog public Ce aleg? pentru produse din România, magazine, categorii, scanare cod de bare și contribuții ale comunității.",
  alternates: {
    canonical: "/catalog-romania",
  },
  openGraph: {
    title: "Catalog România | Ce aleg?",
    description:
      "Vezi cum crește catalogul Ce aleg? și folosește paginile publice pentru magazine și categorii.",
    url: "/catalog-romania",
    images: ["/opengraph-image.png?v=20260623"],
  },
};

export default function CatalogRomaniaLayout({ children }) {
  return children;
}
