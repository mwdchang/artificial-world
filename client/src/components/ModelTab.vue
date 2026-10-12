<template>
  <main class="model-tab-main">
    <div class="editor-header">
      <div class="var-info">
        <h2 class="active-var-name">Model Equations</h2>
        <span class="count-badge">
          {{ world.equations.length }} equation{{ world.equations.length === 1 ? '' : 's' }}
        </span>
      </div>
      <button class="btn btn-primary" @click="addEquation">+ Add Equation</button>
    </div>

    <div class="model-body">
      <p class="model-hint">
        Enter ODE equations of the form <code>dState/dt = expression</code>. Each state is a
        population variable in the grid.
      </p>

      <div v-if="world.equations.length === 0" class="empty-state">
        No equations yet. Click <strong>Add Equation</strong> to define one.
      </div>

      <div v-else class="equation-list">
        <div
          v-for="(_, idx) in world.equations"
          :key="idx"
          class="equation-row"
        >
          <span class="row-index">{{ idx + 1 }}</span>
          <input
            v-model="world.equations[idx]"
            type="text"
            class="equation-input"
            spellcheck="false"
            placeholder="e.g. dS/dt = -beta*S*I"
          />
          <button
            class="delete-btn"
            title="Remove equation"
            @click="removeEquation(idx)"
          >
            &times;
          </button>
        </div>
      </div>
    </div>
  </main>
</template>

<script setup lang="ts">
import type { World } from '../types/world';

const props = defineProps<{
  world: World;
}>();

function addEquation() {
  props.world.equations.push('');
}

function removeEquation(idx: number) {
  props.world.equations.splice(idx, 1);
}
</script>

<style scoped>
.model-tab-main {
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

.count-badge {
  font-size: 0.72rem;
  padding: 0.2rem 0.55rem;
  border-radius: 10px;
  background: #1e293b;
  color: #94a3b8;
  border: 1px solid #334155;
}

.model-body {
  flex: 1;
  overflow-y: auto;
  padding: 1.25rem 4rem;
}

.model-hint {
  margin: 0 0 1rem 0;
  font-size: 0.8rem;
  color: #94a3b8;
  line-height: 1.5;
}

.model-hint code {
  background: #111e38;
  border: 1px solid #1e293b;
  border-radius: 3px;
  padding: 0 0.25rem;
  color: #e2e8f0;
}

.empty-state {
  padding: 3rem 1rem;
  text-align: center;
  color: #64748b;
  font-size: 0.9rem;
  border: 1px dashed #334155;
  border-radius: 8px;
  background: #0f172a;
}

.equation-list {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  max-width: 820px;
}

.equation-row {
  display: flex;
  align-items: center;
  gap: 0.6rem;
}

.row-index {
  width: 1.6rem;
  text-align: right;
  font-size: 0.8rem;
  color: #64748b;
  font-variant-numeric: tabular-nums;
}

.equation-input {
  flex: 1;
  background: #0f172a;
  border: 1px solid #334155;
  border-radius: 5px;
  color: #e2e8f0;
  padding: 0.5rem 0.7rem;
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  font-size: 0.85rem;
}

.equation-input:focus {
  outline: none;
  border-color: #38bdf8;
}

.delete-btn {
  background: transparent;
  border: 1px solid #334155;
  color: #94a3b8;
  font-size: 1.05rem;
  line-height: 1;
  cursor: pointer;
  padding: 0.3rem 0.55rem;
  border-radius: 5px;
}

.delete-btn:hover {
  color: #f87171;
  border-color: #b91c1c;
  background: rgba(239, 68, 68, 0.15);
}

.btn {
  padding: 0.35rem 0.75rem;
  border-radius: 4px;
  font-size: 0.8rem;
  font-weight: 500;
  cursor: pointer;
  border: none;
}

.btn-primary {
  background: #0284c7;
  color: #fff;
}

.btn-primary:hover {
  background: #0369a1;
}
</style>
