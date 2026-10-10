<template>
  <header class="top-bar">
    <div class="brand-section">
      <h1 class="app-title">Artificial World</h1>
      <nav class="tab-nav">
        <button
          class="tab-btn"
          :class="{ active: currentTab === 'build' }"
          @click="$emit('update:currentTab', 'build')"
        >
          Build
        </button>
        <button
          class="tab-btn"
          :class="{ active: currentTab === 'simulate' }"
          @click="$emit('update:currentTab', 'simulate')"
        >
          Simulate
        </button>
      </nav>
    </div>

    <!-- Summary & Controls (visible on Build tab) -->
    <div v-if="currentTab === 'build'" class="world-summary">
      <div class="summary-item">
        <label>World Name:</label>
        <input
          v-model="localName"
          type="text"
          class="input-name"
          placeholder="World name"
          @change="updateWorldName"
        />
      </div>

      <div class="summary-item dimensions-badge">
        <span class="dim-label">Size:</span>
        <span class="dim-val">{{ world.width }} &times; {{ world.height }}</span>
      </div>

      <div class="actions">
        <button class="btn btn-secondary" @click="showNewModal = true">
          New
        </button>

        <button class="btn btn-secondary" @click="openLoadModal">
          Load
        </button>

        <button class="btn btn-primary" :disabled="saving" @click="handleSave">
          <span v-if="saving">Saving...</span>
          <span v-else>Save</span>
        </button>
      </div>
    </div>

    <!-- Feedback Message -->
    <div v-if="notification" class="notification-toast" :class="notification.type">
      {{ notification.message }}
    </div>

    <!-- New World Modal -->
    <div v-if="showNewModal" class="modal-backdrop" @click.self="showNewModal = false">
      <div class="modal-card">
        <h3>Create New World</h3>
        <p class="modal-hint">Will auto-generate predefined variables: <strong>land</strong> and <strong>temperature</strong>.</p>
        
        <div class="form-group">
          <label>Name</label>
          <input v-model="newWorldName" type="text" placeholder="e.g. Terra Nova" />
        </div>

        <div class="form-row">
          <div class="form-group">
            <label>Width</label>
            <input v-model.number="newWorldWidth" type="number" min="3" max="50" />
          </div>
          <div class="form-group">
            <label>Height</label>
            <input v-model.number="newWorldHeight" type="number" min="3" max="50" />
          </div>
        </div>

        <div class="modal-actions">
          <button class="btn btn-secondary" @click="showNewModal = false">Cancel</button>
          <button class="btn btn-primary" @click="confirmNewWorld">Create World</button>
        </div>
      </div>
    </div>

    <!-- Load World Modal -->
    <div v-if="showLoadModal" class="modal-backdrop" @click.self="showLoadModal = false">
      <div class="modal-card">
        <h3>Load Existing World</h3>
        <p class="modal-hint">Select a saved world from the server repository:</p>

        <div v-if="loadingList" class="loading-state">Fetching saved worlds...</div>
        <div v-else-if="savedWorlds.length === 0" class="empty-state">
          No saved worlds found on server.
        </div>
        <div v-else class="world-list-select">
          <div
            v-for="name in savedWorlds"
            :key="name"
            class="world-item-row"
            :class="{ selected: selectedWorldToLoad === name }"
            @click="selectedWorldToLoad = name"
          >
            <span class="world-item-name">{{ name }}</span>
            <button class="btn btn-sm btn-primary" @click.stop="confirmLoad(name)">
              Load
            </button>
          </div>
        </div>

        <div class="modal-actions">
          <button class="btn btn-secondary" @click="showLoadModal = false">Close</button>
        </div>
      </div>
    </div>
  </header>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue';
import type { World } from '../types/world';
import { fetchWorldNames, fetchWorld, saveWorld } from '../api/worldApi';

const props = defineProps<{
  world: World;
  currentTab: 'build' | 'simulate';
}>();

const emit = defineEmits<{
  (e: 'update:currentTab', tab: 'build' | 'simulate'): void;
  (e: 'update:world', world: World): void;
  (e: 'createNewWorld', payload: { name: string; width: number; height: number }): void;
}>();

const localName = ref(props.world.name);
watch(() => props.world.name, (newName) => {
  localName.value = newName;
});

function updateWorldName() {
  if (localName.value.trim()) {
    props.world.name = localName.value.trim();
  }
}

// Modals
const showNewModal = ref(false);
const newWorldName = ref('TestWorld');
const newWorldWidth = ref(10);
const newWorldHeight = ref(10);

function confirmNewWorld() {
  const name = newWorldName.value.trim() || 'New World';
  const width = Math.max(3, Math.min(50, newWorldWidth.value || 10));
  const height = Math.max(3, Math.min(50, newWorldHeight.value || 10));
  emit('createNewWorld', { name, width, height });
  showNewModal.value = false;
}

// Load Modal
const showLoadModal = ref(false);
const loadingList = ref(false);
const savedWorlds = ref<string[]>([]);
const selectedWorldToLoad = ref('');

async function openLoadModal() {
  showLoadModal.value = true;
  loadingList.value = true;
  try {
    savedWorlds.value = await fetchWorldNames();
  } catch (err: any) {
    showToast(err.message, 'error');
  } finally {
    loadingList.value = false;
  }
}

async function confirmLoad(name: string) {
  try {
    const loaded = await fetchWorld(name);
    emit('update:world', loaded);
    showLoadModal.value = false;
    showToast(`Loaded "${name}" successfully`, 'success');
  } catch (err: any) {
    showToast(err.message, 'error');
  }
}

// Save Action
const saving = ref(false);
const notification = ref<{ message: string; type: 'success' | 'error' } | null>(null);

function showToast(message: string, type: 'success' | 'error') {
  notification.value = { message, type };
  setTimeout(() => {
    if (notification.value?.message === message) {
      notification.value = null;
    }
  }, 3500);
}

async function handleSave() {
  saving.value = true;
  updateWorldName();
  try {
    const res = await saveWorld(props.world);
    showToast(res.message || `World "${props.world.name}" saved!`, 'success');
  } catch (err: any) {
    showToast(err.message || 'Failed to save world', 'error');
  } finally {
    saving.value = false;
  }
}
</script>

<style scoped>
.top-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  background: #1e293b;
  color: #f8fafc;
  padding-top: 0.3rem;
  padding-bottom: 0.2rem;
  padding-left: 1rem;
  padding-right: 1rem;
  border-bottom: 1px solid #ccccee;
  position: relative;
  gap: 1rem;
}

.brand-section {
  display: flex;
  align-items: center;
  gap: 1.5rem;
}

.app-title {
  font-size: 1.25rem;
  margin: 0;
  letter-spacing: 0.025em;
  color: #38bdf8;
}

.tab-nav {
  display: flex;
  background: #0f172a;
  border-radius: 6px;
  padding: 3px;
  gap: 2px;
}

.tab-btn {
  background: transparent;
  color: #94a3b8;
  border: none;
  padding: 0.2rem 0.8rem;
  font-size: 0.8rem;
  border-radius: 4px;
  cursor: pointer;
  transition: all 0.15s ease;
}

.tab-btn:hover {
  color: #f1f5f9;
}

.tab-btn.active {
  background: #38bdf8;
  color: #0f172a;
}

.world-summary {
  display: flex;
  align-items: center;
  gap: 1.25rem;
}

.summary-item {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.8rem;
}

.summary-item label {
  color: #94a3b8;
}

.input-name {
  background: #0f172a;
  color: #f8fafc;
  border: 1px solid #475569;
  border-radius: 4px;
  padding: 0.3rem 0.6rem;
  font-size: 0.8rem;
}

.input-name:focus {
  border-color: #38bdf8;
  outline: none;
}

.dimensions-badge {
  background: #0f172a;
  padding: 0.3rem 0.6rem;
  border-radius: 4px;
  border: 1px solid #334155;
}

.dim-label {
  color: #94a3b8;
  margin-right: 0.25rem;
}

.dim-val {
  color: #e2e8f0;
}

.actions {
  display: flex;
  gap: 0.5rem;
}

.btn {
  padding: 0.2rem 0.8rem;
  border-radius: 5px;
  font-size: 0.85rem;
  cursor: pointer;
  border: none;
  transition: background 0.15s ease;
}

.btn-primary {
  background: #0284c7;
  color: #fff;
}

.btn-primary:hover:not(:disabled) {
  background: #0369a1;
}

.btn-secondary {
  background: #334155;
  color: #e2e8f0;
}

.btn-secondary:hover {
  background: #475569;
}

.btn-sm {
  padding: 0.25rem 0.6rem;
  font-size: 0.775rem;
}

.btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.notification-toast {
  position: absolute;
  top: 100%;
  right: 1.5rem;
  margin-top: 0.5rem;
  padding: 0.5rem 1rem;
  border-radius: 6px;
  font-size: 0.85rem;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2);
  z-index: 1000;
}

.notification-toast.success {
  background: #065f46;
  color: #a7f3d0;
  border: 1px solid #059669;
}

.notification-toast.error {
  background: #881337;
  color: #fecdd3;
  border: 1px solid #e11d48;
}

/* Modal styles */
.modal-backdrop {
  position: fixed;
  inset: 0;
  background: rgba(15, 23, 42, 0.75);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 999;
}

.modal-card {
  background: #1e293b;
  border: 1px solid #475569;
  border-radius: 8px;
  width: 380px;
  max-width: 90vw;
  padding: 1.5rem;
  color: #f8fafc;
}

.modal-card h3 {
  margin: 0 0 0.5rem 0;
  font-size: 1.15rem;
}

.modal-hint {
  font-size: 0.8rem;
  color: #94a3b8;
  margin-bottom: 1.25rem;
}

.form-group {
  margin-bottom: 1rem;
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
}

.form-group label {
  font-size: 0.8rem;
  color: #cbd5e1;
}

.form-group input {
  background: #0f172a;
  border: 1px solid #334155;
  color: #f8fafc;
  padding: 0.45rem 0.65rem;
  border-radius: 4px;
}

.form-row {
  display: flex;
  gap: 1rem;
}

.form-row .form-group {
  flex: 1;
}

.modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: 0.75rem;
  margin-top: 1.25rem;
}

.world-list-select {
  max-height: 200px;
  overflow-y: auto;
  border: 1px solid #334155;
  border-radius: 4px;
  background: #0f172a;
  margin-bottom: 1rem;
}

.world-item-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.5rem 0.75rem;
  border-bottom: 1px solid #1e293b;
}

.world-item-row:hover {
  background: #1e293b;
}

.world-item-name {
  font-size: 0.8rem;
}

.loading-state,
.empty-state {
  padding: 1.5rem;
  text-align: center;
  color: #94a3b8;
  font-size: 0.8rem;
}
</style>
