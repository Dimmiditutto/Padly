import type { ReactNode } from 'react';

export function SectionCard({
  title,
  description,
  actions,
  children,
  elevated = false,
}: {
  title: string;
  description?: string;
  actions?: ReactNode;
  children: ReactNode;
  elevated?: boolean;
}) {
  return (
    <section className={`surface-card ${elevated ? 'shadow-lift' : ''}`}>
      <div className='flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between'>
        <div>
          <h2 className='section-title'>{title}</h2>
          {description ? <p className='mt-1 helper-text'>{description}</p> : null}
        </div>
        {actions ? <div className='shrink-0'>{actions}</div> : null}
      </div>
      <div className='mt-5'>{children}</div>
    </section>
  );
}