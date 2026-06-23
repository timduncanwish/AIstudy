<template>
  <view class="container">
    <!-- 科目选择 -->
    <view v-if="state === 'loading'" class="loading-screen">
      <view class="loading-spinner" />
      <text class="loading-text">加载中...</text>
    </view>

    <!-- 就绪态：显示任务信息 -->
    <view v-else-if="state === 'ready'" class="ready-screen">
      <view class="subject-tabs">
        <view :class="['tab', { active: subject === 'chinese' }]" @tap="switchSubject('chinese')">
          <text>语文</text>
        </view>
        <view :class="['tab', { active: subject === 'english' }]" @tap="switchSubject('english')">
          <text>英语</text>
        </view>
      </view>

      <view class="task-card">
        <text class="task-title">今日任务</text>
        <text class="task-date">{{ task.task_date }}</text>
        <view class="task-progress">
          <text class="task-info">已完成 {{ task.completed }}/{{ task.total }} 个字词</text>
          <view class="progress-bar">
            <view class="progress-fill" :style="{ width: progressPercent + '%' }" />
          </view>
        </view>
      </view>

      <view class="stats-card">
        <view class="stat-item">
          <text class="stat-value">{{ stats.total_points }}</text>
          <text class="stat-label">总积分</text>
        </view>
        <view class="stat-item">
          <text class="stat-value">{{ stats.streak_days }}</text>
          <text class="stat-label">连续天数</text>
        </view>
        <view class="stat-item">
          <text class="stat-value">{{ stats.words_mastered }}</text>
          <text class="stat-label">已掌握</text>
        </view>
      </view>

      <view v-if="task.remaining > 0" class="btn-start" @tap="startChallenge">
        <text>开始挑战</text>
      </view>
      <view v-else class="btn-done">
        <text>今日任务已完成！</text>
      </view>
    </view>

    <!-- 答题态 -->
    <view v-else-if="state === 'playing' && question" class="playing-screen">
      <view class="game-header">
        <view class="level-dots">
          <view v-for="n in 4" :key="n" :class="['level-dot', { active: n <= question.level }]" />
        </view>
        <text class="level-name">{{ question.level_name }}</text>
        <text class="streak-count">{{ streak }} 连对</text>
      </view>

      <view class="question-area">
        <text v-if="question.word" class="big-word">{{ question.word }}</text>
        <text v-if="question.pinyin" class="pinyin-hint">{{ question.pinyin }}</text>
        <text class="question-text">{{ question.question_text }}</text>
      </view>

      <view class="options-area">
        <view
          v-for="opt in question.options"
          :key="opt.index"
          class="option-card"
          @tap="selectAnswer(opt)"
        >
          <text>{{ opt.text }}</text>
        </view>
      </view>
    </view>

    <!-- 反馈态 -->
    <view v-else-if="state === 'feedback'" class="feedback-screen">
      <view :class="['feedback-icon', lastCorrect ? 'correct-icon' : 'wrong-icon']">
        <text>{{ lastCorrect ? '✓' : '✗' }}</text>
      </view>
      <text :class="['feedback-text', lastCorrect ? 'correct-text' : 'wrong-text']">
        {{ lastCorrect ? '答对了！' : '答错了' }}
      </text>
      <text v-if="!lastCorrect" class="correct-answer-text">
        正确答案：{{ lastCorrectAnswer }}
      </text>
      <text class="encouragement-text">{{ lastEncouragement }}</text>
      <view v-if="lastBadge" class="badge-popup">
        <text class="badge-icon">🏅</text>
        <text class="badge-text">获得徽章：{{ lastBadge }}</text>
      </view>
    </view>

    <!-- 完成态 -->
    <view v-else-if="state === 'complete'" class="complete-screen">
      <text class="complete-icon">🎉</text>
      <text class="complete-title">今日任务完成！</text>
      <text class="complete-points">+{{ totalPointsEarned }} 积分</text>
      <view class="complete-badges">
        <view v-for="b in earnedBadges" :key="b" class="badge-item">
          <text>🏅 {{ b }}</text>
        </view>
      </view>
      <view class="btn-restart" @tap="resetGame">
        <text>返回</text>
      </view>
    </view>
  </view>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import {
  getDailyTask,
  getChallengeQuestion,
  submitChallengeAnswer,
  getUserStats,
  type ChallengeQuestion,
  type DailyTaskResponse,
  type UserStatsResponse,
} from '@/api/challenge'
import { getUserId } from '@/utils/user'

const props = defineProps<{ grade?: number }>()
const grade = ref(props.grade || 3)
const subject = ref('chinese')
const state = ref<'loading' | 'ready' | 'playing' | 'feedback' | 'complete'>('loading')
const streak = ref(0)
const question = ref<ChallengeQuestion | null>(null)
const submitting = ref(false)  // 防止 await 窗口内连点选项导致重复提交/重复计分
const task = ref<DailyTaskResponse>({ task_date: '', subject: 'chinese', total: 0, completed: 0, remaining: 0, words: [] })
const stats = ref<UserStatsResponse>({ total_points: 0, streak_days: 0, words_mastered: 0, badges: [] })
const lastCorrect = ref(false)
const lastCorrectAnswer = ref('')
const lastEncouragement = ref('')
const lastBadge = ref('')
const totalPointsEarned = ref(0)
const earnedBadges = ref<string[]>([])

const progressPercent = computed(() => {
  if (task.value.total === 0) return 0
  return Math.round((task.value.completed / task.value.total) * 100)
})

const loadData = async () => {
  state.value = 'loading'
  getUserId()
  try {
    const [taskRes, statsRes] = await Promise.all([
      getDailyTask(subject.value, grade.value),
      getUserStats(),
    ])
    task.value = taskRes
    stats.value = statsRes
    state.value = 'ready'
  } catch {
    state.value = 'ready'
    uni.showToast({ title: '加载失败', icon: 'none' })
  }
}

const switchSubject = (s: string) => {
  subject.value = s
  loadData()
}

const startChallenge = async () => {
  try {
    const q = await getChallengeQuestion(subject.value, grade.value)
    if (q) {
      question.value = q
      state.value = 'playing'
    } else {
      state.value = 'complete'
    }
  } catch {
    uni.showToast({ title: '获取题目失败', icon: 'none' })
  }
}

const selectAnswer = async (opt: { text: string; index: number }) => {
  if (!question.value || submitting.value) return
  submitting.value = true

  try {
    const res = await submitChallengeAnswer({
      word: question.value.correct_answer,
      subject: subject.value,
      grade: grade.value,
      level: question.value.level,
      answer: opt.text,
      streak: streak.value,
    })

    lastCorrect.value = res.correct
    lastCorrectAnswer.value = res.correct_answer
    lastEncouragement.value = res.encouragement
    lastBadge.value = res.badge_earned || ''
    streak.value = res.streak
    totalPointsEarned.value += res.points_earned

    if (res.badge_earned) {
      earnedBadges.value.push(res.badge_earned)
    }

    state.value = 'feedback'

    setTimeout(async () => {
      try {
        const q = await getChallengeQuestion(subject.value, grade.value)
        if (q) {
          question.value = q
          state.value = 'playing'
        } else {
          state.value = 'complete'
        }
      } catch {
        // 取下一题失败：退回作答态避免卡在反馈页
        state.value = 'playing'
        uni.showToast({ title: '加载下一题失败，请重试', icon: 'none' })
      } finally {
        submitting.value = false
      }
    }, 1500)
  } catch {
    submitting.value = false
    uni.showToast({ title: '提交失败', icon: 'none' })
  }
}

const resetGame = () => {
  state.value = 'ready'
  streak.value = 0
  totalPointsEarned.value = 0
  earnedBadges.value = []
  loadData()
}

onMounted(() => {
  loadData()
})
</script>

<style scoped>
.container {
  min-height: 100vh;
  background: #EEF2FF;
}

.loading-screen {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100vh;
}

.loading-spinner {
  width: 80rpx;
  height: 80rpx;
  border: 6rpx solid #e0e0e0;
  border-top-color: #4F46E5;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.loading-text {
  margin-top: 20rpx;
  font-size: 28rpx;
  color: #999;
}

.ready-screen, .playing-screen, .feedback-screen, .complete-screen {
  padding: 30rpx;
}

.subject-tabs {
  display: flex;
  background: #fff;
  border-radius: 20rpx;
  overflow: hidden;
  margin-bottom: 24rpx;
  border: 3rpx solid #E0E7FF;
  box-shadow: 4rpx 4rpx 12rpx rgba(79, 70, 229, 0.06);
}

.tab {
  flex: 1;
  text-align: center;
  padding: 22rpx 0;
  font-size: 30rpx;
  color: #666;
}

.tab.active {
  background: #4F46E5;
  color: #fff;
  font-weight: bold;
}

.task-card {
  background: #fff;
  border-radius: 24rpx;
  padding: 36rpx;
  margin-bottom: 24rpx;
  border: 3rpx solid #E0E7FF;
  box-shadow: 4rpx 4rpx 12rpx rgba(79, 70, 229, 0.06), inset -2rpx -2rpx 6rpx rgba(79, 70, 229, 0.03);
}

.task-title {
  font-size: 34rpx;
  font-weight: bold;
  color: #312E81;
  display: block;
  margin-bottom: 8rpx;
}

.task-date {
  font-size: 26rpx;
  color: #999;
  display: block;
  margin-bottom: 20rpx;
}

.task-progress {
  margin-top: 16rpx;
}

.task-info {
  font-size: 28rpx;
  color: #555;
  display: block;
  margin-bottom: 12rpx;
}

.progress-bar {
  height: 16rpx;
  background: #e0e0e0;
  border-radius: 8rpx;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  background: linear-gradient(90deg, #4F46E5, #818CF8);
  border-radius: 8rpx;
  transition: width 0.3s;
}

.stats-card {
  display: flex;
  background: #fff;
  border-radius: 20rpx;
  padding: 30rpx;
  margin-bottom: 30rpx;
  box-shadow: 0 4rpx 16rpx rgba(0, 0, 0, 0.06);
}

.stat-item {
  flex: 1;
  text-align: center;
}

.stat-value {
  font-size: 40rpx;
  font-weight: bold;
  color: #4F46E5;
  display: block;
}

.stat-label {
  font-size: 24rpx;
  color: #999;
  display: block;
  margin-top: 6rpx;
}

.btn-start {
  text-align: center;
  padding: 30rpx;
  background: linear-gradient(135deg, #FF8E53, #FF6B6B);
  border-radius: 20rpx;
  font-size: 36rpx;
  font-weight: bold;
  color: #fff;
  box-shadow: 0 6rpx 20rpx rgba(255, 107, 107, 0.3);
}

.btn-done {
  text-align: center;
  padding: 30rpx;
  background: #4CAF50;
  border-radius: 20rpx;
  font-size: 34rpx;
  font-weight: bold;
  color: #fff;
}

.game-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 20rpx 30rpx;
  background: #fff;
  border-radius: 16rpx;
  margin-bottom: 24rpx;
}

.level-dots {
  display: flex;
  gap: 10rpx;
}

.level-dot {
  width: 24rpx;
  height: 24rpx;
  border-radius: 50%;
  background: #e0e0e0;
}

.level-dot.active {
  background: #FF8E53;
}

.level-name {
  font-size: 28rpx;
  font-weight: bold;
  color: #FF8E53;
}

.streak-count {
  font-size: 26rpx;
  color: #4F46E5;
  font-weight: bold;
}

.question-area {
  background: #fff;
  border-radius: 20rpx;
  padding: 50rpx 36rpx;
  margin-bottom: 24rpx;
  text-align: center;
  box-shadow: 0 4rpx 16rpx rgba(0, 0, 0, 0.06);
}

.big-word {
  font-size: 120rpx;
  font-weight: bold;
  color: #333;
  display: block;
  margin-bottom: 16rpx;
}

.pinyin-hint {
  font-size: 36rpx;
  color: #999;
  display: block;
  margin-bottom: 20rpx;
}

.question-text {
  font-size: 32rpx;
  color: #555;
  line-height: 1.6;
  display: block;
}

.options-area {
  display: flex;
  flex-direction: column;
  gap: 16rpx;
}

.option-card {
  background: #fff;
  border-radius: 16rpx;
  padding: 30rpx 36rpx;
  font-size: 30rpx;
  color: #333;
  box-shadow: 0 2rpx 8rpx rgba(0, 0, 0, 0.06);
  transition: transform 0.1s;
}

.option-card:active {
  transform: scale(0.98);
  background: #f0f7ff;
}

.feedback-screen {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 80vh;
}

.feedback-icon {
  width: 120rpx;
  height: 120rpx;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 60rpx;
  color: #fff;
  margin-bottom: 24rpx;
}

.correct-icon {
  background: #4CAF50;
  animation: bounce 0.5s;
}

.wrong-icon {
  background: #FF6B6B;
  animation: shake 0.5s;
}

@keyframes bounce {
  0%, 100% { transform: scale(1); }
  50% { transform: scale(1.2); }
}

@keyframes shake {
  0%, 100% { transform: translateX(0); }
  25% { transform: translateX(-20rpx); }
  75% { transform: translateX(20rpx); }
}

.feedback-text {
  font-size: 40rpx;
  font-weight: bold;
  margin-bottom: 16rpx;
}

.correct-text { color: #4CAF50; }
.wrong-text { color: #FF6B6B; }

.correct-answer-text {
  font-size: 28rpx;
  color: #4CAF50;
  margin-bottom: 16rpx;
}

.encouragement-text {
  font-size: 30rpx;
  color: #666;
  text-align: center;
}

.badge-popup {
  margin-top: 30rpx;
  background: linear-gradient(135deg, #FFD700, #FFA500);
  border-radius: 16rpx;
  padding: 20rpx 30rpx;
  animation: popIn 0.5s;
}

@keyframes popIn {
  0% { transform: scale(0); }
  70% { transform: scale(1.1); }
  100% { transform: scale(1); }
}

.badge-icon {
  font-size: 36rpx;
  display: block;
  text-align: center;
  margin-bottom: 8rpx;
}

.badge-text {
  font-size: 28rpx;
  color: #fff;
  font-weight: bold;
}

.complete-screen {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 80vh;
}

.complete-icon {
  font-size: 120rpx;
  display: block;
  margin-bottom: 20rpx;
}

.complete-title {
  font-size: 40rpx;
  font-weight: bold;
  color: #333;
  margin-bottom: 16rpx;
}

.complete-points {
  font-size: 36rpx;
  font-weight: bold;
  color: #FF8E53;
  margin-bottom: 24rpx;
}

.complete-badges {
  margin-bottom: 40rpx;
}

.badge-item {
  font-size: 28rpx;
  color: #FF8E53;
  padding: 10rpx 0;
}

.btn-restart {
  padding: 24rpx 80rpx;
  background: #4F46E5;
  border-radius: 16rpx;
  font-size: 30rpx;
  color: #fff;
  font-weight: bold;
}
</style>
