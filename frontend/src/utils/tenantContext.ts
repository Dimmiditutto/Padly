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