import type { LucideIcon } from 'lucide-react';

export function EmptyState({
  icon: Icon,
  title,
  description,
}: {
  icon: LucideIcon;
  title: string;
  description: string;
}) {
  return (
    <div className='surface-muted text-center'>
      <div className='mx-auto flex h-12 w-12 items-center justify-center rounded-2xl bg-white text-slate-500 shadow-sm'>
        <Icon size={20} />
      </div>
      <h3 className='mt-4 text-base font-semibold text-slate-950'>{title}</h3>
      <p className='mt-2 text-sm text-slate-600'>{description}</p>
    </div>
  );
}