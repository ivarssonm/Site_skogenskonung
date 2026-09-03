const months = [
  "januari",
  "februari",
  "mars",
  "april",
  "maj",
  "juni",
  "juli",
  "augusti",
  "september",
  "oktober",
  "november",
  "december",
];

export function parseDate(value: string): Date {
  return new Date(value);
}

export function formatDate(value: string): string {
  const d = parseDate(value);
  if (Number.isNaN(d.getTime())) return value;
  return `${d.getDate()} ${months[d.getMonth()]} ${d.getFullYear()}`;
}

export function formatMonth(year: number, month: number): string {
  return `${months[month - 1]} ${year}`;
}

export function monthSlug(month: number): string {
  return String(month).padStart(2, "0");
}
