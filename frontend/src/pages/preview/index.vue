<template>
  <view class="container">
    <view class="selector-card">
      <view class="subject-tabs">
        <view :class="['tab', { active: subject === 'chinese' }]" @tap="switchSubject('chinese')">
          <text>语文</text>
        </view>
        <view :class="['tab', { active: subject === 'english' }]" @tap="switchSubject('english')">
          <text>英语</text>
        </view>
      </view>

      <view class="row">
        <view class="mini-select" @tap="cycleGrade">
          <text class="mini-label">年级</text>
          <text class="mini-value">{{ grade }}年级</text>
        </view>
        <view class="mini-select" @tap="toggleSemester">
          <text class="mini-label">学期</text>
          <text class="mini-value">{{ semester }}</text>
        </view>
        <view class="mini-select" @tap="goTextbook">
          <text class="mini-label">教材</text>
          <text class="mini-value">{{ textbookVersion }}</text>
        </view>
      </view>
    </view>

    <view v-if="loading" class="state-card">
      <view class="loading-spinner" />
      <text class="state-text">正在加载预习清单...</text>
    </view>

    <view v-else-if="!units.length" class="state-card">
      <text class="empty-title">暂无该册教材数据</text>
      <text class="empty-desc">教材库已预留1-9年级结构，当前先开放3-6年级样例数据，后续接入官方教材复核数据。</text>
    </view>

    <view v-else-if="!detail" class="unit-list">
      <view v-for="unit in units" :key="unit.unit" class="unit-card" @tap="openUnit(unit.unit)">
        <view>
          <text class="unit-title">{{ unit.title }}</text>
          <text class="unit-desc">{{ unit.completed_items }}/{{ unit.total_items }} 项已预习</text>
        </view>
        <view class="unit-progress">
          <view class="progress-bar">
            <view class="progress-fill" :style="{ width: unitPercent(unit) + '%' }" />
          </view>
          <text class="unit-go">进入</text>
        </view>
      </view>
    </view>

    <view v-else class="detail-section">
      <view class="detail-header">
        <view>
          <text class="detail-title">{{ detail.title }}</text>
          <text class="detail-subtitle">{{ detail.guidance }}</text>
        </view>
        <view class="back-btn" @tap="detail = null">
          <text>返回单元</text>
        </view>
      </view>

      <view class="source-card">
        <text class="source-text">来源：{{ detail.source_name }}</text>
        <text class="source-status">状态：待官方教材数据复核</text>
      </view>

      <view class="items-list">
        <view v-for="item in detail.items" :key="item.item_key" :class="['item-card', { done: item.completed }]">
          <view class="item-top">
            <view>
              <text class="tag">{{ item.category_label }}</text>
              <text class="word">{{ item.word }}</text>
              <text class="pronunciation">{{ item.pronunciation }}</text>
            </view>
            <view :class="['complete-btn', { completed: item.completed }]" @tap="markComplete(item)">
              <text>{{ item.completed ? '已完成' : '完成' }}</text>
            </view>
          </view>
          <text class="meaning">{{ item.meaning }}</text>
          <text class="prompt">{{ item.practice_prompt }}</text>
          <view v-if="item.sample_sentences.length" class="sentences">
            <text v-for="sentence in item.sample_sentences.slice(0, 2)" :key="sentence" class="sentence">{{ sentence }}</text>
          </view>
        </view>
      </view>
    </view>
  </view>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import {
  completePreviewItem,
  getPreviewUnitDetail,
  getPreviewUnits,
  type PreviewItem,
  type PreviewUnit,
  type PreviewUnitDetail,
} from '@/api/preview'
import { getUserId } from '@/utils/user'

const subject = ref(String(uni.getStorageSync('preview_subject') || 'chinese'))
const grade = ref(parseInt(String(uni.getStorageSync('selected_grade'))) || 3)
const semester = ref(String(uni.getStorageSync('preview_semester') || '上册'))
const units = ref<PreviewUnit[]>([])
const detail = ref<PreviewUnitDetail | null>(null)
const loading = ref(false)

const textbookVersion = computed(() => subject.value === 'chinese' ? '统编版' : 'PEP人教版')

const loadUnits = async () => {
  loading.value = true
  detail.value = null
  getUserId()
  try {
    const res = await getPreviewUnits({
      subject: subject.value,
      grade: grade.value,
      semester: semester.value,
      textbook_version: textbookVersion.value,
    })
    units.value = res.units
  } catch {
    uni.showToast({ title: '加载预习清单失败', icon: 'none' })
  } finally {
    loading.value = false
  }
}

const switchSubject = (next: string) => {
  subject.value = next
  uni.setStorageSync('preview_subject', next)
  loadUnits()
}

const cycleGrade = () => {
  grade.value = grade.value >= 6 ? 3 : grade.value + 1
  uni.setStorageSync('selected_grade', grade.value)
  loadUnits()
}

const toggleSemester = () => {
  semester.value = semester.value === '上册' ? '下册' : '上册'
  uni.setStorageSync('preview_semester', semester.value)
  loadUnits()
}

const goTextbook = () => {
  uni.navigateTo({ url: `/pages/textbook/index?grade=${grade.value}&subject=${subject.value}` })
}

const openUnit = async (unit: number) => {
  loading.value = true
  try {
    detail.value = await getPreviewUnitDetail({
      subject: subject.value,
      grade: grade.value,
      semester: semester.value,
      textbook_version: textbookVersion.value,
      unit,
    })
  } catch {
    uni.showToast({ title: '加载单元失败', icon: 'none' })
  } finally {
    loading.value = false
  }
}

const markComplete = async (item: PreviewItem) => {
  if (!detail.value || item.completed) return
  try {
    await completePreviewItem({
      subject: subject.value,
      grade: grade.value,
      semester: semester.value,
      textbook_version: textbookVersion.value,
      unit: detail.value.unit,
      item_key: item.item_key,
      item_type: item.item_type,
    })
    item.completed = true
    const unit = units.value.find(u => u.unit === detail.value?.unit)
    if (unit) unit.completed_items += 1
    uni.showToast({ title: '预习完成', icon: 'success' })
  } catch {
    uni.showToast({ title: '保存失败', icon: 'none' })
  }
}

const unitPercent = (unit: PreviewUnit) => {
  if (!unit.total_items) return 0
  return Math.round((unit.completed_items / unit.total_items) * 100)
}

onMounted(loadUnits)
</script>

<style scoped>
.container {
  min-height: 100vh;
  padding: 30rpx;
  background: #EEF2FF;
}

.selector-card, .state-card, .unit-card, .item-card, .source-card {
  background: #fff;
  border: 3rpx solid #E0E7FF;
  border-radius: 20rpx;
  box-shadow: 4rpx 4rpx 12rpx rgba(79, 70, 229, 0.06);
}

.selector-card {
  padding: 24rpx;
  margin-bottom: 24rpx;
}

.subject-tabs {
  display: flex;
  overflow: hidden;
  border-radius: 16rpx;
  background: #EEF2FF;
  margin-bottom: 20rpx;
}

.tab {
  flex: 1;
  text-align: center;
  padding: 20rpx 0;
  font-size: 28rpx;
  color: #4B5563;
}

.tab.active {
  background: #4F46E5;
  color: #fff;
  font-weight: 700;
}

.row {
  display: flex;
  gap: 16rpx;
}

.mini-select {
  flex: 1;
  padding: 18rpx;
  border-radius: 16rpx;
  background: #F8FAFC;
}

.mini-label {
  display: block;
  font-size: 20rpx;
  color: #6B7280;
  margin-bottom: 6rpx;
}

.mini-value {
  display: block;
  font-size: 26rpx;
  color: #312E81;
  font-weight: 700;
}

.state-card {
  padding: 60rpx 36rpx;
  text-align: center;
}

.loading-spinner {
  width: 72rpx;
  height: 72rpx;
  border: 6rpx solid #E0E7FF;
  border-top-color: #4F46E5;
  border-radius: 50%;
  margin: 0 auto 20rpx;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.state-text, .empty-desc {
  display: block;
  font-size: 26rpx;
  color: #6B7280;
  line-height: 1.6;
}

.empty-title {
  display: block;
  font-size: 32rpx;
  color: #312E81;
  font-weight: 700;
  margin-bottom: 12rpx;
}

.unit-list, .items-list {
  display: flex;
  flex-direction: column;
  gap: 18rpx;
}

.unit-card {
  padding: 28rpx;
  display: flex;
  justify-content: space-between;
  gap: 24rpx;
}

.unit-title {
  display: block;
  font-size: 32rpx;
  color: #312E81;
  font-weight: 700;
  margin-bottom: 8rpx;
}

.unit-desc {
  display: block;
  font-size: 24rpx;
  color: #6B7280;
}

.unit-progress {
  width: 180rpx;
  display: flex;
  flex-direction: column;
  justify-content: center;
  gap: 10rpx;
}

.progress-bar {
  height: 12rpx;
  background: #E5E7EB;
  border-radius: 8rpx;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  background: linear-gradient(90deg, #10B981, #4F46E5);
}

.unit-go {
  text-align: right;
  font-size: 24rpx;
  color: #4F46E5;
  font-weight: 700;
}

.detail-header {
  display: flex;
  justify-content: space-between;
  gap: 20rpx;
  margin-bottom: 18rpx;
}

.detail-title {
  display: block;
  font-size: 34rpx;
  color: #312E81;
  font-weight: 700;
  margin-bottom: 8rpx;
}

.detail-subtitle, .source-text, .source-status {
  display: block;
  font-size: 24rpx;
  color: #6B7280;
  line-height: 1.5;
}

.back-btn {
  flex-shrink: 0;
  align-self: flex-start;
  padding: 14rpx 20rpx;
  border-radius: 14rpx;
  background: #4F46E5;
  color: #fff;
  font-size: 24rpx;
}

.source-card {
  padding: 22rpx;
  margin-bottom: 18rpx;
}

.source-status {
  color: #D97706;
  margin-top: 6rpx;
}

.item-card {
  padding: 28rpx;
}

.item-card.done {
  border-color: #BBF7D0;
  background: #F0FDF4;
}

.item-top {
  display: flex;
  justify-content: space-between;
  gap: 18rpx;
  margin-bottom: 16rpx;
}

.tag {
  display: inline-block;
  padding: 6rpx 12rpx;
  background: #E0E7FF;
  color: #4F46E5;
  border-radius: 10rpx;
  font-size: 20rpx;
  margin-right: 12rpx;
}

.word {
  font-size: 44rpx;
  color: #111827;
  font-weight: 800;
  margin-right: 12rpx;
}

.pronunciation {
  font-size: 24rpx;
  color: #6B7280;
}

.complete-btn {
  flex-shrink: 0;
  align-self: flex-start;
  padding: 14rpx 22rpx;
  border-radius: 14rpx;
  background: #FF8E53;
  color: #fff;
  font-size: 24rpx;
  font-weight: 700;
}

.complete-btn.completed {
  background: #10B981;
}

.meaning, .prompt, .sentence {
  display: block;
  font-size: 26rpx;
  color: #374151;
  line-height: 1.6;
}

.prompt {
  margin-top: 8rpx;
  color: #4F46E5;
}

.sentences {
  margin-top: 14rpx;
  padding: 16rpx;
  background: #F8FAFC;
  border-radius: 14rpx;
}

.sentence {
  color: #6B7280;
}
</style>
