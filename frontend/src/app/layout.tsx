/**
 * Root layout
 */

import './globals.css';
import type { Metadata } from 'next';
import { Inter } from 'next/font/google';
import { Providers } from './providers';
import { GlobalCommandPalette } from '@/components/layout/GlobalCommandPalette';

const inter = Inter({ subsets: ['latin'] });

export const metadata: Metadata = {
  title: 'Episteme - Rigorous Decision Making',
  description: 'Workspace for high-stakes decision preparation',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className={inter.className}>
        <Providers>
          <GlobalCommandPalette>
            {children}
          </GlobalCommandPalette>
        </Providers>
      </body>
    </html>
  );
}
