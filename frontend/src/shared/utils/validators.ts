export function isNonEmpty(value: string) {
  return value.trim().length > 0;
}

export function isLikelyPhone(value: string) {
  // Lightweight phone shape check for form-level validation.
  return /^[+0-9()\-\s]{8,20}$/.test(value);
}
