export function AppBrand({ light = false }: { light?: boolean }) {
  return (
    <div className='inline-flex items-center'>
      <p className={`text-sm font-semibold uppercase tracking-[0.24em] ${light ? 'text-cyan-200/80' : 'text-cyan-700'}`}>PadelBooking</p>
    </div>
  );
}