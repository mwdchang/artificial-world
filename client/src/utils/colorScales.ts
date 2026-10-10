export interface CategoricalPalette {
  id: string;
  name: string;
  colors: string[];
  namedDefaults?: Record<string, string>;
}

export interface LinearColorMap {
  id: string;
  name: string;
  // Array of stops: [ratio (0-1), [r, g, b]]
  stops: [number, [number, number, number]][];
}

export const CATEGORICAL_PALETTES: CategoricalPalette[] = [
  {
    id: 'nature',
    name: 'Nature (Default)',
    namedDefaults: {
      plain: '#86efac',
      forest: '#15803d',
      water: '#38bdf8',
      mountain: '#64748b',
    },
    colors: ['#86efac', '#15803d', '#38bdf8', '#64748b', '#fbbf24', '#f87171', '#c084fc'],
  },
  {
    id: 'vivid',
    name: 'Vivid Palette',
    colors: ['#3b82f6', '#f97316', '#22c55e', '#a855f7', '#eab308', '#ef4444', '#06b6d4'],
  },
  {
    id: 'pastel',
    name: 'Pastel Palette',
    colors: ['#bfdbfe', '#fed7aa', '#bbf7d0', '#e9d5ff', '#fef08a', '#fecaca', '#a5f3fc'],
  },
  {
    id: 'contrast',
    name: 'High Contrast',
    colors: ['#2563eb', '#dc2626', '#16a34a', '#d97706', '#9333ea', '#0891b2', '#4b5563'],
  },
];

export const LINEAR_COLORMAPS: LinearColorMap[] = [
  {
    id: 'viridis',
    name: 'Viridis',
    stops: [
      [0.0, [68, 1, 84]],
      [0.25, [59, 82, 139]],
      [0.5, [33, 145, 140]],
      [0.75, [94, 201, 98]],
      [1.0, [253, 231, 37]],
    ],
  },
  {
    id: 'thermal',
    name: 'Thermal / Heat',
    stops: [
      [0.0, [15, 23, 42]],
      [0.3, [88, 28, 135]],
      [0.6, [225, 29, 72]],
      [0.85, [249, 115, 22]],
      [1.0, [254, 240, 138]],
    ],
  },
  {
    id: 'coolwarm',
    name: 'Cool to Warm',
    stops: [
      [0.0, [59, 130, 246]],
      [0.5, [243, 244, 246]],
      [1.0, [239, 68, 68]],
    ],
  },
  {
    id: 'ocean',
    name: 'Ocean Blues',
    stops: [
      [0.0, [8, 47, 73]],
      [0.5, [14, 165, 233]],
      [1.0, [224, 242, 254]],
    ],
  },
  {
    id: 'grayscale',
    name: 'Grayscale',
    stops: [
      [0.0, [15, 23, 42]],
      [0.5, [148, 163, 184]],
      [1.0, [248, 250, 252]],
    ],
  },
];

export function getCategoricalColor(
  category: string,
  categories: string[] = [],
  paletteId = 'nature'
): string {
  const palette = CATEGORICAL_PALETTES.find((p) => p.id === paletteId) || CATEGORICAL_PALETTES[0];

  if (palette.namedDefaults && palette.namedDefaults[category.toLowerCase()]) {
    return palette.namedDefaults[category.toLowerCase()];
  }

  const idx = categories.indexOf(category);
  if (idx >= 0) {
    return palette.colors[idx % palette.colors.length];
  }

  // Hash-based fallback
  let hash = 0;
  for (let i = 0; i < category.length; i++) {
    hash = category.charCodeAt(i) + ((hash << 5) - hash);
  }
  const colorIdx = Math.abs(hash) % palette.colors.length;
  return palette.colors[colorIdx];
}

export function getNumericColor(
  value: number,
  min: number,
  max: number,
  colormapId = 'viridis'
): string {
  const colormap = LINEAR_COLORMAPS.find((c) => c.id === colormapId) || LINEAR_COLORMAPS[0];

  const range = max - min;
  const t = range === 0 ? 0.5 : Math.max(0, Math.min(1, (value - min) / range));

  // Interpolate between stops
  const stops = colormap.stops;
  let s0 = stops[0];
  let s1 = stops[stops.length - 1];

  for (let i = 0; i < stops.length - 1; i++) {
    if (t >= stops[i][0] && t <= stops[i + 1][0]) {
      s0 = stops[i];
      s1 = stops[i + 1];
      break;
    }
  }

  const span = s1[0] - s0[0];
  const ratio = span === 0 ? 0 : (t - s0[0]) / span;

  const r = Math.round(s0[1][0] + (s1[1][0] - s0[1][0]) * ratio);
  const g = Math.round(s0[1][1] + (s1[1][1] - s0[1][1]) * ratio);
  const b = Math.round(s0[1][2] + (s1[1][2] - s0[1][2]) * ratio);

  return `rgb(${r}, ${g}, ${b})`;
}
