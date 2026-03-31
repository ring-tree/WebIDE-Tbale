<script setup>
import { ref, nextTick, watch } from 'vue'

const props = defineProps({
  visible: {
    type: Boolean,
    default: true
  },
  initialOutput: {
    type: Array,
    default: () => []
  }
})

const emit = defineEmits(['execute-command'])

const output = ref([...props.initialOutput])

// 监听initialOutput的变化
watch(() => props.initialOutput, (newValue) => {
  output.value = [...newValue]
  scrollToBottom()
}, { deep: true })
const command = ref('')
const commandHistory = ref([])
const historyIndex = ref(-1)
const outputContainer = ref(null)

// 自动滚动到底部
const scrollToBottom = async () => {
  await nextTick()
  if (outputContainer.value) {
    outputContainer.value.scrollTop = outputContainer.value.scrollHeight
  }
}

// 执行命令
const executeCommand = async () => {
  if (!command.value.trim()) return
  
  const cmd = command.value.trim()
  
  // 添加到历史记录
  commandHistory.value.push(cmd)
  historyIndex.value = commandHistory.value.length
  
  // 显示命令
  output.value.push(`$ ${cmd}`)
  
  try {
    // 调用后端执行命令
    const response = await fetch('/terminal/execute', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ command: cmd })
    })
    
    if (!response.ok) {
      throw new Error(`服务器错误: ${response.status}`)
    }
    
    const data = await response.json()
    
    // 显示执行结果
    if (data.output) {
      const outputLines = data.output.split('\n')
      outputLines.forEach(line => {
        if (line) {
          output.value.push(line)
        }
      })
    }
  } catch (error) {
    console.error('命令执行失败:', error)
    output.value.push(`Error: ${error.message}`)
  }
  
  command.value = ''
  await scrollToBottom()
  
  emit('execute-command', cmd)
}

// 模拟命令执行（后期替换为真实接口）
const simulateCommand = (cmd) => {
  const commands = {
    'help': '可用命令：help, clear, echo [text], date, pwd',
    'clear': () => { output.value = []; return ''; },
    'date': new Date().toString(),
    'pwd': '/home/user/project',
    'ls': 'src  components  App.vue  main.js  package.json',
  }
  
  const cmdName = cmd.split(' ')[0].toLowerCase()
  if (commands[cmdName]) {
    const result = commands[cmdName]
    return typeof result === 'function' ? result() : result
  }
  
  if (cmdName === 'echo') {
    return cmd.substring(5) || ''
  }
  
  return `命令未找到：${cmd}\n输入 'help' 查看可用命令`
}

// 处理键盘事件
const handleKeydown = (e) => {
  if (e.key === 'Enter') {
    e.preventDefault()
    executeCommand()
  } else if (e.key === 'ArrowUp') {
    e.preventDefault()
    if (historyIndex.value > 0) {
      historyIndex.value--
      command.value = commandHistory.value[historyIndex.value]
    }
  } else if (e.key === 'ArrowDown') {
    e.preventDefault()
    if (historyIndex.value < commandHistory.value.length - 1) {
      historyIndex.value++
      command.value = commandHistory.value[historyIndex.value]
    } else {
      historyIndex.value = commandHistory.value.length
      command.value = ''
    }
  }
}

// 清空终端
const clearTerminal = () => {
  output.value = []
}
</script>

<template>
  <div class="terminal-container" v-if="visible">
    <!-- 终端头部 -->
    <div class="terminal-header">
      <span class="terminal-title">🖥️ 终端</span>
      <div class="terminal-actions">
        <button class="action-btn" @click="clearTerminal" title="清空">🗑️</button>
      </div>
    </div>
    
    <!-- 输出区域 -->
    <div class="terminal-output" ref="outputContainer">
      <div 
        v-for="(line, index) in output" 
        :key="index"
        class="output-line"
      >
        {{ line }}
      </div>
    </div>
    
    <!-- 输入区域 -->
    <div class="terminal-input-line">
      <span class="prompt">$</span>
      <input
        v-model="command"
        @keydown="handleKeydown"
        placeholder="输入命令..."
        class="terminal-input"
        autocomplete="off"
        spellcheck="false"
      />
    </div>
  </div>
</template>

<style scoped>
.terminal-container {
  display: flex;
  flex-direction: column;
  height: 100%;
  background-color: #1e1e1e;
  font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
}

.terminal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 6px 10px;
  background-color: #2d2d2d;
  border-bottom: 1px solid #333;
}

.terminal-title {
  font-size: 12px;
  color: #ccc;
}

.terminal-actions {
  display: flex;
  gap: 8px;
}

.action-btn {
  background: none;
  border: none;
  color: #888;
  cursor: pointer;
  font-size: 14px;
  padding: 2px 6px;
  border-radius: 3px;
  transition: all 0.2s;
}

.action-btn:hover {
  background-color: #3c3c3c;
  color: #ccc;
}

.terminal-output {
  flex: 1;
  overflow-y: auto;
  padding: 8px;
  font-size: 12px;
  line-height: 1.5;
  color: #ccc;
}

.output-line {
  white-space: pre-wrap;
  word-break: break-word;
}

.terminal-input-line {
  display: flex;
  align-items: center;
  padding: 6px 8px;
  border-top: 1px solid #333;
  background-color: #1e1e1e;
}

.prompt {
  color: #00ff00;
  margin-right: 8px;
  font-weight: bold;
}

.terminal-input {
  flex: 1;
  background: transparent;
  border: none;
  color: #ccc;
  font-family: inherit;
  font-size: 12px;
  outline: none;
}

.terminal-input::placeholder {
  color: #555;
}
</style>