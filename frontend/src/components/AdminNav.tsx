import { Link, useLocation } from 'react-router-dom';

const navItems = [
  { to: '/admin', label: 'Dashboard' },
  { to: '/admin/prenotazioni', label: 'Prenotazioni' },
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