// Audio belongs in IndexedDB, not sessionStorage's small string quota.
function database() {
  return new Promise((resolve, reject) => {
    const req = indexedDB.open("vaani_audio", 1);
    req.onupgradeneeded = () => req.result.createObjectStore("recordings");
    req.onsuccess = () => resolve(req.result);
    req.onerror = () => reject(req.error);
  });
}
export async function audioStore(operation, id, blob) {
  const db = await database();
  try {
    return await new Promise((resolve, reject) => {
      const tx = db.transaction("recordings", operation === "get" ? "readonly" : "readwrite");
      const store = tx.objectStore("recordings");
      const req = operation === "put" ? store.put(blob, id) : operation === "delete" ? store.delete(id) : store.get(id);
      tx.oncomplete = () => resolve(req.result);
      tx.onerror = () => reject(tx.error);
      tx.onabort = () => reject(tx.error);
    });
  } finally { db.close(); }
}
