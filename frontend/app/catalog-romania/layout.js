export const metadata = {
  title: "Catalog Romania pentru scanare produse",
  description:
    "Catalog public Ce aleg? pentru produse din Romania, magazine, categorii, scanare cod de bare si contributii ale comunitatii.",
  alternates: {
    canonical: "/catalog-romania",
  },
  openGraph: {
    title: "Catalog Romania | Ce aleg?",
    description:
      "Vezi cum creste catalogul Ce aleg? si foloseste paginile publice pentru magazine si categorii.",
    url: "/catalog-romania",
    images: ["/opengraph-image.png?v=20260623"],
  },
};

export default function CatalogRomaniaLayout({ children }) {
  return children;
}
