export function formatIsoDate(value: string) {
  // Simple date formatter helper; localize later as needed.
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toISOString().slice(0, 10);
}
