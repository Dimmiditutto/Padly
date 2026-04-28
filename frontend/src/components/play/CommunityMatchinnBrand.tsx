export function CommunityMatchinnBrand({
  clubName,
}: {
  clubName: string;
}) {
  const normalizedClubName = clubName.toUpperCase();

  return (
    <p className='text-sm font-semibold'>
      <span className='uppercase tracking-[0.18em] text-cyan-100/80'>COMMUNITY</span>{' '}
      <span className='matchinn-wordmark matchinn-wordmark-hero'><span className='matchinn-wordmark-match'>match</span><span className='matchinn-wordmark-inn'>inn</span></span>{' '}
      <span className='uppercase tracking-[0.18em] text-cyan-100/80'>{normalizedClubName}</span>
    </p>
  );
}