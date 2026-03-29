<script setup>
import { ref } from 'vue'
import MonacoEditor from './components/MonacoEditor.vue'

const code = ref()

const handleEditorMount = (editor) => {
  console.log('Editor mounted:', editor)
}
</script>

<template>
  <div class="app">
    <header class="header">
      <h1>Monaco Editor</h1>
    </header>
    <main class="main">
      <MonacoEditor
        v-model="code"
        language="python"
        @editor-mounted="handleEditorMount"
      />
    </main>
  </div>
</template>

<style scoped>
.app {
  width: 100%;
  height: 100vh;
  display: flex;
  flex-direction: column;
}

.header {
  padding: 1rem 2rem;
  background: #1e1e1e;
  color: white;
  border-bottom: 1px solid #333;
}

.header h1 {
  margin: 0;
  font-size: 1.5rem;
}

.main {
  flex: 1;
  padding: 1rem;
}
</style>
