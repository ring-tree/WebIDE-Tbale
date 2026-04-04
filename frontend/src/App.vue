<script setup>
import { ref, reactive, nextTick } from "vue";
import MonacoEditor from "./components/MonacoEditor.vue";
import OutlineView from "./components/OutlineView.vue";
import AiChat from "./components/AiChat.vue";
import Terminal from "./components/Terminal.vue";
import "./App.css";

// 状态管理
const code = ref("");
const leftSidebarCollapsed = ref(false);
const rightSidebarCollapsed = ref(false);
const bottomBarCollapsed = ref(false);
const pythonVersion = ref("Python");
=======
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
>>>>>>> 7d3836b596450ba111deadc1ed2b75626bff120a

// 边栏大小
const leftSidebarWidth = ref(250);
const rightSidebarWidth = ref(250);
const bottomBarHeight = ref(200);

// 编辑器实例
let editorInstance = null;

// 拖动状态
const isDragging = ref(false);
const dragType = ref(''); // 'left', 'right', 'bottom'

// 缓存DOM元素，避免重复查询
const elements = {
  leftSidebar: null,
  rightSidebar: null,
  centralArea: null,
  terminalSection: null
};

// 初始化DOM元素缓存
const initElements = () => {
  elements.leftSidebar = document.querySelector('.sidebar.left-sidebar');
  elements.rightSidebar = document.querySelector('.sidebar.right-sidebar');
  elements.centralArea = document.querySelector('.central-area');
  elements.terminalSection = document.querySelector('.terminal-section');
  
  // 添加硬件加速
  if (elements.leftSidebar) {
    elements.leftSidebar.style.willChange = 'width';
    elements.leftSidebar.style.transform = 'translateZ(0)';
  }
  if (elements.rightSidebar) {
    elements.rightSidebar.style.willChange = 'width';
    elements.rightSidebar.style.transform = 'translateZ(0)';
  }
  if (elements.terminalSection) {
    elements.terminalSection.style.willChange = 'height';
    elements.terminalSection.style.transform = 'translateZ(0)';
  }
};

// 获取Python版本号
const fetchPythonVersion = async () => {
  try {
    const response = await fetch('/python/version');
    if (!response.ok) {
      throw new Error(`服务器错误: ${response.status}`);
    }
    const data = await response.json();
    if (data.status === 'success') {
      pythonVersion.value = data.version;
    }
  } catch (error) {
    console.error('获取Python版本失败:', error);
    pythonVersion.value = 'Python (未知)';
  }
};

// 组件挂载时获取Python版本
fetchPythonVersion();

// 使用nextTick确保DOM已渲染后初始化元素
nextTick(() => {
  initElements();
});

// 开始拖动
const startDrag = (type, event) => {
  // 阻止默认行为，防止文本选择
  event.preventDefault();
  event.stopPropagation();
  
  isDragging.value = true;
  dragType.value = type;
  
  // 根据拖动类型设置willChange
  switch (type) {
    case 'left':
      if (elements.leftSidebar) elements.leftSidebar.style.willChange = 'width';
      break;
    case 'right':
      if (elements.rightSidebar) elements.rightSidebar.style.willChange = 'width';
      break;
    case 'bottom':
      if (elements.terminalSection) elements.terminalSection.style.willChange = 'height';
      break;
  }
  
  document.addEventListener('mousemove', onDrag);
  document.addEventListener('mouseup', stopDrag);
  
  // 添加全局样式防止文本选择
  document.body.style.userSelect = 'none';
  document.body.style.cursor = 'col-resize';
};

// 优化的拖动处理
const onDrag = (event) => {
  if (!isDragging.value) return;
  
  // 阻止默认行为，防止文本选择
  event.preventDefault();
  event.stopPropagation();
  
  // 直接更新DOM，不使用requestAnimationFrame，减少延迟
  switch (dragType.value) {
    case 'left':
      if (!leftSidebarCollapsed.value && elements.leftSidebar) {
        // 直接计算并设置宽度，确保在合理范围内
        const width = Math.max(100, Math.min(event.clientX, window.innerWidth * 0.4));
        elements.leftSidebar.style.width = width + 'px';
        // 异步更新Vue状态，不阻塞拖动
        setTimeout(() => {
          leftSidebarWidth.value = width;
        }, 0);
      }
      break;
    case 'right':
      if (!rightSidebarCollapsed.value && elements.rightSidebar) {
        // 直接计算并设置宽度，确保在合理范围内
        const width = Math.max(100, Math.min(window.innerWidth - event.clientX, window.innerWidth * 0.4));
        elements.rightSidebar.style.width = width + 'px';
        // 异步更新Vue状态，不阻塞拖动
        setTimeout(() => {
          rightSidebarWidth.value = width;
        }, 0);
      }
      break;
    case 'bottom':
      if (!bottomBarCollapsed.value && elements.centralArea && elements.terminalSection) {
        const rect = elements.centralArea.getBoundingClientRect();
        // 计算高度
        const height = Math.max(100, Math.min(rect.bottom - event.clientY, rect.height - 50));
        elements.terminalSection.style.height = height + 'px';
        // 异步更新Vue状态，不阻塞拖动
        setTimeout(() => {
          bottomBarHeight.value = height;
        }, 0);
      }
      break;
  }
};

// 停止拖动
const stopDrag = () => {
  isDragging.value = false;
  dragType.value = '';
  document.removeEventListener('mousemove', onDrag);
  document.removeEventListener('mouseup', stopDrag);
  
  // 恢复正常样式
  document.body.style.userSelect = '';
  document.body.style.cursor = '';
  
  // 清除willChange属性，释放资源
  if (elements.leftSidebar) elements.leftSidebar.style.willChange = '';
  if (elements.rightSidebar) elements.rightSidebar.style.willChange = '';
  if (elements.terminalSection) elements.terminalSection.style.willChange = '';
};

// 终端初始输出
const terminalOutput = ref([
  "WebIDE Terminal v1.0.0",
  '输入 "help" 查看可用命令',
  "=> 环境已就绪",
  ""
]);

// 事件处理
const handleEditorMount = (editor) => {
<<<<<<< HEAD
	console.log("Editor mounted:", editor);
	editorInstance = editor;
};

const toggleLeftSidebar = () => {
	leftSidebarCollapsed.value = !leftSidebarCollapsed.value;
	
	// 确保侧边栏宽度正确
	if (elements.leftSidebar) {
		if (leftSidebarCollapsed.value) {
			elements.leftSidebar.style.width = '30px';
		} else {
			elements.leftSidebar.style.width = leftSidebarWidth.value + 'px';
		}
	}
};

const toggleRightSidebar = () => {
	rightSidebarCollapsed.value = !rightSidebarCollapsed.value;
	
	// 确保侧边栏宽度正确
	if (elements.rightSidebar) {
		if (rightSidebarCollapsed.value) {
			elements.rightSidebar.style.width = '30px';
		} else {
			elements.rightSidebar.style.width = rightSidebarWidth.value + 'px';
		}
	}
};

const toggleBottomBar = () => {
	bottomBarCollapsed.value = !bottomBarCollapsed.value;
};

const onJumpToLine = (item) => {
	console.log("跳转到行:", item.line, "名称:", item.name);
};

const onSendMessage = (message) => {
	console.log("User sent:", message);
};

const onExecuteCommand = (cmd) => {
	console.log("Command executed:", cmd);
};


//运行代码逻辑
const runCode = async () => {
	console.log('按钮被点击了！');

  if (!code.value.trim()) {
    // 如果没有代码，推送到终端显示提示
    terminalOutput.value.push(">>> 错误: 请先在编辑器中输入代码。");
    return;
  }

  try {
    // 1. 发送请求到后端
    // 注意：确保后端 (app.py) 正在运行在 5000 端口
    const response = await fetch('/run', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ code: code.value }) // 将编辑器中的 code 发送给后端
    });

    if (!response.ok) {
      throw new Error(`服务器错误: ${response.status} ${response.statusText}`);
    }

    const data = await response.json();

    // 2. 处理结果
    // 在输出前加个分隔符，方便区分历史记录
    terminalOutput.value.push(">>> 运行开始 -------------------");
    
    // 将后端返回的输出（stdout + stderr）推送到终端数组
    // split('\n') 是为了处理多行输出，每行作为一个数组元素
    const outputLines = data.output.split('\n');
    outputLines.forEach(line => {
      if (line) { // 只添加非空行
        terminalOutput.value.push(line);
      }
    });

    terminalOutput.value.push(">>> 运行结束 -------------------\n");

  } catch (error) {
    console.error('运行失败:', error);
    terminalOutput.value.push(">>> 运行错误 -------------------");
    terminalOutput.value.push(`错误类型: ${error.name}`);
    terminalOutput.value.push(`错误信息: ${error.message}`);
    terminalOutput.value.push("请检查后端服务器是否运行，或代码中是否有语法错误");
    terminalOutput.value.push(">>> 运行错误结束 -------------------\n");
  }

  // 可选：滚动到底部
  // 如果 Terminal 组件有滚动到底部的逻辑，这里可以触发
};
</script>

<template>
	<div class="app-layout">
		<!-- 顶部工具栏 -->
		<header class="top-bar">
			<div class="toolbar">
				<button class="toolbar-btn" @click="toggleLeftSidebar">大纲</button>
				<button class="toolbar-btn">编辑</button>
				<button class="toolbar-btn" @click="toggleRightSidebar">AIchat</button>
				<button class="toolbar-btn" @click="runCode" type="button">运行</button>
				<button class="toolbar-btn" @click="toggleBottomBar">终端</button>
				<div class="version-info">{{ pythonVersion }}</div>
			</div>
		</header>

		<!-- 主容器 -->
		<div class="main-container">
			<!-- 左侧边栏 - 大纲 -->
			<aside 
				:class="['sidebar', 'left-sidebar', { collapsed: leftSidebarCollapsed }]"
				style="width: 250px"
			>
				<div class="sidebar-header">
					<!-- 1. 折叠按钮 (保持在上) -->
					<button @click="toggleLeftSidebar" class="collapse-btn">
						{{ leftSidebarCollapsed ? "»" : "«" }}
					</button>

					<!-- 2. 标题 (移出 wrapper，直接作为 flex item) -->
					<!-- <span class="sidebar-title">大纲</span> -->
				</div>

				<div v-show="!leftSidebarCollapsed" class="sidebar-content outline-sidebar">
					<OutlineView :editor="editorInstance" language="python" @jump-to-line="onJumpToLine" />
				</div>
				<!-- 左侧边栏拖动手柄 -->
				<div 
					v-show="!leftSidebarCollapsed"
					class="resize-handle resize-handle-right"
					@mousedown="startDrag('left', $event)"
				></div>
			</aside>

			<!-- 中央区域 -->
			<main class="central-area">
				<!-- 编辑器区域 -->
				<div class="editor-section">
					<MonacoEditor v-model="code" language="python" @editor-mounted="handleEditorMount" />
				</div>

				<!-- 终端区域 -->
				<div 
					class="terminal-section" 
					v-show="!bottomBarCollapsed"
					:style="{ height: bottomBarHeight + 'px' }"
				>
					<!-- 终端拖动手柄 -->
					<div 
						class="resize-handle resize-handle-top"
						@mousedown="startDrag('bottom', $event)"
					></div>
					<Terminal :initial-output="terminalOutput" @execute-command="onExecuteCommand" />
				</div>
			</main>

			<!-- 右侧边栏 -->
			<aside 
				:class="['sidebar', 'right-sidebar', { collapsed: rightSidebarCollapsed }]"
				style="width: 250px"
			>
				<div class="sidebar-header">
					<div class="sidebar-title-wrapper">
						<span class="sidebar-title">AI Assistant</span>
						<button @click="toggleRightSidebar" class="collapse-btn">
							{{ rightSidebarCollapsed ? "«" : "»" }}
						</button>
					</div>
				</div>

				<!-- 右侧边栏拖动手柄 -->
				<div 
					v-show="!rightSidebarCollapsed"
					class="resize-handle resize-handle-left"
					@mousedown="startDrag('right', $event)"
				></div>

				<div v-if="!rightSidebarCollapsed" class="sidebar-content ai-sidebar">
					<AiChat @send-message="onSendMessage" />
				</div>
			</aside>
		</div>
	</div>
</template>
=======
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
>>>>>>> 7d3836b596450ba111deadc1ed2b75626bff120a
