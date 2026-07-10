const MONTHS = [
  "January",
  "February",
  "March",
  "April",
  "May",
  "June",
  "July",
  "August",
  "September",
  "October",
  "November",
  "December",
];

/**
 * Format an ISO date string (yyyy-mm-dd) as "Month D, YYYY" — e.g. "May 2, 2026".
 *
 * Manual format avoids SSR/locale hydration mismatches that come with
 * `toLocaleDateString`.
 */
export function formatDate(iso: string): string {
  const [y, m, d] = iso.split("-").map(Number);
  return `${MONTHS[m - 1]} ${d}, ${y}`;
}
