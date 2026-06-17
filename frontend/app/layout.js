import "./globals.css";
import { Inter, Space_Grotesk } from "next/font/google";
import { LocaleProvider } from "./components/LocaleProvider";
import { AutomaticPageTranslation } from "./components/AutomaticPageTranslation";
import { ThemeProvider } from "./components/ThemeProvider";
import { LegalFooter } from "./components/LegalFooter";
import { CarbonVaporBackground } from "./components/CarbonVaporBackground";

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
  title: "Ce aleg?",
  description: "Asistent pentru alegeri mai bune la cumparaturi.",
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
            {children}
            <LegalFooter />
          </ThemeProvider>
        </LocaleProvider>
      </body>
    </html>
  );
}
