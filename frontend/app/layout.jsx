import { Hanken_Grotesk, Oswald } from "next/font/google";
import "./globals.css";

const body = Hanken_Grotesk({ subsets: ["latin"], variable: "--font-body", display: "swap" });
const display = Oswald({ subsets: ["latin"], variable: "--font-display", display: "swap" });

export const metadata = {
  title: "Zenfest Intelligence Hub",
  description: "Event news from Tamil Nadu, India and the world, turned into daily reel ideas for Zenfest Events.",
  robots: { index: false, follow: false },
};

export default function RootLayout({ children }) {
  return (
    <html lang="en" className={`${body.variable} ${display.variable}`}>
      <body>{children}</body>
    </html>
  );
}
