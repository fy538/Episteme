/**
 * Inquiries list page — redirects to home.
 * Inquiries are now accessed within individual cases.
 */
import { redirect } from 'next/navigation';

export default function InquiriesPage() {
  redirect('/');
}
