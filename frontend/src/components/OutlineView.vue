<script setup>
import { ref, watch } from 'vue'

const props = defineProps({
  editor: {
    type: Object,
    default: null
  },
  language: {
    type: String,
    default: 'python'
  }
})

const emit = defineEmits(['jump-to-line'])

const outlineItems = ref([])
const isLoading = ref(false)

// 解析 Python 代码结构
const parsePythonCode = (code) => {
  const items = []
  const lines = code.split('\n')
  
  lines.forEach((line, index) => {
    const trimmed = line.trim()
    
    // 函数定义
    const funcMatch = trimmed.match(/^def\s+(\w+)\s*\(/)
    if (funcMatch) {
      items.push({
        name: funcMatch[1],
        type: 'function',
        line: index + 1,
        level: 0,
        icon: 'ƒ'
      })
      return
    }
    
    // 类定义
    const classMatch = trimmed.match(/^class\s+(\w+)/)
    if (classMatch) {
      items.push({
        name: classMatch[1],
        type: 'class',
        line: index + 1,
        level: 0,
        icon: 'Ⓒ'
      })
      return
    }
    
    // 方法定义（缩进）
    const methodMatch = trimmed.match(/^\s+def\s+(\w+)\s*\(/)
    if (methodMatch) {
      items.push({
        name: methodMatch[1],
        type: 'method',
        line: index + 1,
        level: 1,
        icon: 'ⓜ'
      })
      return
    }
    
    // 导入语句
    const importMatch = trimmed.match(/^import\s+(\w+)/)
    if (importMatch) {
      items.push({
        name: importMatch[1],
        type: 'import',
        line: index + 1,
        level: 0,
        icon: '📦'
      })
      return
    }
    
    // from import
    const fromImportMatch = trimmed.match(/^from\s+(\w+)/)
    if (fromImportMatch) {
      items.push({
        name: fromImportMatch[1],
        type: 'import',
        line: index + 1,
        level: 0,
        icon: '📦'
      })
      return
    }
    
    // 变量定义
    const varMatch = trimmed.match(/^(\w+)\s*=/)
    if (varMatch && !trimmed.startsWith(' ') && !['def', 'class', 'import', 'from'].includes(varMatch[1])) {
      items.push({
        name: varMatch[1],
        type: 'variable',
        line: index + 1,
        level: 0,
        icon: 'Ⓥ'
      })
      return
    }
    
    // 注释区块（作为 section）
    const commentMatch = trimmed.match(/^#\s*={2,}\s*(.+)\s*={2,}/)
    if (commentMatch) {
      items.push({
        name: commentMatch[1],
        type: 'section',
        line: index + 1,
        level: 0,
        icon: '📋'
      })
      return
    }
  })
  
  return items
}

// 解析 JavaScript/Vue 代码结构
const parseJavaScriptCode = (code) => {
  const items = []
  const lines = code.split('\n')
  
  lines.forEach((line, index) => {
    const trimmed = line.trim()
    
    // 函数声明
    const funcMatch = trimmed.match(/^(?:async\s+)?function\s+(\w+)/)
    if (funcMatch) {
      items.push({
        name: funcMatch[1],
        type: 'function',
        line: index + 1,
        level: 0,
        icon: 'ƒ'
      })
      return
    }
    
    // 箭头函数赋值
    const arrowFuncMatch = trimmed.match(/^(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s+)?\(/)
    if (arrowFuncMatch) {
      items.push({
        name: arrowFuncMatch[1],
        type: 'function',
        line: index + 1,
        level: 0,
        icon: 'ƒ'
      })
      return
    }
    
    // 类定义
    const classMatch = trimmed.match(/^class\s+(\w+)/)
    if (classMatch) {
      items.push({
        name: classMatch[1],
        type: 'class',
        line: index + 1,
        level: 0,
        icon: 'Ⓒ'
      })
      return
    }
    
    // 导入语句
    const importMatch = trimmed.match(/^import\s+.*\s+from\s+['"](.+)['"]/)
    if (importMatch) {
      items.push({
        name: importMatch[1],
        type: 'import',
        line: index + 1,
        level: 0,
        icon: '📦'
      })
      return
    }
    
    // export
    const exportMatch = trimmed.match(/^export\s+(?:default\s+)?(?:function|class|const)\s+(\w+)/)
    if (exportMatch) {
      items.push({
        name: exportMatch[1],
        type: 'export',
        line: index + 1,
        level: 0,
        icon: '📤'
      })
      return
    }
  })
  
  return items
}

// 根据语言解析代码
const parseCode = (code) => {
  if (!code) return []
  
  switch (props.language) {
    case 'python':
      return parsePythonCode(code)
    case 'javascript':
    case 'typescript':
    case 'vue':
      return parseJavaScriptCode(code)
    default:
      return parsePythonCode(code)
  }
}

// 更新大纲
const updateOutline = () => {
  if (!props.editor) {
    outlineItems.value = []
    return
  }
  
  isLoading.value = true
  
  try {
    const code = props.editor.getValue()
    outlineItems.value = parseCode(code)
  } catch (error) {
    console.error('解析大纲失败:', error)
    outlineItems.value = []
  } finally {
    isLoading.value = false
  }
}

// 跳转到指定行
const jumpToLine = (item) => {
  if (!props.editor) return
  
  props.editor.revealLineInCenter(item.line)
  props.editor.setPosition({ lineNumber: item.line, column: 1 })
  props.editor.focus()
  
  emit('jump-to-line', item)
}

// 监听编辑器变化
watch(() => props.editor, (newEditor) => {
  if (newEditor) {
    // 初始解析
    updateOutline()
    
    // 监听内容变化
    const disposable = newEditor.onDidChangeModelContent(() => {
      updateOutline()
    })
    
    // 组件卸载时清理
    return () => {
      disposable?.dispose()
    }
  }
}, { immediate: true })

// 获取类型图标样式
const getTypeStyle = (type) => {
  const styles = {
    function: { color: '#dcdcaa', bg: 'rgba(220, 220, 170, 0.1)' },
    method: { color: '#dcdcaa', bg: 'rgba(220, 220, 170, 0.1)' },
    class: { color: '#4ec9b0', bg: 'rgba(78, 201, 176, 0.1)' },
    variable: { color: '#9cdcfe', bg: 'rgba(156, 220, 254, 0.1)' },
    import: { color: '#ce9178', bg: 'rgba(206, 145, 120, 0.1)' },
    export: { color: '#569cd6', bg: 'rgba(86, 156, 214, 0.1)' },
    section: { color: '#6a9955', bg: 'rgba(106, 153, 85, 0.1)' }
  }
  return styles[type] || { color: '#ccc', bg: 'rgba(204, 204, 204, 0.1)' }
}
</script>

<template>
  <div class="outline-view">
    <div class="outline-header">
      <span class="outline-title">📋 大纲</span>
      <span v-if="isLoading" class="loading-indicator">加载中...</span>
    </div>
    
    <div class="outline-content">
      <div v-if="outlineItems.length === 0" class="empty-state">
        <p>暂无大纲内容</p>
        <p class="hint">在编辑器中编写代码将自动显示结构</p>
      </div>
      
      <div
        v-for="item in outlineItems"
        :key="item.line"
        class="outline-item"
        :style="{ paddingLeft: item.level * 16 + 'px' }"
        @click="jumpToLine(item)"
      >
        <span class="item-icon">{{ item.icon }}</span>
        <span class="item-name">{{ item.name }}</span>
        <span class="item-line">{{ item.line }}</span>
      </div>
    </div>
  </div>
</template>

<style scoped>
.outline-view {
  display: flex;
  flex-direction: column;
  height: 100%;
}

.outline-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 12px;
  border-bottom: 1px solid #333;
}

.outline-title {
  font-size: 12px;
  font-weight: 600;
  color: #ccc;
}

.loading-indicator {
  font-size: 11px;
  color: #007acc;
}

.outline-content {
  flex: 1;
  overflow-y: auto;
  padding: 4px 0;
}

.empty-state {
  padding: 20px 12px;
  text-align: center;
  color: #666;
}

.empty-state p {
  margin: 4px 0;
  font-size: 12px;
}

.empty-state .hint {
  font-size: 11px;
  color: #555;
}

.outline-item {
  display: flex;
  align-items: center;
  padding: 4px 12px;
  cursor: pointer;
  transition: background-color 0.15s;
  font-size: 12px;
}

.outline-item:hover {
  background-color: #2a2d2e;
}

.item-icon {
  width: 16px;
  margin-right: 6px;
  font-size: 11px;
  text-align: center;
}

.item-name {
  flex: 1;
  color: #ccc;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.item-line {
  font-size: 10px;
  color: #666;
  margin-left: 8px;
}
</style>