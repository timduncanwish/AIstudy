<template>
  <view class="container">
    <view class="header">
      <text class="title">AI助学</text>
      <text class="subtitle">帮助小学3-6年级打好语文和英语基础</text>
    </view>

    <view class="grade-selector">
      <text class="section-title">选择年级</text>
      <view class="grade-list">
        <view
          v-for="g in grades"
          :key="g"
          :class="['grade-item', { active: selectedGrade === g }]"
          @tap="selectGrade(g)"
        >
          <text>{{ g }}年级</text>
        </view>
      </view>
    </view>

    <view class="subject-cards">
      <view class="card chinese-card" @tap="startChat('chinese')">
        <text class="card-icon">📖</text>
        <text class="card-title">语文辅导</text>
        <text class="card-desc">课文理解、作文指导、阅读训练</text>
      </view>
      <view class="card english-card" @tap="startChat('english')">
        <text class="card-icon">🔤</text>
        <text class="card-title">英语辅导</text>
        <text class="card-desc">单词练习、语法讲解、情景对话</text>
      </view>
    </view>

    <view class="tools-section">
      <text class="section-title">学习工具</text>
      <view class="tools-row">
        <view class="tool-card homework-card" @tap="goHomework">
          <text class="tool-icon">📸</text>
          <text class="tool-title">作业批改</text>
          <text class="tool-desc">拍照批改作业</text>
        </view>
        <view class="tool-card mistakes-card" @tap="goMistakes">
          <text class="tool-icon">📝</text>
          <text class="tool-title">错题本</text>
          <text class="tool-desc">复习巩固错题</text>
        </view>
        <view class="tool-card challenge-card" @tap="goChallenge">
          <text class="tool-icon">🎯</text>
          <text class="tool-title">字词闯关</text>
          <text class="tool-desc">每日生字单词</text>
        </view>
        <view class="tool-card report-card" @tap="goReport">
          <text class="tool-icon">📊</text>
          <text class="tool-title">学习报告</text>
          <text class="tool-desc">查看学习数据</text>
        </view>
      </view>
    </view>
  </view>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { getUserId } from '@/utils/user'

const grades = [3, 4, 5, 6]
const selectedGrade = ref(parseInt(String(uni.getStorageSync('selected_grade'))) || 3)

getUserId()

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
  uni.navigateTo({
    url: `/pages/homework/index?grade=${selectedGrade.value}`,
  })
}

const goMistakes = () => {
  uni.navigateTo({
    url: '/pages/mistakes/index',
  })
}

const goChallenge = () => {
  uni.navigateTo({
    url: `/pages/challenge/index?grade=${selectedGrade.value}`,
  })
}

const goReport = () => {
  uni.navigateTo({
    url: '/pages/report/index',
  })
}
</script>

<style scoped>
.container {
  padding: 30rpx;
  min-height: 100vh;
  background: #f5f5f5;
}

.header {
  text-align: center;
  padding: 40rpx 0;
}

.title {
  font-size: 48rpx;
  font-weight: bold;
  color: #333;
  display: block;
}

.subtitle {
  font-size: 28rpx;
  color: #888;
  margin-top: 10rpx;
  display: block;
}

.grade-selector {
  margin: 20rpx 0;
}

.section-title {
  font-size: 30rpx;
  font-weight: bold;
  color: #333;
  margin-bottom: 20rpx;
  display: block;
}

.grade-list {
  display: flex;
  justify-content: space-between;
}

.grade-item {
  flex: 1;
  text-align: center;
  padding: 20rpx 0;
  margin: 0 10rpx;
  background: #fff;
  border-radius: 16rpx;
  font-size: 28rpx;
  color: #666;
  box-shadow: 0 2rpx 8rpx rgba(0, 0, 0, 0.06);
}

.grade-item.active {
  background: #4A90D9;
  color: #fff;
}

.subject-cards {
  margin-top: 40rpx;
}

.card {
  padding: 40rpx;
  border-radius: 20rpx;
  margin-bottom: 24rpx;
  box-shadow: 0 4rpx 16rpx rgba(0, 0, 0, 0.08);
}

.chinese-card {
  background: linear-gradient(135deg, #FF6B6B, #FF8E53);
}

.english-card {
  background: linear-gradient(135deg, #4A90D9, #67B8DE);
}

.card-icon {
  font-size: 60rpx;
  display: block;
  margin-bottom: 16rpx;
}

.card-title {
  font-size: 36rpx;
  font-weight: bold;
  color: #fff;
  display: block;
  margin-bottom: 8rpx;
}

.card-desc {
  font-size: 24rpx;
  color: rgba(255, 255, 255, 0.85);
  display: block;
}

.tools-section {
  margin-top: 20rpx;
}

.tools-row {
  display: flex;
  flex-wrap: wrap;
  gap: 20rpx;
}

.tool-card {
  width: calc(50% - 10rpx);
  background: #fff;
  border-radius: 20rpx;
  padding: 36rpx 24rpx;
  text-align: center;
  box-shadow: 0 4rpx 16rpx rgba(0, 0, 0, 0.06);
}

.tool-icon {
  font-size: 56rpx;
  display: block;
  margin-bottom: 12rpx;
}

.tool-title {
  font-size: 30rpx;
  font-weight: bold;
  color: #333;
  display: block;
  margin-bottom: 6rpx;
}

.tool-desc {
  font-size: 24rpx;
  color: #999;
  display: block;
}
</style>
