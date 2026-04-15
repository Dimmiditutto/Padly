import { Rocket } from 'lucide-react';

export function AppBrand({ light = false }: { light?: boolean }) {
  return (
    <div className='inline-flex items-center gap-3'>
      <div className={`flex h-11 w-11 items-center justify-center rounded-2xl ${light ? 'bg-white/10 text-cyan-200' : 'bg-slate-950 text-cyan-300'}`}>
        <Rocket size={18} />
      </div>
      <div>
        <p className={`text-xs font-semibold uppercase tracking-[0.24em] ${light ? 'text-cyan-200/80' : 'text-cyan-700'}`}>PadelBooking</p>
        <p className={`text-sm font-semibold ${light ? 'text-white' : 'text-slate-950'}`}>1 campo, 1 flusso chiaro, conferma rapida</p>
      </div>
    </div>
  );
}