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

// 边栏大小
const leftSidebarWidth = ref(250);
const rightSidebarWidth = ref(250);
const bottomBarHeight = ref(200);

// 编辑器实例
let editorInstance = null;

// 拖动状态
const isDragging = ref(false);
const dragType = ref(''); // 'left', 'right', 'bottom'

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

// 开始拖动
const startDrag = (type, event) => {
  isDragging.value = true;
  dragType.value = type;
  document.addEventListener('mousemove', onDrag);
  document.addEventListener('mouseup', stopDrag);
};

// 拖动中
const onDrag = (event) => {
  if (!isDragging.value) return;
  
  switch (dragType.value) {
    case 'left':
      if (!leftSidebarCollapsed.value) {
        leftSidebarWidth.value = Math.max(100, event.clientX);
      }
      break;
    case 'right':
      if (!rightSidebarCollapsed.value) {
        rightSidebarWidth.value = Math.max(100, window.innerWidth - event.clientX);
      }
      break;
    case 'bottom':
      if (!bottomBarCollapsed.value) {
        bottomBarHeight.value = Math.max(100, window.innerHeight - event.clientY);
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
	console.log("Editor mounted:", editor);
	editorInstance = editor;
};

const toggleLeftSidebar = () => {
	leftSidebarCollapsed.value = !leftSidebarCollapsed.value;
};

const toggleRightSidebar = () => {
	rightSidebarCollapsed.value = !rightSidebarCollapsed.value;
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
				:style="{ width: leftSidebarCollapsed ? '30px' : leftSidebarWidth + 'px' }"
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
				:style="{ width: rightSidebarCollapsed ? '30px' : rightSidebarWidth + 'px' }"
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
