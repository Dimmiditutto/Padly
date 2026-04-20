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
            className={isActive ? 'btn-primary' : 'btn-secondary'}
          >
            {item.label}
          </Link>
        );
      })}
    </nav>
  );
}