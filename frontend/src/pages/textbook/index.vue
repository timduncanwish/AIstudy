<template>
  <view class="container">
    <view class="summary-card">
      <text class="title">教材选择</text>
      <text class="desc">当前预习功能已预留1-9年级教材结构，3-6年级可先使用本地样例词库。</text>
    </view>

    <view v-for="item in filtered" :key="`${item.subject}-${item.grade}-${item.semester}`" class="book-card" @tap="selectBook(item)">
      <view>
        <text class="book-title">{{ item.label }}</text>
        <text class="book-source">{{ item.source_name }}</text>
      </view>
      <text :class="['status', item.status === 'ready' ? 'ready' : 'pending']">
        {{ item.status === 'ready' ? '可预习' : '待接入' }}
      </text>
    </view>
  </view>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { getTextbooks, type TextbookOption } from '@/api/preview'

const books = ref<TextbookOption[]>([])
const selectedGrade = ref(parseInt(String(uni.getStorageSync('selected_grade'))) || 3)

const filtered = computed(() => books.value.filter(item => item.grade === selectedGrade.value))

const selectBook = (item: TextbookOption) => {
  uni.setStorageSync('selected_grade', item.grade)
  uni.setStorageSync('preview_subject', item.subject)
  uni.setStorageSync('preview_semester', item.semester)
  if (item.status !== 'ready') {
    uni.showToast({ title: '该册教材数据待接入', icon: 'none' })
    return
  }
  uni.navigateTo({ url: '/pages/preview/index' })
}

onMounted(async () => {
  try {
    const res = await getTextbooks()
    books.value = res.items
  } catch {
    uni.showToast({ title: '加载教材失败', icon: 'none' })
  }
})
</script>

<style scoped>
.container {
  min-height: 100vh;
  padding: 30rpx;
  background: #EEF2FF;
}

.summary-card, .book-card {
  background: #fff;
  border: 3rpx solid #E0E7FF;
  border-radius: 20rpx;
  box-shadow: 4rpx 4rpx 12rpx rgba(79, 70, 229, 0.06);
}

.summary-card {
  padding: 30rpx;
  margin-bottom: 20rpx;
}

.title {
  display: block;
  font-size: 36rpx;
  font-weight: 800;
  color: #312E81;
  margin-bottom: 10rpx;
}

.desc {
  display: block;
  font-size: 26rpx;
  color: #6B7280;
  line-height: 1.6;
}

.book-card {
  padding: 26rpx;
  margin-bottom: 16rpx;
  display: flex;
  justify-content: space-between;
  gap: 20rpx;
  align-items: center;
}

.book-title {
  display: block;
  font-size: 30rpx;
  color: #312E81;
  font-weight: 700;
  margin-bottom: 8rpx;
}

.book-source {
  display: block;
  font-size: 23rpx;
  color: #6B7280;
  line-height: 1.4;
}

.status {
  flex-shrink: 0;
  padding: 10rpx 16rpx;
  border-radius: 999rpx;
  font-size: 22rpx;
  font-weight: 700;
}

.ready {
  background: #DCFCE7;
  color: #16A34A;
}

.pending {
  background: #FEF3C7;
  color: #D97706;
}
</style>
