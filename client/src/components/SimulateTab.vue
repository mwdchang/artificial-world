<template>
  <div class="simulate-tab-container">
    <div class="placeholder-card">
      <div class="icon">🔬</div>
      <h2>Simulate Tab</h2>
      <p>
        The simulation engine will run on the server side in a future phase.
      </p>
      <div class="hint-box">
        Current dataset is configured and ready in the <strong>Build</strong> tab.
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
</script>

<style scoped>
.simulate-tab-container {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #0b1329;
  color: #f8fafc;
  padding: 2rem;
}

.placeholder-card {
  background: #111e38;
  border: 1px solid #1e293b;
  border-radius: 12px;
  padding: 3rem 2.5rem;
  max-width: 480px;
  text-align: center;
  box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.5);
}

.icon {
  font-size: 3rem;
  margin-bottom: 1rem;
}

.placeholder-card h2 {
  font-size: 1.5rem;
  margin: 0 0 0.75rem 0;
  color: #38bdf8;
}

.placeholder-card p {
  color: #94a3b8;
  font-size: 0.95rem;
  line-height: 1.5;
  margin-bottom: 1.5rem;
}

.hint-box {
  background: #0f172a;
  border: 1px solid #334155;
  padding: 0.75rem 1rem;
  border-radius: 6px;
  font-size: 0.85rem;
  color: #cbd5e1;
}
</style>
