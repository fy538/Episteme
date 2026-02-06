/**
 * Root page - redirects to login or workspace based on auth status
 */

'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { authAPI } from '@/lib/api/auth';

export default function Home() {
  const router = useRouter();
  const [checked, setChecked] = useState(false);

  useEffect(() => {
    const devMode = process.env.NEXT_PUBLIC_DEV_MODE === 'true';
    const isAuthenticated = authAPI.isAuthenticated() || devMode;

    if (isAuthenticated) {
      router.push('/workspace');
    } else {
      router.push('/login');
    }
    setChecked(true);
  }, [router]);

  // Show nothing while checking auth and redirecting
  if (!checked) {
    return null;
  }

  return null;
}
