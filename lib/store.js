import fs from "node:fs/promises";
import path from "node:path";

const STORE_PATH = path.join(process.cwd(), "data", "store.json");

export async function loadStore() {
  try {
    const raw = await fs.readFile(STORE_PATH, "utf8");
    return JSON.parse(raw);
  } catch {
    return { goats: [], breeds: [], orders: [] };
  }
}

export async function saveStore(store) {
  store.updated_at = new Date().toISOString();
  await fs.mkdir(path.dirname(STORE_PATH), { recursive: true });
  const tmp = STORE_PATH + ".tmp";
  await fs.writeFile(tmp, JSON.stringify(store, null, 2), "utf8");
  await fs.rename(tmp, STORE_PATH);
}
