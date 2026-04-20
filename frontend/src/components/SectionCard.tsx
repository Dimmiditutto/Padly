import { ChevronDown, ChevronUp } from 'lucide-react';
import type { ReactNode } from 'react';
import { useId, useState } from 'react';

export function SectionCard({
  title,
  description,
  actions,
  children,
  elevated = false,
  collapsible = false,
  defaultExpanded = true,
}: {
  title: string;
  description?: string;
  actions?: ReactNode;
  children?: ReactNode;
  elevated?: boolean;
  collapsible?: boolean;
  defaultExpanded?: boolean;
}) {
  const [expanded, setExpanded] = useState(defaultExpanded);
  const contentId = useId();
  const hasContent = children !== undefined && children !== null;

  return (
    <section className={`surface-card ${elevated ? 'shadow-lift' : ''}`}>
      <div className='flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between'>
        <div>
          <h2 className='section-title'>{title}</h2>
          {description ? <p className='mt-1 helper-text'>{description}</p> : null}
        </div>
        {actions || (collapsible && hasContent) ? (
          <div className='flex flex-wrap items-center gap-2 sm:shrink-0 sm:justify-end'>
            {actions ? <div className='shrink-0'>{actions}</div> : null}
            {collapsible && hasContent ? (
              <button
                type='button'
                aria-expanded={expanded}
                aria-controls={contentId}
                aria-label={`${expanded ? 'Comprimi' : 'Espandi'} ${title}`}
                className='inline-flex min-h-10 items-center justify-center gap-2 rounded-full border border-slate-200 bg-white px-3 py-2 text-sm font-semibold text-slate-600 transition hover:border-slate-300 hover:text-slate-950 focus:outline-none focus:ring-2 focus:ring-cyan-100'
                onClick={() => setExpanded((prev) => !prev)}
              >
                {expanded ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
                <span>{expanded ? 'Comprimi' : 'Espandi'}</span>
              </button>
            ) : null}
          </div>
        ) : null}
      </div>
      {hasContent && expanded ? <div id={contentId} className='mt-5'>{children}</div> : null}
    </section>
  );
}