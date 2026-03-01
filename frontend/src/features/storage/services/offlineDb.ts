// SQLite boundary for offline persistence (trips, days, incidents).
// TODO: integrate expo-sqlite schema creation and migration strategy.
export async function initializeOfflineDb() {
  return { initialized: false };
}
