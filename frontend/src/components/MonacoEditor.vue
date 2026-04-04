<template>
  <!-- Monaco 编辑器容器 -->
  <div ref="editorContainer" class="editor-container"></div>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount, shallowRef } from 'vue'
import * as monaco from 'monaco-editor'

// 定义组件属性
const props = defineProps({
  // 编辑器当前值
  modelValue: String,
  // 编辑器语言类型，默认为python
  language: {
    type: String,
    default: 'python'
  }
})

// 定义组件事件
const emit = defineEmits(['update:modelValue', 'editor-mounted'])

// 编辑器容器引用
const editorContainer = ref(null)
// 编辑器实例引用
const editor = shallowRef(null)
// 自动补全提供者
let completionProvider = null
// 存储上次获取的补全项
let lastCompletions = []
// 标记是否已请求过补全项
let hasRequestedCompletions = false
// 防抖计时器
let debounceTimer = null
// 本地缓存，存储代码补全结果
const completionCache = new Map()
// 缓存键生成函数
const generateCacheKey = (code, line, column) => {
  return `${code.substring(0, 100)}...${line}:${column}`
}

/**
 * 防抖函数
 * @param {Function} func - 要执行的函数
 * @param {number} delay - 延迟时间（毫秒）
 * @returns {Function} 防抖处理后的函数
 */
const debounce = (func, delay) => {
  return function(...args) {
    clearTimeout(debounceTimer)
    debounceTimer = setTimeout(() => func.apply(this, args), delay)
  }
}

/**
 * 向后端发送代码并获取补全建议
 * @param {string} code - 当前编辑器中的完整代码
 * @param {object} position - 光标位置信息
 */
const sendToBackend = debounce(async (code, position) => {
  const { lineNumber, column } = position
  
  // 生成缓存键
  const cacheKey = generateCacheKey(code, lineNumber, column)
  
  // 检查缓存中是否已有结果
  if (completionCache.has(cacheKey)) {
    lastCompletions = completionCache.get(cacheKey)
    hasRequestedCompletions = true
    // 触发编辑器显示建议
    editor.value.trigger('keyboard', 'editor.action.triggerSuggest', {})
    return
  }
  
  try {
    // 发送代码到后端接口获取补全建议
    const response = await fetch('/update', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ code, line: lineNumber, column: column })
    })
    
    if (!response.ok) {
      throw new Error(`服务器错误: ${response.status} ${response.statusText}`);
    }
    
    const data = await response.json()
    
    // 如果返回了补全项，则更新本地缓存并触发编辑器建议
    if (data.completions?.length) {
      lastCompletions = data.completions
      // 存储到缓存
      completionCache.set(cacheKey, data.completions)
      // 限制缓存大小，最多存储100个结果
      if (completionCache.size > 100) {
        const firstKey = completionCache.keys().next().value
        completionCache.delete(firstKey)
      }
      hasRequestedCompletions = true
      // 触发编辑器显示建议
      editor.value.trigger('keyboard', 'editor.action.triggerSuggest', {})
    } else {
      lastCompletions = []
      // 缓存空结果，避免重复请求
      completionCache.set(cacheKey, [])
    }
  } catch (error) {
    console.error('Failed to send code to backend:', error)
    // 可以在这里添加用户友好的错误提示
    // 例如：显示一个浮动提示或在状态栏显示错误信息
  }
}, 300)

// 组件挂载时初始化编辑器
onMounted(() => {
  if (!editorContainer.value) return

  // 创建 Monaco 编辑器实例
  editor.value = monaco.editor.create(editorContainer.value, {
    value: props.modelValue,
    language: props.language,
    automaticLayout: true,
    theme: 'vs-dark',
    // 配置建议设置
    suggest: { 
      showWords: false, 
      showSnippets: false, 
      autoSuggestions: false, 
      suppressSuggestions: true 
    },
    quickSuggestions: false,
    suggestOnTriggerCharacters: false,
    acceptSuggestionOnEnter: 'on',
    tabCompletion: 'off',
    tabSize: 4,
    insertSpaces: true,
    renderWhitespace: 'none',
    useTabStops: false
  })

  // 注册 Tab 键命令处理函数
  editor.value.addCommand(monaco.KeyCode.Tab, () => {
    const position = editor.value.getPosition()
    const model = editor.value.getModel()
    const lineContent = model.getLineContent(position.lineNumber)
    const column = position.column
    
    // 检查光标前的内容
    const textBeforeCursor = lineContent.substring(0, column - 1)
    
    // 仅在光标前无任何字符或全部为空格时，用Tab键为缩进
    if (textBeforeCursor === '' || /^\s*$/.test(textBeforeCursor)) {
      // 插入四个空格（用于缩进）
      editor.value.trigger('keyboard', 'type', { text: '    ' })
    } else {
      // 其他情况皆为强制显示补全
      // 清除之前的补全结果，强制重新获取
      lastCompletions = []
      sendToBackend(editor.value.getValue(), position)
    }
  }, 'editorTextFocus')

  // 监听内容变化事件，重置补全状态并通知父组件
  editor.value.onDidChangeModelContent((event) => {
    // 重置补全状态，这样在用户输入时会隐藏补全框
    hasRequestedCompletions = false
    lastCompletions = []
    
    // 隐藏补全框
    editor.value.trigger('keyboard', 'hideSuggestWidget', {})
    
    // 获取当前编辑器内容并通知父组件
    const currentValue = editor.value.getValue()
    emit('update:modelValue', currentValue)
  })

  // 注册自定义补全项提供者
  completionProvider = monaco.languages.registerCompletionItemProvider(props.language, {
    provideCompletionItems: (model, position) => {
      // 如果没有补全项或补全项为空数组，则返回null（不显示补全框）
      if (!lastCompletions || lastCompletions.length === 0) {
        return null
      }
      
      // 过滤掉错误信息和无效项
      const validCompletions = lastCompletions.filter(item => 
        item && item.name && 
        item.name !== 'Error' && 
        item.name !== 'error' &&
        item.name.trim() !== ''
      )
      
      // 如果没有有效的补全项，返回null
      if (validCompletions.length === 0) {
        return null
      }
      
      // 将后端返回的补全项转换为Monaco编辑器所需的格式
      const suggestions = validCompletions.map(item => ({
        label: item.name,                          // 补全项名称
        kind: monaco.languages.CompletionItemKind.Function, // 补全项类型
        insertText: item.name,                     // 插入的文本
        documentation: item.description,           // 补全项描述
        detail: 'Python'                           // 详细信息
      }))

      return {
        suggestions: suggestions
      }
    }
  })

  // 触发编辑器已挂载事件
  emit('editor-mounted', editor.value)
})

// 组件卸载前清理资源
onBeforeUnmount(() => {
  if (completionProvider) {
    completionProvider.dispose()
  }
  editor.value?.dispose()
})

// 暴露编辑器实例给父组件
defineExpose({
  getEditor: () => editor.value
})
</script>

<style scoped>
/* 编辑器容器样式 */
.editor-container {
  width: 100%;
  height: 100%;
}
</style>