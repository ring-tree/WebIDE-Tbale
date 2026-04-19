<script setup>
import { ref } from 'vue'

const props = defineProps({
  visible: {
    type: Boolean,
    default: true
  }
})

const emit = defineEmits(['send-message'])

const inputMessage = ref('')
const chatHistory = ref([
  {
    role: 'assistant',
    content: '你好！我是 AI 助手，可以帮你解答编程问题、生成代码或调试错误。请问有什么可以帮你的？',
    timestamp: new Date().toLocaleTimeString()
  }
])
const isLoading = ref(false)

const sendMessage = async () => {
  if (!inputMessage.value.trim() || isLoading.value) return

  const userMsg = inputMessage.value.trim()
  chatHistory.value.push({
    role: 'user',
    content: userMsg,
    timestamp: new Date().toLocaleTimeString()
  })

  inputMessage.value = ''
  isLoading.value = true

  try {
    const response = await fetch('/api/ai/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        messages: chatHistory.value.map(msg => ({
          role: msg.role === 'assistant' ? 'assistant' : 'user',
          content: msg.content
        }))
      })
    })

    const result = await response.json()

    if (result.status === 'success' && result.data) {
      chatHistory.value.push({
        role: 'assistant',
        content: result.data.content || '抱歉，我没有收到有效的回复。',
        timestamp: new Date().toLocaleTimeString()
      })
    } else {
      chatHistory.value.push({
        role: 'assistant',
        content: `错误: ${result.message || '未知错误'}`,
        timestamp: new Date().toLocaleTimeString()
      })
    }
  } catch (error) {
    chatHistory.value.push({
      role: 'assistant',
      content: `网络错误: ${error.message}`,
      timestamp: new Date().toLocaleTimeString()
    })
  } finally {
    isLoading.value = false
  }

  emit('send-message', userMsg)
}

// 按 Enter 发送
const handleEnter = (e) => {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault()
    sendMessage()
  }
}

// 清空对话
const clearChat = () => {
  chatHistory.value = [
    {
      role: 'assistant',
      content: '对话已清空。有什么可以帮你的？',
      timestamp: new Date().toLocaleTimeString()
    }
  ]
}
</script>

<template>
  <div class="ai-chat-container" v-if="visible">
    <!-- 聊天头部 -->
    <div class="chat-header">
      <span class="chat-title">🤖 AI 助手</span>
      <button class="clear-btn" @click="clearChat" title="清空对话">🗑️</button>
    </div>
    
    <!-- 消息列表 -->
    <div class="chat-messages">
      <div 
        v-for="(msg, index) in chatHistory" 
        :key="index"
        :class="['message', msg.role]"
      >
        <div class="message-header">
          <span class="message-role">
            {{ msg.role === 'user' ? '👤 我' : '🤖 AI' }}
          </span>
          <span class="message-time">{{ msg.timestamp }}</span>
        </div>
        <div class="message-content">{{ msg.content }}</div>
      </div>
      
      <!-- 加载中状态 -->
      <div v-if="isLoading" class="message assistant">
        <div class="message-content loading">
          <span class="loading-dot">●</span>
          <span class="loading-dot">●</span>
          <span class="loading-dot">●</span>
        </div>
      </div>
    </div>
    
    <!-- 输入区域 -->
    <div class="chat-input-area">
      <textarea
        v-model="inputMessage"
        @keydown="handleEnter"
        placeholder="输入问题，按 Enter 发送..."
        rows="3"
        class="chat-input"
        :disabled="isLoading"
      ></textarea>
      <button 
        class="send-btn" 
        @click="sendMessage"
        :disabled="!inputMessage.trim() || isLoading"
      >
        发送
      </button>
    </div>
  </div>
</template>

<style scoped>
.ai-chat-container {
  display: flex;
  flex-direction: column;
  height: 100%;
  padding: 10px;
}

.chat-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-bottom: 10px;
  border-bottom: 1px solid #333;
  margin-bottom: 10px;
}

.chat-title {
  font-size: 14px;
  font-weight: bold;
  color: #ddd;
}

.clear-btn {
  background: none;
  border: none;
  cursor: pointer;
  font-size: 16px;
  opacity: 0.6;
  transition: opacity 0.2s;
}

.clear-btn:hover {
  opacity: 1;
}

.chat-messages {
  flex: 1;
  overflow-y: auto;
  margin-bottom: 10px;
}

.message {
  margin-bottom: 12px;
  padding: 8px 10px;
  border-radius: 6px;
}

.message.user {
  background-color: #007acc;
  color: white;
}

.message.assistant {
  background-color: #2d2d2d;
  color: #ccc;
}

.message-header {
  display: flex;
  justify-content: space-between;
  font-size: 11px;
  margin-bottom: 4px;
  opacity: 0.8;
}

.message-content {
  font-size: 13px;
  line-height: 1.5;
  white-space: pre-wrap;
  word-break: break-word;
}

.loading {
  display: flex;
  gap: 4px;
}

.loading-dot {
  animation: bounce 1.4s infinite ease-in-out;
}

.loading-dot:nth-child(1) { animation-delay: -0.32s; }
.loading-dot:nth-child(2) { animation-delay: -0.16s; }

@keyframes bounce {
  0%, 80%, 100% { transform: scale(0.6); opacity: 0.5; }
  40% { transform: scale(1); opacity: 1; }
}

.chat-input-area {
  display: flex;
  flex-direction: column;
  gap: 8px;
  border-top: 1px solid #333;
  padding-top: 10px;
}

.chat-input {
  width: 100%;
  padding: 8px;
  background-color: #3c3c3c;
  border: 1px solid #454545;
  border-radius: 4px;
  color: #ddd;
  font-family: inherit;
  font-size: 13px;
  resize: none;
}

.chat-input:focus {
  outline: none;
  border-color: #007acc;
}

.chat-input:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.send-btn {
  padding: 8px 16px;
  background-color: #007acc;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 13px;
  transition: background-color 0.2s;
}

.send-btn:hover:not(:disabled) {
  background-color: #006bb3;
}

.send-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
</style>