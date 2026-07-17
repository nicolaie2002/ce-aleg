import "./globals.css";
import { Inter, Space_Grotesk } from "next/font/google";
import { LocaleProvider } from "./components/LocaleProvider";
import { AutomaticPageTranslation } from "./components/AutomaticPageTranslation";
import { ThemeProvider } from "./components/ThemeProvider";
import { LegalFooter } from "./components/LegalFooter";
import { CarbonVaporBackground } from "./components/CarbonVaporBackground";
import { CookieConsentBanner } from "./components/CookieConsentBanner";
import { BackendWarmup } from "./components/BackendWarmup";
import { ServiceWorkerRegistration } from "./components/ServiceWorkerRegistration";
import { PostHogProvider } from "@/components/PostHogProvider";
import { Analytics } from "./components/Analytics";

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-inter",
  display: "swap",
});

const spaceGrotesk = Space_Grotesk({
  subsets: ["latin"],
  variable: "--font-space-grotesk",
  display: "swap",
});

const siteUrl = process.env.NEXT_PUBLIC_SITE_URL || "https://www.cealeg.shop";
const siteName = "Ce aleg?";
const siteDescription =
  "Scanează codul de bare al unui produs, vezi rapid verdictul și compară alternative mai bune pentru bugetul și preferințele tale.";
const socialImage = "/opengraph-image.png?v=20260623";

export const viewport = {
  width: "device-width",
  initialScale: 1,
  themeColor: [
    { media: "(prefers-color-scheme: light)", color: "#f5f8f9" },
    { media: "(prefers-color-scheme: dark)", color: "#05080f" },
  ],
};

export const metadata = {
  metadataBase: new URL(siteUrl),
  applicationName: siteName,
  title: {
    default: "Ce aleg? | Scanează produse și compară alternative la cumpărături",
    template: "%s | Ce aleg?",
  },
  description: siteDescription,
  keywords: [
    "Ce aleg",
    "scanare cod de bare",
    "alternative produse",
    "cumpărături inteligente",
    "comparare produse",
    "Open Food Facts",
    "Lidl",
    "Kaufland",
    "Carrefour",
    "Mega Image",
  ],
  authors: [{ name: siteName }],
  creator: siteName,
  publisher: siteName,
  category: "shopping",
  alternates: {
    canonical: "/",
  },
  icons: {
    icon: [
      {
        url: "/icon.png",
        sizes: "512x512",
        type: "image/png",
      },
      {
        url: "/favicon.ico",
        sizes: "any",
      },
    ],
    apple: [
      {
        url: "/apple-icon.png",
        sizes: "180x180",
        type: "image/png",
      },
    ],
    shortcut: ["/icon.png"],
  },
  manifest: "/manifest.webmanifest",
  openGraph: {
    type: "website",
    locale: "ro_RO",
    url: siteUrl,
    siteName,
    title: "Ce aleg? - scanează produse și compară alternative",
    description: siteDescription,
    images: [
      {
        url: socialImage,
        width: 1200,
        height: 630,
        alt: "Ce aleg? - scanează produse și compară alternative",
      },
    ],
  },
  twitter: {
    card: "summary_large_image",
    title: "Ce aleg? - scanează produse și compară alternative",
    description: siteDescription,
    images: [socialImage],
  },
  robots: {
    index: true,
    follow: true,
    googleBot: {
      index: true,
      follow: true,
      "max-image-preview": "large",
      "max-snippet": -1,
      "max-video-preview": -1,
    },
  },
};

const structuredData = {
  "@context": "https://schema.org",
  "@type": "WebApplication",
  name: siteName,
  url: siteUrl,
  applicationCategory: "ShoppingApplication",
  operatingSystem: "Web, iOS, Android",
  description: siteDescription,
  inLanguage: ["ro-RO", "en"],
  image: `${siteUrl}/opengraph-image.png`,
  thumbnailUrl: `${siteUrl}/opengraph-image.png`,
  logo: `${siteUrl}/icon.png`,
  offers: [
    {
      "@type": "Offer",
      name: "Free",
      price: "0",
      priceCurrency: "RON",
      category: "free",
    },
    {
      "@type": "Offer",
      name: "Pro",
      price: "19.99",
      priceCurrency: "RON",
      category: "subscription",
    },
    {
      "@type": "Offer",
      name: "Family",
      price: "29.99",
      priceCurrency: "RON",
      category: "subscription",
    },
  ],
  publisher: {
    "@type": "Organization",
    name: siteName,
    url: siteUrl,
    logo: `${siteUrl}/icon.png`,
    contactPoint: {
      "@type": "ContactPoint",
      contactType: "customer support",
      email: "contact@cealeg.shop",
      availableLanguage: ["Romanian", "English"],
    },
  },
};

export default function RootLayout({ children }) {
  return (
    <html
      lang="ro"
      className={`${inter.variable} ${spaceGrotesk.variable} h-full antialiased`}
      suppressHydrationWarning
    >
      <body className="min-h-full flex flex-col">
        <script
          type="application/ld+json"
          suppressHydrationWarning
          dangerouslySetInnerHTML={{ __html: JSON.stringify(structuredData) }}
        />
        <LocaleProvider>
          <ThemeProvider>
            <AutomaticPageTranslation />
            <CarbonVaporBackground />
              <BackendWarmup />
              <ServiceWorkerRegistration />
            <PostHogProvider>
              <Analytics />
              {children}
            </PostHogProvider>
            <LegalFooter />
            <CookieConsentBanner />
          </ThemeProvider>
        </LocaleProvider>
      </body>
    </html>
  );
}
