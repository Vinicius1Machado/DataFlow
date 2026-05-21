import type { Metadata } from "next";
import { Outfit } from "next/font/google";
import "./globals.css";

const outfit = Outfit({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "DataFlow",
  description: "Ferramenta para transformar arquivos de dados em scripts Python organizados, rastreaveis e prontos para uso.",
  icons: {
    icon: "/dataflow-logo.svg",
    shortcut: "/dataflow-logo.svg",
    apple: "/dataflow-logo.svg",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="pt-BR">
      <body className={outfit.className}>{children}</body>
    </html>
  );
}
