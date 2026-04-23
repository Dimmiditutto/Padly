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
  collapsedUniform = false,
}: {
  title: string;
  description?: string;
  actions?: ReactNode;
  children?: ReactNode;
  elevated?: boolean;
  collapsible?: boolean;
  defaultExpanded?: boolean;
  collapsedUniform?: boolean;
}) {
  const [expanded, setExpanded] = useState(defaultExpanded);
  const contentId = useId();
  const hasContent = children !== undefined && children !== null;

  return (
    <section className={`surface-card ${elevated ? 'shadow-lift' : ''} ${collapsedUniform && collapsible && !expanded ? 'section-card-collapsed-uniform' : ''}`}>
      <div className='section-card-header'>
        <div className='min-w-0'>
          <h2 className='section-title'>{title}</h2>
          {description ? <p className='mt-1 helper-text'>{description}</p> : null}
        </div>
        {actions || (collapsible && hasContent) ? (
          <div className='section-card-actions'>
            {actions ? <div className='w-full min-w-0 sm:w-auto'>{actions}</div> : null}
            {collapsible && hasContent ? (
              <button
                type='button'
                aria-expanded={expanded}
                aria-controls={contentId}
                aria-label={`${expanded ? 'Comprimi' : 'Espandi'} ${title}`}
                className='btn-pill-secondary sm:self-auto'
                onClick={() => setExpanded((prev) => !prev)}
              >
                {expanded ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
                <span>{expanded ? 'Comprimi' : 'Espandi'}</span>
              </button>
            ) : null}
          </div>
        ) : null}
      </div>
      {hasContent && expanded ? <div id={contentId} className='section-card-content'>{children}</div> : null}
    </section>
  );
}