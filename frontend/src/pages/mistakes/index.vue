<template>
  <view class="container">
    <view class="filter-bar">
      <view class="subject-filter">
        <view
          :class="['filter-tab', { active: filterSubject === '' }]"
          @tap="filterSubject = ''"
        >
          <text>全部</text>
        </view>
        <view
          :class="['filter-tab', { active: filterSubject === 'chinese' }]"
          @tap="filterSubject = 'chinese'"
        >
          <text>语文</text>
        </view>
        <view
          :class="['filter-tab', { active: filterSubject === 'english' }]"
          @tap="filterSubject = 'english'"
        >
          <text>英语</text>
        </view>
      </view>
      <view
        :class="['review-toggle', { active: reviewDueOnly }]"
        @tap="reviewDueOnly = !reviewDueOnly"
      >
        <text>{{ reviewDueOnly ? '待复习' : '全部' }}</text>
      </view>
    </view>

    <view v-if="loading" class="loading">
      <text>加载中...</text>
    </view>

    <view v-else-if="mistakes.length === 0" class="empty">
      <text class="empty-icon">📝</text>
      <text class="empty-text">{{ reviewDueOnly ? '暂无待复习的错题' : '还没有错题哦，继续加油！' }}</text>
    </view>

    <view v-else class="mistakes-list">
      <view
        v-for="item in mistakes"
        :key="item.id"
        :class="['mistake-card', { expanded: expandedId === item.id }]"
      >
        <view class="card-header" @tap="toggleExpand(item.id)">
          <view class="card-left">
            <text :class="['subject-tag', item.subject]">
              {{ item.subject === 'chinese' ? '语文' : '英语' }}
            </text>
            <text class="question-preview">{{ truncate(item.question_text, 30) }}</text>
          </view>
          <view class="card-right">
            <view class="mastery-dots">
              <view
                v-for="n in 5"
                :key="n"
                :class="['dot', { filled: n <= item.mastery }, `level-${item.mastery}`]"
              />
            </view>
            <text class="expand-icon">{{ expandedId === item.id ? '▼' : '▶' }}</text>
          </view>
        </view>

        <view v-if="expandedId === item.id" class="card-detail">
          <view class="detail-section">
            <text class="detail-label">题目</text>
            <text class="detail-text">{{ item.question_text }}</text>
          </view>

          <view class="detail-section">
            <text class="detail-label">你的答案</text>
            <text class="detail-text wrong-text">{{ item.student_answer }}</text>
          </view>

          <view class="detail-section">
            <text class="detail-label">正确答案</text>
            <text class="detail-text correct-text">{{ item.correct_answer }}</text>
          </view>

          <view v-if="item.explanation" class="detail-section explanation">
            <text class="detail-label">讲解</text>
            <text class="detail-text">{{ item.explanation }}</text>
          </view>

          <view v-if="item.topic" class="detail-section">
            <text class="topic-tag">{{ item.topic }}</text>
          </view>

          <view class="review-section">
            <text class="review-hint">现在你还能答对吗？</text>
            <view class="review-buttons">
              <view class="btn-review wrong-btn" @tap="doReview(item.id, false)">
                <text>还不会</text>
              </view>
              <view class="btn-review correct-btn" @tap="doReview(item.id, true)">
                <text>会了！</text>
              </view>
            </view>
          </view>
        </view>
      </view>

      <view v-if="hasMore" class="load-more" @tap="loadMore">
        <text>加载更多</text>
      </view>
    </view>
  </view>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import { getMistakes, reviewMistake, type MistakeItem } from '@/api/mistakes'
import { getUserId } from '@/utils/user'

const filterSubject = ref('')
const reviewDueOnly = ref(false)
const mistakes = ref<MistakeItem[]>([])
const expandedId = ref<number | null>(null)
const loading = ref(false)
const page = ref(1)
const total = ref(0)
const hasMore = ref(false)

getUserId()

const pageSize = 20

const truncate = (text: string, max: number) => {
  return text.length > max ? text.slice(0, max) + '...' : text
}

const fetchMistakes = async () => {
  loading.value = true
  try {
    const res = await getMistakes({
      subject: filterSubject.value || undefined,
      review_due: reviewDueOnly.value || undefined,
      page: page.value,
      size: pageSize,
    })
    if (page.value === 1) {
      mistakes.value = res.items
    } else {
      mistakes.value.push(...res.items)
    }
    total.value = res.total
    hasMore.value = mistakes.value.length < total.value
  } catch {
    uni.showToast({ title: '加载失败', icon: 'none' })
  } finally {
    loading.value = false
  }
}

const loadMore = () => {
  page.value++
  fetchMistakes()
}

const toggleExpand = (id: number) => {
  expandedId.value = expandedId.value === id ? null : id
}

const doReview = async (id: number, correct: boolean) => {
  try {
    await reviewMistake(id, correct)
    uni.showToast({
      title: correct ? '太棒了！继续加油！' : '没关系，多复习几次就会了',
      icon: 'none',
    })
    page.value = 1
    expandedId.value = null
    await fetchMistakes()
  } catch {
    uni.showToast({ title: '操作失败', icon: 'none' })
  }
}

watch([filterSubject, reviewDueOnly], () => {
  page.value = 1
  expandedId.value = null
  fetchMistakes()
})

fetchMistakes()
</script>

<style scoped>
.container {
  padding: 30rpx;
  min-height: 100vh;
  background: #f5f5f5;
}

.filter-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24rpx;
}

.subject-filter {
  display: flex;
  background: #fff;
  border-radius: 16rpx;
  overflow: hidden;
}

.filter-tab {
  padding: 18rpx 32rpx;
  font-size: 28rpx;
  color: #666;
}

.filter-tab.active {
  background: #4A90D9;
  color: #fff;
  font-weight: bold;
}

.review-toggle {
  padding: 18rpx 28rpx;
  background: #fff;
  border-radius: 16rpx;
  font-size: 26rpx;
  color: #666;
}

.review-toggle.active {
  background: #FF8E53;
  color: #fff;
  font-weight: bold;
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

.mistakes-list {
  padding-bottom: 40rpx;
}

.mistake-card {
  background: #fff;
  border-radius: 16rpx;
  margin-bottom: 16rpx;
  overflow: hidden;
  box-shadow: 0 2rpx 8rpx rgba(0, 0, 0, 0.04);
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 24rpx 28rpx;
}

.card-left {
  display: flex;
  align-items: center;
  gap: 16rpx;
  flex: 1;
  overflow: hidden;
}

.subject-tag {
  padding: 6rpx 16rpx;
  border-radius: 8rpx;
  font-size: 22rpx;
  color: #fff;
  flex-shrink: 0;
}

.subject-tag.chinese {
  background: #FF6B6B;
}

.subject-tag.english {
  background: #4A90D9;
}

.question-preview {
  font-size: 28rpx;
  color: #333;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.card-right {
  display: flex;
  align-items: center;
  gap: 16rpx;
  flex-shrink: 0;
}

.mastery-dots {
  display: flex;
  gap: 6rpx;
}

.dot {
  width: 16rpx;
  height: 16rpx;
  border-radius: 50%;
  background: #e0e0e0;
}

.dot.filled {
  background: #FF6B6B;
}

.dot.level-1 { background: #FF8E53; }
.dot.level-2 { background: #FFB74D; }
.dot.level-3 { background: #FFD54F; }
.dot.level-4,
.dot.level-5 { background: #4CAF50; }

.expand-icon {
  font-size: 22rpx;
  color: #999;
}

.card-detail {
  padding: 0 28rpx 24rpx;
  border-top: 1rpx solid #f0f0f0;
}

.detail-section {
  padding: 16rpx 0;
}

.detail-label {
  font-size: 24rpx;
  color: #999;
  display: block;
  margin-bottom: 6rpx;
}

.detail-text {
  font-size: 28rpx;
  color: #333;
  line-height: 1.5;
}

.wrong-text {
  color: #FF6B6B;
}

.correct-text {
  color: #4CAF50;
  font-weight: bold;
}

.explanation {
  background: #f8f9fa;
  border-radius: 12rpx;
  padding: 16rpx 20rpx;
}

.topic-tag {
  display: inline-block;
  padding: 4rpx 16rpx;
  background: #e3f2fd;
  color: #4A90D9;
  border-radius: 8rpx;
  font-size: 24rpx;
}

.review-section {
  margin-top: 20rpx;
  padding-top: 20rpx;
  border-top: 1rpx solid #f0f0f0;
  text-align: center;
}

.review-hint {
  font-size: 26rpx;
  color: #999;
  display: block;
  margin-bottom: 16rpx;
}

.review-buttons {
  display: flex;
  gap: 20rpx;
}

.btn-review {
  flex: 1;
  text-align: center;
  padding: 20rpx 0;
  border-radius: 16rpx;
  font-size: 28rpx;
  font-weight: bold;
}

.wrong-btn {
  background: #fff;
  color: #FF6B6B;
  border: 2rpx solid #FF6B6B;
}

.correct-btn {
  background: #4CAF50;
  color: #fff;
}

.load-more {
  text-align: center;
  padding: 24rpx;
  font-size: 28rpx;
  color: #4A90D9;
}
</style>
