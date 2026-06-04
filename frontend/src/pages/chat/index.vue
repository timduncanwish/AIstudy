<template>
  <view class="chat-container">
    <view class="subject-bar">
      <view :class="['subject-tab', { active: subject === 'chinese' }]" @tap="switchSubject('chinese')">
        <text>语文</text>
      </view>
      <view :class="['subject-tab', { active: subject === 'english' }]" @tap="switchSubject('english')">
        <text>英语</text>
      </view>
      <text class="grade-tag">{{ grade }}年级</text>
    </view>

    <scroll-view
      class="message-list"
      scroll-y
      :scroll-top="scrollTop"
      :scroll-with-animation="true"
    >
      <view class="welcome-tip" v-if="messages.length === 0">
        <text class="tip-icon">{{ subject === 'chinese' ? '语文' : '英文' }}</text>
        <text class="tip-text">
          你好！我是你的{{ subject === 'chinese' ? '语文' : '英语' }}小助手。
          有什么不懂的尽管问我吧！
        </text>
      </view>

      <view
        v-for="(msg, idx) in messages"
        :key="idx"
        :class="['message-row', msg.role === 'user' ? 'user-row' : 'ai-row']"
      >
        <view :class="['avatar', msg.role === 'user' ? 'avatar-user' : 'avatar-ai']">
          <text class="avatar-text">{{ msg.role === 'user' ? '我' : 'AI' }}</text>
        </view>
        <view :class="['bubble', msg.role === 'user' ? 'bubble-user' : 'bubble-ai']">
          <text class="bubble-text">{{ msg.content }}</text>
          <view v-if="msg.role === 'assistant' && msg.mistakesReferenced" class="kb-hint">
            <text class="kb-hint-text">参考了 {{ msg.mistakesReferenced }} 条错题记录</text>
          </view>
        </view>
      </view>

      <view v-if="loading" class="message-row ai-row">
        <view class="avatar avatar-ai">
          <text class="avatar-text">AI</text>
        </view>
        <view class="bubble bubble-ai">
          <text class="bubble-text typing">正在思考...</text>
        </view>
      </view>
    </scroll-view>

    <view class="input-bar">
      <input
        class="input-field"
        v-model="inputText"
        placeholder="输入你的问题..."
        :disabled="loading"
        confirm-type="send"
        @confirm="sendMessage"
      />
      <view
        :class="['send-btn', { disabled: !inputText.trim() || loading }]"
        @tap="sendMessage"
      >
        <text class="send-text">发送</text>
      </view>
    </view>
  </view>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { chat } from '@/api/chat'
import { getUserId } from '@/utils/user'

interface Message {
  role: 'user' | 'assistant'
  content: string
  mistakesReferenced?: number
}

const subject = ref('chinese')
const grade = ref(3)
const sessionId = ref('')

const messages = ref<Message[]>([])
const inputText = ref('')
const loading = ref(false)
const scrollTop = ref(0)

onMounted(() => {
  subject.value = uni.getStorageSync('chat_subject') || 'chinese'
  grade.value = parseInt(String(uni.getStorageSync('chat_grade') || '3'))
  sessionId.value = 'sess_' + Date.now() + '_' + Math.random().toString(36).slice(2, 8)
})

const scrollToBottom = () => {
  setTimeout(() => {
    scrollTop.value = scrollTop.value + 1000
  }, 50)
}

const switchSubject = (s: string) => {
  if (s === subject.value) return
  subject.value = s
  messages.value = []
  sessionId.value = 'sess_' + Date.now() + '_' + Math.random().toString(36).slice(2, 8)
  uni.setStorageSync('chat_subject', s)
}

const sendMessage = async () => {
  const text = inputText.value.trim()
  if (!text || loading.value) return

  messages.value.push({ role: 'user', content: text })
  inputText.value = ''
  loading.value = true
  scrollToBottom()

  try {
    const chatMessages = messages.value.map((m) => ({
      role: m.role,
      content: m.content,
    }))

    const dbUserId = uni.getStorageSync('db_user_id') || null

    const data = await chat({
      messages: chatMessages,
      subject: subject.value,
      grade: grade.value,
      user_id: dbUserId,
      session_id: sessionId.value,
    })

    if (data.reply) {
      messages.value.push({
        role: 'assistant',
        content: data.reply,
        mistakesReferenced: data.mistakes_referenced || 0,
      })
    }
  } catch {
    messages.value.push({
      role: 'assistant',
      content: '抱歉，网络出了点问题，请稍后再试。',
    })
  }

  loading.value = false
  scrollToBottom()
}
</script>

<style scoped>
.chat-container {
  display: flex;
  flex-direction: column;
  height: 100vh;
  background: #f0f0f0;
}

.subject-bar {
  display: flex;
  align-items: center;
  background: #fff;
  padding: 12rpx 20rpx;
  border-bottom: 1rpx solid #e0e0e0;
}

.subject-tab {
  padding: 12rpx 28rpx;
  border-radius: 24rpx;
  font-size: 26rpx;
  color: #666;
  margin-right: 16rpx;
}

.subject-tab.active {
  background: #4A90D9;
  color: #fff;
  font-weight: bold;
}

.grade-tag {
  margin-left: auto;
  font-size: 24rpx;
  color: #999;
  padding: 8rpx 20rpx;
  background: #f5f5f5;
  border-radius: 20rpx;
}

.message-list {
  flex: 1;
  padding: 20rpx;
  overflow-y: auto;
}

.welcome-tip {
  text-align: center;
  padding: 60rpx 40rpx;
}

.tip-icon {
  font-size: 80rpx;
  display: block;
  margin-bottom: 20rpx;
}

.tip-text {
  font-size: 28rpx;
  color: #888;
  line-height: 1.6;
  display: block;
}

.message-row {
  display: flex;
  margin-bottom: 24rpx;
  align-items: flex-start;
}

.user-row {
  flex-direction: row-reverse;
}

.avatar {
  width: 64rpx;
  height: 64rpx;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.avatar-user {
  background: #4A90D9;
  margin-left: 16rpx;
}

.avatar-ai {
  background: #FF8E53;
  margin-right: 16rpx;
}

.avatar-text {
  color: #fff;
  font-size: 22rpx;
  font-weight: bold;
}

.bubble {
  max-width: 70%;
  padding: 20rpx 28rpx;
  border-radius: 20rpx;
  word-break: break-all;
}

.bubble-user {
  background: #4A90D9;
  border-top-right-radius: 4rpx;
}

.bubble-ai {
  background: #fff;
  border-top-left-radius: 4rpx;
}

.bubble-text {
  font-size: 28rpx;
  line-height: 1.6;
  display: block;
}

.bubble-user .bubble-text {
  color: #fff;
}

.bubble-ai .bubble-text {
  color: #333;
}

.typing {
  color: #aaa;
}

.kb-hint {
  margin-top: 12rpx;
  padding-top: 8rpx;
  border-top: 1rpx solid #f0f0f0;
}

.kb-hint-text {
  font-size: 20rpx;
  color: #aaa;
}

.input-bar {
  display: flex;
  padding: 16rpx 20rpx;
  background: #fff;
  border-top: 1rpx solid #e0e0e0;
  padding-bottom: calc(16rpx + env(safe-area-inset-bottom));
}

.input-field {
  flex: 1;
  height: 72rpx;
  padding: 0 24rpx;
  background: #f5f5f5;
  border-radius: 36rpx;
  font-size: 28rpx;
}

.send-btn {
  margin-left: 16rpx;
  background: #4A90D9;
  border-radius: 36rpx;
  padding: 0 32rpx;
  display: flex;
  align-items: center;
  justify-content: center;
}

.send-btn.disabled {
  background: #ccc;
}

.send-text {
  color: #fff;
  font-size: 28rpx;
}
</style>
