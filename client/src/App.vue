<template>
  <div class="app-layout">
    <!-- Top summary & navigation -->
    <TopBar
      :world="world"
      :currentTab="currentTab"
      @update:currentTab="currentTab = $event"
      @update:world="handleWorldLoaded"
      @createNewWorld="handleCreateNewWorld"
    />

    <!-- Main View Content -->
    <div class="app-body">
      <!-- Build Tab -->
      <template v-if="currentTab === 'build'">
        <!-- Left Pane: Variable Selector -->
        <VariableList
          :variables="world.variables"
          :selectedIndex="selectedVariableIndex"
          :worldWidth="world.width"
          :worldHeight="world.height"
          @selectVariable="selectedVariableIndex = $event"
          @addVariable="handleAddVariable"
          @deleteVariable="handleDeleteVariable"
        />

        <!-- Right Pane: Grid Information and Editor -->
        <GridEditor
          v-if="selectedVariable"
          :key="selectedVariable.name"
          :variable="selectedVariable"
          :worldWidth="world.width"
          :worldHeight="world.height"
          @variableUpdated="handleVariableUpdated"
        />
        <div v-else class="empty-selection">
          No variable selected. Add or select a variable from the left pane.
        </div>
      </template>

      <!-- Simulate Tab -->
      <SimulateTab v-else />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue';
import type { World, Variable } from './types/world';
import { createDefaultWorld } from './types/world';
import TopBar from './components/TopBar.vue';
import VariableList from './components/VariableList.vue';
import GridEditor from './components/GridEditor.vue';
import SimulateTab from './components/SimulateTab.vue';

// Initialize with predefined variables (land, temperature)
const world = ref<World>(createDefaultWorld('TestWorld', 10, 10));
const currentTab = ref<'build' | 'simulate'>('build');
const selectedVariableIndex = ref<number>(0);

const selectedVariable = computed<Variable | null>(() => {
  if (
    selectedVariableIndex.value >= 0 &&
    selectedVariableIndex.value < world.value.variables.length
  ) {
    return world.value.variables[selectedVariableIndex.value];
  }
  return world.value.variables[0] || null;
});

function handleCreateNewWorld(payload: { name: string; width: number; height: number }) {
  world.value = createDefaultWorld(payload.name, payload.width, payload.height);
  selectedVariableIndex.value = 0;
}

function handleWorldLoaded(loaded: World) {
  world.value = loaded;
  selectedVariableIndex.value = 0;
}

function handleAddVariable(newVar: Variable) {
  world.value.variables.push(newVar);
  selectedVariableIndex.value = world.value.variables.length - 1;
}

function handleDeleteVariable(idx: number) {
  world.value.variables.splice(idx, 1);
  if (selectedVariableIndex.value >= world.value.variables.length) {
    selectedVariableIndex.value = Math.max(0, world.value.variables.length - 1);
  }
}

function handleVariableUpdated(updated: Variable) {
  if (selectedVariableIndex.value >= 0) {
    world.value.variables[selectedVariableIndex.value] = updated;
  }
}
</script>

<style scoped>
.app-layout {
  display: flex;
  flex-direction: column;
  height: 100vh;
  width: 100vw;
  overflow: hidden;
  background: #0f172a;
}

.app-body {
  display: flex;
  flex: 1;
  overflow: hidden;
}

.empty-selection {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #94a3b8;
  font-size: 1rem;
}
</style>
