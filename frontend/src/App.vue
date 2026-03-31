<script setup>
import { ref, reactive } from 'vue'
import MonacoEditor from './components/MonacoEditor.vue'

// 状态管理
const code = ref('')
const leftSidebarCollapsed = ref(false)
const rightSidebarCollapsed = ref(false)
const bottomBarCollapsed = ref(false)

// 文件树数据
const fileTree = reactive([
  {
    name: 'src',
    isFolder: true,
    expanded: true,
    children: [
      { name: 'App.vue', isFolder: false },
      { name: 'main.js', isFolder: false },
      { name: 'style.css', isFolder: false },
      {
        name: 'components',
        isFolder: true,
        expanded: false,
        children: [
          { name: 'MonacoEditor.vue', isFolder: false }
        ]
      }
    ]
  },
  { name: 'index.html', isFolder: false },
  { name: 'package.json', isFolder: false },
  { name: 'vite.config.js', isFolder: false }
])

// 大纲数据
const outline = ref([
  { name: 'handleEditorMount', type: 'function', level: 0 },
  { name: 'setup', type: 'section', level: 0 },
  { name: 'template', type: 'section', level: 0 },
  { name: 'styles', type: 'section', level: 0 }
])

// 终端输出
const terminalOutput = ref([
  '$ npm run dev',
  '> vite',
  '',
  'Local:   http://localhost:5173/',
  'Network: http://192.168.1.100:5173/',
  '',
  'Press q to quit'
])
const terminalInput = ref('')

// 处理编辑器挂载完成的回调函数
const handleEditorMount = (editor) => {
  console.log('Editor mounted:', editor)
}

// 切换侧边栏展开/收起状态
const toggleLeftSidebar = () => {
  leftSidebarCollapsed.value = !leftSidebarCollapsed.value
}

const toggleRightSidebar = () => {
  rightSidebarCollapsed.value = !rightSidebarCollapsed.value
}

const toggleBottomBar = () => {
  bottomBarCollapsed.value = !bottomBarCollapsed.value
}

// 文件树节点点击处理
const onTreeNodeClick = (node) => {
  if (node.isFolder) {
    node.expanded = !node.expanded
  } else {
    // 在实际项目中，这里会加载文件内容到编辑器
    console.log('Opening file:', node.name)
  }
}

// 执行终端命令
const executeCommand = () => {
  if (terminalInput.value.trim()) {
    terminalOutput.value.push(`$ ${terminalInput.value}`)
    // 这里可以添加实际的命令执行逻辑
    terminalInput.value = ''
  }
}
</script>

<template>
  <div class="app-layout">
    <!-- 顶部工具栏 -->
    <header class="top-bar">
      <div class="toolbar">
        <button class="toolbar-btn">文件</button>
        <button class="toolbar-btn">编辑</button>
        <button class="toolbar-btn">查看</button>
        <button class="toolbar-btn">运行</button>
        <button class="toolbar-btn">终端</button>
      </div>
    </header>

    <!-- 主容器 -->
    <div class="main-container">
      <!-- 左侧边栏 -->
      <aside :class="['sidebar', 'left-sidebar', { collapsed: leftSidebarCollapsed }]">
        <div class="sidebar-header">
          <span>Explorer</span>
          <button @click="toggleLeftSidebar" class="collapse-btn">
            {{ leftSidebarCollapsed ? '»' : '«' }}
          </button>
        </div>
        
        <div v-if="!leftSidebarCollapsed" class="sidebar-content">
          <div class="panel-tabs">
            <button class="tab-btn active">📁 文件</button>
            <button class="tab-btn">📋 大纲</button>
          </div>
          
          <!-- 文件树 -->
          <div class="file-tree">
            <div 
              v-for="item in fileTree" 
              :key="item.name"
              class="tree-node"
            >
              <FileTreeNode 
                :node="item" 
                @node-click="onTreeNodeClick"
              />
            </div>
          </div>
          
          <!-- 大纲 -->
          <div v-show="false" class="outline-panel">
            <div 
              v-for="item in outline" 
              :key="item.name"
              class="outline-item"
              :style="{ paddingLeft: item.level * 20 + 'px' }"
            >
              <span class="outline-type">{{ item.type }}</span>
              <span>{{ item.name }}</span>
            </div>
          </div>
        </div>
      </aside>

      <!-- 中央编辑器区域 -->
      <main class="editor-area">
        <MonacoEditor
          v-model="code"
          language="python"
          @editor-mounted="handleEditorMount"
        />
      </main>

      <!-- 右侧边栏 -->
      <aside :class="['sidebar', 'right-sidebar', { collapsed: rightSidebarCollapsed }]">
        <div class="sidebar-header">
          <span>AI Assistant</span>
          <button @click="toggleRightSidebar" class="collapse-btn">
            {{ rightSidebarCollapsed ? '«' : '»' }}
          </button>
        </div>
        
        <div v-if="!rightSidebarCollapsed" class="sidebar-content ai-content">
          <div class="ai-panel">
            <h3>AI 助手</h3>
            <p>这里可以集成 AI 代码补全、错误检测等功能</p>
            
            <div class="ai-input-section">
              <textarea 
                placeholder="询问 AI 助手..." 
                rows="3"
                class="ai-textarea"
              ></textarea>
              <button class="ai-submit-btn">发送</button>
            </div>
            
            <div class="ai-response">
              <h4>AI 回复:</h4>
              <div class="response-content">
                这里将显示 AI 的回复内容...
              </div>
            </div>
          </div>
        </div>
      </aside>
    </div>

    <!-- 底部终端栏 -->
    <footer :class="['bottom-bar', { collapsed: bottomBarCollapsed }]">
      <div class="terminal-header">
        <span>终端</span>
        <button @click="toggleBottomBar" class="collapse-btn">
          {{ bottomBarCollapsed ? '▲' : '▼' }}
        </button>
      </div>
      
      <div v-if="!bottomBarCollapsed" class="terminal-content">
        <pre class="terminal-output">{{ terminalOutput.join('\n') }}</pre>
        <div class="terminal-input">
          <span>$</span>
          <input 
            v-model="terminalInput" 
            @keyup.enter="executeCommand"
            placeholder="输入命令..."
            class="terminal-command"
          />
        </div>
      </div>
    </footer>
  </div>
</template>

<style scoped>
.app-layout {
  height: 100vh;
  display: flex;
  flex-direction: column;
  background-color: #1e1e1e;
  color: #ccc;
  overflow: hidden;
}

.top-bar {
  background-color: #3c3c3c;
  padding: 0.5rem 1rem;
  border-bottom: 1px solid #333;
  z-index: 100;
}

.toolbar {
  display: flex;
  gap: 1rem;
}

.toolbar-btn {
  background: none;
  border: 1px solid transparent;
  color: #ccc;
  padding: 0.2rem 0.5rem;
  cursor: pointer;
  border-radius: 3px;
}

.toolbar-btn:hover {
  background-color: #2d2d2d;
}

.main-container {
  display: flex;
  flex: 1;
  overflow: hidden;
}

.sidebar {
  background-color: #252526;
  width: 250px;
  display: flex;
  flex-direction: column;
  transition: all 0.2s ease;
  border-right: 1px solid #333;
  overflow: hidden;
}

.left-sidebar {
  border-right: 1px solid #333;
}

.right-sidebar {
  border-left: 1px solid #333;
}

.sidebar.collapsed {
  width: 30px;
}

.sidebar-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.5rem;
  background-color: #2d2d2d;
  border-bottom: 1px solid #333;
  font-weight: bold;
}

.collapse-btn {
  background: none;
  border: 1px solid #555;
  color: #ccc;
  width: 20px;
  height: 20px;
  cursor: pointer;
  border-radius: 3px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.collapse-btn:hover {
  background-color: #3a3a3a;
}

.sidebar-content {
  padding: 0.5rem;
  overflow-y: auto;
  flex: 1;
}

.panel-tabs {
  display: flex;
  border-bottom: 1px solid #333;
  margin-bottom: 1rem;
}

.tab-btn {
  flex: 1;
  background: none;
  border: none;
  padding: 0.5rem;
  color: #aaa;
  cursor: pointer;
  border-bottom: 2px solid transparent;
}

.tab-btn.active {
  color: #fff;
  border-bottom: 2px solid #007acc;
}

.file-tree .tree-node {
  padding: 0.2rem 0.5rem;
  cursor: pointer;
  border-radius: 3px;
}

.file-tree .tree-node:hover {
  background-color: #2a2d2e;
}

.outline-item {
  padding: 0.2rem 0.5rem;
  font-size: 0.9rem;
}

.outline-type {
  font-size: 0.7rem;
  color: #888;
  margin-right: 0.5rem;
}

.ai-content {
  padding: 1rem;
}

.ai-panel h3 {
  margin-top: 0;
  margin-bottom: 1rem;
  color: #ddd;
}

.ai-textarea {
  width: 100%;
  padding: 0.5rem;
  background-color: #3c3c3c;
  border: 1px solid #454545;
  border-radius: 3px;
  color: #ddd;
  resize: vertical;
  margin-bottom: 0.5rem;
}

.ai-submit-btn {
  background-color: #007acc;
  color: white;
  border: none;
  padding: 0.3rem 0.8rem;
  border-radius: 3px;
  cursor: pointer;
}

.ai-submit-btn:hover {
  background-color: #006bb3;
}

.ai-response {
  margin-top: 1rem;
  padding-top: 1rem;
  border-top: 1px solid #333;
}

.response-content {
  background-color: #2d2d2d;
  padding: 0.8rem;
  border-radius: 3px;
  font-size: 0.9rem;
  line-height: 1.4;
}

.editor-area {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.bottom-bar {
  background-color: #252526;
  height: 200px;
  display: flex;
  flex-direction: column;
  transition: all 0.2s ease;
  border-top: 1px solid #333;
}

.bottom-bar.collapsed {
  height: 30px;
}

.terminal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.3rem 0.5rem;
  background-color: #2d2d2d;
  border-bottom: 1px solid #333;
  font-weight: bold;
}

.terminal-content {
  flex: 1;
  padding: 0.5rem;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
}

.terminal-output {
  flex: 1;
  background-color: #1e1e1e;
  color: #ccc;
  padding: 0.5rem;
  margin: 0;
  overflow-y: auto;
  font-family: monospace;
  white-space: pre-wrap;
  line-height: 1.4;
}

.terminal-input {
  display: flex;
  align-items: center;
  padding-top: 0.5rem;
  gap: 0.5rem;
}

.terminal-input span {
  color: #aaa;
  font-family: monospace;
}

.terminal-command {
  flex: 1;
  background-color: #3c3c3c;
  border: 1px solid #454545;
  color: #ddd;
  padding: 0.3rem 0.5rem;
  border-radius: 3px;
  font-family: monospace;
}
</style>