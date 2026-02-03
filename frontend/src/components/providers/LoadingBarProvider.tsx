/**
 * Loading Bar Provider
 * Wraps app with loading bar that shows during navigation
 */

'use client';

import { Suspense, useEffect } from 'react';
import { usePathname, useSearchParams } from 'next/navigation';
import { LoadingBar, useLoadingBar } from '@/components/ui/loading-bar';

function LoadingBarContent({ children }: { children: React.ReactNode }) {
  const { isLoading, startLoading, stopLoading } = useLoadingBar();
  const pathname = usePathname();
  const searchParams = useSearchParams();

  useEffect(() => {
    // Start loading on navigation
    startLoading();

    // Stop loading after a short delay (page has rendered)
    const timer = setTimeout(() => {
      stopLoading();
    }, 300);

    return () => {
      clearTimeout(timer);
      stopLoading();
    };
  }, [pathname, searchParams, startLoading, stopLoading]);

  return (
    <>
      <LoadingBar isLoading={isLoading} />
      {children}
    </>
  );
}

export function LoadingBarProvider({ children }: { children: React.ReactNode }) {
  return (
    <Suspense fallback={children}>
      <LoadingBarContent>{children}</LoadingBarContent>
    </Suspense>
  );
}
