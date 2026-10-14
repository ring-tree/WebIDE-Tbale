<template>
  <div ref="editorContainer" class="editor-container"></div>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount, shallowRef, watch } from 'vue'
import * as monaco from 'monaco-editor'

const props = defineProps({
  modelValue: String,
  language: {
    type: String,
    default: 'python'
  }
})

const emit = defineEmits(['update:modelValue', 'editor-mounted'])

const editorContainer = ref(null)
const editor = shallowRef(null)
let completionProvider = null
let lastCompletions = []
let requestId = 0
const completionCache = new Map()

const getCacheKey = (code, line, column) => {
  const codeHash = code.split('').reduce((a, b) => ((a << 5) - a + b.charCodeAt(0)) | 0, 0)
  return `${codeHash}:${line}:${column}`
}

const debounce = (fn, delay) => {
  let timer = null
  return (...args) => {
    clearTimeout(timer)
    timer = setTimeout(() => fn(...args), delay)
  }
}

const showWidget = () => {
  if (editor.value) {
    editor.value.trigger('keyboard', 'editor.action.triggerSuggest', {})
  }
}

const fetchCompletions = debounce(async (code, position) => {
  const { lineNumber, column } = position
  const cacheKey = getCacheKey(code, lineNumber, column)
  const currentRequestId = ++requestId

  if (completionCache.has(cacheKey)) {
    const cached = completionCache.get(cacheKey)
    if (currentRequestId === requestId) {
      lastCompletions = cached
      if (cached.length > 0) {
        showWidget()
      }
    }
    return
  }

  try {
    const response = await fetch('/update', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ code, line: lineNumber, column: column })
    })

    if (!response.ok || currentRequestId !== requestId) return

    const data = await response.json()
    const completions = data.completions || []

    if (currentRequestId !== requestId) return

    completionCache.set(cacheKey, completions)
    if (completionCache.size > 50) {
      const firstKey = completionCache.keys().next().value
      completionCache.delete(firstKey)
    }

    lastCompletions = completions
    if (completions.length > 0) {
      showWidget()
    }
  } catch (error) {
    if (currentRequestId === requestId) {
      lastCompletions = []
    }
  }
}, 150)

onMounted(() => {
  if (!editorContainer.value) return

  editor.value = monaco.editor.create(editorContainer.value, {
    value: props.modelValue,
    language: props.language,
    automaticLayout: true,
    theme: 'vs-dark',
    suggest: {
      showWords: false,
      showSnippets: false,
      showIcons: true,
      insertMode: 'replace',
      preview: true
    },
    quickSuggestions: {
      other: true,
      comments: false,
      strings: false
    },
    acceptSuggestionOnEnter: 'on',
    tabCompletion: 'off',
    tabSize: 4,
    insertSpaces: true,
    renderWhitespace: 'none',
    useTabStops: false,
    parameterHints: { enabled: false },
    hover: { enabled: false },
    wordBasedSuggestions: 'off'
  })

  editor.value.addCommand(monaco.KeyCode.Tab, () => {
    const position = editor.value.getPosition()
    const model = editor.value.getModel()
    const lineContent = model.getLineContent(position.lineNumber)
    const textBeforeCursor = lineContent.substring(0, position.column - 1)

    if (textBeforeCursor === '' || /^\s*$/.test(textBeforeCursor)) {
      editor.value.trigger('keyboard', 'type', { text: '    ' })
    } else if (lastCompletions.length > 0) {
      editor.value.trigger('keyboard', 'acceptSelectedSuggestion', {})
    } else {
      lastCompletions = []
      fetchCompletions(editor.value.getValue(), position)
    }
  }, 'editorTextFocus')

  editor.value.onDidChangeModelContent(() => {
    const currentValue = editor.value.getValue()
    emit('update:modelValue', currentValue)

    const position = editor.value.getPosition()
    const lineContent = editor.value.getModel().getLineContent(position.lineNumber)
    const textBeforeCursor = lineContent.substring(0, position.column - 1).trim()

    if (textBeforeCursor.length > 0) {
      fetchCompletions(currentValue, position)
    } else {
      lastCompletions = []
    }
  })

  editor.value.onDidChangeCursorPosition(() => {
    lastCompletions = []
  })

  editor.value.onKeyDown((e) => {
    if (e.equals(monaco.KeyCode.Escape)) {
      lastCompletions = []
    }
  })

  completionProvider = monaco.languages.registerCompletionItemProvider(props.language, {
    provideCompletionItems: (model, position) => {
      if (!lastCompletions || lastCompletions.length === 0) {
        return { suggestions: [] }
      }

      const suggestions = lastCompletions
        .filter(item => item && item.name && item.name.trim() !== '')
        .map(item => ({
          label: item.name,
          kind: monaco.languages.CompletionItemKind.Function,
          insertText: item.name,
          documentation: item.description || '',
          detail: 'Python'
        }))

      return { suggestions }
    }
  })

  emit('editor-mounted', editor.value)

  watch(() => props.modelValue, (newValue) => {
    if (editor.value && newValue !== editor.value.getValue()) {
      editor.value.setValue(newValue || '')
      lastCompletions = []
    }
  })
})

onBeforeUnmount(() => {
  if (completionProvider) {
    completionProvider.dispose()
  }
  editor.value?.dispose()
})

defineExpose({
  getEditor: () => editor.value
})
</script>

<style scoped>
.editor-container {
  width: 100%;
  height: 100%;
}
</style>
