export const SITE_LABEL: Record<string, string> = {
  site_a: 'Site A',
  site_b: 'Site B',
  site_c_low_data: 'Site C, low data',
}

export function pct(n: number) {
  return `${(n * 100).toFixed(1)}%`
}

export function pts(n: number) {
  return `${(n * 100).toFixed(1)} pts`
}
