export type GridType = 'static' | 'timeVarying';
export type VariableType = 'numeric' | 'categorical' | 'movement';
export type DistributionType = 'scalar' | 'normal' | 'uniform';

export interface NumericDistribution {
  type: DistributionType;
  value: number | { mean: number; stddev: number } | { min: number; max: number };
}

export function scalarDistribution(value = 0): NumericDistribution {
  return { type: 'scalar', value };
}

export function distributionValue(distribution: NumericDistribution): number {
  if (distribution.type === 'normal') {
    const value = distribution.value as { mean: number; stddev: number };
    return value.mean;
  }
  if (distribution.type === 'uniform') {
    const value = distribution.value as { min: number; max: number };
    return (value.min + value.max) / 2;
  }
  return Number(distribution.value) || 0;
}

export interface Keyframe {
  step: number;
  data: NumericDistribution[][];
}

export interface MovementRates {
  n: number;
  s: number;
  e: number;
  w: number;
  ne: number;
  nw: number;
  se: number;
  sw: number;
}

// Compass order used for display and summation.
export const MOVEMENT_DIRECTIONS: (keyof MovementRates)[] = [
  'nw',
  'n',
  'ne',
  'w',
  'e',
  'sw',
  's',
  'se',
];

export function createDefaultMovementRates(rate = 0.01): MovementRates {
  return {
    n: rate,
    s: rate,
    e: rate,
    w: rate,
    ne: rate,
    nw: rate,
    se: rate,
    sw: rate,
  };
}

export function movementSum(rates: any): number {
  if (!rates || typeof rates !== 'object') return 0;
  return MOVEMENT_DIRECTIONS.reduce(
    (total, dir) => total + (Number(rates[dir]) || 0),
    0
  );
}

export interface Variable {
  name: string;
  gridType: GridType;
  variableType: VariableType;
  categories: string[] | null;
  keyframes: Keyframe[] | null;
  // For static: 2D array [row][col] (strings, movement rates, or distributions)
  // For timeVarying: 3D data cube [stepIndex][row][col] (scalar distributions)
  data: any[][];
}

export interface World {
  name: string;
  width: number;
  height: number;
  variables: Variable[];
  equations: string[];
}

export function createDefaultWorld(name = 'New World', width = 10, height = 10): World {
  // Predefined variables according to plan.md:
  // 1. land (static, categorical, categories: plain, forest, water, mountain, default plain)
  const landData: string[][] = Array.from({ length: height }, () =>
    Array.from({ length: width }, () => 'plain')
  );

  const landVariable: Variable = {
    name: 'land',
    gridType: 'static',
    variableType: 'categorical',
    categories: ['plain', 'forest', 'water', 'mountain'],
    keyframes: null,
    data: landData,
  };

  // 2. temperature (timeVarying, numeric, steps [0, 20], default 15)
  const defaultTemp = scalarDistribution(15);
  const tempGridStep0: NumericDistribution[][] = Array.from({ length: height }, () =>
    Array.from({ length: width }, () => ({ ...defaultTemp }))
  );
  const tempGridStep20: NumericDistribution[][] = Array.from({ length: height }, () =>
    Array.from({ length: width }, () => ({ ...defaultTemp }))
  );

  // Generate initial data cube for steps 0 to 20 (21 steps)
  const tempCube: NumericDistribution[][][] = Array.from({ length: 21 }, () =>
    Array.from({ length: height }, () =>
      Array.from({ length: width }, () => ({ ...defaultTemp }))
    )
  );

  const temperatureVariable: Variable = {
    name: 'temperature',
    gridType: 'timeVarying',
    variableType: 'numeric',
    categories: null,
    keyframes: [
      { step: 0, data: tempGridStep0 },
      { step: 20, data: tempGridStep20 },
    ],
    data: tempCube,
  };

  return {
    name,
    width,
    height,
    variables: [landVariable, temperatureVariable],
    equations: [],
  };
}
