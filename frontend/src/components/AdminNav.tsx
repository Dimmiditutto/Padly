import { Link, useLocation } from 'react-router-dom';

const navItems = [
  { to: '/admin', label: 'Crea Prenotazioni' },
  { to: '/admin/prenotazioni-attuali', label: 'Prenotazioni Attuali' },
  { to: '/admin/prenotazioni', label: 'Elenco Prenotazioni' },
  { to: '/admin/log', label: 'Log' },
];

export function AdminNav() {
  const location = useLocation();

  return (
    <nav className='flex flex-wrap gap-2'>
      {navItems.map((item) => {
        const isActive = location.pathname === item.to;

        return (
          <Link
            key={item.to}
            to={item.to}
            className={isActive ? 'inline-flex min-h-12 items-center justify-center gap-2 rounded-2xl border border-brand-700 bg-brand-700 px-4 py-3 text-sm font-semibold text-white transition hover:bg-brand-600 focus:outline-none focus:ring-2 focus:ring-cyan-200' : 'btn-secondary'}
          >
            {item.label}
          </Link>
        );
      })}
    </nav>
  );
}