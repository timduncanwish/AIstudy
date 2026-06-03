<template>
  <view class="container">
    <view class="tab-bar">
      <view :class="['tab', { active: mode === 'daily' }]" @tap="mode = 'daily'">
        <text>日报</text>
      </view>
      <view :class="['tab', { active: mode === 'weekly' }]" @tap="mode = 'weekly'">
        <text>周报</text>
      </view>
    </view>

    <view v-if="loading" class="loading">
      <view class="loading-spinner" />
    </view>

    <!-- 日报 -->
    <view v-else-if="mode === 'daily' && daily" class="report-content">
      <view class="date-bar">
        <text class="date-text">{{ daily.date }}</text>
      </view>

      <view class="overview-cards">
        <view class="ov-card">
          <text class="ov-value">{{ daily.total_interactions }}</text>
          <text class="ov-label">学习次数</text>
        </view>
        <view class="ov-card">
          <text class="ov-value">{{ daily.words_learned }}</text>
          <text class="ov-label">字词学习</text>
        </view>
        <view class="ov-card">
          <text class="ov-value">{{ daily.mistakes_count }}</text>
          <text class="ov-label">错题数</text>
        </view>
        <view class="ov-card">
          <text class="ov-value">{{ daily.homework_count }}</text>
          <text class="ov-label">作业批改</text>
        </view>
      </view>

      <view class="chart-card">
        <text class="card-title">科目分布</text>
        <view class="bar-chart">
          <view class="bar-row">
            <text class="bar-label">语文</text>
            <view class="bar-track">
              <view class="bar-fill chinese" :style="{ width: chinesePercent + '%' }" />
            </view>
            <text class="bar-num">{{ daily.subject_dist.chinese || 0 }}</text>
          </view>
          <view class="bar-row">
            <text class="bar-label">英语</text>
            <view class="bar-track">
              <view class="bar-fill english" :style="{ width: englishPercent + '%' }" />
            </view>
            <text class="bar-num">{{ daily.subject_dist.english || 0 }}</text>
          </view>
        </view>
      </view>

      <view v-if="daily.weak_topics.length > 0" class="chart-card">
        <text class="card-title">薄弱知识点</text>
        <view v-for="t in daily.weak_topics" :key="t.topic" class="topic-row">
          <text class="topic-name">{{ t.topic }}</text>
          <text class="topic-count">{{ t.count }}次</text>
        </view>
      </view>
    </view>

    <!-- 周报 -->
    <view v-else-if="mode === 'weekly' && weekly" class="report-content">
      <view class="date-bar">
        <text class="date-text">{{ weekly.week_start }} ~ {{ weekly.week_end }}</text>
      </view>

      <view class="overview-cards">
        <view class="ov-card">
          <text class="ov-value">{{ weekly.total_interactions }}</text>
          <text class="ov-label">总学习</text>
        </view>
        <view class="ov-card">
          <text class="ov-value">{{ weekly.words_mastered }}</text>
          <text class="ov-label">掌握字词</text>
        </view>
        <view class="ov-card">
          <text class="ov-value">{{ weekly.words_learned }}</text>
          <text class="ov-label">学习字词</text>
        </view>
        <view class="ov-card">
          <text class="ov-value">{{ weekly.mistakes_reviewed }}</text>
          <text class="ov-label">复习错题</text>
        </view>
      </view>

      <view class="chart-card">
        <text class="card-title">7日趋势</text>
        <view class="trend-chart">
          <view v-for="d in weekly.daily_trend" :key="d.date" class="trend-col">
            <view class="trend-bar" :style="{ height: getTrendHeight(d.count) + 'rpx' }" />
            <text class="trend-day">{{ d.date.slice(5) }}</text>
          </view>
        </view>
      </view>

      <view class="chart-card">
        <text class="card-title">科目分布</text>
        <view class="bar-chart">
          <view class="bar-row">
            <text class="bar-label">语文</text>
            <view class="bar-track">
              <view class="bar-fill chinese" :style="{ width: weeklyChinesePercent + '%' }" />
            </view>
            <text class="bar-num">{{ weekly.subject_dist.chinese || 0 }}</text>
          </view>
          <view class="bar-row">
            <text class="bar-label">英语</text>
            <view class="bar-track">
              <view class="bar-fill english" :style="{ width: weeklyEnglishPercent + '%' }" />
            </view>
            <text class="bar-num">{{ weekly.subject_dist.english || 0 }}</text>
          </view>
        </view>
      </view>

      <view v-if="weekly.vs_last_week" class="vs-card">
        <text class="card-title">与上周对比</text>
        <text class="vs-text">
          学习次数 {{ weekly.vs_last_week.interactions >= 0 ? '+' : '' }}{{ weekly.vs_last_week.interactions }}
        </text>
      </view>

      <view v-if="weekly.weak_topics.length > 0" class="chart-card">
        <text class="card-title">薄弱知识点</text>
        <view v-for="t in weekly.weak_topics" :key="t.topic" class="topic-row">
          <text class="topic-name">{{ t.topic }}</text>
          <text class="topic-count">{{ t.count }}次</text>
        </view>
      </view>
    </view>

    <view v-else-if="!loading" class="no-data">
      <text>暂无数据</text>
    </view>
  </view>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue'
import { getDailyReport, getWeeklyReport, type DailyReport, type WeeklyReport } from '@/api/reports'

const mode = ref<'daily' | 'weekly'>('daily')
const loading = ref(false)
const daily = ref<DailyReport | null>(null)
const weekly = ref<WeeklyReport | null>(null)

const chinesePercent = computed(() => {
  if (!daily.value) return 0
  const total = (daily.value.subject_dist.chinese || 0) + (daily.value.subject_dist.english || 0)
  return total > 0 ? Math.round(((daily.value.subject_dist.chinese || 0) / total) * 100) : 0
})

const englishPercent = computed(() => {
  if (!daily.value) return 0
  const total = (daily.value.subject_dist.chinese || 0) + (daily.value.subject_dist.english || 0)
  return total > 0 ? Math.round(((daily.value.subject_dist.english || 0) / total) * 100) : 0
})

const weeklyChinesePercent = computed(() => {
  if (!weekly.value) return 0
  const total = (weekly.value.subject_dist.chinese || 0) + (weekly.value.subject_dist.english || 0)
  return total > 0 ? Math.round(((weekly.value.subject_dist.chinese || 0) / total) * 100) : 0
})

const weeklyEnglishPercent = computed(() => {
  if (!weekly.value) return 0
  const total = (weekly.value.subject_dist.chinese || 0) + (weekly.value.subject_dist.english || 0)
  return total > 0 ? Math.round(((weekly.value.subject_dist.english || 0) / total) * 100) : 0
})

const getTrendHeight = (count: number) => {
  if (!weekly.value) return 0
  const max = Math.max(...weekly.value.daily_trend.map(d => d.count), 1)
  return Math.max(4, (count / max) * 200)
}

const loadData = async () => {
  loading.value = true
  try {
    if (mode.value === 'daily') {
      daily.value = await getDailyReport()
    } else {
      weekly.value = await getWeeklyReport()
    }
  } catch {
    /* ignore */
  } finally {
    loading.value = false
  }
}

watch(mode, () => loadData())
onMounted(() => loadData())
</script>

<style scoped>
.container {
  padding: 30rpx;
  min-height: 100vh;
  background: #f5f5f5;
}

.tab-bar {
  display: flex;
  background: #fff;
  border-radius: 16rpx;
  overflow: hidden;
  margin-bottom: 24rpx;
}

.tab {
  flex: 1;
  text-align: center;
  padding: 22rpx 0;
  font-size: 30rpx;
  color: #666;
}

.tab.active {
  background: #4A90D9;
  color: #fff;
  font-weight: bold;
}

.loading {
  display: flex;
  justify-content: center;
  padding: 100rpx 0;
}

.loading-spinner {
  width: 60rpx;
  height: 60rpx;
  border: 4rpx solid #e0e0e0;
  border-top-color: #4A90D9;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.date-bar {
  text-align: center;
  margin-bottom: 20rpx;
}

.date-text {
  font-size: 28rpx;
  color: #999;
}

.overview-cards {
  display: flex;
  gap: 12rpx;
  margin-bottom: 24rpx;
}

.ov-card {
  flex: 1;
  background: #fff;
  border-radius: 16rpx;
  padding: 20rpx 12rpx;
  text-align: center;
  box-shadow: 0 2rpx 8rpx rgba(0, 0, 0, 0.04);
}

.ov-value {
  font-size: 36rpx;
  font-weight: bold;
  color: #4A90D9;
  display: block;
}

.ov-label {
  font-size: 22rpx;
  color: #999;
  display: block;
  margin-top: 4rpx;
}

.chart-card {
  background: #fff;
  border-radius: 16rpx;
  padding: 24rpx;
  margin-bottom: 20rpx;
}

.card-title {
  font-size: 28rpx;
  font-weight: bold;
  color: #333;
  display: block;
  margin-bottom: 20rpx;
}

.bar-chart {
  display: flex;
  flex-direction: column;
  gap: 16rpx;
}

.bar-row {
  display: flex;
  align-items: center;
  gap: 12rpx;
}

.bar-label {
  font-size: 26rpx;
  color: #666;
  width: 60rpx;
}

.bar-track {
  flex: 1;
  height: 24rpx;
  background: #f0f0f0;
  border-radius: 12rpx;
  overflow: hidden;
}

.bar-fill {
  height: 100%;
  border-radius: 12rpx;
  transition: width 0.3s;
}

.bar-fill.chinese { background: linear-gradient(90deg, #FF6B6B, #FF8E53); }
.bar-fill.english { background: linear-gradient(90deg, #4A90D9, #67B8DE); }

.bar-num {
  font-size: 26rpx;
  color: #666;
  width: 50rpx;
  text-align: right;
}

.trend-chart {
  display: flex;
  align-items: flex-end;
  justify-content: space-around;
  height: 240rpx;
  padding: 10rpx 0;
}

.trend-col {
  display: flex;
  flex-direction: column;
  align-items: center;
  flex: 1;
}

.trend-bar {
  width: 40rpx;
  background: linear-gradient(180deg, #4A90D9, #67B8DE);
  border-radius: 8rpx 8rpx 0 0;
  min-height: 4rpx;
}

.trend-day {
  font-size: 20rpx;
  color: #999;
  margin-top: 8rpx;
}

.topic-row {
  display: flex;
  justify-content: space-between;
  padding: 12rpx 0;
  border-bottom: 1rpx solid #f5f5f5;
}

.topic-name {
  font-size: 28rpx;
  color: #333;
}

.topic-count {
  font-size: 26rpx;
  color: #FF6B6B;
  font-weight: bold;
}

.vs-card {
  background: #fff;
  border-radius: 16rpx;
  padding: 24rpx;
  margin-bottom: 20rpx;
}

.vs-text {
  font-size: 30rpx;
  color: #4A90D9;
  font-weight: bold;
  display: block;
  text-align: center;
}

.no-data {
  text-align: center;
  padding: 100rpx 0;
  font-size: 28rpx;
  color: #999;
}
</style>
