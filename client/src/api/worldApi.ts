import type { World } from '../types/world';

const BASE_URL = '/api';

export async function fetchWorldNames(): Promise<string[]> {
  const res = await fetch(`${BASE_URL}/worlds`);
  if (!res.ok) {
    throw new Error(`Failed to fetch world list: ${res.statusText}`);
  }
  return res.json();
}

export async function fetchWorld(name: string): Promise<World> {
  const res = await fetch(`${BASE_URL}/worlds/${encodeURIComponent(name)}`);
  if (!res.ok) {
    throw new Error(`Failed to load world "${name}": ${res.statusText}`);
  }
  return res.json();
}

export async function saveWorld(world: World): Promise<{ success: boolean; message: string }> {
  const res = await fetch(`${BASE_URL}/worlds/${encodeURIComponent(world.name)}`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(world),
  });

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.error || `Failed to save world "${world.name}"`);
  }

  return res.json();
}
