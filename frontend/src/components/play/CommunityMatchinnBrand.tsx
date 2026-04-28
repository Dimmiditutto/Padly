export function CommunityMatchinnBrand({
  clubName,
}: {
  clubName: string;
}) {
  const normalizedClubName = clubName.toUpperCase();

  return (
    <p className='text-sm font-semibold'>
      <span className='uppercase tracking-[0.18em] text-cyan-100/80'>COMMUNITY</span>{' '}
      <span className='text-white'>MATCH</span><span className='text-brand-600'>INN</span>{' '}
      <span className='uppercase tracking-[0.18em] text-cyan-100/80'>{normalizedClubName}</span>
    </p>
  );
}