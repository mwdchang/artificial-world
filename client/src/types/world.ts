export type GridType = 'static' | 'timeVarying';
export type VariableType = 'numeric' | 'categorical';

export interface Keyframe {
  step: number;
  data: number[][];
}

export interface Variable {
  name: string;
  gridType: GridType;
  variableType: VariableType;
  categories: string[] | null;
  keyframes: Keyframe[] | null;
  // For static: 2D array [row][col] (strings or numbers)
  // For timeVarying: 3D data cube [stepIndex][row][col] (numbers)
  data: any[][];
}

export interface World {
  name: string;
  width: number;
  height: number;
  variables: Variable[];
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

  // 2. temperature (timeVarying, numeric, steps [0, 20], default 17)
  const tempGridStep0: number[][] = Array.from({ length: height }, () =>
    Array.from({ length: width }, () => 17)
  );
  const tempGridStep20: number[][] = Array.from({ length: height }, () =>
    Array.from({ length: width }, () => 17)
  );

  // Generate initial data cube for steps 0 to 20 (21 steps)
  const tempCube: number[][][] = Array.from({ length: 21 }, () =>
    Array.from({ length: height }, () => Array.from({ length: width }, () => 17))
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
  };
}
