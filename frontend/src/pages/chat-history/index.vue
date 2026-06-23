<template>
  <view class="container">
    <!-- 列表模式 -->
    <view v-if="!detail">
      <view v-if="!userId" class="empty">
        <text class="empty-icon">🔒</text>
        <text class="empty-text">登录后可查看历史对话</text>
      </view>
      <view v-else-if="loading" class="empty">
        <text class="empty-text">加载中...</text>
      </view>
      <view v-else-if="sessions.length === 0" class="empty">
        <text class="empty-icon">💬</text>
        <text class="empty-text">还没有历史对话</text>
        <text class="empty-hint">去「AI辅导」和老师聊聊吧</text>
      </view>
      <view v-else>
        <view
          v-for="s in sessions"
          :key="s.session_id"
          class="session-card clay-tap"
          hover-class="clay-pressed"
          hover-stay-time="80"
          @tap="openSession(s)"
        >
          <view class="session-head">
            <view :class="['subj-pill', s.subject]">
              <text>{{ s.subject === 'chinese' ? '语文' : '英语' }} · {{ s.grade }}年级</text>
            </view>
            <text class="msg-count">{{ s.message_count }} 条</text>
          </view>
          <text class="last-msg">{{ s.last_message }}</text>
          <view class="session-foot">
            <text class="time">{{ formatTime(s.created_at) }}</text>
            <text class="del-btn" @tap.stop="confirmDelete(s)">删除</text>
          </view>
        </view>
      </view>
    </view>

    <!-- 详情模式 -->
    <view v-else class="detail">
      <view class="detail-head">
        <text class="back" @tap="detail = null">‹ 返回</text>
        <text class="detail-title">
          {{ detail.subject === 'chinese' ? '语文' : '英语' }} · {{ detail.grade }}年级
        </text>
      </view>
      <scroll-view scroll-y class="msg-scroll">
        <view
          v-for="(m, i) in detail.messages"
          :key="i"
          :class="['row', m.role === 'user' ? 'user-row' : 'ai-row']"
        >
          <view :class="['avatar', m.role === 'user' ? 'avatar-user' : 'avatar-ai']">
            <text class="avatar-text">{{ m.role === 'user' ? '我' : 'AI' }}</text>
          </view>
          <view :class="['bubble', m.role === 'user' ? 'bubble-user' : 'bubble-ai']">
            <text class="bubble-text">{{ m.content }}</text>
          </view>
        </view>
      </scroll-view>
    </view>
  </view>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import {
  getChatSessions,
  getChatHistory,
  deleteChatHistory,
  type ChatSessionSummary,
  type ChatHistoryResponse,
} from '@/api/chat'

const userId = ref<number | null>(null)
const sessions = ref<ChatSessionSummary[]>([])
const detail = ref<ChatHistoryResponse | null>(null)
const loading = ref(false)

onMounted(() => {
  const uid = uni.getStorageSync('db_user_id')
  userId.value = uid ? Number(uid) : null
  if (userId.value) loadSessions()
})

const loadSessions = async () => {
  if (!userId.value) return
  loading.value = true
  try {
    const res = await getChatSessions(userId.value)
    sessions.value = res.sessions
  } catch {
    sessions.value = []
  } finally {
    loading.value = false
  }
}

const openSession = async (s: ChatSessionSummary) => {
  if (!userId.value) return
  try {
    detail.value = await getChatHistory(userId.value, s.session_id)
  } catch {
    uni.showToast({ title: '加载失败', icon: 'none' })
  }
}

const confirmDelete = (s: ChatSessionSummary) => {
  if (!userId.value) return
  uni.showModal({
    title: '删除对话',
    content: '确定删除这段对话记录？',
    success: async (res) => {
      if (!res.confirm || !userId.value) return
      try {
        await deleteChatHistory(userId.value, s.session_id)
        sessions.value = sessions.value.filter((x) => x.session_id !== s.session_id)
        uni.showToast({ title: '已删除', icon: 'none' })
      } catch {
        uni.showToast({ title: '删除失败', icon: 'none' })
      }
    },
  })
}

const formatTime = (t: string) => {
  if (!t) return ''
  // 后端返回类似 "2026-06-18 01:42:00"，截到分钟
  return t.replace('T', ' ').slice(0, 16)
}
</script>

<style scoped>
.container {
  min-height: 100vh;
  background: #EEF2FF;
  padding: 24rpx;
  box-sizing: border-box;
}

/* 空状态 */
.empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding-top: 200rpx;
}
.empty-icon {
  font-size: 96rpx;
  margin-bottom: 24rpx;
}
.empty-text {
  font-size: 30rpx;
  color: #666;
  margin-bottom: 12rpx;
}
.empty-hint {
  font-size: 24rpx;
  color: #aaa;
}

/* 会话卡片 */
.session-card {
  background: #fff;
  border-radius: 24rpx;
  padding: 28rpx;
  margin-bottom: 20rpx;
  border: 2rpx solid #E0E7FF;
  box-shadow: 3rpx 3rpx 12rpx rgba(79, 70, 229, 0.06);
}
.session-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16rpx;
}
.subj-pill {
  padding: 6rpx 18rpx;
  border-radius: 10rpx;
  font-size: 24rpx;
}
.subj-pill.chinese {
  background: #FEF3C7;
  color: #D97706;
}
.subj-pill.english {
  background: #DBEAFE;
  color: #2563EB;
}
.msg-count {
  font-size: 24rpx;
  color: #999;
}
.last-msg {
  font-size: 28rpx;
  color: #333;
  line-height: 1.5;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
.session-foot {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 18rpx;
}
.time {
  font-size: 22rpx;
  color: #bbb;
}
.del-btn {
  font-size: 24rpx;
  color: #EF4444;
  padding: 4rpx 16rpx;
}

/* 详情 */
.detail-head {
  display: flex;
  align-items: center;
  margin-bottom: 20rpx;
}
.back {
  font-size: 30rpx;
  color: #4F46E5;
  padding-right: 24rpx;
}
.detail-title {
  font-size: 30rpx;
  font-weight: bold;
  color: #333;
}
.msg-scroll {
  height: calc(100vh - 140rpx);
}
.row {
  display: flex;
  margin-bottom: 28rpx;
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
  background: linear-gradient(135deg, #818CF8, #4F46E5);
}
.avatar-ai {
  background: linear-gradient(135deg, #6366F1, #4338CA);
}
.avatar-text {
  color: #fff;
  font-size: 26rpx;
  font-weight: bold;
}
.bubble {
  max-width: 70%;
  padding: 20rpx 24rpx;
  border-radius: 20rpx;
  margin: 0 16rpx;
}
.bubble-user {
  background: #4F46E5;
}
.bubble-ai {
  background: #fff;
  border: 2rpx solid #E0E7FF;
}
.bubble-text {
  font-size: 28rpx;
  line-height: 1.6;
}
.bubble-user .bubble-text {
  color: #fff;
}
.bubble-ai .bubble-text {
  color: #333;
}
</style>
