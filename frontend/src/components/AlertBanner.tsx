import { AlertCircle, BadgeCheck, Info, OctagonAlert } from 'lucide-react';
import type { ReactNode } from 'react';

const toneMap = {
  info: { className: 'alert-info', icon: Info },
  success: { className: 'alert-success', icon: BadgeCheck },
  warning: { className: 'alert-warning', icon: OctagonAlert },
  error: { className: 'alert-error', icon: AlertCircle },
} as const;

export function AlertBanner({
  tone,
  title,
  children,
}: {
  tone: keyof typeof toneMap;
  title?: string;
  children: ReactNode;
}) {
  const Icon = toneMap[tone].icon;

  return (
    <div className={toneMap[tone].className}>
      <div className='flex items-start gap-3'>
        <Icon size={18} className='mt-0.5 shrink-0' />
        <div>
          {title ? <p className='font-semibold'>{title}</p> : null}
          <div className={title ? 'mt-1' : ''}>{children}</div>
        </div>
      </div>
    </div>
  );
}