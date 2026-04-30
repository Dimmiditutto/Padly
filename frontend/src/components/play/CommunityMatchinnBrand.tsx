export function CommunityMatchinnBrand({
  clubName,
}: {
  clubName?: string | null;
}) {
  const normalizedClubName = clubName?.trim().toUpperCase();

  return (
    <p className='text-sm font-semibold text-cyan-100/80'>
      <span>Community</span>
      {normalizedClubName ? (
        <>
          {' '}
          <span className='uppercase tracking-[0.18em] text-cyan-100/80'>{normalizedClubName}</span>
        </>
      ) : null}
    </p>
  );
}