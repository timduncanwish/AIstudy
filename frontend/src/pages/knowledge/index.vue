<template>
  <view class="container">
    <view v-if="loading" class="loading">
      <text>加载中...</text>
    </view>

    <view v-else-if="isEmpty" class="empty">
      <text class="empty-icon">📚</text>
      <text class="empty-text">还没有知识沉淀，快去做作业积累错题吧！</text>
    </view>

    <view v-else>
      <view class="subject-tabs">
        <view
          :class="['subject-tab', { active: currentSubject === '' }]"
          @tap="currentSubject = ''"
        >
          <text>全部</text>
        </view>
        <view
          v-for="(topics, subj) in knowledgeMap.subjects"
          :key="subj"
          :class="['subject-tab', { active: currentSubject === subj }]"
          @tap="currentSubject = subj"
        >
          <text>{{ subj === 'chinese' ? '语文' : '英语' }}</text>
        </view>
      </view>

      <view class="overview-bar">
        <view class="overview-item">
          <text class="overview-number">{{ totalTopics }}</text>
          <text class="overview-label">知识点</text>
        </view>
        <view class="overview-item">
          <text class="overview-number weak">{{ weakCount }}</text>
          <text class="overview-label">待加强</text>
        </view>
        <view class="overview-item">
          <text class="overview-number mastered">{{ masteredCount }}</text>
          <text class="overview-label">已掌握</text>
        </view>
      </view>

      <view class="topic-list">
        <view
          v-for="item in filteredTopics"
          :key="item.topic"
          class="topic-card"
          @tap="openTopic(item)"
        >
          <view class="topic-header">
            <text class="topic-name">{{ item.topic }}</text>
            <view :class="['mastery-badge', masteryLevel(item.avg_mastery)]">
              <text class="mastery-badge-text">{{ masteryLabel(item.avg_mastery) }}</text>
            </view>
          </view>
          <view class="topic-meta">
            <text class="topic-count">{{ item.count }} 道错题</text>
            <view class="mastery-bar">
              <view class="mastery-bar-fill" :style="{ width: (item.avg_mastery / 5 * 100) + '%', background: masteryColor(item.avg_mastery) }" />
            </view>
            <text class="mastery-text">{{ item.avg_mastery }}/5</text>
          </view>
        </view>
      </view>
    </view>

    <!-- 知识点详情弹窗 -->
    <view v-if="showDetail" class="modal-mask" @tap="showDetail = false">
      <view class="modal-content" @tap.stop>
        <view class="modal-header">
          <text class="modal-title">{{ detailData?.topic }}</text>
          <text class="modal-close" @tap="showDetail = false">✕</text>
        </view>
        <view class="modal-meta">
          <text :class="['modal-subject', detailData?.subject]">
            {{ detailData?.subject === 'chinese' ? '语文' : '英语' }}
          </text>
          <text class="modal-count">{{ detailData?.count }} 道错题</text>
          <view class="mastery-bar modal-bar">
            <view class="mastery-bar-fill" :style="{ width: (detailData!.avg_mastery / 5 * 100) + '%', background: masteryColor(detailData!.avg_mastery) }" />
          </view>
          <text class="mastery-text">{{ detailData?.avg_mastery }}/5</text>
        </view>
        <scroll-view class="modal-body" scroll-y>
          <view v-for="m in detailData?.mistakes" :key="m.id" class="detail-mistake">
            <text class="dm-question">{{ m.question_text }}</text>
            <view class="dm-answers">
              <text class="dm-wrong">{{ m.student_answer }}</text>
              <text class="dm-arrow">→</text>
              <text class="dm-correct">{{ m.correct_answer }}</text>
            </view>
            <view class="dm-mastery">
              <text class="dm-mastery-label">掌握度</text>
              <view class="dm-dots">
                <view v-for="n in 5" :key="n" :class="['dm-dot', { filled: n <= m.mastery }]" />
              </view>
            </view>
          </view>
        </scroll-view>
        <view class="modal-footer">
          <view class="btn-practice" @tap="startPractice">
            <text class="btn-practice-text">{{ practiceLoading ? '生成中...' : 'AI 针对练习' }}</text>
          </view>
        </view>
      </view>
    </view>

    <!-- 练习弹窗 -->
    <view v-if="showPractice" class="modal-mask" @tap="showPractice = false">
      <view class="modal-content practice-modal" @tap.stop>
        <view class="modal-header">
          <text class="modal-title">练习 - {{ practiceData?.topic }}</text>
          <text class="modal-close" @tap="showPractice = false">✕</text>
        </view>
        <scroll-view class="modal-body" scroll-y>
          <view v-for="(q, qi) in practiceData?.questions" :key="qi" class="practice-q">
            <text class="pq-number">第{{ qi + 1 }}题</text>
            <text class="pq-text">{{ q.question }}</text>
            <view
              v-for="(opt, oi) in q.options"
              :key="oi"
              :class="['pq-option', getOptionClass(qi, oi, q.correct_index)]"
              @tap="selectAnswer(qi, oi, q.correct_index)"
            >
              <text>{{ ['A', 'B', 'C', 'D'][oi] }}. {{ opt }}</text>
            </view>
            <view v-if="answered[qi]" class="pq-explanation">
              <text>{{ q.explanation }}</text>
            </view>
          </view>
        </scroll-view>
      </view>
    </view>
  </view>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import {
  getKnowledgeMap, getTopicDetail, generatePractice,
  type KnowledgeTopic, type KnowledgeMapResponse,
  type TopicDetailResponse, type PracticeResponse,
} from '@/api/knowledge'

const loading = ref(true)
const knowledgeMap = ref<KnowledgeMapResponse>({ subjects: {} })
const currentSubject = ref('')
const showDetail = ref(false)
const showPractice = ref(false)
const detailData = ref<TopicDetailResponse | null>(null)
const practiceData = ref<PracticeResponse | null>(null)
const practiceLoading = ref(false)
const answered = ref<Record<number, number>>({})

const isEmpty = computed(() => {
  const s = knowledgeMap.value.subjects
  return Object.keys(s).length === 0
})

const totalTopics = computed(() => {
  let n = 0
  for (const topics of Object.values(knowledgeMap.value.subjects)) n += topics.length
  return n
})

const weakCount = computed(() => {
  let n = 0
  for (const topics of Object.values(knowledgeMap.value.subjects)) {
    for (const t of topics) if (t.avg_mastery <= 2) n++
  }
  return n
})

const masteredCount = computed(() => {
  let n = 0
  for (const topics of Object.values(knowledgeMap.value.subjects)) {
    for (const t of topics) if (t.avg_mastery >= 4) n++
  }
  return n
})

const filteredTopics = computed(() => {
  if (!currentSubject.value) {
    const all: KnowledgeTopic[] = []
    for (const topics of Object.values(knowledgeMap.value.subjects)) all.push(...topics)
    return all.sort((a, b) => a.avg_mastery - b.avg_mastery)
  }
  return (knowledgeMap.value.subjects[currentSubject.value] || []).sort(
    (a, b) => a.avg_mastery - b.avg_mastery
  )
})

const masteryLevel = (m: number) => {
  if (m <= 1) return 'level-weak'
  if (m <= 3) return 'level-medium'
  return 'level-good'
}

const masteryLabel = (m: number) => {
  if (m <= 1) return '薄弱'
  if (m <= 3) return '学习中'
  return '已掌握'
}

const masteryColor = (m: number) => {
  if (m <= 1) return '#FF6B6B'
  if (m <= 2) return '#FF8E53'
  if (m <= 3) return '#FFB74D'
  if (m <= 4) return '#FFD54F'
  return '#4CAF50'
}

const openTopic = async (item: KnowledgeTopic) => {
  try {
    detailData.value = await getTopicDetail(item.subject, item.topic)
    showDetail.value = true
  } catch {
    uni.showToast({ title: '加载失败', icon: 'none' })
  }
}

const startPractice = async () => {
  if (!detailData.value || practiceLoading.value) return
  practiceLoading.value = true
  try {
    practiceData.value = await generatePractice(detailData.value.subject, detailData.value.topic)
    answered.value = {}
    showPractice.value = true
  } catch {
    uni.showToast({ title: '生成练习失败', icon: 'none' })
  } finally {
    practiceLoading.value = false
  }
}

const selectAnswer = (qi: number, oi: number, correct: number) => {
  if (answered.value[qi] !== undefined) return
  answered.value = { ...answered.value, [qi]: oi }
  if (oi === correct) {
    uni.showToast({ title: '回答正确！', icon: 'success' })
  } else {
    uni.showToast({ title: '再想想哦', icon: 'none' })
  }
}

const getOptionClass = (qi: number, oi: number, correct: number) => {
  const a = answered.value[qi]
  if (a === undefined) return ''
  if (oi === correct) return 'correct'
  if (oi === a && a !== correct) return 'wrong'
  return 'dimmed'
}

const fetchKnowledgeMap = async () => {
  loading.value = true
  try {
    knowledgeMap.value = await getKnowledgeMap()
  } catch {
    uni.showToast({ title: '加载失败', icon: 'none' })
  } finally {
    loading.value = false
  }
}

fetchKnowledgeMap()
</script>

<style scoped>
.container {
  padding: 30rpx;
  min-height: 100vh;
  background: #f5f5f5;
}

.loading {
  text-align: center;
  padding: 100rpx 0;
  font-size: 28rpx;
  color: #999;
}

.empty {
  text-align: center;
  padding: 120rpx 0;
}

.empty-icon {
  font-size: 100rpx;
  display: block;
  margin-bottom: 20rpx;
}

.empty-text {
  font-size: 28rpx;
  color: #999;
}

.subject-tabs {
  display: flex;
  background: #fff;
  border-radius: 16rpx;
  overflow: hidden;
  margin-bottom: 24rpx;
}

.subject-tab {
  flex: 1;
  text-align: center;
  padding: 20rpx 0;
  font-size: 28rpx;
  color: #666;
}

.subject-tab.active {
  background: #4A90D9;
  color: #fff;
  font-weight: bold;
}

.overview-bar {
  display: flex;
  background: #fff;
  border-radius: 16rpx;
  padding: 24rpx;
  margin-bottom: 24rpx;
  box-shadow: 0 2rpx 8rpx rgba(0, 0, 0, 0.04);
}

.overview-item {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
}

.overview-number {
  font-size: 44rpx;
  font-weight: bold;
  color: #333;
}

.overview-number.weak {
  color: #FF6B6B;
}

.overview-number.mastered {
  color: #4CAF50;
}

.overview-label {
  font-size: 22rpx;
  color: #999;
  margin-top: 4rpx;
}

.topic-list {
  padding-bottom: 40rpx;
}

.topic-card {
  background: #fff;
  border-radius: 16rpx;
  padding: 24rpx 28rpx;
  margin-bottom: 16rpx;
  box-shadow: 0 2rpx 8rpx rgba(0, 0, 0, 0.04);
}

.topic-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16rpx;
}

.topic-name {
  font-size: 30rpx;
  font-weight: bold;
  color: #333;
  flex: 1;
}

.mastery-badge {
  padding: 4rpx 16rpx;
  border-radius: 16rpx;
  font-size: 22rpx;
}

.mastery-badge.level-weak {
  background: #ffebee;
}

.mastery-badge.level-weak .mastery-badge-text {
  color: #FF6B6B;
}

.mastery-badge.level-medium {
  background: #fff3e0;
}

.mastery-badge.level-medium .mastery-badge-text {
  color: #FF8E53;
}

.mastery-badge.level-good {
  background: #e8f5e9;
}

.mastery-badge.level-good .mastery-badge-text {
  color: #4CAF50;
}

.topic-meta {
  display: flex;
  align-items: center;
  gap: 16rpx;
}

.topic-count {
  font-size: 24rpx;
  color: #999;
  flex-shrink: 0;
}

.mastery-bar {
  flex: 1;
  height: 12rpx;
  background: #e0e0e0;
  border-radius: 6rpx;
  overflow: hidden;
}

.mastery-bar-fill {
  height: 100%;
  border-radius: 6rpx;
  transition: width 0.3s;
}

.mastery-text {
  font-size: 22rpx;
  color: #999;
  flex-shrink: 0;
  width: 60rpx;
  text-align: right;
}

/* Modal */
.modal-mask {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: flex-end;
  z-index: 1000;
}

.modal-content {
  width: 100%;
  max-height: 80vh;
  background: #fff;
  border-radius: 32rpx 32rpx 0 0;
  display: flex;
  flex-direction: column;
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 28rpx 32rpx;
  border-bottom: 1rpx solid #f0f0f0;
}

.modal-title {
  font-size: 32rpx;
  font-weight: bold;
  color: #333;
}

.modal-close {
  font-size: 36rpx;
  color: #999;
  padding: 8rpx;
}

.modal-meta {
  display: flex;
  align-items: center;
  gap: 16rpx;
  padding: 16rpx 32rpx;
  border-bottom: 1rpx solid #f0f0f0;
}

.modal-subject {
  padding: 4rpx 16rpx;
  border-radius: 8rpx;
  font-size: 22rpx;
  color: #fff;
}

.modal-subject.chinese {
  background: #FF6B6B;
}

.modal-subject.english {
  background: #4A90D9;
}

.modal-count {
  font-size: 24rpx;
  color: #999;
}

.modal-bar {
  width: 120rpx;
}

.modal-body {
  flex: 1;
  padding: 20rpx 32rpx;
  max-height: 50vh;
}

.detail-mistake {
  padding: 20rpx 0;
  border-bottom: 1rpx solid #f0f0f0;
}

.detail-mistake:last-child {
  border-bottom: none;
}

.dm-question {
  font-size: 28rpx;
  color: #333;
  display: block;
  margin-bottom: 12rpx;
  line-height: 1.5;
}

.dm-answers {
  display: flex;
  align-items: center;
  gap: 12rpx;
  margin-bottom: 12rpx;
}

.dm-wrong {
  font-size: 26rpx;
  color: #FF6B6B;
}

.dm-arrow {
  color: #999;
  font-size: 24rpx;
}

.dm-correct {
  font-size: 26rpx;
  color: #4CAF50;
  font-weight: bold;
}

.dm-mastery {
  display: flex;
  align-items: center;
  gap: 12rpx;
}

.dm-mastery-label {
  font-size: 22rpx;
  color: #999;
}

.dm-dots {
  display: flex;
  gap: 6rpx;
}

.dm-dot {
  width: 14rpx;
  height: 14rpx;
  border-radius: 50%;
  background: #e0e0e0;
}

.dm-dot.filled {
  background: #4CAF50;
}

.modal-footer {
  padding: 20rpx 32rpx;
  border-top: 1rpx solid #f0f0f0;
  padding-bottom: calc(20rpx + env(safe-area-inset-bottom));
}

.btn-practice {
  background: linear-gradient(135deg, #4A90D9, #357ABD);
  text-align: center;
  padding: 24rpx 0;
  border-radius: 16rpx;
}

.btn-practice-text {
  color: #fff;
  font-size: 30rpx;
  font-weight: bold;
}

/* Practice modal */
.practice-modal {
  max-height: 85vh;
}

.practice-q {
  padding: 20rpx 0;
  border-bottom: 1rpx solid #f0f0f0;
}

.practice-q:last-child {
  border-bottom: none;
}

.pq-number {
  font-size: 22rpx;
  color: #4A90D9;
  font-weight: bold;
  display: block;
  margin-bottom: 8rpx;
}

.pq-text {
  font-size: 28rpx;
  color: #333;
  display: block;
  margin-bottom: 16rpx;
  line-height: 1.5;
}

.pq-option {
  padding: 16rpx 20rpx;
  margin-bottom: 10rpx;
  background: #f5f5f5;
  border-radius: 12rpx;
  font-size: 26rpx;
  color: #333;
}

.pq-option.correct {
  background: #e8f5e9;
  color: #4CAF50;
  font-weight: bold;
}

.pq-option.wrong {
  background: #ffebee;
  color: #FF6B6B;
}

.pq-option.dimmed {
  opacity: 0.5;
}

.pq-explanation {
  margin-top: 12rpx;
  padding: 16rpx 20rpx;
  background: #f8f9fa;
  border-radius: 12rpx;
  font-size: 24rpx;
  color: #666;
  line-height: 1.5;
}
</style>
