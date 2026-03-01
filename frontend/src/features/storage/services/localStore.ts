// AsyncStorage wrapper boundary for lightweight key-value persistence.
const memoryStore = new Map<string, string>();

export async function setItem(key: string, value: string) {
  memoryStore.set(key, value);
}

export async function getItem(key: string) {
  return memoryStore.get(key) ?? null;
}
