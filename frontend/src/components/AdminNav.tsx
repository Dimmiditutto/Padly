import { Link, useLocation } from 'react-router-dom';
import type { AdminSession } from '../types';
import { getTenantSlugFromSearchParams, withTenantPath } from '../utils/tenantContext';

const navItems = [
  { to: '/admin', label: 'Crea Prenotazioni' },
  { to: '/admin/prenotazioni-attuali', label: 'Prenotazioni Attuali' },
  { to: '/admin/prenotazioni', label: 'Elenco Prenotazioni' },
];

export function AdminNav(_: { session?: AdminSession | null; notificationEmail?: string | null }) {
  const location = useLocation();
  const tenantSlug = getTenantSlugFromSearchParams(new URLSearchParams(location.search));

  return (
    <nav className='admin-nav'>
      {navItems.map((item) => {
        const isActive = location.pathname === item.to;

        return (
          <Link
            key={item.to}
            to={withTenantPath(item.to, tenantSlug)}
            className={isActive ? 'admin-nav-tab admin-nav-tab-active' : 'admin-nav-tab'}
          >
            <span className='admin-nav-tab-label'>{item.label}</span>
          </Link>
        );
      })}
    </nav>
  );
}