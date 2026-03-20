export type TabId = 'game' | 'workshop' | 'mods' | 'settings' | 'editor' | 'admin';

const TAB_TO_PATH: Record<TabId, string> = {
  game: '/game',
  workshop: '/workshop',
  mods: '/mods',
  settings: '/settings',
  editor: '/editor',
  admin: '/admin',
};

const PATH_TO_TAB: Record<string, TabId> = {
  '/': 'game',
  '/game': 'game',
  '/workshop': 'workshop',
  '/mods': 'mods',
  '/settings': 'settings',
  '/editor': 'editor',
  '/admin': 'admin',
};

function normalizePath(pathname: string): string {
  const p = pathname?.trim() || '/';
  if (p === '') return '/';
  return p.endsWith('/') && p !== '/' ? p.slice(0, -1) : p;
}

function resolveHashPath(hash: string): string | null {
  if (!hash || !hash.startsWith('#/')) return null;
  return normalizePath(hash.slice(1));
}

export function tabToPath(tab: TabId): string {
  return TAB_TO_PATH[tab] || '/game';
}

export function locationToTab(loc: Location): TabId {
  const hashPath = resolveHashPath(loc.hash);
  if (hashPath && PATH_TO_TAB[hashPath]) return PATH_TO_TAB[hashPath];

  const path = normalizePath(loc.pathname);
  return PATH_TO_TAB[path] || 'game';
}

