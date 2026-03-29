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

/**
 * 向后端发送代码并获取补全建议
 * @param {string} code - 当前编辑器中的完整代码
 * @param {object} position - 光标位置信息
 */
const sendToBackend = async (code, position) => {
  try {
    // 发送代码到后端接口获取补全建议
    const response = await fetch('http://localhost:5000/update', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ code, line: position.lineNumber, column: position.column })
    })
    const data = await response.json()
    
    // 如果返回了补全项，则更新本地缓存并触发编辑器建议
    if (data.completions?.length) {
      lastCompletions = data.completions
      hasRequestedCompletions = true
      // 触发编辑器显示建议
      editor.value.trigger('keyboard', 'editor.action.triggerSuggest', {})
    } else {
      lastCompletions = []
    }
  } catch (error) {
    console.error('Failed to send code to backend:', error)
  }
}

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
    
    // 如果当前光标前不是空格或制表符，则尝试获取补全建议
    if (column > 1 && lineContent[column - 2] !== ' ' && lineContent[column - 2] !== '\t') {
      if (!hasRequestedCompletions) {
        sendToBackend(editor.value.getValue(), editor.value.getPosition())
      }
    } else {
      // 否则插入四个空格
      editor.value.trigger('keyboard', 'type', { text: '    ' })
    }
  }, 'editorTextFocus')

  // 监听内容变化事件，重置补全状态
  editor.value.onDidChangeModelContent(() => {
    hasRequestedCompletions = false
  })

  // 注册自定义补全项提供者
  completionProvider = monaco.languages.registerCompletionItemProvider(props.language, {
    provideCompletionItems: (model, position) => {
      // 如果没有补全项则返回null
      if (lastCompletions.length === 0) {
        return null
      }
      // 将后端返回的补全项转换为Monaco编辑器所需的格式
      const suggestions = lastCompletions.map(item => ({
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