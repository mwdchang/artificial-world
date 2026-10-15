import type { Keyframe, NumericDistribution } from '../types/world';
import { distributionValue, scalarDistribution } from '../types/world';

/**
 * Smoothstep interpolation factor: 3u^2 - 2u^3
 * Ensures 0 derivative at endpoints for smooth blending.
 */
function smoothstep(u: number): number {
  const clamped = Math.max(0, Math.min(1, u));
  return clamped * clamped * (3 - 2 * clamped);
}

/**
 * Interpolates full 3D data cube from keyframes.
 * Returns an array of 2D grids from minStep to maxStep.
 */
export function generateDataCube(
  keyframes: Keyframe[],
  width: number,
  height: number
): { dataCube: NumericDistribution[][][]; startStep: number; endStep: number } {
  if (!keyframes || keyframes.length === 0) {
    return { dataCube: [], startStep: 0, endStep: 0 };
  }

  // Sort keyframes ascending by step
  const sorted = [...keyframes].sort((a, b) => a.step - b.step);

  const startStep = sorted[0].step;
  const endStep = sorted[sorted.length - 1].step;
  const totalSteps = endStep - startStep + 1;

  if (totalSteps <= 0) {
    return { dataCube: [sorted[0].data], startStep, endStep: startStep };
  }

  const dataCube: NumericDistribution[][][] = [];

  for (let s = startStep; s <= endStep; s++) {
    // Find surrounding keyframes
    let k0 = sorted[0];
    let k1 = sorted[sorted.length - 1];

    for (let i = 0; i < sorted.length - 1; i++) {
      if (s >= sorted[i].step && s <= sorted[i + 1].step) {
        k0 = sorted[i];
        k1 = sorted[i + 1];
        break;
      }
    }

    const grid: NumericDistribution[][] = [];
    const stepSpan = k1.step - k0.step;
    const factor = stepSpan === 0 ? 0 : smoothstep((s - k0.step) / stepSpan);

    for (let r = 0; r < height; r++) {
      const row: NumericDistribution[] = [];
      for (let c = 0; c < width; c++) {
        const v0 = distributionValue(k0.data[r]?.[c] ?? scalarDistribution(0));
        const v1 = distributionValue(k1.data[r]?.[c] ?? scalarDistribution(0));
        const val = v0 + (v1 - v0) * factor;
        row.push(scalarDistribution(Number(val.toFixed(2))));
      }
      grid.push(row);
    }
    dataCube.push(grid);
  }

  return { dataCube, startStep, endStep };
}
