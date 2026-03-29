<template>
  <div ref="editorContainer" class="editor-container"></div>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount, shallowRef } from 'vue'
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
let hasRequestedCompletions = false

const sendToBackend = async (code, position) => {
  try {
    const response = await fetch('http://localhost:5000/update', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ code, line: position.lineNumber, column: position.column })
    })
    const data = await response.json()
    
    if (data.completions?.length) {
      lastCompletions = data.completions
      hasRequestedCompletions = true
      editor.value.trigger('keyboard', 'editor.action.triggerSuggest', {})
    } else {
      lastCompletions = []
    }
  } catch (error) {
    console.error('Failed to send code to backend:', error)
  }
}

onMounted(() => {
  if (!editorContainer.value) return

  editor.value = monaco.editor.create(editorContainer.value, {
    value: props.modelValue,
    language: props.language,
    automaticLayout: true,
    theme: 'vs-dark',
    suggest: { showWords: false, showSnippets: false, autoSuggestions: false, suppressSuggestions: true },
    quickSuggestions: false,
    suggestOnTriggerCharacters: false,
    acceptSuggestionOnEnter: 'on',
    tabCompletion: 'off',
    tabSize: 4,
    insertSpaces: true,
    renderWhitespace: 'none',
    useTabStops: false
  })

  editor.value.addCommand(monaco.KeyCode.Tab, () => {
    const position = editor.value.getPosition()
    const model = editor.value.getModel()
    const lineContent = model.getLineContent(position.lineNumber)
    const column = position.column
    
    if (column > 1 && lineContent[column - 2] !== ' ' && lineContent[column - 2] !== '\t') {
      if (!hasRequestedCompletions) {
        sendToBackend(editor.value.getValue(), editor.value.getPosition())
      }
    } else {
      editor.value.trigger('keyboard', 'type', { text: '    ' })
    }
  }, 'editorTextFocus')

  editor.value.onDidChangeModelContent(() => {
    hasRequestedCompletions = false
  })

  completionProvider = monaco.languages.registerCompletionItemProvider(props.language, {
    provideCompletionItems: (model, position) => {
      if (lastCompletions.length === 0) {
        return null
      }
      const suggestions = lastCompletions.map(item => ({
        label: item.name,
        kind: monaco.languages.CompletionItemKind.Function,
        insertText: item.name,
        documentation: item.description,
        detail: 'Python'
      }))

      return {
        suggestions: suggestions
      }
    }
  })

  emit('editor-mounted', editor.value)
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
