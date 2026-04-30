import type { ReactNode } from 'react';
import { Link } from 'react-router-dom';

export function PageBrandBar({
  actions,
  className = '',
  logoTo = '/',
}: {
  actions?: ReactNode;
  className?: string;
  logoTo?: string;
}) {
  return (
    <div className={`page-brand-bar ${className}`.trim()}>
      <Link className='page-brand-logo-link' to={logoTo} aria-label='Torna alla home Matchinn'>
        <img src='/dark.png' alt='Matchinn' className='page-brand-logo-image' />
      </Link>
      {actions ? <div className='page-brand-actions'>{actions}</div> : null}
    </div>
  );
}