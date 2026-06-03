<template>
  <view class="container">
    <!-- 上传态 -->
    <view v-if="state === 'upload'" class="upload-section">
      <view class="subject-tabs">
        <view
          :class="['tab', { active: subject === 'chinese' }]"
          @tap="subject = 'chinese'"
        >
          <text>语文</text>
        </view>
        <view
          :class="['tab', { active: subject === 'english' }]"
          @tap="subject = 'english'"
        >
          <text>英语</text>
        </view>
      </view>

      <view class="upload-area" @tap="chooseImage">
        <text class="upload-icon">📸</text>
        <text class="upload-text">拍照上传作业</text>
        <text class="upload-hint">支持拍照或从相册选择</text>
      </view>

      <view v-if="previewUrl" class="preview-section">
        <image :src="previewUrl" class="preview-image" mode="aspectFit" />
        <view class="preview-actions">
          <view class="btn-rechoose" @tap="chooseImage">
            <text>重新选择</text>
          </view>
          <view class="btn-submit" @tap="submitHomework">
            <text>开始批改</text>
          </view>
        </view>
      </view>
    </view>

    <!-- 批改中 -->
    <view v-if="state === 'grading'" class="grading-section">
      <view class="loading-card">
        <view class="loading-spinner" />
        <text class="loading-text">AI 正在批改中...</text>
        <text class="loading-hint">大约需要 10-20 秒</text>
        <image v-if="previewUrl" :src="previewUrl" class="grading-preview" mode="aspectFit" />
      </view>
    </view>

    <!-- 结果态 -->
    <view v-if="state === 'result'" class="result-section">
      <view class="score-card">
        <text class="score-label">批改结果</text>
        <text v-if="result.score !== null" class="score-number">{{ result.score }}</text>
        <text class="score-unit">分</text>
      </view>

      <view class="encouragement-card">
        <text class="encouragement-text">{{ result.encouragement }}</text>
      </view>

      <view class="summary-card">
        <text class="summary-text">{{ result.summary }}</text>
      </view>

      <view class="questions-list">
        <view
          v-for="(q, idx) in result.questions"
          :key="idx"
          :class="['question-card', q.is_correct ? 'correct' : 'wrong']"
        >
          <view class="question-header" @tap="toggleQuestion(idx)">
            <view class="question-left">
              <text :class="['question-badge', q.is_correct ? 'badge-correct' : 'badge-wrong']">
                {{ q.is_correct ? '✓' : '✗' }}
              </text>
              <text class="question-num">第{{ q.question_number }}题</text>
            </view>
            <text class="question-toggle">{{ expandedQuestions.includes(idx) ? '▼' : '▶' }}</text>
          </view>

          <view v-if="expandedQuestions.includes(idx)" class="question-detail">
            <view class="detail-row">
              <text class="detail-label">题目：</text>
              <text class="detail-content">{{ q.question_text }}</text>
            </view>
            <view class="detail-row">
              <text class="detail-label">你的答案：</text>
              <text class="detail-content">{{ q.student_answer }}</text>
            </view>
            <view v-if="!q.is_correct" class="detail-row">
              <text class="detail-label">正确答案：</text>
              <text class="detail-content correct-answer">{{ q.correct_answer }}</text>
            </view>
            <view v-if="q.explanation" class="detail-row explanation-row">
              <text class="detail-label">讲解：</text>
              <text class="detail-content">{{ q.explanation }}</text>
            </view>
          </view>
        </view>
      </view>

      <view class="result-actions">
        <view class="btn-mistakes" @tap="goToMistakes">
          <text>查看错题本 ({{ result.mistake_count }})</text>
        </view>
        <view class="btn-reupload" @tap="resetPage">
          <text>再拍一份</text>
        </view>
      </view>
    </view>
  </view>
</template>

<script setup lang="ts">
import { ref, reactive } from 'vue'
import { uploadHomework, type HomeworkUploadResponse, type QuestionResult } from '@/api/homework'
import { getUserId } from '@/utils/user'

const props = defineProps<{
  subject?: string
  grade?: number
}>()

const subject = ref(props.subject || 'chinese')
const grade = ref(props.grade || 3)
const state = ref<'upload' | 'grading' | 'result'>('upload')
const previewUrl = ref('')
const filePath = ref('')
const expandedQuestions = ref<number[]>([])

const result = reactive<{
  homework_id: number
  questions: QuestionResult[]
  summary: string
  score: number | null
  encouragement: string
  mistake_count: number
}>({
  homework_id: 0,
  questions: [],
  summary: '',
  score: null,
  encouragement: '',
  mistake_count: 0,
})

const chooseImage = () => {
  uni.chooseImage({
    count: 1,
    sourceType: ['camera', 'album'],
    success: (res) => {
      const tempPath = res.tempFilePaths[0]
      previewUrl.value = tempPath
      filePath.value = tempPath
    },
  })
}

const submitHomework = async () => {
  if (!filePath.value) return

  getUserId()
  state.value = 'grading'

  try {
    uni.compressImage({
      src: filePath.value,
      quality: 80,
      success: async (compressRes) => {
        try {
          const res = await uploadHomework({
            filePath: compressRes.tempFilePath,
            subject: subject.value,
            grade: grade.value,
          })
          Object.assign(result, res)
          state.value = 'result'
        } catch {
          showError()
        }
      },
      fail: async () => {
        try {
          const res = await uploadHomework({
            filePath: filePath.value,
            subject: subject.value,
            grade: grade.value,
          })
          Object.assign(result, res)
          state.value = 'result'
        } catch {
          showError()
        }
      },
    })
  } catch {
    showError()
  }
}

const showError = () => {
  state.value = 'upload'
  uni.showToast({ title: '批改失败，请重试', icon: 'none' })
}

const toggleQuestion = (idx: number) => {
  const pos = expandedQuestions.value.indexOf(idx)
  if (pos >= 0) {
    expandedQuestions.value.splice(pos, 1)
  } else {
    expandedQuestions.value.push(idx)
  }
}

const goToMistakes = () => {
  uni.navigateTo({ url: '/pages/mistakes/index' })
}

const resetPage = () => {
  state.value = 'upload'
  previewUrl.value = ''
  filePath.value = ''
  expandedQuestions.value = []
  result.questions = []
  result.summary = ''
  result.score = null
  result.encouragement = ''
  result.mistake_count = 0
}
</script>

<style scoped>
.container {
  padding: 30rpx;
  min-height: 100vh;
  background: #f5f5f5;
}

.subject-tabs {
  display: flex;
  margin-bottom: 30rpx;
  background: #fff;
  border-radius: 16rpx;
  overflow: hidden;
}

.tab {
  flex: 1;
  text-align: center;
  padding: 24rpx 0;
  font-size: 30rpx;
  color: #666;
}

.tab.active {
  color: #fff;
  background: #4A90D9;
  font-weight: bold;
}

.upload-area {
  background: #fff;
  border-radius: 20rpx;
  padding: 80rpx 40rpx;
  text-align: center;
  box-shadow: 0 4rpx 16rpx rgba(0, 0, 0, 0.06);
}

.upload-icon {
  font-size: 120rpx;
  display: block;
  margin-bottom: 20rpx;
}

.upload-text {
  font-size: 36rpx;
  font-weight: bold;
  color: #333;
  display: block;
  margin-bottom: 12rpx;
}

.upload-hint {
  font-size: 26rpx;
  color: #999;
  display: block;
}

.preview-section {
  margin-top: 30rpx;
}

.preview-image {
  width: 100%;
  max-height: 500rpx;
  border-radius: 16rpx;
  background: #fff;
}

.preview-actions {
  display: flex;
  margin-top: 24rpx;
  gap: 20rpx;
}

.btn-rechoose {
  flex: 1;
  text-align: center;
  padding: 24rpx 0;
  background: #fff;
  border-radius: 16rpx;
  font-size: 30rpx;
  color: #666;
  box-shadow: 0 2rpx 8rpx rgba(0, 0, 0, 0.06);
}

.btn-submit {
  flex: 1;
  text-align: center;
  padding: 24rpx 0;
  background: linear-gradient(135deg, #4A90D9, #67B8DE);
  border-radius: 16rpx;
  font-size: 30rpx;
  color: #fff;
  font-weight: bold;
}

.grading-section {
  padding-top: 100rpx;
}

.loading-card {
  background: #fff;
  border-radius: 20rpx;
  padding: 60rpx 40rpx;
  text-align: center;
}

.loading-spinner {
  width: 80rpx;
  height: 80rpx;
  border: 6rpx solid #e0e0e0;
  border-top-color: #4A90D9;
  border-radius: 50%;
  margin: 0 auto 30rpx;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.loading-text {
  font-size: 34rpx;
  font-weight: bold;
  color: #333;
  display: block;
  margin-bottom: 12rpx;
}

.loading-hint {
  font-size: 26rpx;
  color: #999;
  display: block;
  margin-bottom: 30rpx;
}

.grading-preview {
  width: 100%;
  max-height: 300rpx;
  border-radius: 12rpx;
}

.result-section {
  padding-bottom: 40rpx;
}

.score-card {
  background: linear-gradient(135deg, #4A90D9, #67B8DE);
  border-radius: 20rpx;
  padding: 40rpx;
  text-align: center;
  margin-bottom: 24rpx;
}

.score-label {
  font-size: 28rpx;
  color: rgba(255, 255, 255, 0.85);
  display: block;
  margin-bottom: 10rpx;
}

.score-number {
  font-size: 80rpx;
  font-weight: bold;
  color: #fff;
}

.score-unit {
  font-size: 32rpx;
  color: rgba(255, 255, 255, 0.85);
  margin-left: 8rpx;
}

.encouragement-card {
  background: linear-gradient(135deg, #FF8E53, #FF6B6B);
  border-radius: 16rpx;
  padding: 30rpx;
  margin-bottom: 24rpx;
}

.encouragement-text {
  font-size: 30rpx;
  color: #fff;
  line-height: 1.6;
}

.summary-card {
  background: #fff;
  border-radius: 16rpx;
  padding: 30rpx;
  margin-bottom: 24rpx;
}

.summary-text {
  font-size: 28rpx;
  color: #555;
  line-height: 1.6;
}

.questions-list {
  margin-bottom: 30rpx;
}

.question-card {
  background: #fff;
  border-radius: 16rpx;
  margin-bottom: 16rpx;
  overflow: hidden;
}

.question-card.wrong {
  border-left: 6rpx solid #FF6B6B;
}

.question-card.correct {
  border-left: 6rpx solid #4CAF50;
}

.question-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 24rpx 30rpx;
}

.question-left {
  display: flex;
  align-items: center;
  gap: 16rpx;
}

.question-badge {
  width: 44rpx;
  height: 44rpx;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 28rpx;
  color: #fff;
}

.badge-correct {
  background: #4CAF50;
}

.badge-wrong {
  background: #FF6B6B;
}

.question-num {
  font-size: 30rpx;
  font-weight: bold;
  color: #333;
}

.question-toggle {
  font-size: 24rpx;
  color: #999;
}

.question-detail {
  padding: 0 30rpx 24rpx;
  border-top: 1rpx solid #f0f0f0;
}

.detail-row {
  padding: 16rpx 0;
}

.detail-label {
  font-size: 26rpx;
  color: #999;
  display: block;
  margin-bottom: 6rpx;
}

.detail-content {
  font-size: 28rpx;
  color: #333;
  line-height: 1.5;
}

.correct-answer {
  color: #4CAF50;
  font-weight: bold;
}

.explanation-row {
  background: #f8f9fa;
  border-radius: 12rpx;
  padding: 16rpx 20rpx;
  margin-top: 8rpx;
}

.result-actions {
  display: flex;
  gap: 20rpx;
}

.btn-mistakes {
  flex: 1;
  text-align: center;
  padding: 26rpx 0;
  background: linear-gradient(135deg, #FF6B6B, #FF8E53);
  border-radius: 16rpx;
  font-size: 30rpx;
  color: #fff;
  font-weight: bold;
}

.btn-reupload {
  flex: 1;
  text-align: center;
  padding: 26rpx 0;
  background: #fff;
  border-radius: 16rpx;
  font-size: 30rpx;
  color: #666;
  box-shadow: 0 2rpx 8rpx rgba(0, 0, 0, 0.06);
}
</style>
