export function normalizeTenantSlug(value: string | null | undefined): string | null {
  const normalized = value?.trim().toLowerCase() || '';
  return normalized || null;
}


export function getTenantSlugFromSearchParams(searchParams: Pick<URLSearchParams, 'get'>): string | null {
  return normalizeTenantSlug(
    searchParams.get('tenant')
    || searchParams.get('club')
    || searchParams.get('club_slug')
  );
}


export function getTenantSlugFromPathname(pathname: string | null | undefined): string | null {
  const normalizedPathname = String(pathname || '').trim();
  if (!normalizedPathname.startsWith('/')) {
    return null;
  }

  const segments = normalizedPathname.split('/').filter(Boolean);
  if (segments.length < 2 || segments[0]?.toLowerCase() !== 'c') {
    return null;
  }

  return normalizeTenantSlug(decodeURIComponent(segments[1]));
}


export function resolveTenantSlugFromLocation(locationLike: {
  pathname?: string | null;
  search?: string | null;
}): string | null {
  const fromPathname = getTenantSlugFromPathname(locationLike.pathname);
  if (fromPathname) {
    return fromPathname;
  }

  return getTenantSlugFromSearchParams(new URLSearchParams(locationLike.search || ''));
}


export function withTenantPath(path: string, tenantSlug?: string | null): string {
  const resolvedTenantSlug = normalizeTenantSlug(tenantSlug);
  if (!resolvedTenantSlug) {
    return path;
  }

  const [pathname, search = ''] = path.split('?', 2);
  const params = new URLSearchParams(search);
  if (!params.get('tenant')) {
    params.set('tenant', resolvedTenantSlug);
  }

  const serialized = params.toString();
  return serialized ? `${pathname}?${serialized}` : pathname;
}