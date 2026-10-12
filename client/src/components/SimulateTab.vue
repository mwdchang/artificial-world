<template>
  <div class="simulate-tab-container">
    <!-- Control bar -->
    <div class="sim-controls">
      <div class="control-section">
        <label class="control-label" for="stepsInput">Steps:</label>
        <input
          id="stepsInput"
          v-model.number="stepsInput"
          type="number"
          min="1"
          class="number-input"
        />
        <label class="control-label" for="sizeInput">Step size:</label>
        <input
          id="sizeInput"
          v-model.number="sizeInput"
          type="number"
          min="0.1"
          class="number-input"
        />


      </div>

      <button class="btn btn-primary" :disabled="running" @click="runSimulation">
        <span v-if="running">Running&hellip;</span>
        <span v-else>Run Simulation</span>
      </button>

      <div v-if="error" class="error-msg">{{ error }}</div>
    </div>

    <!-- Running -->
    <div v-if="running" class="empty-state">
      <p>
      Running with steps={{stepsInput}} and stepSize={{sizeInput}}
      </p>
    </div>


    <!-- Empty state -->
    <div v-if="!result && !running" class="empty-state">
      <h2>Run Simulation</h2>
      <p>
        Set the number of steps and step size, then click <strong>Run Simulation</strong>.
      </p>
    </div>

    <!-- Result view -->
    <div v-if="result && !running" class="result-view">
      <!-- State selector + legend -->
      <div class="state-toolbar">
        <div class="control-section">
          <label class="control-label" for="stateSelect">State:</label>
          <select id="stateSelect" v-model="selectedState" class="select-input">
            <option v-for="name in stateNames" :key="name" :value="name">
              {{ name }}
            </option>
          </select>
          &nbsp;
          &nbsp;
          &nbsp;
          <label class="control-label" for="colormapSelect">Color:</label>
          <select id="colormapSelect" v-model="selectedColormap" class="select-input">
            <option v-for="cmap in LINEAR_COLORMAPS" :key="cmap.id" :value="cmap.id">
              {{ cmap.name }}
            </option>
          </select>
          &nbsp;
          &nbsp;
          &nbsp;
          <label class="toggle-label">
            <input v-model="globalScale" type="checkbox" />
            Global
          </label>
        </div>


        <div class="time-readout">
          Timestep: <strong>{{ currentStep }}</strong> / {{ totalSteps - 1 }}
          <span class="time-value">(t = {{ currentTime.toFixed(2) }})</span>
        </div>
      </div>

      <!-- Timeline playback -->
      <div class="timeline-bar">
        <button class="btn btn-icon" @click="togglePlayback">
          {{ isPlaying ? '⏸ Pause' : '▶ Play' }}
        </button>
        <button class="btn btn-icon btn-sm" @click="currentStep = 0">⏮</button>
        <input
          v-model.number="currentStep"
          type="range"
          min="0"
          :max="totalSteps - 1"
          class="timeline-slider"
          @input="pausePlayback"
        />
        <button class="btn btn-icon btn-sm" @click="currentStep = totalSteps - 1">⏭</button>
      </div>

      <!-- Grid -->
      <div class="grid-scroll">
        <div
          class="grid-board"
          :style="{
            gridTemplateColumns: `repeat(${world.width}, 42px)`,
            gridTemplateRows: `repeat(${world.height}, 42px)`
          }"
        >
          <div
            v-for="cell in flatCells"
            :key="`${cell.r}-${cell.c}`"
            class="grid-cell"
            :style="{ backgroundColor: cellColor(cell.value) }"
            :title="`[${cell.c}, ${cell.r}] = ${formatValue(cell.value)}`"
            @click="openPopup(cell.r, cell.c, $event)"
          >
            <span class="cell-text">{{ formatValue(cell.value) }}</span>
          </div>
        </div>
      </div>

      <!-- Cell timeseries popup -->
      <div v-if="popup" class="popup-backdrop" @click.self="popup = null">
        <div class="timeseries-popup" :style="popupStyle">
          <div class="popup-header">
            <span>Cell [{{ popup.c }}, {{ popup.r }}] &mdash; states over time</span>
            <button class="popup-close" @click="popup = null">&times;</button>
          </div>

          <svg v-if="chart" class="chart" :viewBox="`0 0 ${chart.W} ${chart.H}`">
            <!-- axes -->
            <line
              :x1="chart.padL"
              :y1="chart.padT"
              :x2="chart.padL"
              :y2="chart.padT + chart.plotH"
              class="axis"
            />
            <line
              :x1="chart.padL"
              :y1="chart.padT + chart.plotH"
              :x2="chart.padL + chart.plotW"
              :y2="chart.padT + chart.plotH"
              class="axis"
            />

            <!-- y range labels -->
            <text :x="chart.padL - 4" :y="chart.padT + 4" class="axis-label" text-anchor="end">
              {{ formatValue(chart.max) }}
            </text>
            <text
              :x="chart.padL - 4"
              :y="chart.padT + chart.plotH"
              class="axis-label"
              text-anchor="end"
            >
              {{ formatValue(chart.min) }}
            </text>

            <!-- series -->
            <polyline
              v-for="s in chart.series"
              :key="s.name"
              :points="s.points"
              fill="none"
              :stroke="s.color"
              stroke-width="1.5"
            />

            <!-- current timestep indicator -->
            <line
              :x1="chart.cursorX"
              :y1="chart.padT"
              :x2="chart.cursorX"
              :y2="chart.padT + chart.plotH"
              class="cursor-line"
            />
          </svg>

          <div class="chart-legend">
            <div v-for="s in chart?.series || []" :key="s.name" class="legend-item">
              <span class="legend-swatch" :style="{ background: s.color }" />
              <span class="legend-name">{{ s.name }}</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onUnmounted, watch } from 'vue';
import type { World } from '../types/world';
import { simulateWorld, type SimulationResult } from '../api/worldApi';
import { getNumericColor, LINEAR_COLORMAPS } from '../utils/colorScales';

const props = defineProps<{
  world: World;
}>();

const STATE_COLORS = ['#38bdf8', '#f472b6', '#4ade80', '#facc15', '#c084fc', '#fb923c'];

// Controls
const stepsInput = ref(50);
const sizeInput = ref(0.1);
const running = ref(false);
const error = ref('');
const result = ref<SimulationResult | null>(null);
const selectedState = ref('');
const selectedColormap = ref('grayscale');
const globalScale = ref(true);

// Playback
const currentStep = ref(0);
const isPlaying = ref(false);
let playbackTimer: number | null = null;

// Cell popup
const popup = ref<{ r: number; c: number; x: number; y: number } | null>(null);

const stateNames = computed<string[]>(() =>
  result.value ? Object.keys(result.value.states) : []
);

const totalSteps = computed(() => result.value?.times.length ?? 0);

const currentTime = computed(() => {
  if (!result.value) return 0;
  return result.value.times[currentStep.value] ?? 0;
});

// Min/max for the selected state - global or per step
const stateBounds = computed(() => {
  const res = result.value;
  const name = selectedState.value;
  if (!res || !name || !res.states[name]) return { min: 0, max: 1 };

  let min = Infinity;
  let max = -Infinity;
  if (globalScale.value) {
    for (const frame of res.states[name]) {
      for (const row of frame) {
        for (const value of row) {
          if (value < min) min = value;
          if (value > max) max = value;
        }
      }
    }
  } else {
    const frame = res.states[name][currentStep.value];
    if (frame) {
      for (const row of frame) {
        for (const value of row) {
          if (value < min) min = value;
          if (value > max) max = value;
        }
      }
    }
  }
  if (min === Infinity) min = 0;
  if (max === -Infinity) max = 1;
  if (min === max) max = min + 1;
  return { min, max };
});

const currentGrid = computed<number[][]>(() => {
  const res = result.value;
  const name = selectedState.value;
  if (!res || !name || !res.states[name]) return [];
  return res.states[name][currentStep.value] || [];
});

const flatCells = computed(() => {
  const cells: { r: number; c: number; value: number }[] = [];
  const grid = currentGrid.value;
  for (let r = 0; r < props.world.height; r++) {
    for (let c = 0; c < props.world.width; c++) {
      cells.push({ r, c, value: grid[r]?.[c] ?? 0 });
    }
  }
  return cells;
});

// Chart data for the selected cell
const chart = computed(() => {
  const res = result.value;
  const p = popup.value;
  if (!res || !p) return null;

  const names = stateNames.value;
  const n = totalSteps.value;

  let min = Infinity;
  let max = -Infinity;
  for (const name of names) {
    for (const frame of res.states[name]) {
      const v = frame[p.r]?.[p.c];
      if (typeof v === 'number') {
        if (v < min) min = v;
        if (v > max) max = v;
      }
    }
  }
  if (min === Infinity) min = 0;
  if (max === -Infinity) max = 1;
  if (min === max) max = min + 1;

  const W = 340;
  const H = 190;
  const padL = 44;
  const padR = 12;
  const padT = 12;
  const padB = 26;
  const plotW = W - padL - padR;
  const plotH = H - padT - padB;

  const xOf = (i: number) => padL + (n <= 1 ? 0 : (i / (n - 1)) * plotW);
  const yOf = (v: number) => padT + plotH - ((v - min) / (max - min)) * plotH;

  const series = names.map((name, idx) => ({
    name,
    color: STATE_COLORS[idx % STATE_COLORS.length],
    points: res.states[name]
      .map((frame, i) => `${xOf(i).toFixed(1)},${yOf(frame[p.r][p.c]).toFixed(1)}`)
      .join(' '),
  }));

  return {
    W,
    H,
    padL,
    padT,
    plotW,
    plotH,
    min,
    max,
    series,
    cursorX: xOf(currentStep.value),
  };
});

const popupStyle = computed(() => {
  const p = popup.value;
  if (!p) return {};
  const width = 380;
  const height = 300;
  const pad = 12;
  let left = p.x + 12;
  let top = p.y + 12;
  if (left + width > window.innerWidth) left = Math.max(pad, p.x - width - 12);
  if (top + height > window.innerHeight) top = Math.max(pad, p.y - height - 12);
  return { left: `${left}px`, top: `${top}px` };
});

function cellColor(value: number): string {
  return getNumericColor(value, stateBounds.value.min, stateBounds.value.max, selectedColormap.value);
}

function formatValue(value: number): string {
  if (typeof value !== 'number' || !isFinite(value)) return '';
  const abs = Math.abs(value);
  if (abs >= 1000) return value.toFixed(0);
  if (abs >= 1) return value.toFixed(1);
  return value.toFixed(2);
}

function openPopup(r: number, c: number, event: MouseEvent) {
  popup.value = { r, c, x: event.clientX, y: event.clientY };
}

async function runSimulation() {
  error.value = '';
  running.value = true;
  pausePlayback();
  try {
    const res = await simulateWorld(props.world.name, stepsInput.value, sizeInput.value);
    result.value = res;
    selectedState.value = Object.keys(res.states)[0] || '';
    currentStep.value = 0;
    popup.value = null;
  } catch (err: any) {
    error.value = err?.message || 'Simulation failed';
  } finally {
    running.value = false;
  }
}

function togglePlayback() {
  if (isPlaying.value) {
    pausePlayback();
  } else {
    startPlayback();
  }
}

function startPlayback() {
  if (totalSteps.value <= 1) return;
  isPlaying.value = true;
  playbackTimer = window.setInterval(() => {
    currentStep.value = (currentStep.value + 1) % totalSteps.value;
  }, 300);
}

function pausePlayback() {
  isPlaying.value = false;
  if (playbackTimer !== null) {
    clearInterval(playbackTimer);
    playbackTimer = null;
  }
}

onUnmounted(() => {
  pausePlayback();
});


watch(
  () => props.world.name,
  () => {
    result.value = null;
  }
)


</script>

<style scoped>
.simulate-tab-container {
  flex: 1;
  display: flex;
  flex-direction: column;
  background: #0b1329;
  color: #f1f5f9;
  overflow: hidden;
}

.sim-controls {
  display: flex;
  align-items: center;
  gap: 1rem;
  padding: 0.75rem 1.25rem;
  background: #111e38;
  border-bottom: 1px solid #1e293b;
}

.control-section {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.control-label {
  color: #94a3b8;
  font-size: 0.8rem;
}

.number-input,
.select-input {
  background: #1e293b;
  border: 1px solid #334155;
  color: #f8fafc;
  padding: 0.3rem 0.6rem;
  border-radius: 4px;
  font-size: 0.8rem;
}

.number-input {
  width: 90px;
}

.toggle-label {
  display: flex;
  align-items: center;
  gap: 0.35rem;
  color: #94a3b8;
  font-size: 0.8rem;
  cursor: pointer;
}

.error-msg {
  color: #fecaca;
  background: rgba(153, 27, 27, 0.35);
  border: 1px solid #b91c1c;
  padding: 0.35rem 0.65rem;
  border-radius: 5px;
  font-size: 0.8rem;
}

/* Empty state */
.empty-state {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  text-align: center;
  padding: 2rem;
  color: #94a3b8;
}

.empty-state h2 {
  color: #38bdf8;
  margin: 0 0 0.75rem 0;
}

.empty-state p {
  max-width: 460px;
  line-height: 1.5;
  font-size: 0.95rem;
}

/* Result */
.result-view {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.state-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  padding: 0.65rem 1.25rem;
  background: #0f172a;
  border-bottom: 1px solid #1e293b;
}

.time-readout {
  font-size: 0.8rem;
  color: #cbd5e1;
}

.time-value {
  color: #94a3b8;
  margin-left: 0.35rem;
}

.timeline-bar {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.5rem 1.25rem;
  background: #162444;
  border-bottom: 1px solid #1e293b;
}

.timeline-slider {
  flex: 1;
  accent-color: #38bdf8;
}

/* Grid */
.grid-scroll {
  flex: 1;
  overflow: auto;
  display: flex;
  justify-content: center;
  align-items: flex-start;
  padding: 1.5rem;
  background: #080e1e;
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
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  border-radius: 2px;
  transition: filter 0.1s ease, outline 0.1s ease;
}

.grid-cell:hover {
  filter: brightness(1.2);
  outline: 2px solid #38bdf8;
  z-index: 2;
}

.cell-text {
  font-size: 0.6rem;
  font-weight: 600;
  color: #0f172a;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  max-width: 38px;
  padding: 0 2px;
}

/* Popup */
.popup-backdrop {
  position: fixed;
  inset: 0;
  z-index: 900;
}

.timeseries-popup {
  position: fixed;
  width: 380px;
  background: #111e38;
  border: 1px solid #334155;
  border-radius: 8px;
  padding: 0.65rem 0.75rem;
  box-shadow: 0 12px 30px -8px rgba(0, 0, 0, 0.7);
  color: #f1f5f9;
}

.popup-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 0.82rem;
  font-weight: 600;
  color: #38bdf8;
  margin-bottom: 0.5rem;
}

.popup-close {
  background: transparent;
  border: none;
  color: #94a3b8;
  font-size: 1.15rem;
  line-height: 1;
  cursor: pointer;
  padding: 0 0.2rem;
}

.popup-close:hover {
  color: #f87171;
}

.chart {
  width: 100%;
  height: auto;
  display: block;
}

.axis {
  stroke: #475569;
  stroke-width: 1;
}

.axis-label {
  fill: #94a3b8;
  font-size: 9px;
}

.cursor-line {
  stroke: #fbbf24;
  stroke-width: 1.5;
  stroke-dasharray: 3 2;
}

.chart-legend {
  display: flex;
  flex-wrap: wrap;
  gap: 0.75rem;
  margin-top: 0.5rem;
}

.legend-item {
  display: flex;
  align-items: center;
  gap: 0.3rem;
  font-size: 0.75rem;
  color: #cbd5e1;
}

.legend-swatch {
  width: 12px;
  height: 3px;
  border-radius: 2px;
  display: inline-block;
}

.btn {
  padding: 0.35rem 0.8rem;
  border-radius: 5px;
  font-size: 0.8rem;
  font-weight: 500;
  cursor: pointer;
  border: none;
}

.btn-primary {
  background: #0284c7;
  color: #fff;
}

.btn-primary:hover:not(:disabled) {
  background: #0369a1;
}

.btn-primary:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-icon {
  background: #1e293b;
  color: #f8fafc;
}

.btn-icon:hover {
  background: #334155;
}

.btn-sm {
  padding: 0.25rem 0.5rem;
  font-size: 0.75rem;
}
</style>
