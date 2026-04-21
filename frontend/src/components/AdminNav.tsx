import { Link, useLocation } from 'react-router-dom';
import type { AdminSession } from '../types';
import { getTenantSlugFromSearchParams, withTenantPath } from '../utils/tenantContext';

const navItems = [
  { to: '/admin', label: 'Crea Prenotazioni' },
  { to: '/admin/prenotazioni-attuali', label: 'Prenotazioni Attuali' },
  { to: '/admin/prenotazioni', label: 'Elenco Prenotazioni' },
  { to: '/admin/log', label: 'Log' },
];

export function AdminNav({ session, notificationEmail }: { session?: AdminSession | null; notificationEmail?: string | null }) {
  const location = useLocation();
  const tenantSlug = getTenantSlugFromSearchParams(new URLSearchParams(location.search));

  return (
    <div className='space-y-3'>
      <nav className='flex flex-wrap gap-2'>
        {navItems.map((item) => {
          const isActive = location.pathname === item.to;

          return (
            <Link
              key={item.to}
              to={withTenantPath(item.to, tenantSlug)}
              className={isActive ? 'inline-flex min-h-12 items-center justify-center gap-2 rounded-2xl border border-brand-700 bg-brand-700 px-4 py-3 text-sm font-semibold text-white transition hover:bg-brand-600 focus:outline-none focus:ring-2 focus:ring-cyan-200' : 'btn-secondary'}
            >
              {item.label}
            </Link>
          );
        })}
      </nav>
      {session ? (
        <div className='flex flex-wrap items-center gap-3 rounded-[20px] border border-white/10 bg-white/5 px-4 py-3 text-sm text-slate-200'>
          <span className='font-semibold text-white'>Tenant attivo: {session.club_public_name}</span>
          <span className='text-slate-300'>Slug: {session.club_slug}</span>
          {notificationEmail ? <span className='text-slate-300'>Notifiche: {notificationEmail}</span> : null}
        </div>
      ) : null}
    </div>
  );
}