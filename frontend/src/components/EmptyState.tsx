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
    <div className='surface-muted px-5 py-6 text-center'>
      <div className='mx-auto flex h-12 w-12 items-center justify-center rounded-2xl border border-cyan-100 bg-white text-cyan-700 shadow-sm'>
        <Icon size={20} />
      </div>
      <h3 className='mt-4 text-base font-semibold text-slate-950'>{title}</h3>
      <p className='mt-2 text-sm text-slate-600'>{description}</p>
    </div>
  );
}