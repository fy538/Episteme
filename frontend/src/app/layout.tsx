/**
 * Root layout
 */

import './globals.css';
import type { Metadata } from 'next';
import { Inter, DM_Sans } from 'next/font/google';
import { Providers } from './providers';
import { GlobalCommandPalette } from '@/components/layout/GlobalCommandPalette';
import { LoadingBarProvider } from '@/components/providers/LoadingBarProvider';
import { KeyboardShortcutsModal } from '@/components/layout/KeyboardShortcutsModal';

const inter = Inter({ 
  subsets: ['latin'],
  variable: '--font-inter',
  display: 'swap',
});

const dmSans = DM_Sans({ 
  subsets: ['latin'],
  weight: ['400', '500', '600', '700'],
  variable: '--font-dm-sans',
  display: 'swap',
});

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
    <html lang="en" className={`${inter.variable} ${dmSans.variable}`}>
      <body className={inter.className}>
        <Providers>
          <LoadingBarProvider>
            <GlobalCommandPalette>
              {children}
              <KeyboardShortcutsModal />
            </GlobalCommandPalette>
          </LoadingBarProvider>
        </Providers>
      </body>
    </html>
  );
}
