<template>
  <aside class="variable-list-pane">
    <div class="pane-header">
      <h2>Variables</h2>
      <button class="btn btn-sm btn-outline" @click="showAddModal = true">
        + Add
      </button>
    </div>

    <div class="var-list">
      <div
        v-for="(v, idx) in variables"
        :key="v.name"
        class="var-card"
        :class="{ active: selectedIndex === idx }"
        @click="$emit('selectVariable', idx)"
      >
        <div class="var-card-header">
          <span class="var-name">{{ v.name }}</span>
          <button
            class="delete-btn"
            title="Delete variable"
            @click.stop="confirmDelete(idx)"
          >
            &times;
          </button>
        </div>

        <div class="var-badges">
          <span class="badge" :class="v.gridType">
            {{ v.gridType === 'static' ? 'Static' : 'Time-Varying' }}
          </span>
          <span class="badge" :class="v.variableType">
            {{
              v.variableType === 'numeric'
                ? 'Numeric'
                : v.variableType === 'categorical'
                  ? 'Categorical'
                  : 'Movement'
            }}
          </span>
        </div>
      </div>
    </div>

    <!-- Add Variable Modal -->
    <div v-if="showAddModal" class="modal-backdrop" @click.self="showAddModal = false">
      <div class="modal-card">
        <h3>Add Variable</h3>

        <div class="form-group">
          <label>Variable Name</label>
          <input
            v-model="newVarName"
            type="text"
            placeholder="e.g. elevation, population"
            @keydown.enter="confirmAdd"
          />
        </div>

        <div class="form-group">
          <label>Grid Type</label>
          <div class="radio-group">
            <label class="radio-label">
              <input v-model="newGridType" type="radio" value="static" />
              Static
            </label>
            <label class="radio-label">
              <input
                v-model="newGridType"
                type="radio"
                value="timeVarying"
                :disabled="newVarType === 'movement'"
              />
              Time-Varying
            </label>
          </div>
        </div>

        <div class="form-group">
          <label>Variable Type</label>
          <div class="radio-group">
            <label class="radio-label" :class="{ disabled: newGridType === 'timeVarying' }">
              <input
                v-model="newVarType"
                type="radio"
                value="categorical"
                :disabled="newGridType === 'timeVarying'"
              />
              Categorical
            </label>
            <label class="radio-label">
              <input v-model="newVarType" type="radio" value="numeric" />
              Numeric
            </label>
            <label class="radio-label" :class="{ disabled: newGridType === 'timeVarying' }">
              <input
                v-model="newVarType"
                type="radio"
                value="movement"
                :disabled="newGridType === 'timeVarying'"
              />
              Movement
            </label>
          </div>
          <span v-if="newGridType === 'timeVarying'" class="field-note">
            * Time-varying variables can only be numerical.
          </span>
          <span v-else-if="newVarType === 'movement'" class="field-note">
            * Movement variables are always static. Rates must be between 0 and 1.
          </span>
        </div>

        <div v-if="newVarType === 'categorical'" class="form-group">
          <label>Categories (comma separated)</label>
          <input
            v-model="newCategoriesInput"
            type="text"
            placeholder="e.g. desert, grassland, snow"
          />
        </div>

        <div v-if="newVarType === 'numeric'" class="form-group">
          <label>Default Initial Value</label>
          <input v-model.number="newDefaultNumeric" type="number" step="any" />
        </div>

        <div v-if="newVarType === 'movement'" class="form-group">
          <label>Default Movement Rate (all directions)</label>
          <input
            v-model.number="newDefaultMovement"
            type="number"
            step="0.01"
            min="0"
            max="1"
          />
        </div>

        <div class="modal-actions">
          <button class="btn btn-secondary" @click="showAddModal = false">Cancel</button>
          <button class="btn btn-primary" :disabled="!isFormValid" @click="confirmAdd">
            Add Variable
          </button>
        </div>
      </div>
    </div>
  </aside>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue';
import type { Variable, GridType, VariableType } from '../types/world';
import { createDefaultMovementRates } from '../types/world';
import { generateDataCube } from '../utils/interpolation';

const props = defineProps<{
  variables: Variable[];
  selectedIndex: number;
  worldWidth: number;
  worldHeight: number;
}>();

const emit = defineEmits<{
  (e: 'selectVariable', index: number): void;
  (e: 'addVariable', variable: Variable): void;
  (e: 'deleteVariable', index: number): void;
}>();

// Add variable modal state
const showAddModal = ref(false);
const newVarName = ref('');
const newGridType = ref<GridType>('static');
const newVarType = ref<VariableType>('numeric');
const newCategoriesInput = ref('catA, catB, catC');
const newDefaultNumeric = ref(0);
const newDefaultMovement = ref(0.01);

// Auto-switch variableType to numeric if timeVarying is selected
watch(newGridType, (val) => {
  if (val === 'timeVarying') {
    newVarType.value = 'numeric';
  }
});

// Movement variables are always static
watch(newVarType, (val) => {
  if (val === 'movement') {
    newGridType.value = 'static';
  }
});

const isFormValid = computed(() => {
  if (!newVarName.value.trim()) return false;
  if (newVarType.value === 'categorical') {
    const cats = newCategoriesInput.value.split(',').map(c => c.trim()).filter(Boolean);
    if (cats.length === 0) return false;
  }
  return true;
});

function confirmAdd() {
  if (!isFormValid.value) return;

  const name = newVarName.value.trim();
  const width = props.worldWidth;
  const height = props.worldHeight;

  if (newVarType.value === 'movement') {
    const rate = Math.max(0, Math.min(1, Number(newDefaultMovement.value) || 0));
    const data = Array.from({ length: height }, () =>
      Array.from({ length: width }, () => createDefaultMovementRates(rate))
    );

    emit('addVariable', {
      name,
      gridType: 'static',
      variableType: 'movement',
      categories: null,
      keyframes: null,
      data,
    });
  } else if (newGridType.value === 'static') {
    if (newVarType.value === 'categorical') {
      const categories = newCategoriesInput.value
        .split(',')
        .map((c) => c.trim())
        .filter(Boolean);
      const defaultCategory = categories[0] || 'unknown';
      const data = Array.from({ length: height }, () =>
        Array.from({ length: width }, () => defaultCategory)
      );

      emit('addVariable', {
        name,
        gridType: 'static',
        variableType: 'categorical',
        categories,
        keyframes: null,
        data,
      });
    } else {
      const defaultVal = Number(newDefaultNumeric.value || 0);
      const data = Array.from({ length: height }, () =>
        Array.from({ length: width }, () => defaultVal)
      );

      emit('addVariable', {
        name,
        gridType: 'static',
        variableType: 'numeric',
        categories: null,
        keyframes: null,
        data,
      });
    }
  } else {
    // Time-varying (numeric only)
    const defaultVal = Number(newDefaultNumeric.value || 0);
    const grid0 = Array.from({ length: height }, () =>
      Array.from({ length: width }, () => defaultVal)
    );
    const grid20 = Array.from({ length: height }, () =>
      Array.from({ length: width }, () => defaultVal)
    );

    const keyframes = [
      { step: 0, data: grid0 },
      { step: 20, data: grid20 },
    ];

    const { dataCube } = generateDataCube(keyframes, width, height);

    emit('addVariable', {
      name,
      gridType: 'timeVarying',
      variableType: 'numeric',
      categories: null,
      keyframes,
      data: dataCube,
    });
  }

  // Reset modal
  newVarName.value = '';
  newCategoriesInput.value = 'catA, catB, catC';
  newDefaultNumeric.value = 0;
  newDefaultMovement.value = 0.01;
  newVarType.value = 'numeric';
  newGridType.value = 'static';
  showAddModal.value = false;
}

function confirmDelete(idx: number) {
  if (props.variables.length <= 1) {
    alert('At least one variable must remain in the world.');
    return;
  }
  const variable = props.variables[idx];
  if (confirm(`Are you sure you want to delete variable "${variable.name}"?`)) {
    emit('deleteVariable', idx);
  }
}
</script>

<style scoped>
.variable-list-pane {
  width: 270px;
  background: #111827;
  border-right: 1px solid #1f2937;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.pane-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.85rem 1rem;
  border-bottom: 1px solid #1f2937;
}

.pane-header h2 {
  font-size: 0.95rem;
  font-weight: 600;
  color: #e5e7eb;
  margin: 0;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.var-list {
  flex: 1;
  overflow-y: auto;
  padding: 0.75rem;
  display: flex;
  flex-direction: column;
  gap: 0.6rem;
}

.var-card {
  background: #1f2937;
  border: 1px solid #374151;
  border-radius: 6px;
  padding: 0.75rem;
  cursor: pointer;
  transition: all 0.15s ease;
}

.var-card:hover {
  background: #283548;
  border-color: #4b5563;
}

.var-card.active {
  background: #1e3a5f;
  border-color: #38bdf8;
  box-shadow: 0 0 0 1px #38bdf8;
}

.var-card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 0.4rem;
}

.var-name {
  font-weight: 600;
  color: #f9fafb;
  font-size: 0.925rem;
}

.delete-btn {
  background: transparent;
  border: none;
  color: #9ca3af;
  font-size: 1.1rem;
  line-height: 1;
  cursor: pointer;
  padding: 0 0.2rem;
  border-radius: 3px;
}

.delete-btn:hover {
  color: #f87171;
  background: rgba(239, 68, 68, 0.15);
}

.var-badges {
  display: flex;
  gap: 0.35rem;
  margin-bottom: 0.4rem;
}

.badge {
  font-size: 0.7rem;
  padding: 0.15rem 0.4rem;
  border-radius: 3px;
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

.badge.movement {
  background: #555;
  color: #eee;
}

.categories-preview,
.keyframes-preview {
  font-size: 0.725rem;
  color: #9ca3af;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.btn {
  padding: 0.3rem 0.65rem;
  border-radius: 4px;
  font-size: 0.8rem;
  font-weight: 500;
  cursor: pointer;
  border: none;
}

.btn-outline {
  background: transparent;
  border: 1px solid #4b5563;
  color: #d1d5db;
}

.btn-outline:hover {
  background: #374151;
  color: #fff;
}

.btn-primary {
  background: #0284c7;
  color: #fff;
}

.btn-primary:hover:not(:disabled) {
  background: #0369a1;
}

.btn-secondary {
  background: #374151;
  color: #e5e7eb;
}

.btn-secondary:hover {
  background: #4b5563;
}

.btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* Modal */
.modal-backdrop {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.75);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 999;
}

.modal-card {
  background: #1f2937;
  border: 1px solid #374151;
  border-radius: 8px;
  width: 400px;
  max-width: 90vw;
  padding: 1.5rem;
  color: #f9fafb;
}

.modal-card h3 {
  margin: 0 0 1rem 0;
  font-size: 1.15rem;
}

.form-group {
  margin-bottom: 1rem;
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
}

.form-group label {
  font-size: 0.8rem;
  font-weight: 500;
  color: #d1d5db;
}

.form-group input[type="text"],
.form-group input[type="number"] {
  background: #111827;
  border: 1px solid #374151;
  color: #f9fafb;
  padding: 0.45rem 0.65rem;
  border-radius: 4px;
}

.radio-group {
  display: flex;
  gap: 1.25rem;
  margin-top: 0.2rem;
}

.radio-label {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  font-size: 0.85rem;
  cursor: pointer;
}

.radio-label.disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.field-note {
  font-size: 0.725rem;
  color: #f59e0b;
}

.modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: 0.75rem;
  margin-top: 1.25rem;
}
</style>
