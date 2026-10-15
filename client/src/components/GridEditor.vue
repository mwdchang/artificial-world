<template>
  <main class="grid-editor-main">
    <!-- Header bar for active variable -->
    <div class="editor-header">
      <div class="var-info">
        <h2 class="active-var-name">{{ variable.name }}</h2>
      </div>

      <!-- Time-varying controls: Mode Toggle & Generate Button -->
      <div v-if="variable.gridType === 'timeVarying'" class="time-varying-actions">
        <div class="view-mode-toggle">
          <button
            class="mode-btn"
            :class="{ active: viewMode === 'keyframe' }"
            @click="viewMode = 'keyframe'"
          >
            Keyframes
          </button>
          <button
            class="mode-btn"
            :class="{ active: viewMode === 'datacube' }"
            @click="viewMode = 'datacube'"
          >
            Result
          </button>
        </div>

        <button class="btn btn-generate" @click="handleGenerateDataCube">
          &#x21bb; Generate Result
        </button>
      </div>
    </div>

    <!-- Toolbar: Editing controls & Color scales -->
    <div class="editor-toolbar">
      <!-- Brush / Value selector -->
      <div v-if="isEditingEnabled && !isMovement" class="tool-section">
        <span class="tool-label">
          {{ variable.variableType === 'categorical' ? 'Tile:' : 'Value:' }}
        </span>

        <!-- Categorical: Dropdown with possible categories -->
        <div v-if="variable.variableType === 'categorical'" class="category-selector">
          <select v-model="selectedCategory" class="select-input">
            <option v-for="cat in variable.categories" :key="cat" :value="cat">
              {{ cat }}
            </option>
          </select>
          <span
            class="cat-color-dot"
            :style="{ background: getCategoricalColor(selectedCategory, variable.categories || [], selectedPalette) }"
          />
        </div>

        <!-- Numeric: Distribution editor -->
        <div v-else class="numeric-editor">
          <select v-model="selectedDistributionType" class="select-input">
            <option value="scalar">Scalar</option>
            <option v-if="variable.gridType !== 'timeVarying'" value="normal">Normal</option>
            <option v-if="variable.gridType !== 'timeVarying'" value="uniform">Uniform</option>
          </select>
          <span v-if="selectedDistributionType === 'scalar'" class="parameter-label">Value</span>
          <input
            v-if="selectedDistributionType === 'scalar'"
            v-model.number="selectedScalarValue"
            type="number"
            step="any"
            class="number-input"
            title="Value"
          />
          <template v-else-if="selectedDistributionType === 'normal'">
            <span class="parameter-label">Mean</span>
            <input
              v-model.number="selectedNormalMean"
              type="number"
              step="any"
              class="number-input"
              title="Mean"
              placeholder="Mean"
            />
            <span class="parameter-label">Stddev</span>
            <input
              v-model.number="selectedNormalStddev"
              type="number"
              min="0"
              step="any"
              class="number-input"
              title="Standard deviation"
              placeholder="Stddev"
            />
          </template>
          <template v-else>
            <span class="parameter-label">Min</span>
            <input
              v-model.number="selectedUniformMin"
              type="number"
              step="any"
              class="number-input"
              title="Minimum"
              placeholder="Min"
            />
            <span class="parameter-label">Max</span>
            <input
              v-model.number="selectedUniformMax"
              type="number"
              step="any"
              class="number-input"
              title="Maximum"
              placeholder="Max"
            />
          </template>
        </div>
      </div>

      <div v-else-if="isMovement" class="tool-section movement-hint">
        <button class="btn btn-primary btn-sm" @click="openAlgorithmDialog">
          Custom Algorithm
        </button>
      </div>

      <div v-else class="tool-section read-only-hint">
        <span class="cube-inspect-badge">Data Cube Playback Mode (Read-Only)</span>
      </div>

      <!-- Brush Slider (0 to 5) -->
      <div v-if="isEditingEnabled && !isMovement" class="tool-section brush-control">
        <label for="brushSlider" class="tool-label" :title="brushTooltip">
          Brush: <strong class="brush-value">{{ brushRadius }}</strong>
        </label>
        <input
          id="brushSlider"
          v-model.number="brushRadius"
          type="range"
          min="0"
          max="5"
          step="1"
          class="slider"
        />
      </div>

      <div
        v-if="isEditingEnabled && variable.variableType === 'numeric'"
        class="tool-section"
      >
        <label class="toggle-label" :title="dampenTooltip">
          <input v-model="dampen" type="checkbox" />
          Dampen
        </label>
      </div>

      <!-- Color scale selector -->
      <div class="tool-section">
        <span class="tool-label">Color:</span>
        <select
          v-if="variable.variableType === 'categorical'"
          v-model="selectedPalette"
          class="select-input"
        >
          <option v-for="pal in CATEGORICAL_PALETTES" :key="pal.id" :value="pal.id">
            {{ pal.name }}
          </option>
        </select>
        <select
          v-else
          v-model="selectedColormap"
          class="select-input"
        >
          <option v-for="cmap in LINEAR_COLORMAPS" :key="cmap.id" :value="cmap.id">
            {{ cmap.name }}
          </option>
        </select>
      </div>

      <!-- Grid Overlay Toggles -->
      <div class="tool-section">
        <label class="toggle-label">
          <input v-model="showCellValues" type="checkbox" />
          Show Values
        </label>
      </div>
    </div>

    <!-- Time Slider Bar (for Data Cube inspection mode) -->
    <div v-if="variable.gridType === 'timeVarying' && viewMode === 'datacube'" class="timeline-bar">
      <div class="timeline-controls">
        <button class="btn btn-icon" @click="togglePlayback">
          {{ isPlaying ? '⏸ Pause' : '▶ Play' }}
        </button>
        <button class="btn btn-icon btn-sm" @click="currentStepIndex = 0">
          ⏮ Start
        </button>
        <button class="btn btn-icon btn-sm" @click="currentStepIndex = totalCubeSteps - 1">
          ⏭ End
        </button>
      </div>

      <div class="timeline-scrubber">
        <span class="time-label">Timestep: <strong>{{ currentStepNumber }}</strong></span>
        <input
          v-model.number="currentStepIndex"
          type="range"
          min="0"
          :max="totalCubeSteps - 1"
          class="timeline-slider"
        />
        <span class="step-counter">{{ currentStepIndex + 1 }} / {{ totalCubeSteps }}</span>
      </div>
    </div>

    <!-- Keyframe Selector Bar (for Keyframe editing mode) -->
    <div v-if="variable.gridType === 'timeVarying' && viewMode === 'keyframe'" class="keyframe-bar">
      <div class="kf-label">Active Keyframe:</div>
      <div class="kf-pills">
        <button
          v-for="(kf, idx) in variable.keyframes || []"
          :key="kf.step"
          class="kf-pill"
          :class="{ active: selectedKeyframeIndex === idx }"
          @click="selectedKeyframeIndex = idx"
        >
          Step {{ kf.step }}
        </button>
      </div>

      <div class="kf-add-row">
        <input
          v-model.number="newKeyframeStep"
          type="number"
          placeholder="Step #"
          class="kf-step-input"
          min="0"
          max="100"
        />
        <button class="btn btn-sm btn-outline" @click="addKeyframe">
          + Add Keyframe
        </button>
        <button
          v-if="(variable.keyframes?.length || 0) > 2"
          class="btn btn-sm btn-danger"
          @click="deleteSelectedKeyframe"
        >
          Delete Keyframe
        </button>
      </div>
    </div>

    <!-- Main Grid Canvas Area -->
    <div
      ref="canvasContainerRef"
      class="canvas-container"
      :class="{ 'is-panning': isPanning }"
      @wheel.prevent="handleWheel"
      @mousedown="handleMouseDown"
      @mouseleave="hoverCell = null"
    >
      <div
        class="viewport-layer"
        :style="{
          transform: `translate(${panX}px, ${panY}px) scale(${zoomLevel})`
        }"
      >
        <div
          class="grid-board"
          :style="{
            gridTemplateColumns: `repeat(${worldWidth}, 30px)`,
            gridTemplateRows: `repeat(${worldHeight}, 30px)`
          }"
        >
          <div
            v-for="cell in flatGridCells"
            :key="`${cell.r}-${cell.c}`"
            class="grid-cell"
            :class="{
              'hovered': hoverCell?.r === cell.r && hoverCell?.c === cell.c,
              'in-brush': isCellInBrush(cell.r, cell.c)
            }"
            :style="{ backgroundColor: getCellColor(cell.value) }"
            @mouseenter="hoverCell = { r: cell.r, c: cell.c }"
            @click="handleCellClick(cell.r, cell.c, $event)"
          >
            <span
              v-if="showCellValues"
              class="cell-text distribution-values"
            >{{ formatCellValue(cell.value) }}</span>
            <span
              v-else-if="variable.variableType === 'numeric'"
              class="cell-text distribution-type"
            >{{ getDistributionTypeLabel(cell.value) }}</span>
          </div>
        </div>
      </div>
    </div>

    <!-- Custom Movement Algorithm Dialog -->
    <div
      v-if="showAlgorithmDialog"
      class="algorithm-backdrop"
      @click.self="closeAlgorithmDialog"
    >
      <div class="algorithm-dialog">
        <h3>Custom Movement Algorithm</h3>
        <p class="algorithm-help">
          Define <code>callback(i, j, world)</code> &mdash; <code>i</code> is the row,
          <code>j</code> is the column. Return all 8 rates
          (<code>n, s, e, w, ne, nw, se, sw</code>) as numbers between 0 and 1.
        </p>

        <textarea
          v-model="algorithmCode"
          class="algorithm-textarea"
          spellcheck="false"
          rows="12"
        />

        <div v-if="algorithmError" class="algorithm-error">{{ algorithmError }}</div>

        <div class="algorithm-actions">
          <button class="btn btn-secondary btn-sm" @click="closeAlgorithmDialog">
            Cancel
          </button>
          <button class="btn btn-primary btn-sm" @click="generateAlgorithm">
            Generate
          </button>
        </div>
      </div>
    </div>

    <!-- Movement Cell Editor Popover -->
    <div
      v-if="movementEditor"
      class="movement-popover-backdrop"
      @click.self="movementEditor = null"
    >
      <div class="movement-popover" :style="popoverStyle">
        <div class="mp-header">
          <span>Cell [{{ movementEditor.c }}, {{ movementEditor.r }}]</span>
          <button class="mp-close" @click="movementEditor = null">&times;</button>
        </div>

        <div class="movement-compass">
          <label class="mc-cell">
            <span class="mc-dir">NW</span>
            <input v-model.number="movementEditor.rates.nw" type="number" min="0" max="1" step="0.01" />
          </label>
          <label class="mc-cell">
            <span class="mc-dir">N</span>
            <input v-model.number="movementEditor.rates.n" type="number" min="0" max="1" step="0.01" />
          </label>
          <label class="mc-cell">
            <span class="mc-dir">NE</span>
            <input v-model.number="movementEditor.rates.ne" type="number" min="0" max="1" step="0.01" />
          </label>
          <label class="mc-cell">
            <span class="mc-dir">W</span>
            <input v-model.number="movementEditor.rates.w" type="number" min="0" max="1" step="0.01" />
          </label>
          <div class="mc-cell mc-center" :title="'Sum of all outgoing rates'">
            &Sigma; {{ editorSum.toFixed(2) }}
          </div>
          <label class="mc-cell">
            <span class="mc-dir">E</span>
            <input v-model.number="movementEditor.rates.e" type="number" min="0" max="1" step="0.01" />
          </label>
          <label class="mc-cell">
            <span class="mc-dir">SW</span>
            <input v-model.number="movementEditor.rates.sw" type="number" min="0" max="1" step="0.01" />
          </label>
          <label class="mc-cell">
            <span class="mc-dir">S</span>
            <input v-model.number="movementEditor.rates.s" type="number" min="0" max="1" step="0.01" />
          </label>
          <label class="mc-cell">
            <span class="mc-dir">SE</span>
            <input v-model.number="movementEditor.rates.se" type="number" min="0" max="1" step="0.01" />
          </label>
        </div>

        <div class="mp-actions">
          <button class="btn btn-outline btn-sm" @click="resetMovementEditor">
            Reset 0.01
          </button>
          <button class="btn btn-primary btn-sm" @click="applyMovementEdit">
            Apply
          </button>
        </div>
      </div>
    </div>

    <!-- Legend & Cell Details Footer -->
    <div class="editor-footer">
      <div class="cell-inspect-info">
        <span v-if="hoverCell">
          Cell [{{ hoverCell.c }}, {{ hoverCell.r }}]:
          <strong>{{ formatCellValue(getCellValue(hoverCell.r, hoverCell.c)) }}</strong>
        </span>
      </div>

      <!-- Color Legend -->
      <div class="color-legend">
        <!-- Categorical Legend -->
        <template v-if="variable.variableType === 'categorical'">
          <div
            v-for="cat in variable.categories || []"
            :key="cat"
            class="legend-item"
            @click="selectedCategory = cat"
          >
            <span
              class="legend-color-box"
              :style="{ background: getCategoricalColor(cat, variable.categories || [], selectedPalette) }"
            />
            <span class="legend-label">{{ cat }}</span>
          </div>
        </template>

        <!-- Numeric Legend -->
        <template v-else>
          <span class="legend-label">{{ numericMin }}</span>
          <div
            class="linear-gradient-bar"
            :style="{ background: getLinearGradientCss }"
          />
          <span class="legend-label">{{ numericMax }}</span>
        </template>
      </div>
    </div>
  </main>
</template>

<script setup lang="ts">
import { ref, computed, watch, onUnmounted } from 'vue';
import type {
  Variable,
  MovementRates,
  World,
  DistributionType,
  NumericDistribution,
} from '../types/world';
import {
  MOVEMENT_DIRECTIONS,
  createDefaultMovementRates,
  distributionValue,
  movementSum,
} from '../types/world';
import { generateDataCube } from '../utils/interpolation';
import {
  CATEGORICAL_PALETTES,
  LINEAR_COLORMAPS,
  getCategoricalColor,
  getNumericColor,
} from '../utils/colorScales';

const props = defineProps<{
  variable: Variable;
  worldWidth: number;
  worldHeight: number;
  world: World;
}>();

const emit = defineEmits<{
  (e: 'variableUpdated', variable: Variable): void;
}>();

// Modes
const viewMode = ref<'keyframe' | 'datacube'>(
  props.variable.gridType === 'timeVarying' ? 'keyframe' : 'keyframe'
);

// If variable changes, reset state
watch(
  () => props.variable.name,
  () => {
    viewMode.value = 'keyframe';
    selectedKeyframeIndex.value = 0;
    currentStepIndex.value = 0;
    if (props.variable.gridType === 'timeVarying') {
      selectedDistributionType.value = 'scalar';
    }
    movementEditor.value = null;
    if (props.variable.variableType === 'categorical' && props.variable.categories?.length) {
      selectedCategory.value = props.variable.categories[0];
    }
  }
);

// View scales
const selectedPalette = ref('nature');
const selectedColormap = ref('grayscale');
const showCellValues = ref(false);

// Tile Tools
const selectedCategory = ref(props.variable.categories?.[0] || 'plain');
const selectedDistributionType = ref<DistributionType>('scalar');
const selectedScalarValue = ref(17);
const selectedNormalMean = ref(17);
const selectedNormalStddev = ref(1);
const selectedUniformMin = ref(0);
const selectedUniformMax = ref(1);

// Brush radius (0 to 5)
const brushRadius = ref(0);
const dampen = ref(true);

const brushTooltip = computed(() => {
  if (props.variable.variableType === 'categorical') {
    return 'Neighbouring cells within the brush radius take the selected category.';
  }
  return dampen.value
    ? 'Numerical brush values are reduced with distance from the selected cell.'
    : 'Numerical brush values use the selected value across the brush radius.';
});

const dampenTooltip = 'Reduce numeric brush values with distance from the selected cell.';

// Time-varying keyframes
const selectedKeyframeIndex = ref(0);
const newKeyframeStep = ref(10);

// Data cube timeline scrubbing
const currentStepIndex = ref(0);
const isPlaying = ref(false);
let playbackTimer: number | null = null;

// Hover state
const hoverCell = ref<{ r: number; c: number } | null>(null);

// Zoom & Pan state
const canvasContainerRef = ref<HTMLElement | null>(null);
const zoomLevel = ref(1);
const panX = ref(0);
const panY = ref(0);
const isPanning = ref(false);
let panStartX = 0;
let panStartY = 0;
let panStartPanX = 0;
let panStartPanY = 0;
let didDrag = false;

const MIN_ZOOM = 0.3;
const MAX_ZOOM = 4;
const ZOOM_SENSITIVITY = 0.002;
const PAN_THRESHOLD = 4;

const isEditingEnabled = computed(() => {
  if (props.variable.gridType === 'static') return true;
  return viewMode.value === 'keyframe';
});

const isMovement = computed(() => props.variable.variableType === 'movement');

// Movement cell editor popover state
const movementEditor = ref<{
  r: number;
  c: number;
  x: number;
  y: number;
  rates: MovementRates;
} | null>(null);

// Custom movement algorithm dialog state
const ALGORITHM_STORAGE_KEY = 'artificial_world';
const DEFAULT_ALGORITHM_TEMPLATE = `function callback(i, j, world) {
  return { n: 0.01, s: 0.01, e: 0.01, w: 0.01, ne: 0.01, nw: 0.01, se: 0.01, sw: 0.01 };
}`;
const showAlgorithmDialog = ref(false);
const algorithmCode = ref('');
const algorithmError = ref('');

// Current active 2D grid for display
const activeGrid = computed<any[][]>(() => {
  if (props.variable.gridType === 'static') {
    return props.variable.data || [];
  }

  if (viewMode.value === 'keyframe') {
    const kfs = props.variable.keyframes || [];
    const kf = kfs[selectedKeyframeIndex.value] || kfs[0];
    return kf ? kf.data : [];
  } else {
    // Data cube mode
    const cube = props.variable.data || [];
    const stepIdx = Math.max(0, Math.min(cube.length - 1, currentStepIndex.value));
    return cube[stepIdx] || [];
  }
});

// Flat cells for grid rendering
const flatGridCells = computed(() => {
  const cells: { r: number; c: number; value: any }[] = [];
  const grid = activeGrid.value;
  for (let r = 0; r < props.worldHeight; r++) {
    for (let c = 0; c < props.worldWidth; c++) {
      const fallback = isMovement.value
        ? createDefaultMovementRates()
        : props.variable.variableType === 'numeric'
          ? 0
          : 'unknown';
      const val = grid[r]?.[c] ?? fallback;
      cells.push({ r, c, value: val });
    }
  }
  return cells;
});

// Global numeric range for linear scales across all frames/keyframes
const globalNumericBounds = computed(() => {
  if (props.variable.variableType === 'movement') {
    let min = Infinity;
    let max = -Infinity;
    if (Array.isArray(props.variable.data)) {
      for (const row of props.variable.data) {
        if (!Array.isArray(row)) continue;
        for (const cell of row) {
          const s = movementSum(cell);
          if (s < min) min = s;
          if (s > max) max = s;
        }
      }
    }
    if (min === Infinity) min = 0;
    if (max === -Infinity) max = 0.08; // 8 directions * 0.01 default
    return { min, max };
  }

  if (props.variable.variableType !== 'numeric') {
    return { min: 0, max: 100 };
  }

  let min = Infinity;
  let max = -Infinity;

  const checkVal = (v: any) => {
    const n = typeof v === 'object' && v !== null
      ? distributionValue(v as NumericDistribution)
      : Number(v);
    if (!isNaN(n)) {
      if (n < min) min = n;
      if (n > max) max = n;
    }
  };

  if (props.variable.gridType === 'timeVarying') {
    // 1. Scan across all keyframes
    if (props.variable.keyframes) {
      for (const kf of props.variable.keyframes) {
        if (Array.isArray(kf.data)) {
          for (const row of kf.data) {
            if (Array.isArray(row)) {
              for (const val of row) {
                checkVal(val);
              }
            }
          }
        }
      }
    }

    // 2. Scan across entire data cube if generated
    if (Array.isArray(props.variable.data)) {
      for (const grid of props.variable.data) {
        if (Array.isArray(grid)) {
          for (const row of grid) {
            if (Array.isArray(row)) {
              for (const val of row) {
                checkVal(val);
              }
            }
          }
        }
      }
    }
  } else {
    // Static variable grid
    if (Array.isArray(props.variable.data)) {
      for (const row of props.variable.data) {
        if (Array.isArray(row)) {
          for (const val of row) {
            checkVal(val);
          }
        }
      }
    }
  }

  if (min === Infinity) min = 0;
  if (max === -Infinity) max = 100;

  return { min, max };
});

const numericMin = computed(() => globalNumericBounds.value.min);
const numericMax = computed(() => globalNumericBounds.value.max);

// Total steps in data cube
const totalCubeSteps = computed(() => {
  if (props.variable.gridType !== 'timeVarying') return 0;
  return Array.isArray(props.variable.data) ? props.variable.data.length : 0;
});

const currentStepNumber = computed(() => {
  const kfs = props.variable.keyframes || [];
  if (kfs.length === 0) return currentStepIndex.value;
  const startStep = Math.min(...kfs.map(k => k.step));
  return startStep + currentStepIndex.value;
});

function getCellValue(r: number, c: number): any {
  return activeGrid.value[r]?.[c] ?? '';
}

function formatCellValue(val: any): string {
  if (props.variable.variableType === 'movement') {
    return movementSum(val).toFixed(2);
  }
  if (props.variable.variableType === 'numeric' && val && typeof val === 'object') {
    const distribution = val as NumericDistribution;
    if (distribution.type === 'normal') {
      const value = distribution.value as { mean: number; stddev: number };
      return `mean: ${value.mean}\nstddev: ${value.stddev}`;
    }
    if (distribution.type === 'uniform') {
      const value = distribution.value as { min: number; max: number };
      return `min: ${value.min}\nmax: ${value.max}`;
    }
    return `value: ${Number(distribution.value).toFixed(2)}`;
  }
  if (typeof val === 'number') {
    return Number.isInteger(val) ? val.toString() : val.toFixed(1);
  }
  return String(val ?? '');
}

function getDistributionTypeLabel(value: any): string {
  if (value && typeof value === 'object') {
    if (value.type === 'normal') return 'n';
    if (value.type === 'uniform') return 'u';
  }
  return 's';
}

function getCellColor(value: any): string {
  if (props.variable.variableType === 'categorical') {
    return getCategoricalColor(
      String(value),
      props.variable.categories || [],
      selectedPalette.value
    );
  }
  if (props.variable.variableType === 'movement') {
    return getNumericColor(
      movementSum(value),
      numericMin.value,
      numericMax.value,
      selectedColormap.value
    );
  }
  const num = typeof value === 'object' && value !== null
    ? distributionValue(value as NumericDistribution)
    : typeof value === 'number'
      ? value
      : parseFloat(value) || 0;
  return getNumericColor(num, numericMin.value, numericMax.value, selectedColormap.value);
}

const getLinearGradientCss = computed(() => {
  const cmap = LINEAR_COLORMAPS.find(c => c.id === selectedColormap.value) || LINEAR_COLORMAPS[0];
  const stops = cmap.stops
    .map(([ratio, [r, g, b]]) => `rgb(${r},${g},${b}) ${Math.round(ratio * 100)}%`)
    .join(', ');
  return `linear-gradient(to right, ${stops})`;
});

// Brush highlight calculation
function isCellInBrush(r: number, c: number): boolean {
  if (isMovement.value) return false;
  if (!hoverCell.value || brushRadius.value <= 0 || !isEditingEnabled.value) return false;
  const dist = Math.max(Math.abs(r - hoverCell.value.r), Math.abs(c - hoverCell.value.c));
  return dist <= brushRadius.value;
}

function createBrushDistribution(distance: number): NumericDistribution {
  const factor = dampen.value ? Math.pow(0.95, distance) : 1;

  if (selectedDistributionType.value === 'normal') {
    return {
      type: 'normal',
      value: {
        mean: (Number(selectedNormalMean.value) || 0) * factor,
        stddev: Math.max(0, Number(selectedNormalStddev.value) || 0) * factor,
      },
    };
  }

  if (selectedDistributionType.value === 'uniform') {
    const min = (Number(selectedUniformMin.value) || 0) * factor;
    const max = (Number(selectedUniformMax.value) || 0) * factor;
    return {
      type: 'uniform',
      value: { min: Math.min(min, max), max: Math.max(min, max) },
    };
  }

  return {
    type: 'scalar',
    value: (Number(selectedScalarValue.value) || 0) * factor,
  };
}

function handleCellClick(targetR: number, targetC: number, event?: MouseEvent) {
  if (didDrag) return;
  if (!isEditingEnabled.value) return;

  if (isMovement.value) {
    openMovementEditor(targetR, targetC, event);
    return;
  }

  const isCategorical = props.variable.variableType === 'categorical';
  const radius = brushRadius.value;
  const catVal = selectedCategory.value;

  // Clone grid to update
  const grid = activeGrid.value;

  for (let r = 0; r < props.worldHeight; r++) {
    for (let c = 0; c < props.worldWidth; c++) {
      // Chebyshev distance
      const k = Math.max(Math.abs(r - targetR), Math.abs(c - targetC));
      if (k <= radius) {
        if (isCategorical) {
          // Categorical: neighbours take what user selected
          grid[r][c] = catVal;
        } else {
          grid[r][c] = createBrushDistribution(k);
        }
      }
    }
  }

  emit('variableUpdated', props.variable);
}

// Movement editors
const editorSum = computed(() => {
  const ed = movementEditor.value;
  return ed ? movementSum(ed.rates) : 0;
});

const popoverStyle = computed(() => {
  const ed = movementEditor.value;
  if (!ed) return {};
  const width = 260;
  const height = 240;
  const pad = 12;
  let left = ed.x + 10;
  let top = ed.y + 10;
  if (left + width > window.innerWidth) left = Math.max(pad, ed.x - width - 10);
  if (top + height > window.innerHeight) top = Math.max(pad, ed.y - height - 10);
  return { left: `${left}px`, top: `${top}px` };
});

function openMovementEditor(targetR: number, targetC: number, event?: MouseEvent) {
  const grid = activeGrid.value;
  const current = grid[targetR]?.[targetC];
  const rates: MovementRates = createDefaultMovementRates(0);
  for (const dir of MOVEMENT_DIRECTIONS) {
    const v = Number(current?.[dir]);
    rates[dir] = isNaN(v) ? 0.01 : v;
  }
  movementEditor.value = {
    r: targetR,
    c: targetC,
    x: event?.clientX ?? window.innerWidth / 2,
    y: event?.clientY ?? window.innerHeight / 2,
    rates,
  };
}

function resetMovementEditor() {
  const ed = movementEditor.value;
  if (!ed) return;
  ed.rates = createDefaultMovementRates(0.01);
}

function applyMovementEdit() {
  const ed = movementEditor.value;
  if (!ed) return;
  const cleaned: MovementRates = createDefaultMovementRates(0);
  for (const dir of MOVEMENT_DIRECTIONS) {
    const n = Number(ed.rates[dir]);
    cleaned[dir] = Math.max(0, Math.min(1, isNaN(n) ? 0 : n));
  }
  const grid = activeGrid.value;
  if (grid[ed.r]) grid[ed.r][ed.c] = cleaned;
  movementEditor.value = null;
  emit('variableUpdated', props.variable);
}

// Persist draft algorithm code as { [worldName]: { [variableName]: code } }
function loadAlgorithmCode(worldName: string, variableName: string): string {
  try {
    const raw = localStorage.getItem(ALGORITHM_STORAGE_KEY);
    if (!raw) return '';
    const all = JSON.parse(raw);
    return all?.[worldName]?.[variableName] ?? '';
  } catch {
    return '';
  }
}

function persistAlgorithmCode(worldName: string, variableName: string, code: string) {
  try {
    const raw = localStorage.getItem(ALGORITHM_STORAGE_KEY);
    const all = raw ? JSON.parse(raw) : {};
    if (!all[worldName]) all[worldName] = {};
    all[worldName][variableName] = code;
    localStorage.setItem(ALGORITHM_STORAGE_KEY, JSON.stringify(all));
  } catch {
    // Ignore storage failures (private mode, quota, etc.)
  }
}

function openAlgorithmDialog() {
  const saved = loadAlgorithmCode(props.world.name, props.variable.name);
  algorithmCode.value = saved || DEFAULT_ALGORITHM_TEMPLATE;
  algorithmError.value = '';
  showAlgorithmDialog.value = true;
}

function closeAlgorithmDialog() {
  persistAlgorithmCode(props.world.name, props.variable.name, algorithmCode.value);
  showAlgorithmDialog.value = false;
  algorithmError.value = '';
}

function generateAlgorithm() {
  algorithmError.value = '';
  persistAlgorithmCode(props.world.name, props.variable.name, algorithmCode.value);

  let callback: any;
  try {
    const factory = new Function(
      `${algorithmCode.value}\n;return typeof callback !== 'undefined' ? callback : undefined;`
    );
    callback = factory();
  } catch (err: any) {
    algorithmError.value = `Syntax error: ${err?.message ?? err}`;
    return;
  }

  if (typeof callback !== 'function') {
    algorithmError.value = 'No function named "callback" was defined.';
    return;
  }

  const width = props.worldWidth;
  const height = props.worldHeight;

  // Snapshot the world so the callback can read it without mutating live state.
  let worldSnapshot: World;
  try {
    worldSnapshot = JSON.parse(JSON.stringify(props.world));
  } catch {
    worldSnapshot = props.world;
  }

  const newMovement: MovementRates[][] = Array.from({ length: height }, () =>
    new Array(width)
  );

  for (let i = 0; i < height; i++) {
    for (let j = 0; j < width; j++) {
      let result: any;
      try {
        result = callback(i, j, worldSnapshot);
      } catch (err: any) {
        algorithmError.value = `Error at (${i}, ${j}): ${err?.message ?? err}`;
        return;
      }

      if (!result || typeof result !== 'object') {
        algorithmError.value = `callback(${i}, ${j}) must return an object with all 8 rates.`;
        return;
      }

      const cell: MovementRates = createDefaultMovementRates(0);
      for (const dir of MOVEMENT_DIRECTIONS) {
        const v = result[dir];
        if (typeof v !== 'number' || !isFinite(v) || v < 0 || v > 1) {
          algorithmError.value = `Invalid rate "${dir}" at (${i}, ${j}): ${JSON.stringify(v)}. Must be a number between 0 and 1.`;
          return;
        }
        cell[dir] = v;
      }
      newMovement[i][j] = cell;
    }
  }

  props.variable.data = newMovement;
  showAlgorithmDialog.value = false;
  algorithmError.value = '';
  emit('variableUpdated', props.variable);
}

// Generate full data cube
function handleGenerateDataCube() {
  if (props.variable.gridType !== 'timeVarying' || !props.variable.keyframes) return;

  const { dataCube } = generateDataCube(
    props.variable.keyframes,
    props.worldWidth,
    props.worldHeight
  );

  props.variable.data = dataCube;
  viewMode.value = 'datacube';
  currentStepIndex.value = 0;
  emit('variableUpdated', props.variable);
}

// Keyframe management
function addKeyframe() {
  const step = Number(newKeyframeStep.value);
  if (isNaN(step) || step < 0) return;

  const kfs = props.variable.keyframes || [];
  if (kfs.some(k => k.step === step)) {
    alert(`A keyframe at step ${step} already exists.`);
    return;
  }

  // Clone current active grid or initialize
  const newGrid = Array.from({ length: props.worldHeight }, (_, r) =>
    Array.from({ length: props.worldWidth }, (_, c) => activeGrid.value[r]?.[c] ?? 17)
  );

  kfs.push({ step, data: newGrid });
  kfs.sort((a, b) => a.step - b.step);
  props.variable.keyframes = kfs;

  selectedKeyframeIndex.value = kfs.findIndex(k => k.step === step);
  emit('variableUpdated', props.variable);
}

function deleteSelectedKeyframe() {
  const kfs = props.variable.keyframes || [];
  if (kfs.length <= 2) {
    alert('At least two keyframes (first and last step) must be preserved.');
    return;
  }

  const kf = kfs[selectedKeyframeIndex.value];
  if (confirm(`Delete keyframe at step ${kf.step}?`)) {
    kfs.splice(selectedKeyframeIndex.value, 1);
    selectedKeyframeIndex.value = Math.max(0, selectedKeyframeIndex.value - 1);
    emit('variableUpdated', props.variable);
  }
}

// Timeline Playback
function togglePlayback() {
  if (isPlaying.value) {
    pausePlayback();
  } else {
    startPlayback();
  }
}

function startPlayback() {
  if (totalCubeSteps.value <= 1) return;
  isPlaying.value = true;
  playbackTimer = window.setInterval(() => {
    currentStepIndex.value = (currentStepIndex.value + 1) % totalCubeSteps.value;
  }, 250);
}

function pausePlayback() {
  isPlaying.value = false;
  if (playbackTimer !== null) {
    clearInterval(playbackTimer);
    playbackTimer = null;
  }
}

// Zoom & Pan handlers
function handleWheel(e: WheelEvent) {
  const container = canvasContainerRef.value;
  if (!container) return;

  const rect = container.getBoundingClientRect();
  // Mouse position relative to container center
  const mouseX = e.clientX - rect.left - rect.width / 2;
  const mouseY = e.clientY - rect.top - rect.height / 2;

  const oldZoom = zoomLevel.value;
  const delta = -e.deltaY * ZOOM_SENSITIVITY;
  const newZoom = Math.min(MAX_ZOOM, Math.max(MIN_ZOOM, oldZoom * (1 + delta)));

  // Adjust pan so zoom is centered on mouse position
  const scaleFactor = newZoom / oldZoom;
  panX.value = mouseX - scaleFactor * (mouseX - panX.value);
  panY.value = mouseY - scaleFactor * (mouseY - panY.value);
  zoomLevel.value = newZoom;
}

function handleMouseDown(e: MouseEvent) {
  // Left button drag for panning
  if (e.button === 0) {
    e.preventDefault();
    didDrag = false;
    panStartX = e.clientX;
    panStartY = e.clientY;
    panStartPanX = panX.value;
    panStartPanY = panY.value;

    window.addEventListener('mousemove', handlePanMove);
    window.addEventListener('mouseup', handlePanEnd);
  }
}

function handlePanMove(e: MouseEvent) {
  const dx = e.clientX - panStartX;
  const dy = e.clientY - panStartY;

  // Only start panning after exceeding the threshold
  if (!isPanning.value) {
    if (Math.abs(dx) > PAN_THRESHOLD || Math.abs(dy) > PAN_THRESHOLD) {
      isPanning.value = true;
      didDrag = true;
    } else {
      return;
    }
  }

  panX.value = panStartPanX + dx;
  panY.value = panStartPanY + dy;
}

function handlePanEnd() {
  isPanning.value = false;
  window.removeEventListener('mousemove', handlePanMove);
  window.removeEventListener('mouseup', handlePanEnd);
}

onUnmounted(() => {
  pausePlayback();
  window.removeEventListener('mousemove', handlePanMove);
  window.removeEventListener('mouseup', handlePanEnd);
});
</script>

<style scoped>
.grid-editor-main {
  flex: 1;
  display: flex;
  flex-direction: column;
  background: #0b1329;
  color: #f1f5f9;
  overflow: hidden;
}

.editor-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.75rem 1.25rem;
  background: #111e38;
  border-bottom: 1px solid #1e293b;
  gap: 1rem;
}

.var-info {
  display: flex;
  align-items: center;
  gap: 0.65rem;
}

.active-var-name {
  font-size: 1.15rem;
  font-weight: 700;
  margin: 0;
  color: #38bdf8;
}

.time-varying-actions {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.view-mode-toggle {
  display: flex;
  background: #0f172a;
  padding: 2px;
  border-radius: 6px;
  border: 1px solid #334155;
}

.mode-btn {
  background: transparent;
  color: #94a3b8;
  border: none;
  padding: 0.3rem 0.75rem;
  font-size: 0.8rem;
  font-weight: 500;
  border-radius: 4px;
  cursor: pointer;
}

.mode-btn.active {
  background: #0284c7;
  color: #fff;
}

.btn-generate {
  background: #059669;
  color: #fff;
  font-weight: 600;
  padding: 0.35rem 0.85rem;
  border-radius: 5px;
  border: none;
  cursor: pointer;
  font-size: 0.8rem;
  transition: background 0.15s ease;
}

.btn-generate:hover {
  background: #047857;
}

.editor-toolbar {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 1.25rem;
  padding: 0.65rem 1.25rem;
  background: #0f172a;
  border-bottom: 1px solid #1e293b;
  font-size: 0.8rem;
}

.tool-section {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.tool-label {
  color: #94a3b8;
  font-weight: 500;
}

.select-input,
.number-input {
  background: #1e293b;
  border: 1px solid #334155;
  color: #f8fafc;
  padding: 0.2rem 0.8rem;
  border-radius: 4px;
  font-size: 0.8rem;
}

.number-input {
  width: 80px;
}

.category-selector {
  display: flex;
  align-items: center;
  gap: 0.4rem;
}

.cat-color-dot {
  width: 14px;
  height: 14px;
  border-radius: 50%;
  border: 1px solid #fff;
  display: inline-block;
}

.brush-control {
  display: flex;
  align-items: center;
  gap: 0.4rem;
}

.brush-value {
  color: #38bdf8;
  font-size: 0.95rem;
}

.slider {
  width: 80px;
  accent-color: #38bdf8;
  cursor: pointer;
}


.toggle-label {
  display: flex;
  align-items: center;
  gap: 0.35rem;
  color: #cbd5e1;
  cursor: pointer;
  user-select: none;
}

.read-only-hint .cube-inspect-badge {
  background: #1e3a8a;
  color: #93c5fd;
  padding: 0.25rem 0.6rem;
  border-radius: 4px;
  font-size: 0.8rem;
  font-weight: 500;
}

/* Timeline & Keyframe sub-bars */
.timeline-bar,
.keyframe-bar {
  display: flex;
  align-items: center;
  gap: 1rem;
  padding: 0.5rem 1.25rem;
  background: #162444;
  border-bottom: 1px solid #1e293b;
}

.timeline-controls {
  display: flex;
  gap: 0.35rem;
}

.timeline-scrubber {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  flex: 1;
}

.timeline-slider {
  flex: 1;
  max-width: 320px;
  accent-color: #38bdf8;
}

.time-label {
  font-size: 0.8rem;
  color: #cbd5e1;
}

.step-counter {
  font-size: 0.8rem;
  color: #94a3b8;
  font-variant-numeric: tabular-nums;
}

.kf-label {
  font-size: 0.8rem;
  color: #94a3b8;
  font-weight: 500;
}

.kf-pills {
  display: flex;
  gap: 0.4rem;
}

.kf-pill {
  background: #1e293b;
  border: 1px solid #334155;
  color: #cbd5e1;
  padding: 0.25rem 0.65rem;
  border-radius: 4px;
  font-size: 0.8rem;
  cursor: pointer;
}

.kf-pill.active {
  background: #0284c7;
  color: #fff;
  border-color: #38bdf8;
}

.kf-add-row {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  margin-left: auto;
}

.kf-step-input {
  width: 70px;
  background: #0f172a;
  border: 1px solid #334155;
  color: #f8fafc;
  padding: 0.25rem 0.5rem;
  border-radius: 4px;
  font-size: 0.8rem;
}

/* Grid Area */
.canvas-container {
  flex: 1;
  overflow: hidden;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #080e1e;
  position: relative;
  cursor: grab;
}

.canvas-container.is-panning {
  cursor: grabbing;
}

.viewport-layer {
  transform-origin: center center;
  will-change: transform;
}

.grid-board {
  display: grid;
  gap: 2px;
  background: #1e293b;
  padding: 4px;
  border-radius: 6px;
  box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.4);
}

.grid-cell {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  position: relative;
  transition: transform 0.05s ease, filter 0.1s ease;
  user-select: none;
  border-radius: 2px;
}

.grid-cell:hover,
.grid-cell.hovered {
  filter: brightness(1.2);
  outline: 2px solid #38bdf8;
  z-index: 2;
}

.grid-cell.in-brush {
  box-shadow: inset 0 0 0 2px rgba(255, 255, 255, 0.7);
}

.cell-text {
  font-size: 0.55rem;
  font-weight: 600;
  color: #0f172a;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  max-width: 28px;
  padding: 0 1px;
}

.distribution-type {
  font-size: 0.8rem;
}

.distribution-values {
  white-space: pre-line;
  line-height: 1.15;
}

.parameter-label {
  color: #94a3b8;
  font-size: 0.7rem;
  white-space: nowrap;
}

/* Footer / Legend */
.editor-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.65rem 1.25rem;
  background: #0f172a;
  border-top: 1px solid #1e293b;
  font-size: 0.825rem;
}

.cell-inspect-info {
  color: #cbd5e1;
}

.text-muted {
  color: #64748b;
}

.color-legend {
  display: flex;
  align-items: center;
  gap: 0.85rem;
}

.legend-item {
  display: flex;
  align-items: center;
  gap: 0.35rem;
  cursor: pointer;
}

.legend-color-box {
  width: 14px;
  height: 14px;
  border-radius: 3px;
  display: inline-block;
}

.legend-label {
  font-size: 0.775rem;
  color: #cbd5e1;
}

.linear-gradient-bar {
  width: 120px;
  height: 12px;
  border-radius: 3px;
}

.btn {
  padding: 0.35rem 0.75rem;
  border-radius: 4px;
  font-size: 0.8rem;
  font-weight: 500;
  cursor: pointer;
  border: none;
}

.btn-icon {
  background: #1e293b;
  color: #f8fafc;
}

.btn-icon:hover {
  background: #334155;
}

.btn-sm {
  padding: 0.2rem 0.5rem;
  font-size: 0.75rem;
}

.btn-outline {
  background: transparent;
  border: 1px solid #475569;
  color: #cbd5e1;
}

.btn-outline:hover {
  background: #334155;
}

.btn-danger {
  background: #991b1b;
  color: #fee2e2;
}

.btn-danger:hover {
  background: #b91c1c;
}

.btn-primary {
  background: #0284c7;
  color: #fff;
}

.btn-primary:hover {
  background: #0369a1;
}

.movement-hint .cube-inspect-badge {
  background: #1e3a8a;
  color: #93c5fd;
  padding: 0.25rem 0.6rem;
  border-radius: 4px;
  font-size: 0.8rem;
  font-weight: 500;
}

/* Movement cell editor popover */
.movement-popover-backdrop {
  position: fixed;
  inset: 0;
  z-index: 800;
}

.movement-popover {
  position: fixed;
  width: 260px;
  background: #111e38;
  border: 1px solid #334155;
  border-radius: 8px;
  padding: 0.65rem;
  box-shadow: 0 12px 30px -8px rgba(0, 0, 0, 0.7);
  color: #f1f5f9;
}

.mp-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 0.8rem;
  font-weight: 600;
  color: #38bdf8;
  margin-bottom: 0.5rem;
}

.mp-close {
  background: transparent;
  border: none;
  color: #94a3b8;
  font-size: 1.15rem;
  line-height: 1;
  cursor: pointer;
  padding: 0 0.2rem;
}

.mp-close:hover {
  color: #f87171;
}

.movement-compass {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 4px;
}

.mc-cell {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2px;
}

.mc-dir {
  font-size: 0.65rem;
  color: #94a3b8;
  font-weight: 600;
}

.mc-cell input {
  width: 100%;
  box-sizing: border-box;
  background: #0f172a;
  border: 1px solid #334155;
  color: #f8fafc;
  padding: 0.2rem;
  border-radius: 4px;
  font-size: 0.75rem;
  text-align: center;
}

.mc-center {
  display: flex;
  align-items: center;
  justify-content: center;
  background: #0f172a;
  border: 1px solid #334155;
  border-radius: 4px;
  font-size: 0.8rem;
  font-weight: 700;
  color: #38bdf8;
}

.mp-actions {
  display: flex;
  justify-content: flex-end;
  gap: 0.5rem;
  margin-top: 0.65rem;
}

.btn-secondary {
  background: #374151;
  color: #e5e7eb;
}

.btn-secondary:hover {
  background: #4b5563;
}

/* Custom algorithm dialog */
.algorithm-backdrop {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.7);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 900;
}

.algorithm-dialog {
  width: 620px;
  max-width: 92vw;
  background: #111e38;
  border: 1px solid #334155;
  border-radius: 10px;
  padding: 1.25rem;
  color: #f1f5f9;
  box-shadow: 0 20px 45px -10px rgba(0, 0, 0, 0.8);
}

.algorithm-dialog h3 {
  margin: 0 0 0.5rem 0;
  font-size: 1.1rem;
  color: #38bdf8;
}

.algorithm-help {
  margin: 0 0 0.75rem 0;
  font-size: 0.8rem;
  line-height: 1.5;
  color: #94a3b8;
}

.algorithm-help code {
  background: #0f172a;
  border: 1px solid #1e293b;
  border-radius: 3px;
  padding: 0 0.25rem;
  color: #e2e8f0;
}

.algorithm-textarea {
  width: 100%;
  box-sizing: border-box;
  background: #0b1329;
  border: 1px solid #334155;
  border-radius: 6px;
  color: #e2e8f0;
  padding: 0.65rem;
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  font-size: 0.8rem;
  line-height: 1.5;
  resize: vertical;
}

.algorithm-textarea:focus {
  outline: none;
  border-color: #38bdf8;
}

.algorithm-error {
  margin-top: 0.6rem;
  background: rgba(153, 27, 27, 0.35);
  border: 1px solid #b91c1c;
  color: #fecaca;
  padding: 0.5rem 0.65rem;
  border-radius: 5px;
  font-size: 0.78rem;
  white-space: pre-wrap;
}

.algorithm-actions {
  display: flex;
  justify-content: flex-end;
  gap: 0.6rem;
  margin-top: 0.9rem;
}
</style>
