<template>
  <view class="container">
    <view v-if="stats" class="stats-card">
      <view class="stats-title-row">
        <text class="stats-title">知识掌握概览</text>
        <text class="stats-total">共 {{ stats.total_mistakes }} 题</text>
      </view>
      <view class="stats-row">
        <view class="stat-item">
          <view class="stat-ring new-ring">
            <text class="stat-number">{{ stats.new_count }}</text>
          </view>
          <text class="stat-label">新错题</text>
        </view>
        <view class="stat-item">
          <view class="stat-ring reviewing-ring">
            <text class="stat-number">{{ stats.reviewing_count }}</text>
          </view>
          <text class="stat-label">复习中</text>
        </view>
        <view class="stat-item">
          <view class="stat-ring mastered-ring">
            <text class="stat-number">{{ stats.mastered_count }}</text>
          </view>
          <text class="stat-label">已掌握</text>
        </view>
      </view>
      <view v-if="stats.topics.length > 0" class="topics-row">
        <text class="topics-label">薄弱知识点</text>
        <view class="topic-tags">
          <view
            v-for="t in stats.topics.slice(0, 6)"
            :key="t.topic"
            :class="['topic-chip', { active: filterTopic === t.topic }]"
            @tap="toggleTopic(t.topic)"
          >
            <text class="topic-chip-text">{{ t.topic }}</text>
            <text class="topic-chip-count">{{ t.count }}</text>
          </view>
        </view>
      </view>
    </view>

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
      <view class="typing-dots">
        <view class="dot-anim" />
        <view class="dot-anim" />
        <view class="dot-anim" />
      </view>
    </view>

    <view v-else-if="mistakes.length === 0" class="empty">
      <view class="empty-circle">
        <text class="empty-icon-text">无</text>
      </view>
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
            <view :class="['subject-dot', item.subject]" />
            <text class="question-preview">{{ truncate(item.question_text, 30) }}</text>
          </view>
          <view class="card-right">
            <view class="mastery-bar-mini">
              <view class="mastery-bar-fill" :style="{ width: (item.mastery / 5 * 100) + '%', background: masteryColor(item.mastery) }" />
            </view>
            <text class="expand-icon">{{ expandedId === item.id ? '▾' : '▸' }}</text>
          </view>
        </view>

        <view v-if="expandedId === item.id" class="card-detail">
          <view class="detail-row">
            <view class="detail-label-wrap">
              <text class="detail-label">题目</text>
            </view>
            <text class="detail-text">{{ item.question_text }}</text>
          </view>

          <view class="detail-row">
            <view class="detail-label-wrap wrong-label">
              <text class="detail-label">你的答案</text>
            </view>
            <text class="detail-text wrong-text">{{ item.student_answer }}</text>
          </view>

          <view class="detail-row">
            <view class="detail-label-wrap correct-label">
              <text class="detail-label">正确答案</text>
            </view>
            <text class="detail-text correct-text">{{ item.correct_answer }}</text>
          </view>

          <view v-if="item.explanation" class="detail-row explanation-row">
            <view class="detail-label-wrap">
              <text class="detail-label">讲解</text>
            </view>
            <text class="detail-text explanation-text">{{ item.explanation }}</text>
          </view>

          <view v-if="item.topic" class="topic-tag-wrap">
            <text class="topic-tag-text">{{ item.topic }}</text>
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

    <!-- 待复习入口 banner -->
    <view v-if="dueItems.length > 0 && reviewMode === 'off'" class="review-start-banner" @tap="startReviewMode">
      <text class="review-start-text">📖 开始复习 {{ dueItems.length }} 道待复习错题</text>
    </view>

    <!-- 专注复习模式覆盖层 -->
    <view v-if="reviewMode === 'on'" class="review-overlay">
      <view class="review-header">
        <text class="review-progress">{{ reviewIndex + 1 }} / {{ dueItems.length }}</text>
        <view class="review-close" @tap="reviewMode = 'off'"><text>✕ 退出</text></view>
      </view>

      <view class="review-card">
        <text class="review-subject-tag">{{ dueItems[reviewIndex]?.subject === 'chinese' ? '语文' : '英语' }}</text>
        <text class="review-question">{{ dueItems[reviewIndex]?.question_text }}</text>

        <view v-if="!answerRevealed" class="reveal-btn" @tap="answerRevealed = true">
          <text>点击显示答案</text>
        </view>

        <view v-else class="answer-area">
          <view class="answer-block wrong-block">
            <text class="answer-label">你曾回答</text>
            <text class="answer-text">{{ dueItems[reviewIndex]?.student_answer }}</text>
          </view>
          <view class="answer-block correct-block">
            <text class="answer-label">正确答案</text>
            <text class="answer-text">{{ dueItems[reviewIndex]?.correct_answer }}</text>
          </view>
          <view v-if="dueItems[reviewIndex]?.explanation" class="review-explanation">
            <text>{{ dueItems[reviewIndex]?.explanation }}</text>
          </view>

          <view class="review-actions">
            <view class="btn-review-wrong" @tap="reviewCurrent(false)"><text>还不会 😞</text></view>
            <view class="btn-review-correct" @tap="reviewCurrent(true)"><text>会了！🎉</text></view>
          </view>
        </view>
      </view>
    </view>

    <!-- 复习完成 -->
    <view v-if="reviewMode === 'done'" class="review-done">
      <text class="done-icon">🎊</text>
      <text class="done-title">复习完成！</text>
      <text class="done-sub">共复习了 {{ dueItems.length }} 道题，继续加油！</text>
      <view class="done-btn" @tap="reviewMode = 'off'; fetchMistakes(); fetchStats(); loadDueItems()">
        <text>返回错题本</text>
      </view>
    </view>
  </view>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import { getMistakes, reviewMistake, getMistakeStats, type MistakeItem, type MistakeStatsResponse } from '@/api/mistakes'
import { getUserId } from '@/utils/user'

const filterSubject = ref('')
const filterTopic = ref('')
const reviewDueOnly = ref(false)
const mistakes = ref<MistakeItem[]>([])
const expandedId = ref<number | null>(null)
const loading = ref(false)
const page = ref(1)
const total = ref(0)
const hasMore = ref(false)
const stats = ref<MistakeStatsResponse | null>(null)

// 专注复习模式
const dueItems = ref<MistakeItem[]>([])
const reviewMode = ref<'off' | 'on' | 'done'>('off')
const reviewIndex = ref(0)
const answerRevealed = ref(false)

getUserId()

const pageSize = 20

const masteryColor = (m: number) => {
  if (m <= 1) return '#EF4444'
  if (m <= 2) return '#F97316'
  if (m <= 3) return '#EAB308'
  if (m <= 4) return '#22C55E'
  return '#16A34A'
}

const fetchStats = async () => {
  try {
    stats.value = await getMistakeStats()
  } catch {}
}

const toggleTopic = (topic: string) => {
  filterTopic.value = filterTopic.value === topic ? '' : topic
  page.value = 1
  expandedId.value = null
  fetchMistakes()
}

fetchStats()

const truncate = (text: string, max: number) => {
  return text.length > max ? text.slice(0, max) + '...' : text
}

const fetchMistakes = async () => {
  loading.value = true
  try {
    const res = await getMistakes({
      subject: filterSubject.value || undefined,
      review_due: reviewDueOnly.value || undefined,
      topic: filterTopic.value || undefined,
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
    fetchStats()
  } catch {
    uni.showToast({ title: '操作失败', icon: 'none' })
  }
}

const startReviewMode = () => {
  reviewIndex.value = 0
  answerRevealed.value = false
  reviewMode.value = 'on'
}

const reviewCurrent = async (correct: boolean) => {
  const item = dueItems.value[reviewIndex.value]
  if (!item) return
  try {
    await reviewMistake(item.id, correct)
  } catch { /* ignore */ }

  if (reviewIndex.value + 1 < dueItems.value.length) {
    reviewIndex.value++
    answerRevealed.value = false
  } else {
    reviewMode.value = 'done'
  }
}

const loadDueItems = async () => {
  try {
    const res = await getMistakes({ review_due: true, page: 1, size: 50 })
    dueItems.value = res.items
  } catch { /* ignore */ }
}

watch([filterSubject, reviewDueOnly, filterTopic], () => {
  page.value = 1
  expandedId.value = null
  fetchMistakes()
})

fetchMistakes()
loadDueItems()
</script>

<style scoped>
.container {
  padding: 24rpx;
  min-height: 100vh;
  background: #EEF2FF;
}

/* Stats Card */
.stats-card {
  background: #fff;
  border-radius: 24rpx;
  padding: 24rpx 28rpx;
  margin-bottom: 20rpx;
  border: 2rpx solid #E0E7FF;
  box-shadow: 4rpx 4rpx 14rpx rgba(79, 70, 229, 0.06), inset -2rpx -2rpx 6rpx rgba(79, 70, 229, 0.03);
}

.stats-title-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20rpx;
}

.stats-title {
  font-size: 28rpx;
  font-weight: 700;
  color: #312E81;
}

.stats-total {
  font-size: 22rpx;
  color: #6366F1;
  opacity: 0.7;
}

.stats-row {
  display: flex;
  justify-content: space-around;
  margin-bottom: 20rpx;
}

.stat-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8rpx;
}

.stat-ring {
  width: 80rpx;
  height: 80rpx;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 3rpx 3rpx 8rpx rgba(0, 0, 0, 0.06), inset -2rpx -2rpx 4rpx rgba(0, 0, 0, 0.04);
}

.new-ring { background: #FEE2E2; }
.reviewing-ring { background: #FEF3C7; }
.mastered-ring { background: #DCFCE7; }

.stat-number {
  font-size: 32rpx;
  font-weight: 700;
  color: #312E81;
}

.stat-label {
  font-size: 22rpx;
  color: #6B7280;
}

.topics-row {
  padding-top: 16rpx;
  border-top: 2rpx solid #E0E7FF;
}

.topics-label {
  font-size: 22rpx;
  color: #6B7280;
  display: block;
  margin-bottom: 12rpx;
}

.topic-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 12rpx;
}

.topic-chip {
  display: flex;
  align-items: center;
  gap: 6rpx;
  padding: 8rpx 18rpx;
  background: #F5F3FF;
  border-radius: 20rpx;
  border: 2rpx solid #E0E7FF;
}

.topic-chip.active {
  background: #EDE9FE;
  border-color: #818CF8;
}

.topic-chip-text {
  font-size: 24rpx;
  color: #312E81;
}

.topic-chip-count {
  font-size: 20rpx;
  color: #818CF8;
  background: #E0E7FF;
  border-radius: 10rpx;
  padding: 2rpx 8rpx;
}

.topic-chip.active .topic-chip-text {
  color: #4F46E5;
  font-weight: 600;
}

.topic-chip.active .topic-chip-count {
  background: #4F46E5;
  color: #fff;
}

/* Filter Bar */
.filter-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20rpx;
}

.subject-filter {
  display: flex;
  background: #fff;
  border-radius: 20rpx;
  overflow: hidden;
  border: 2rpx solid #E0E7FF;
}

.filter-tab {
  padding: 16rpx 28rpx;
  font-size: 26rpx;
  color: #6B7280;
}

.filter-tab.active {
  background: linear-gradient(135deg, #818CF8, #4F46E5);
  color: #fff;
  font-weight: 700;
}

.review-toggle {
  padding: 16rpx 24rpx;
  background: #fff;
  border-radius: 20rpx;
  font-size: 24rpx;
  color: #6B7280;
  border: 2rpx solid #E0E7FF;
}

.review-toggle.active {
  background: linear-gradient(135deg, #FDBA74, #FB923C);
  color: #fff;
  font-weight: 700;
  border-color: transparent;
}

/* Loading */
.loading {
  display: flex;
  justify-content: center;
  padding: 80rpx 0;
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

/* Empty */
.empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 120rpx 0;
}

.empty-circle {
  width: 100rpx;
  height: 100rpx;
  border-radius: 50%;
  background: #E0E7FF;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 24rpx;
  box-shadow: 3rpx 3rpx 8rpx rgba(79, 70, 229, 0.1);
}

.empty-icon-text {
  font-size: 36rpx;
  color: #818CF8;
  font-weight: bold;
}

.empty-text {
  font-size: 28rpx;
  color: #6B7280;
}

/* Mistake Cards */
.mistakes-list {
  padding-bottom: 40rpx;
}

.mistake-card {
  background: #fff;
  border-radius: 20rpx;
  margin-bottom: 16rpx;
  overflow: hidden;
  border: 2rpx solid #E0E7FF;
  box-shadow: 3rpx 3rpx 10rpx rgba(79, 70, 229, 0.05);
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 22rpx 24rpx;
}

.card-left {
  display: flex;
  align-items: center;
  gap: 14rpx;
  flex: 1;
  overflow: hidden;
}

.subject-dot {
  width: 16rpx;
  height: 16rpx;
  border-radius: 50%;
  flex-shrink: 0;
}

.subject-dot.chinese { background: #F97316; }
.subject-dot.english { background: #3B82F6; }

.question-preview {
  font-size: 28rpx;
  color: #312E81;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.card-right {
  display: flex;
  align-items: center;
  gap: 14rpx;
  flex-shrink: 0;
}

.mastery-bar-mini {
  width: 80rpx;
  height: 10rpx;
  background: #E0E7FF;
  border-radius: 5rpx;
  overflow: hidden;
}

.mastery-bar-fill {
  height: 100%;
  border-radius: 5rpx;
  transition: width 0.3s;
}

.expand-icon {
  font-size: 22rpx;
  color: #818CF8;
}

.card-detail {
  padding: 0 24rpx 22rpx;
  border-top: 2rpx solid #E0E7FF;
}

.detail-row {
  padding: 14rpx 0;
}

.detail-label-wrap {
  display: inline-block;
  margin-bottom: 6rpx;
}

.detail-label {
  font-size: 22rpx;
  color: #818CF8;
  font-weight: 600;
  display: block;
}

.detail-label-wrap.wrong-label .detail-label { color: #EF4444; }
.detail-label-wrap.correct-label .detail-label { color: #16A34A; }

.detail-text {
  font-size: 28rpx;
  color: #312E81;
  line-height: 1.6;
  display: block;
}

.wrong-text { color: #EF4444; }
.correct-text { color: #16A34A; font-weight: 600; }

.explanation-row {
  background: #F5F3FF;
  border-radius: 14rpx;
  padding: 14rpx 18rpx;
  margin: 8rpx 0;
}

.explanation-text {
  color: #475569;
  font-size: 26rpx;
}

.topic-tag-wrap {
  padding: 8rpx 0;
}

.topic-tag-text {
  display: inline-block;
  padding: 4rpx 16rpx;
  background: #EDE9FE;
  color: #6366F1;
  border-radius: 10rpx;
  font-size: 22rpx;
  font-weight: 500;
}

.review-section {
  margin-top: 18rpx;
  padding-top: 18rpx;
  border-top: 2rpx solid #E0E7FF;
  text-align: center;
}

.review-hint {
  font-size: 24rpx;
  color: #6B7280;
  display: block;
  margin-bottom: 14rpx;
}

.review-buttons {
  display: flex;
  gap: 20rpx;
}

.btn-review {
  flex: 1;
  text-align: center;
  padding: 18rpx 0;
  border-radius: 18rpx;
  font-size: 28rpx;
  font-weight: 600;
}

.wrong-btn {
  background: #fff;
  color: #EF4444;
  border: 3rpx solid #FECACA;
}

.correct-btn {
  background: linear-gradient(135deg, #4ADE80, #22C55E);
  color: #fff;
  border: 3rpx solid transparent;
  box-shadow: 2rpx 2rpx 8rpx rgba(34, 197, 94, 0.25);
}

.load-more {
  text-align: center;
  padding: 24rpx;
  font-size: 28rpx;
  color: #6366F1;
}
/* 待复习入口 */
.review-start-banner {
  position: fixed;
  bottom: 32rpx;
  left: 32rpx;
  right: 32rpx;
  background: linear-gradient(135deg, #818CF8, #4F46E5);
  border-radius: 24rpx;
  padding: 28rpx 32rpx;
  text-align: center;
  box-shadow: 0 6rpx 20rpx rgba(79, 70, 229, 0.35);
  z-index: 10;
}
.review-start-text { color: #fff; font-size: 30rpx; font-weight: 700; }

/* 专注复习覆盖层 */
.review-overlay {
  position: fixed;
  inset: 0;
  background: #EEF2FF;
  z-index: 100;
  display: flex;
  flex-direction: column;
  padding: 40rpx 32rpx;
}
.review-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 32rpx;
}
.review-progress { font-size: 28rpx; color: #6366F1; font-weight: 700; }
.review-close { padding: 10rpx 24rpx; background: #E0E7FF; border-radius: 20rpx; }
.review-close text { font-size: 24rpx; color: #4F46E5; }

.review-card {
  background: #fff;
  border-radius: 28rpx;
  padding: 40rpx 32rpx;
  flex: 1;
  box-shadow: 4rpx 4rpx 16rpx rgba(79, 70, 229, 0.1);
}
.review-subject-tag {
  display: inline-block;
  background: #E0E7FF;
  color: #4F46E5;
  font-size: 22rpx;
  font-weight: 600;
  padding: 6rpx 20rpx;
  border-radius: 20rpx;
  margin-bottom: 24rpx;
}
.review-question { font-size: 34rpx; color: #1E1B4B; font-weight: 600; line-height: 1.6; display: block; margin-bottom: 40rpx; }

.reveal-btn {
  background: linear-gradient(135deg, #C4B5FD, #8B5CF6);
  border-radius: 20rpx;
  padding: 28rpx 0;
  text-align: center;
}
.reveal-btn text { color: #fff; font-size: 30rpx; font-weight: 700; }

.answer-area { display: flex; flex-direction: column; gap: 20rpx; }
.answer-block { padding: 20rpx 24rpx; border-radius: 16rpx; }
.wrong-block { background: #FEF2F2; border: 2rpx solid #FECACA; }
.correct-block { background: #F0FDF4; border: 2rpx solid #BBF7D0; }
.answer-label { font-size: 22rpx; color: #9CA3AF; display: block; margin-bottom: 6rpx; }
.wrong-block .answer-text { color: #EF4444; font-size: 28rpx; font-weight: 600; }
.correct-block .answer-text { color: #16A34A; font-size: 28rpx; font-weight: 600; }
.review-explanation { background: #F5F3FF; border-radius: 16rpx; padding: 16rpx 20rpx; }
.review-explanation text { font-size: 26rpx; color: #6366F1; line-height: 1.6; }

.review-actions { display: flex; gap: 20rpx; margin-top: 8rpx; }
.btn-review-wrong, .btn-review-correct {
  flex: 1;
  text-align: center;
  padding: 26rpx 0;
  border-radius: 20rpx;
  font-size: 28rpx;
  font-weight: 700;
}
.btn-review-wrong { background: #FEE2E2; color: #DC2626; }
.btn-review-correct { background: #DCFCE7; color: #16A34A; }

/* 复习完成 */
.review-done {
  position: fixed;
  inset: 0;
  background: #EEF2FF;
  z-index: 100;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 20rpx;
}
.done-icon { font-size: 100rpx; }
.done-title { font-size: 48rpx; font-weight: 800; color: #312E81; }
.done-sub { font-size: 28rpx; color: #6366F1; }
.done-btn {
  margin-top: 40rpx;
  background: linear-gradient(135deg, #818CF8, #4F46E5);
  border-radius: 24rpx;
  padding: 28rpx 80rpx;
}
.done-btn text { color: #fff; font-size: 30rpx; font-weight: 700; }
</style>
