import { LoaderCircle } from 'lucide-react';

export function LoadingBlock({
  label = 'Caricamento in corso…',
  labelClassName = 'text-sm',
}: {
  label?: string;
  labelClassName?: string;
}) {
  return (
    <div className='surface-muted flex items-center gap-3'>
      <LoaderCircle className='animate-spin text-cyan-600' size={18} />
      <p className={`${labelClassName} font-medium text-slate-700`}>{label}</p>
    </div>
  );
}

export function SkeletonRows({ rows = 3 }: { rows?: number }) {
  return (
    <div className='space-y-3'>
      {Array.from({ length: rows }).map((_, index) => (
        <div key={index} className='surface-muted'>
          <div className='skeleton h-4 w-24' />
          <div className='mt-3 skeleton h-4 w-full' />
          <div className='mt-2 skeleton h-4 w-2/3' />
        </div>
      ))}
    </div>
  );
}