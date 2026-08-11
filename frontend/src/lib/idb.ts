import { get, set, del, keys } from 'idb-keyval'

/**
 * Wraps idb-keyval so offline drafts (e.g. an in-progress ticket report) survive
 * a page reload while the device has no connectivity.
 */
export const idbStore = {
  get: <T>(key: string) => get<T>(key),
  set: <T>(key: string, value: T) => set(key, value),
  remove: (key: string) => del(key),
  keys: () => keys(),
}
