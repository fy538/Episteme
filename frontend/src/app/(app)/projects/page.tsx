/**
 * Projects list page — redirects to home.
 * Projects are now accessible via the sidebar HOME mode.
 */
import { redirect } from 'next/navigation';

export default function ProjectsListPage() {
  redirect('/');
}
