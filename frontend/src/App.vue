<script setup>
// 导入Vue的ref函数用于创建响应式变量
import { ref } from 'vue'
// 导入MonacoEditor组件
import MonacoEditor from './components/MonacoEditor.vue'

// 创建一个响应式的code变量用于存储编辑器内容
const code = ref()

// 处理编辑器挂载完成的回调函数
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
      <!-- MonacoEditor组件：绑定code数据、设置语言为Python、监听编辑器挂载事件 -->
      <MonacoEditor
        v-model="code"
        language="python"
        @editor-mounted="handleEditorMount"
      />
    </main>
  </div>
</template>

<style scoped>
/* 应用容器样式：占据全屏高度并使用flex布局 */
.app {
  width: 100%;
  height: 100vh;
  display: flex;
  flex-direction: column;
}

/* 页眉样式：深色背景配白色文字 */
.header {
  padding: 1rem 2rem;
  background: #1e1e1e;
  color: white;
  border-bottom: 1px solid #333;
}

/* 标题样式 */
.header h1 {
  margin: 0;
  font-size: 1.5rem;
}

/* 主体内容样式：占据剩余空间并添加内边距 */
.main {
  flex: 1;
  padding: 1rem;
}
</style>