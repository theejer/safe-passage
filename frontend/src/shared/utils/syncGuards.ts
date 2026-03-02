const UUID_REGEX = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;

export function isUuidLike(value: string) {
  return UUID_REGEX.test(String(value || "").trim());
}

export function isLocalOnlyUserId(userId: string) {
  const normalized = String(userId || "").trim().toLowerCase();
  if (!normalized) return true;
  if (normalized.startsWith("local_")) return true;
  if (normalized.startsWith("demo-")) return true;
  return !isUuidLike(normalized);
}

export function isLocalOnlyTripId(tripId: string) {
  const normalized = String(tripId || "").trim().toLowerCase();
  if (!normalized) return true;
  if (normalized.startsWith("local_")) return true;
  return !isUuidLike(normalized);
}

export function canSyncTripOnline(userId: string) {
  return !isLocalOnlyUserId(userId);
}

export function canSyncItineraryOnline(tripId: string) {
  return !isLocalOnlyTripId(tripId);
}
