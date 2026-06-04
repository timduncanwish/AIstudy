<template>
  <view class="chat-container">
    <view class="subject-bar">
      <view :class="['subject-tab', { active: subject === 'chinese' }]" @tap="switchSubject('chinese')">
        <view v-if="subject === 'chinese'" class="tab-dot chinese-dot" />
        <text>语文</text>
      </view>
      <view :class="['subject-tab', { active: subject === 'english' }]" @tap="switchSubject('english')">
        <view v-if="subject === 'english'" class="tab-dot english-dot" />
        <text>英语</text>
      </view>
      <view class="grade-pill">
        <text class="grade-text">{{ grade }}年级</text>
      </view>
    </view>

    <scroll-view
      class="message-list"
      scroll-y
      :scroll-top="scrollTop"
      :scroll-with-animation="true"
    >
      <view class="welcome-tip" v-if="messages.length === 0">
        <view class="welcome-avatar">
          <text class="welcome-avatar-text">AI</text>
        </view>
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
        <view class="bubble bubble-ai typing-bubble">
          <view class="typing-dots">
            <view class="dot-anim" />
            <view class="dot-anim" />
            <view class="dot-anim" />
          </view>
        </view>
      </view>
    </scroll-view>

    <view class="input-bar">
      <view class="input-wrap">
        <input
          class="input-field"
          v-model="inputText"
          placeholder="输入你的问题..."
          :disabled="loading"
          confirm-type="send"
          @confirm="sendMessage"
        />
      </view>
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
  background: #EEF2FF;
}

.subject-bar {
  display: flex;
  align-items: center;
  background: #fff;
  padding: 16rpx 24rpx;
  border-bottom: 2rpx solid #E0E7FF;
  gap: 12rpx;
}

.subject-tab {
  display: flex;
  align-items: center;
  gap: 8rpx;
  padding: 12rpx 28rpx;
  border-radius: 24rpx;
  font-size: 26rpx;
  color: #6B7280;
  background: #F5F3FF;
  border: 2rpx solid #E0E7FF;
}

.subject-tab.active {
  background: linear-gradient(135deg, #818CF8, #4F46E5);
  color: #fff;
  font-weight: 700;
  border-color: transparent;
  box-shadow: 2rpx 2rpx 8rpx rgba(79, 70, 229, 0.2);
}

.tab-dot {
  width: 12rpx;
  height: 12rpx;
  border-radius: 50%;
}

.chinese-dot {
  background: #FB923C;
}

.english-dot {
  background: #38BDF8;
}

.grade-pill {
  margin-left: auto;
  padding: 8rpx 20rpx;
  background: #F5F3FF;
  border-radius: 20rpx;
  border: 2rpx solid #E0E7FF;
}

.grade-text {
  font-size: 22rpx;
  color: #6366F1;
  font-weight: 600;
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

.welcome-avatar {
  width: 80rpx;
  height: 80rpx;
  border-radius: 50%;
  background: linear-gradient(135deg, #818CF8, #4F46E5);
  margin: 0 auto 20rpx;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 3rpx 3rpx 10rpx rgba(79, 70, 229, 0.25);
}

.welcome-avatar-text {
  color: #fff;
  font-size: 28rpx;
  font-weight: bold;
}

.tip-text {
  font-size: 28rpx;
  color: #6366F1;
  line-height: 1.6;
  display: block;
  opacity: 0.8;
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
  box-shadow: 2rpx 2rpx 8rpx rgba(0, 0, 0, 0.08);
}

.avatar-user {
  background: linear-gradient(135deg, #818CF8, #4F46E5);
  margin-left: 16rpx;
}

.avatar-ai {
  background: linear-gradient(135deg, #FDBA74, #FB923C);
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
  border-radius: 24rpx;
  word-break: break-all;
}

.bubble-user {
  background: linear-gradient(135deg, #818CF8, #4F46E5);
  border-bottom-right-radius: 8rpx;
  box-shadow: 2rpx 2rpx 10rpx rgba(79, 70, 229, 0.2);
}

.bubble-ai {
  background: #fff;
  border-bottom-left-radius: 8rpx;
  border: 2rpx solid #E0E7FF;
  box-shadow: 3rpx 3rpx 10rpx rgba(79, 70, 229, 0.06);
}

.bubble-text {
  font-size: 28rpx;
  line-height: 1.7;
  display: block;
}

.bubble-user .bubble-text {
  color: #fff;
}

.bubble-ai .bubble-text {
  color: #312E81;
}

.typing-bubble {
  padding: 24rpx 32rpx;
}

.typing-dots {
  display: flex;
  gap: 10rpx;
  align-items: center;
}

.dot-anim {
  width: 14rpx;
  height: 14rpx;
  border-radius: 50%;
  background: #818CF8;
  animation: bounce-dot 1.4s infinite ease-in-out both;
}

.dot-anim:nth-child(1) { animation-delay: 0s; }
.dot-anim:nth-child(2) { animation-delay: 0.16s; }
.dot-anim:nth-child(3) { animation-delay: 0.32s; }

@keyframes bounce-dot {
  0%, 80%, 100% { transform: scale(0.6); opacity: 0.4; }
  40% { transform: scale(1); opacity: 1; }
}

.kb-hint {
  margin-top: 14rpx;
  padding-top: 10rpx;
  border-top: 1rpx solid #E0E7FF;
}

.kb-hint-text {
  font-size: 20rpx;
  color: #818CF8;
}

.input-bar {
  display: flex;
  padding: 16rpx 20rpx;
  background: #fff;
  border-top: 2rpx solid #E0E7FF;
  padding-bottom: calc(16rpx + env(safe-area-inset-bottom));
  gap: 16rpx;
  align-items: center;
}

.input-wrap {
  flex: 1;
  background: #F5F3FF;
  border-radius: 28rpx;
  border: 2rpx solid #E0E7FF;
  overflow: hidden;
}

.input-field {
  height: 72rpx;
  padding: 0 28rpx;
  font-size: 28rpx;
  color: #312E81;
}

.send-btn {
  background: linear-gradient(135deg, #818CF8, #4F46E5);
  border-radius: 28rpx;
  padding: 0 36rpx;
  height: 72rpx;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 2rpx 2rpx 8rpx rgba(79, 70, 229, 0.25);
}

.send-btn.disabled {
  background: #CBD5E1;
  box-shadow: none;
}

.send-text {
  color: #fff;
  font-size: 28rpx;
  font-weight: 600;
}
</style>
