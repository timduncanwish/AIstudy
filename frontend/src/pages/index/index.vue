<template>
  <view class="container">
    <view class="header">
      <view class="logo-circle">
        <text class="logo-text">AI</text>
      </view>
      <text class="title">AI助学</text>
      <text class="subtitle">帮助小学3-6年级打好语文和英语基础</text>
    </view>

    <view class="grade-selector">
      <text class="section-title">选择年级</text>
      <view class="grade-list">
        <view
          v-for="g in grades"
          :key="g"
          :class="['grade-item', 'clay-tap', { active: selectedGrade === g }]"
          hover-class="clay-pressed"
          hover-stay-time="80"
          @tap="selectGrade(g)"
        >
          <text class="grade-text">{{ g }}年级</text>
        </view>
      </view>
    </view>

    <view class="subject-cards">
      <view class="card chinese-card clay-tap" hover-class="clay-pressed" hover-stay-time="80" @tap="startChat('chinese')">
        <view class="card-badge chinese-badge">
          <text class="badge-text">语</text>
        </view>
        <text class="card-title">语文辅导</text>
        <text class="card-desc">课文理解 · 作文指导 · 阅读训练</text>
      </view>
      <view class="card english-card clay-tap" hover-class="clay-pressed" hover-stay-time="80" @tap="startChat('english')">
        <view class="card-badge english-badge">
          <text class="badge-text">En</text>
        </view>
        <text class="card-title">英语辅导</text>
        <text class="card-desc">单词练习 · 语法讲解 · 情景对话</text>
      </view>
    </view>

    <view class="daily-practice-card clay-tap" hover-class="clay-pressed" hover-stay-time="80" @tap="goDailyPractice">
      <view class="dp-left">
        <view class="dp-icon-wrap">
          <text class="dp-icon-text">练</text>
        </view>
        <view class="dp-text-wrap">
          <text class="dp-title">每日一练</text>
          <text class="dp-desc">基于薄弱知识点，AI智能出题</text>
        </view>
      </view>
      <view class="dp-arrow-wrap">
        <text class="dp-arrow">GO</text>
      </view>
    </view>

    <view class="tools-section">
      <text class="section-title">学习工具</text>
      <view class="tools-grid">
        <view class="tool-card clay-tap" hover-class="clay-pressed" hover-stay-time="80" @tap="goHomework">
          <view class="tool-icon-wrap homework-icon">
            <text class="tool-icon-text">批</text>
          </view>
          <text class="tool-title">作业批改</text>
          <text class="tool-desc">拍照批改作业</text>
        </view>
        <view class="tool-card clay-tap" hover-class="clay-pressed" hover-stay-time="80" @tap="goMistakes">
          <view class="tool-icon-wrap mistakes-icon">
            <text class="tool-icon-text">错</text>
            <view v-if="dueCount > 0" class="due-badge">
              <text class="due-badge-text">{{ dueCount > 99 ? '99+' : dueCount }}</text>
            </view>
          </view>
          <text class="tool-title">错题本</text>
          <text class="tool-desc">{{ dueCount > 0 ? `今日待复习 ${dueCount} 题` : '复习巩固错题' }}</text>
        </view>
        <view class="tool-card clay-tap" hover-class="clay-pressed" hover-stay-time="80" @tap="goChallenge">
          <view class="tool-icon-wrap challenge-icon">
            <text class="tool-icon-text">闯</text>
          </view>
          <text class="tool-title">字词闯关</text>
          <text class="tool-desc">每日生字单词</text>
        </view>
        <view class="tool-card clay-tap" hover-class="clay-pressed" hover-stay-time="80" @tap="goReport">
          <view class="tool-icon-wrap report-icon">
            <text class="tool-icon-text">报</text>
          </view>
          <text class="tool-title">学习报告</text>
          <text class="tool-desc">查看学习数据</text>
        </view>
        <view class="tool-card clay-tap" hover-class="clay-pressed" hover-stay-time="80" @tap="goKnowledge">
          <view class="tool-icon-wrap knowledge-icon">
            <text class="tool-icon-text">识</text>
          </view>
          <text class="tool-title">知识库</text>
          <text class="tool-desc">知识点图谱</text>
        </view>
      </view>
    </view>
  </view>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { getUserId } from '@/utils/user'

const grades = [3, 4, 5, 6]
const selectedGrade = ref(parseInt(String(uni.getStorageSync('selected_grade'))) || 3)
const dueCount = ref(0)

getUserId()

onMounted(async () => {
  try {
    const { request } = await import('@/api/config')
    const res = await request<{ count: number }>({ url: '/mistakes/due-count', method: 'GET' })
    dueCount.value = res.count
  } catch { /* ignore */ }
})

const selectGrade = (grade: number) => {
  selectedGrade.value = grade
  uni.setStorageSync('selected_grade', grade)
}

const startChat = (subject: string) => {
  uni.setStorageSync('chat_subject', subject)
  uni.setStorageSync('chat_grade', selectedGrade.value)
  uni.switchTab({ url: '/pages/chat/index' })
}

const goHomework = () => {
  uni.navigateTo({ url: `/pages/homework/index?grade=${selectedGrade.value}` })
}
const goMistakes = () => {
  uni.navigateTo({ url: '/pages/mistakes/index' })
}
const goChallenge = () => {
  uni.navigateTo({ url: `/pages/challenge/index?grade=${selectedGrade.value}` })
}
const goReport = () => {
  uni.navigateTo({ url: '/pages/report/index' })
}
const goKnowledge = () => {
  uni.navigateTo({ url: '/pages/knowledge/index' })
}
const goDailyPractice = () => {
  const subject = uni.getStorageSync('chat_subject') || 'chinese'
  uni.navigateTo({ url: `/pages/daily-practice/index?subject=${subject}` })
}
</script>

<style scoped>
.container {
  padding: 30rpx;
  min-height: 100vh;
  background: #EEF2FF;
}

/* Header */
.header {
  text-align: center;
  padding: 48rpx 0 32rpx;
}

.logo-circle {
  width: 96rpx;
  height: 96rpx;
  border-radius: 50%;
  background: linear-gradient(135deg, #818CF8, #4F46E5);
  margin: 0 auto 20rpx;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 4rpx 12rpx rgba(79, 70, 229, 0.3), inset 0 2rpx 4rpx rgba(255, 255, 255, 0.3);
}

.logo-text {
  color: #fff;
  font-size: 36rpx;
  font-weight: bold;
}

.title {
  font-size: 44rpx;
  font-weight: bold;
  color: #312E81;
  display: block;
}

.subtitle {
  font-size: 26rpx;
  color: #6366F1;
  margin-top: 8rpx;
  display: block;
  opacity: 0.7;
}

/* Grade Selector */
.grade-selector {
  margin: 24rpx 0;
}

.section-title {
  font-size: 28rpx;
  font-weight: 600;
  color: #312E81;
  margin-bottom: 20rpx;
  display: block;
}

.grade-list {
  display: flex;
  gap: 16rpx;
}

.grade-item {
  flex: 1;
  text-align: center;
  padding: 22rpx 0;
  background: #fff;
  border-radius: 20rpx;
  border: 3rpx solid #E0E7FF;
  box-shadow: 4rpx 4rpx 12rpx rgba(79, 70, 229, 0.08), inset -2rpx -2rpx 6rpx rgba(79, 70, 229, 0.04);
}

.grade-item.active {
  background: linear-gradient(135deg, #818CF8, #4F46E5);
  border-color: transparent;
  box-shadow: 4rpx 4rpx 16rpx rgba(79, 70, 229, 0.25), inset 0 2rpx 4rpx rgba(255, 255, 255, 0.2);
}

.grade-text {
  font-size: 28rpx;
  color: #6366F1;
  font-weight: 500;
}

.grade-item.active .grade-text {
  color: #fff;
  font-weight: 700;
}

/* Subject Cards */
.subject-cards {
  margin-top: 32rpx;
  display: flex;
  gap: 20rpx;
}

.card {
  flex: 1;
  padding: 32rpx 28rpx;
  border-radius: 24rpx;
  border: 3rpx solid transparent;
}

.chinese-card {
  background: linear-gradient(145deg, #FED7AA, #FDBA74);
  border-color: #FDBA74;
  box-shadow: 4rpx 4rpx 16rpx rgba(251, 146, 60, 0.25), inset -2rpx -2rpx 8rpx rgba(251, 146, 60, 0.15);
}

.english-card {
  background: linear-gradient(145deg, #BAE6FD, #7DD3FC);
  border-color: #7DD3FC;
  box-shadow: 4rpx 4rpx 16rpx rgba(56, 189, 248, 0.25), inset -2rpx -2rpx 8rpx rgba(56, 189, 248, 0.15);
}

.card-badge {
  width: 64rpx;
  height: 64rpx;
  border-radius: 18rpx;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 20rpx;
  box-shadow: inset 0 2rpx 4rpx rgba(255, 255, 255, 0.5);
}

.chinese-badge {
  background: #EA580C;
}

.english-badge {
  background: #0284C7;
}

.badge-text {
  color: #fff;
  font-size: 28rpx;
  font-weight: bold;
}

.card-title {
  font-size: 32rpx;
  font-weight: 700;
  color: #312E81;
  display: block;
  margin-bottom: 8rpx;
}

.card-desc {
  font-size: 22rpx;
  color: #475569;
  display: block;
  line-height: 1.5;
}

/* Daily Practice */
.daily-practice-card {
  display: flex;
  justify-content: space-between;
  align-items: center;
  background: linear-gradient(145deg, #C4B5FD, #8B5CF6);
  border-radius: 24rpx;
  padding: 28rpx 32rpx;
  margin-top: 28rpx;
  border: 3rpx solid #A78BFA;
  box-shadow: 4rpx 4rpx 16rpx rgba(139, 92, 246, 0.3), inset -2rpx -2rpx 8rpx rgba(139, 92, 246, 0.15);
}

.dp-left {
  display: flex;
  align-items: center;
  gap: 20rpx;
}

.dp-icon-wrap {
  width: 64rpx;
  height: 64rpx;
  border-radius: 18rpx;
  background: rgba(255, 255, 255, 0.25);
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: inset 0 2rpx 4rpx rgba(255, 255, 255, 0.3);
}

.dp-icon-text {
  color: #fff;
  font-size: 28rpx;
  font-weight: bold;
}

.dp-text-wrap {
  display: flex;
  flex-direction: column;
}

.dp-title {
  font-size: 32rpx;
  font-weight: 700;
  color: #fff;
  display: block;
  margin-bottom: 4rpx;
}

.dp-desc {
  font-size: 22rpx;
  color: rgba(255, 255, 255, 0.8);
}

.dp-arrow-wrap {
  background: rgba(255, 255, 255, 0.25);
  border-radius: 28rpx;
  padding: 12rpx 28rpx;
  box-shadow: inset 0 2rpx 4rpx rgba(255, 255, 255, 0.3);
}

.dp-arrow {
  color: #fff;
  font-size: 26rpx;
  font-weight: bold;
  letter-spacing: 2rpx;
}

/* Tools */
.tools-section {
  margin-top: 32rpx;
}

.tools-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 20rpx;
}

.tool-card {
  width: calc(33.33% - 14rpx);
  background: #fff;
  border-radius: 24rpx;
  padding: 28rpx 16rpx;
  text-align: center;
  border: 3rpx solid #E0E7FF;
  box-shadow: 4rpx 4rpx 12rpx rgba(79, 70, 229, 0.06), inset -2rpx -2rpx 6rpx rgba(79, 70, 229, 0.03);
}

.tool-icon-wrap {
  width: 72rpx;
  height: 72rpx;
  border-radius: 20rpx;
  margin: 0 auto 14rpx;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 3rpx 3rpx 8rpx rgba(0, 0, 0, 0.08), inset -1rpx -1rpx 4rpx rgba(0, 0, 0, 0.04);
  position: relative;
}

.due-badge {
  position: absolute;
  top: -10rpx;
  right: -10rpx;
  background: #EF4444;
  border-radius: 20rpx;
  min-width: 32rpx;
  height: 32rpx;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 0 6rpx;
  border: 2rpx solid #fff;
}

.due-badge-text {
  color: #fff;
  font-size: 18rpx;
  font-weight: bold;
}

.homework-icon {
  background: #FEF3C7;
}
.homework-icon .tool-icon-text {
  color: #D97706;
}

.mistakes-icon {
  background: #FFE4E6;
}
.mistakes-icon .tool-icon-text {
  color: #E11D48;
}

.challenge-icon {
  background: #DCFCE7;
}
.challenge-icon .tool-icon-text {
  color: #16A34A;
}

.report-icon {
  background: #DBEAFE;
}
.report-icon .tool-icon-text {
  color: #2563EB;
}

.knowledge-icon {
  background: #F3E8FF;
}
.knowledge-icon .tool-icon-text {
  color: #7C3AED;
}

.tool-icon-text {
  font-size: 30rpx;
  font-weight: bold;
}

.tool-title {
  font-size: 26rpx;
  font-weight: 600;
  color: #312E81;
  display: block;
  margin-bottom: 4rpx;
}

.tool-desc {
  font-size: 20rpx;
  color: #6B7280;
  display: block;
}
</style>
