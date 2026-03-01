import { deleteMetadata, getMetadata, initializeOfflineDb, setMetadata } from "@/features/storage/services/offlineDb";

const fallbackMemoryStore = new Map<string, string>();

// Lightweight KV storage for app metadata (active user, last sync cursor, flags).
// Uses SQLite metadata table for persistence; falls back to in-memory map if DB is unavailable.
export async function setItem(key: string, value: string) {
  try {
    await initializeOfflineDb();
    await setMetadata(key, value);
  } catch {
    fallbackMemoryStore.set(key, value);
  }
}

export async function getItem(key: string) {
  try {
    await initializeOfflineDb();
    return getMetadata(key);
  } catch {
    return fallbackMemoryStore.get(key) ?? null;
  }
}

export async function removeItem(key: string) {
  try {
    await initializeOfflineDb();
    await deleteMetadata(key);
  } catch {
    fallbackMemoryStore.delete(key);
  }
}
