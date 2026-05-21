import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "DataFlow",
  description: "Plataforma para transformar arquivos de dados em scripts Python organizados, rastreaveis e prontos para uso.",
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
      <body>{children}</body>
    </html>
  );
}
