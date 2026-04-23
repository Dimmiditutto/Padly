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
      <nav className='admin-nav'>
        {navItems.map((item) => {
          const isActive = location.pathname === item.to;

          return (
            <Link
              key={item.to}
              to={withTenantPath(item.to, tenantSlug)}
              className={isActive ? 'admin-nav-tab admin-nav-tab-active' : 'admin-nav-tab'}
            >
              {item.label}
            </Link>
          );
        })}
      </nav>
      {session ? (
        <div className='admin-nav-context'>
          <span className='font-semibold text-white'>Tenant attivo: {session.club_public_name}</span>
          <span className='text-slate-300'>Slug: {session.club_slug}</span>
          {notificationEmail ? <span className='text-slate-300'>Notifiche: {notificationEmail}</span> : null}
        </div>
      ) : null}
    </div>
  );
}