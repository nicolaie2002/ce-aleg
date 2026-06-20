import "./globals.css";
import { Inter, Space_Grotesk } from "next/font/google";
import { LocaleProvider } from "./components/LocaleProvider";
import { AutomaticPageTranslation } from "./components/AutomaticPageTranslation";
import { ThemeProvider } from "./components/ThemeProvider";
import { LegalFooter } from "./components/LegalFooter";
import { CarbonVaporBackground } from "./components/CarbonVaporBackground";
import { ScrollRevealController } from "./components/ScrollRevealController";
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

export const metadata = {
  metadataBase: new URL(process.env.NEXT_PUBLIC_SITE_URL || "https://www.cealeg.shop"),
  applicationName: "Ce aleg?",
  title: {
    default: "Ce aleg?",
    template: "%s | Ce aleg?",
  },
  description:
    "Scaneaza produse, compara rapid alternative si alege mai bine la cumparaturi.",
  alternates: {
    canonical: "/",
  },
  icons: {
    icon: [
      {
        url: "/icon.png",
        sizes: "500x500",
        type: "image/png",
      },
    ],
    apple: [
      {
        url: "/icon.png",
        sizes: "500x500",
        type: "image/png",
      },
    ],
    shortcut: ["/icon.png"],
  },
  openGraph: {
    type: "website",
    locale: "ro_RO",
    url: "/",
    siteName: "Ce aleg?",
    title: "Ce aleg? - cumparaturi mai inteligente",
    description:
      "Scaneaza produsul, vezi verdictul si primeste alternative clare pentru bugetul si preferintele tale.",
    images: [
      {
        url: "/icon.png",
        width: 500,
        height: 500,
        alt: "Ce aleg?",
      },
    ],
  },
  twitter: {
    card: "summary_large_image",
    title: "Ce aleg? - cumparaturi mai inteligente",
    description:
      "Scaneaza produsul, vezi verdictul si primeste alternative clare pentru cumparaturi.",
    images: ["/icon.png"],
  },
  robots: {
    index: true,
    follow: true,
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
        <LocaleProvider>
          <ThemeProvider>
            <AutomaticPageTranslation />
            <CarbonVaporBackground />
            <ScrollRevealController />
            <Analytics />
            {children}
            <LegalFooter />
          </ThemeProvider>
        </LocaleProvider>
      </body>
    </html>
  );
}
