<template>
  <view class="container">
    <view v-if="step === 'loading'" class="loading-section">
      <text class="loading-icon">🎯</text>
      <text class="loading-text">正在为你生成专属练习...</text>
      <text class="loading-hint">根据你的薄弱知识点智能出题</text>
    </view>

    <view v-else-if="step === 'quiz'" class="quiz-section">
      <view class="progress-bar">
        <view class="progress-fill" :style="{ width: progressPercent + '%' }" />
      </view>
      <view class="progress-text">
        <text>{{ currentIndex + 1 }} / {{ practice.questions.length }}</text>
        <text class="topic-tag">{{ practice.topic }}</text>
      </view>

      <view class="question-card">
        <text class="question-text">{{ currentQuestion.question }}</text>
        <view
          v-for="(opt, oi) in currentQuestion.options"
          :key="oi"
          :class="['option-item', getOptionClass(oi)]"
          @tap="selectAnswer(oi)"
        >
          <view class="option-letter">
            <text>{{ ['A', 'B', 'C', 'D'][oi] }}</text>
          </view>
          <text class="option-text">{{ opt }}</text>
          <text v-if="answered && oi === currentQuestion.correct_index" class="option-check">✓</text>
          <text v-if="answered && oi === selectedAnswer && oi !== currentQuestion.correct_index" class="option-cross">✗</text>
        </view>
      </view>

      <view v-if="answered" class="explanation-card">
        <text class="explanation-label">解析</text>
        <text class="explanation-text">{{ currentQuestion.explanation }}</text>
      </view>

      <view v-if="answered" class="next-btn" @tap="nextQuestion">
        <text class="next-btn-text">{{ isLast ? '查看结果' : '下一题' }}</text>
      </view>
    </view>

    <view v-else-if="step === 'result'" class="result-section">
      <view class="result-header">
        <text class="result-icon">{{ scorePercent >= 80 ? '🎉' : scorePercent >= 60 ? '👍' : '💪' }}</text>
        <text class="result-score">{{ practice.score }} / {{ practice.total }}</text>
        <text class="result-label">正确率 {{ scorePercent }}%</text>
      </view>

      <view class="result-topic">
        <text class="result-topic-label">练习知识点</text>
        <text class="result-topic-name">{{ practice.topic }}</text>
      </view>

      <view class="result-message">
        <text class="result-msg-text">{{ resultMessage }}</text>
      </view>

      <view class="result-actions">
        <view class="btn-retry" @tap="retry">
          <text class="btn-text">再来一轮</text>
        </view>
        <view class="btn-home" @tap="goHome">
          <text class="btn-text-home">返回首页</text>
        </view>
      </view>

      <view v-if="history.streak > 0" class="streak-card">
        <text class="streak-icon">🔥</text>
        <text class="streak-text">连续练习 {{ history.streak }} 天</text>
      </view>
    </view>

    <view v-if="step === 'error'" class="error-section">
      <text class="error-icon">😔</text>
      <text class="error-text">{{ errorMsg }}</text>
      <view class="btn-retry" @tap="retry">
        <text class="btn-text">重新生成</text>
      </view>
    </view>
  </view>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import {
  generateDailyPractice, submitPractice, getPracticeHistory,
  type DailyPracticeResponse, type PracticeHistoryResponse, type PracticeQuestion,
} from '@/api/practice'

type Step = 'loading' | 'quiz' | 'result' | 'error'

const step = ref<Step>('loading')
const subject = ref('chinese')

onMounted(() => {
  const pages = getCurrentPages()
  const page = pages[pages.length - 1]
  const opts = (page as any)?.options || {}
  if (opts.subject) subject.value = opts.subject
})
const practice = ref<DailyPracticeResponse>(null as any)
const currentIndex = ref(0)
const selectedAnswer = ref(-1)
const answered = ref(false)
const answers = ref<number[]>([])
const errorMsg = ref('')
const history = ref<PracticeHistoryResponse>({ items: [], streak: 0 })

const currentQuestion = computed<PracticeQuestion>(() => {
  return practice.value?.questions[currentIndex.value] || {} as any
})

const progressPercent = computed(() => {
  if (!practice.value) return 0
  return ((currentIndex.value + 1) / practice.value.questions.length) * 100
})

const isLast = computed(() => {
  return currentIndex.value >= (practice.value?.questions.length || 0) - 1
})

const scorePercent = computed(() => {
  if (!practice.value || !practice.value.total) return 0
  return Math.round(((practice.value.score ?? 0) / practice.value.total) * 100)
})

const resultMessage = computed(() => {
  const p = scorePercent.value
  if (p >= 100) return '太棒了！全部答对，继续保持！'
  if (p >= 80) return '非常棒！掌握得很好，再接再厉！'
  if (p >= 60) return '不错哦！还有一些可以加强的地方'
  if (p >= 40) return '继续加油！多练习几次就会了'
  return '没关系，多复习几次就会进步的！'
})

const selectAnswer = (oi: number) => {
  if (answered.value) return
  selectedAnswer.value = oi
  answered.value = true
  answers.value[currentIndex.value] = oi

  if (oi === currentQuestion.value.correct_index) {
    uni.showToast({ title: '回答正确！', icon: 'success' })
  }
}

const getOptionClass = (oi: number) => {
  if (!answered.value) return ''
  if (oi === currentQuestion.value.correct_index) return 'correct'
  if (oi === selectedAnswer.value && oi !== currentQuestion.value.correct_index) return 'wrong'
  return 'dimmed'
}

const nextQuestion = async () => {
  if (isLast.value) {
    try {
      practice.value = await submitPractice(practice.value.id, answers.value)
      step.value = 'result'
      loadHistory()
    } catch {
      step.value = 'error'
      errorMsg.value = '提交结果失败'
    }
    return
  }
  currentIndex.value++
  selectedAnswer.value = -1
  answered.value = false
}

const startPractice = async () => {
  step.value = 'loading'
  try {
    practice.value = await generateDailyPractice(subject.value)
    if (!practice.value.questions || practice.value.questions.length === 0) {
      step.value = 'error'
      errorMsg.value = '暂无错题数据，先去做作业积累错题吧'
      return
    }
    currentIndex.value = 0
    selectedAnswer.value = -1
    answered.value = false
    answers.value = []
    step.value = 'quiz'
  } catch (e) {
    step.value = 'error'
    errorMsg.value = '生成练习失败，请稍后再试'
  }
}

const retry = () => {
  startPractice()
}

const goHome = () => {
  uni.navigateBack()
}

const loadHistory = async () => {
  try {
    history.value = await getPracticeHistory()
  } catch {}
}

startPractice()
</script>

<style scoped>
.container {
  padding: 30rpx;
  min-height: 100vh;
  background: #EEF2FF;
}

/* Loading */
.loading-section {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding-top: 200rpx;
}

.loading-icon {
  font-size: 120rpx;
  display: block;
  margin-bottom: 40rpx;
}

.loading-text {
  font-size: 34rpx;
  font-weight: bold;
  color: #333;
  display: block;
  margin-bottom: 16rpx;
}

.loading-hint {
  font-size: 26rpx;
  color: #999;
}

/* Quiz */
.progress-bar {
  height: 8rpx;
  background: #e0e0e0;
  border-radius: 4rpx;
  overflow: hidden;
  margin-bottom: 16rpx;
}

.progress-fill {
  height: 100%;
  background: linear-gradient(90deg, #818CF8, #4F46E5);
  border-radius: 4rpx;
  transition: width 0.3s;
}

.progress-text {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 32rpx;
  font-size: 26rpx;
  color: #999;
}

.topic-tag {
  padding: 4rpx 16rpx;
  background: #E0E7FF;
  color: #4F46E5;
  border-radius: 8rpx;
  font-size: 24rpx;
}

.question-card {
  background: #fff;
  border-radius: 24rpx;
  padding: 32rpx;
  margin-bottom: 24rpx;
  border: 2rpx solid #E0E7FF;
  box-shadow: 3rpx 3rpx 12rpx rgba(79, 70, 229, 0.06);
}

.question-text {
  font-size: 32rpx;
  color: #333;
  line-height: 1.6;
  display: block;
  margin-bottom: 28rpx;
  font-weight: bold;
}

.option-item {
  display: flex;
  align-items: center;
  padding: 20rpx 24rpx;
  margin-bottom: 16rpx;
  background: #F5F3FF;
  border-radius: 16rpx;
  position: relative;
}

.option-item.correct {
  background: #DCFCE7;
  border: 2rpx solid #16A34A;
}

.option-item.wrong {
  background: #FEE2E2;
  border: 2rpx solid #EF4444;
}

.option-item.dimmed {
  opacity: 0.5;
}

.option-letter {
  width: 48rpx;
  height: 48rpx;
  background: #4F46E5;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-right: 20rpx;
  flex-shrink: 0;
}

.option-letter text {
  color: #fff;
  font-size: 24rpx;
  font-weight: bold;
}

.option-text {
  font-size: 28rpx;
  color: #333;
  flex: 1;
  line-height: 1.4;
}

.option-check {
  color: #16A34A;
  font-size: 32rpx;
  font-weight: bold;
  margin-left: 12rpx;
}

.option-cross {
  color: #EF4444;
  font-size: 32rpx;
  font-weight: bold;
  margin-left: 12rpx;
}

.explanation-card {
  background: #fff;
  border-radius: 16rpx;
  padding: 24rpx;
  margin-bottom: 24rpx;
  border-left: 6rpx solid #818CF8;
}

.explanation-label {
  font-size: 24rpx;
  color: #4F46E5;
  font-weight: bold;
  display: block;
  margin-bottom: 8rpx;
}

.explanation-text {
  font-size: 26rpx;
  color: #666;
  line-height: 1.5;
}

.next-btn {
  background: linear-gradient(135deg, #818CF8, #4F46E5);
  text-align: center;
  padding: 28rpx 0;
  border-radius: 16rpx;
  margin-top: 16rpx;
}

.next-btn-text {
  color: #fff;
  font-size: 32rpx;
  font-weight: bold;
}

/* Result */
.result-section {
  padding-top: 60rpx;
}

.result-header {
  text-align: center;
  margin-bottom: 40rpx;
}

.result-icon {
  font-size: 120rpx;
  display: block;
  margin-bottom: 20rpx;
}

.result-score {
  font-size: 72rpx;
  font-weight: bold;
  color: #333;
  display: block;
}

.result-label {
  font-size: 28rpx;
  color: #999;
  display: block;
  margin-top: 8rpx;
}

.result-topic {
  text-align: center;
  margin-bottom: 32rpx;
}

.result-topic-label {
  font-size: 24rpx;
  color: #999;
  display: block;
  margin-bottom: 8rpx;
}

.result-topic-name {
  font-size: 30rpx;
  color: #4F46E5;
  font-weight: bold;
  display: block;
}

.result-message {
  text-align: center;
  background: #fff;
  border-radius: 16rpx;
  padding: 28rpx;
  margin-bottom: 32rpx;
}

.result-msg-text {
  font-size: 30rpx;
  color: #333;
  line-height: 1.6;
}

.result-actions {
  display: flex;
  gap: 20rpx;
  margin-bottom: 32rpx;
}

.btn-retry {
  flex: 1;
  background: linear-gradient(135deg, #818CF8, #4F46E5);
  text-align: center;
  padding: 24rpx 0;
  border-radius: 16rpx;
}

.btn-text {
  color: #fff;
  font-size: 30rpx;
  font-weight: bold;
}

.btn-home {
  flex: 1;
  background: #fff;
  text-align: center;
  padding: 24rpx 0;
  border-radius: 16rpx;
  border: 2rpx solid #ddd;
}

.btn-text-home {
  color: #666;
  font-size: 30rpx;
}

.streak-card {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12rpx;
  background: #fff;
  border-radius: 16rpx;
  padding: 20rpx;
}

.streak-icon {
  font-size: 40rpx;
}

.streak-text {
  font-size: 28rpx;
  color: #F97316;
  font-weight: bold;
}

/* Error */
.error-section {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding-top: 200rpx;
}

.error-icon {
  font-size: 120rpx;
  display: block;
  margin-bottom: 30rpx;
}

.error-text {
  font-size: 30rpx;
  color: #666;
  display: block;
  margin-bottom: 40rpx;
  text-align: center;
  padding: 0 60rpx;
  line-height: 1.5;
}
</style>
