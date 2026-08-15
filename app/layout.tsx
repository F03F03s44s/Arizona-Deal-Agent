import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: 'Arizona Deal Agent | Best Value AI Finder & Ranker',
  description: 'AI-driven engine that continuously finds, normalizes, and ranks Arizona deals across Real Estate, Cars, Resorts, Dining, and Tech by best value score.',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark">
      <body className="bg-slate-950 text-slate-100 antialiased selection:bg-amber-500 selection:text-black">
        {children}
      </body>
    </html>
  );
}
