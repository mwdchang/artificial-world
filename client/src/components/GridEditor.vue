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
      <div v-if="isEditingEnabled" class="tool-section">
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

        <!-- Numeric: Edit box with numeric value -->
        <div v-else class="numeric-editor">
          <input
            v-model.number="selectedNumericValue"
            type="number"
            step="any"
            class="number-input"
          />
        </div>
      </div>

      <div v-else class="tool-section read-only-hint">
        <span class="cube-inspect-badge">Data Cube Playback Mode (Read-Only)</span>
      </div>

      <!-- Dispersion Slider (0 to 5) -->
      <div v-if="isEditingEnabled" class="tool-section dispersion-control">
        <label for="dispersionSlider" class="tool-label" :title="dispersionTooltip">
          Disperse: <strong class="dispersion-value">{{ dispersionRadius }}</strong>
        </label>
        <input
          id="dispersionSlider"
          v-model.number="dispersionRadius"
          type="range"
          min="0"
          max="5"
          step="1"
          class="slider"
        />
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
              'in-dispersion': isCellInDispersion(cell.r, cell.c)
            }"
            :style="{ backgroundColor: getCellColor(cell.value) }"
            @mouseenter="hoverCell = { r: cell.r, c: cell.c }"
            @click="handleCellClick(cell.r, cell.c)"
          >
            <span v-if="showCellValues" class="cell-text">
              {{ formatCellValue(cell.value) }}
            </span>
          </div>
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
import type { Variable } from '../types/world';
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
    if (props.variable.variableType === 'categorical' && props.variable.categories?.length) {
      selectedCategory.value = props.variable.categories[0];
    }
  }
);

// View scales
const selectedPalette = ref('nature');
const selectedColormap = ref('viridis');
const showCellValues = ref(false);

// Tile Tools
const selectedCategory = ref(props.variable.categories?.[0] || 'plain');
const selectedNumericValue = ref(17);

// Dispersion slider (0 to 5)
const dispersionRadius = ref(0);

const dispersionTooltip = computed(() => {
  if (props.variable.variableType === 'categorical') {
    return 'Categorical dispersion: Neighbouring cells within radius take the selected category.';
  }
  return 'Numerical dispersion: Neighbours take (1.0 - 0.5 * k) * inputValue at distance k.';
});

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
      const val = grid[r]?.[c] ?? (props.variable.variableType === 'numeric' ? 0 : 'unknown');
      cells.push({ r, c, value: val });
    }
  }
  return cells;
});

// Global numeric range for linear scales across all frames/keyframes
const globalNumericBounds = computed(() => {
  if (props.variable.variableType !== 'numeric') {
    return { min: 0, max: 100 };
  }

  let min = Infinity;
  let max = -Infinity;

  const checkVal = (v: any) => {
    const n = Number(v);
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
  if (typeof val === 'number') {
    return Number.isInteger(val) ? val.toString() : val.toFixed(1);
  }
  return String(val ?? '');
}

function getCellColor(value: any): string {
  if (props.variable.variableType === 'categorical') {
    return getCategoricalColor(
      String(value),
      props.variable.categories || [],
      selectedPalette.value
    );
  }
  const num = typeof value === 'number' ? value : parseFloat(value) || 0;
  return getNumericColor(num, numericMin.value, numericMax.value, selectedColormap.value);
}

const getLinearGradientCss = computed(() => {
  const cmap = LINEAR_COLORMAPS.find(c => c.id === selectedColormap.value) || LINEAR_COLORMAPS[0];
  const stops = cmap.stops
    .map(([ratio, [r, g, b]]) => `rgb(${r},${g},${b}) ${Math.round(ratio * 100)}%`)
    .join(', ');
  return `linear-gradient(to right, ${stops})`;
});

// Dispersion calculation
function isCellInDispersion(r: number, c: number): boolean {
  if (!hoverCell.value || dispersionRadius.value <= 0 || !isEditingEnabled.value) return false;
  const dist = Math.max(Math.abs(r - hoverCell.value.r), Math.abs(c - hoverCell.value.c));
  return dist <= dispersionRadius.value;
}

function handleCellClick(targetR: number, targetC: number) {
  if (didDrag) return;
  if (!isEditingEnabled.value) return;

  const isCategorical = props.variable.variableType === 'categorical';
  const radius = dispersionRadius.value;
  const inputVal = selectedNumericValue.value;
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
          // Numerical: fraction (1.0 - 0.5 * k) * inputValue
          // Clamp at 0 to prevent negative values for k >= 2
          const factor = Math.max(0, 1.0 - 0.5 * k);
          const cellVal = factor * inputVal;
          grid[r][c] = Number(cellVal.toFixed(2));
        }
      }
    }
  }

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

.badge {
  font-size: 0.7rem;
  padding: 0.2rem 0.5rem;
  border-radius: 4px;
  font-weight: 500;
}

.badge.static {
  background: #555;
  color: #eee;
}

.badge.timeVarying {
  background: #555;
  color: #eee;
}

.badge.numeric {
  background: #555;
  color: #eee;
}

.badge.categorical {
  background: #555;
  color: #eee;
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
  font-size: 0.85rem;
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
  font-size: 0.85rem;
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
  font-size: 0.85rem;
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

.dispersion-control {
  display: flex;
  align-items: center;
  gap: 0.4rem;
}

.dispersion-value {
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
  font-size: 0.85rem;
  color: #cbd5e1;
}

.step-counter {
  font-size: 0.8rem;
  color: #94a3b8;
  font-variant-numeric: tabular-nums;
}

.kf-label {
  font-size: 0.85rem;
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

.grid-cell.in-dispersion {
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
</style>
