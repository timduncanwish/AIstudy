<template>
  <view class="container">
    <view class="user-card">
      <text class="avatar">{{ currentAvatar }}</text>
      <view class="user-info">
        <text class="nickname">{{ nickname }}</text>
        <text v-if="isLoggedIn" class="login-status logged">已登录</text>
        <text v-else class="login-status" @tap="doLogin">点击登录</text>
      </view>
    </view>

    <view v-if="stats" class="section">
      <text class="section-title">学习成长</text>
      <view class="growth-stats">
        <view class="growth-item">
          <text class="growth-num">{{ stats.total_points }}</text>
          <text class="growth-label">积分</text>
        </view>
        <view class="growth-item">
          <text class="growth-num">{{ stats.streak_days }}</text>
          <text class="growth-label">连续天数</text>
        </view>
        <view class="growth-item">
          <text class="growth-num">{{ stats.words_mastered }}</text>
          <text class="growth-label">掌握字词</text>
        </view>
      </view>
      <view v-if="stats.badges.length" class="badge-list">
        <view v-for="b in stats.badges" :key="b.id" class="badge-chip">
          <text>🏅 {{ b.name }}</text>
        </view>
      </view>
      <text v-else class="badge-empty">完成闯关即可解锁徽章 ✨</text>
    </view>

    <view v-if="summary && summary.weekly_completed > 0" class="section">
      <text class="section-title">本周预习</text>
      <text class="preview-stat">已预习 {{ summary.weekly_completed }} 项 · 语文 {{ summary.subject_breakdown.chinese }} · 英语 {{ summary.subject_breakdown.english }}</text>
      <view v-if="summary.review_suggestions.length" class="preview-tips">
        <text class="preview-tips-title">建议复习</text>
        <text v-for="(s, i) in summary.review_suggestions.slice(0, 3)" :key="i" class="preview-tip">· {{ s }}</text>
      </view>
      <view class="menu-item" style="margin-top:8rpx;" @tap="goPreview">
        <text>去预习</text>
        <text class="arrow">></text>
      </view>
    </view>

    <view class="section">
      <view class="section-header">
        <text class="section-title">我的孩子</text>
        <text class="add-btn" @tap="openAddStudent">+ 添加</text>
      </view>
      <view v-if="students.length === 0" class="empty-tip">
        <text>还没有添加孩子，点击右上角添加</text>
      </view>
      <view
        v-for="s in students"
        :key="s.id"
        :class="['student-card', { active: s.is_active }]"
        @tap="switchStudent(s)"
      >
        <text class="student-avatar">{{ s.avatar_tag }}</text>
        <view class="student-info">
          <text class="student-name">{{ s.name }}</text>
          <text class="student-grade">{{ s.grade }}年级</text>
        </view>
        <view v-if="s.is_active" class="active-tag">
          <text>当前</text>
        </view>
        <text class="student-edit" @tap.stop="openEdit(s)">编辑</text>
      </view>
    </view>

    <view class="section">
      <text class="section-title">学习提醒</text>
      <view class="reminder-card">
        <text class="reminder-label">每日提醒时间</text>
        <picker mode="time" :value="reminderTime" @change="setReminderTime">
          <text class="reminder-time">{{ reminderTime || '未设置' }}</text>
        </picker>
      </view>
      <view class="reminder-card" style="margin-top:16rpx;">
        <text class="reminder-label">微信学习通知</text>
        <view
          :class="['notify-btn', notifySubscribed ? 'notify-on' : 'notify-off']"
          @tap="toggleNotify"
        >
          <text class="notify-btn-text">{{ notifySubscribed ? '已订阅 ✓' : '点击订阅' }}</text>
        </view>
      </view>
    </view>

    <view class="section">
      <text class="section-title">其他</text>
      <view class="menu-item" @tap="goReport">
        <text>学习报告</text>
        <text class="arrow">></text>
      </view>
      <view class="menu-item" @tap="goChatHistory">
        <text>历史对话</text>
        <text class="arrow">></text>
      </view>
      <view class="menu-item" @tap="goAbout">
        <text>关于AI助学</text>
        <text class="arrow">></text>
      </view>
      <view v-if="isLoggedIn" class="menu-item logout" @tap="doLogout">
        <text>退出登录</text>
      </view>
    </view>

    <!-- 添加孩子弹窗 -->
    <view v-if="showAddStudent" class="modal-mask" @tap="showAddStudent = false">
      <view class="modal-content" @tap.stop>
        <text class="modal-title">添加孩子</text>
        <input v-model="newName" class="modal-input" placeholder="孩子姓名" />
        <view class="grade-picker">
          <view
            v-for="g in [3, 4, 5, 6]"
            :key="g"
            :class="['grade-btn', { active: newGrade === g }]"
            @tap="newGrade = g"
          >
            <text>{{ g }}年级</text>
          </view>
        </view>
        <text class="section-title" style="margin: 16rpx 0 12rpx;">选择头像</text>
        <view class="avatar-picker">
          <view
            v-for="av in avatarOptions"
            :key="av"
            :class="['avatar-option', { active: newAvatar === av }]"
            @tap="newAvatar = av"
          >
            <text>{{ av }}</text>
          </view>
        </view>
        <view class="modal-actions">
          <view class="btn-cancel" @tap="showAddStudent = false"><text>取消</text></view>
          <view class="btn-confirm" @tap="doAddStudent"><text>确认</text></view>
        </view>
      </view>
    </view>

    <!-- 编辑孩子弹窗 -->
    <view v-if="showEditStudent" class="modal-mask" @tap="showEditStudent = false">
      <view class="modal-content" @tap.stop>
        <text class="modal-title">编辑孩子</text>
        <input v-model="editName" class="modal-input" placeholder="孩子姓名" />
        <view class="grade-picker">
          <view
            v-for="g in [3, 4, 5, 6]"
            :key="g"
            :class="['grade-btn', { active: editGrade === g }]"
            @tap="editGrade = g"
          >
            <text>{{ g }}年级</text>
          </view>
        </view>
        <text class="section-title" style="margin: 16rpx 0 12rpx;">选择头像</text>
        <view class="avatar-picker">
          <view
            v-for="av in avatarOptions"
            :key="av"
            :class="['avatar-option', { active: editAvatar === av }]"
            @tap="editAvatar = av"
          >
            <text>{{ av }}</text>
          </view>
        </view>
        <view class="modal-actions">
          <view class="btn-cancel" @tap="doDeleteStudent"><text>删除</text></view>
          <view class="btn-confirm" @tap="doUpdateStudent"><text>保存</text></view>
        </view>
      </view>
    </view>
  </view>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { getStudents, addStudent, activateStudent, updateStudent, deleteStudent, type StudentInfo } from '@/api/students'
import { request } from '@/api/config'
import { wxLogin } from '@/api/auth'
import { getUserStats, type UserStatsResponse } from '@/api/challenge'
import { getParentSummary, type ParentSummary } from '@/api/preview'

const isLoggedIn = ref(false)
const nickname = ref('家长')
const currentAvatar = ref('👤')
const students = ref<StudentInfo[]>([])
const showAddStudent = ref(false)
const newName = ref('')
const newGrade = ref(3)
const newAvatar = ref('👦')
const showEditStudent = ref(false)
const editId = ref(0)
const editName = ref('')
const editGrade = ref(3)
const editAvatar = ref('👦')
const reminderTime = ref('')
const notifySubscribed = ref(false)
const stats = ref<UserStatsResponse | null>(null)
const summary = ref<ParentSummary | null>(null)

const avatarOptions = ['👦', '👧', '🧒', '👶', '🐱', '🐶']

const token = uni.getStorageSync('token')
isLoggedIn.value = !!token
if (token) {
  nickname.value = uni.getStorageSync('nickname') || '家长'
}

reminderTime.value = uni.getStorageSync('reminder_time') || ''

// 加载通知订阅状态
const loadNotifyStatus = async () => {
  const dbUserId = uni.getStorageSync('db_user_id')
  if (!dbUserId) return
  try {
    const res = await request<{ subscribed: boolean; notify_time: string }>({
      url: `/notify/status/${dbUserId}`,
      method: 'GET',
    })
    notifySubscribed.value = res.subscribed
    if (res.notify_time) reminderTime.value = res.notify_time
  } catch { /* ignore */ }
}
loadNotifyStatus()

const loadStudents = async () => {
  try {
    students.value = await getStudents()
    const active = students.value.find(s => s.is_active)
    if (active) {
      currentAvatar.value = active.avatar_tag
    }
  } catch { /* ignore */ }
}

const doLogin = () => {
  uni.login({
    success: async (res) => {
      if (res.code) {
        try {
          const result = await wxLogin(res.code)
          uni.setStorageSync('token', result.token)
          uni.setStorageSync('db_user_id', result.user_id)
          uni.setStorageSync('nickname', result.nickname)
          isLoggedIn.value = true
          nickname.value = result.nickname
          uni.showToast({ title: '登录成功', icon: 'success' })
        } catch {
          uni.showToast({ title: '登录失败', icon: 'none' })
        }
      }
    },
  })
}

const doLogout = () => {
  uni.removeStorageSync('token')
  uni.removeStorageSync('db_user_id')
  uni.removeStorageSync('nickname')
  isLoggedIn.value = false
  nickname.value = '家长'
  uni.showToast({ title: '已退出', icon: 'none' })
}

const requireLogin = (): boolean => {
  if (isLoggedIn.value) return true
  uni.showToast({ title: '孩子档案需要先登录', icon: 'none' })
  return false
}

const switchStudent = async (s: StudentInfo) => {
  if (s.is_active) return
  if (!requireLogin()) return
  try {
    await activateStudent(s.id)
    await loadStudents()
    uni.showToast({ title: `已切换到 ${s.name}`, icon: 'none' })
  } catch { /* ignore */ }
}

const openAddStudent = () => {
  if (!requireLogin()) return
  showAddStudent.value = true
}

const doAddStudent = async () => {
  if (!newName.value.trim()) {
    uni.showToast({ title: '请输入姓名', icon: 'none' })
    return
  }
  try {
    await addStudent({ name: newName.value, grade: newGrade.value, avatar_tag: newAvatar.value })
    showAddStudent.value = false
    newName.value = ''
    newGrade.value = 3
    newAvatar.value = '👦'
    await loadStudents()
    uni.showToast({ title: '添加成功', icon: 'success' })
  } catch {
    uni.showToast({ title: '添加失败', icon: 'none' })
  }
}

const openEdit = (s: StudentInfo) => {
  if (!requireLogin()) return
  editId.value = s.id
  editName.value = s.name
  editGrade.value = s.grade
  editAvatar.value = s.avatar_tag
  showEditStudent.value = true
}

const doUpdateStudent = async () => {
  if (!editName.value.trim()) {
    uni.showToast({ title: '请输入姓名', icon: 'none' })
    return
  }
  try {
    await updateStudent(editId.value, {
      name: editName.value,
      grade: editGrade.value,
      avatar_tag: editAvatar.value,
    })
    showEditStudent.value = false
    await loadStudents()
    uni.showToast({ title: '已保存', icon: 'success' })
  } catch {
    uni.showToast({ title: '保存失败', icon: 'none' })
  }
}

const doDeleteStudent = () => {
  uni.showModal({
    title: '删除孩子',
    content: `确定删除「${editName.value}」吗？该孩子的学习记录将不再展示。`,
    confirmColor: '#EF4444',
    success: async (r) => {
      if (!r.confirm) return
      try {
        await deleteStudent(editId.value)
        showEditStudent.value = false
        await loadStudents()
        uni.showToast({ title: '已删除', icon: 'none' })
      } catch {
        uni.showToast({ title: '删除失败', icon: 'none' })
      }
    },
  })
}

const setReminderTime = async (e: any) => {
  reminderTime.value = e.detail.value
  uni.setStorageSync('reminder_time', reminderTime.value)
  const dbUserId = uni.getStorageSync('db_user_id')
  if (dbUserId) {
    try {
      await request({ url: '/notify/time', method: 'POST', data: { user_id: dbUserId, notify_time: reminderTime.value } })
    } catch { /* ignore */ }
  }
  uni.showToast({ title: `提醒时间设为 ${reminderTime.value}`, icon: 'none' })
}

const toggleNotify = async () => {
  const dbUserId = uni.getStorageSync('db_user_id')
  if (!dbUserId) {
    uni.showToast({ title: '请先登录', icon: 'none' })
    return
  }
  if (notifySubscribed.value) {
    // 取消订阅
    uni.showModal({
      title: '取消通知',
      content: '确定取消学习通知？',
      success: async (res) => {
        if (!res.confirm) return
        try {
          await request({ url: '/notify/subscribe', method: 'POST', data: { user_id: dbUserId, subscribed: false } })
          notifySubscribed.value = false
          uni.showToast({ title: '已取消通知', icon: 'none' })
        } catch { uni.showToast({ title: '操作失败', icon: 'none' }) }
      },
    })
  } else {
    // 先从后端拿模板 ID，再调起微信订阅授权
    let tmplIds: string[] = []
    try {
      const cfg = await request<{ tmpl_ids: string[] }>({ url: '/notify/config', method: 'GET' })
      tmplIds = cfg.tmpl_ids
    } catch { /* ignore */ }

    if (!tmplIds.length) {
      uni.showToast({ title: '通知服务暂未配置', icon: 'none' })
      return
    }

    uni.requestSubscribeMessage({
      tmplIds,
      success: async (authRes: any) => {
        const accepted = Object.values(authRes).some((v) => v === 'accept')
        if (!accepted) { uni.showToast({ title: '未授权通知', icon: 'none' }); return }
        try {
          await request({ url: '/notify/subscribe', method: 'POST', data: { user_id: dbUserId, subscribed: true } })
          notifySubscribed.value = true
          uni.showToast({ title: '已开启学习通知', icon: 'success' })
        } catch { uni.showToast({ title: '开启失败', icon: 'none' }) }
      },
      fail: () => uni.showToast({ title: '订阅失败，请重试', icon: 'none' }),
    })
  }
}

const goReport = () => {
  uni.navigateTo({ url: '/pages/report/index' })
}

const goPreview = () => {
  uni.navigateTo({ url: '/pages/preview/index' })
}

const goChatHistory = () => {
  uni.navigateTo({ url: '/pages/chat-history/index' })
}

const goAbout = () => {
  uni.showToast({ title: 'AI助学 v1.0', icon: 'none' })
}

const loadGrowth = async () => {
  const active = students.value.find(s => s.is_active)
  const grade = active?.grade || 3
  try {
    stats.value = await getUserStats()
  } catch {
    stats.value = null
  }
  try {
    summary.value = await getParentSummary({ days: 7, grade })
  } catch {
    summary.value = null
  }
}

onMounted(async () => {
  await loadStudents()
  loadGrowth()
})
</script>

<style scoped>
.container {
  padding: 30rpx;
  min-height: 100vh;
  background: #EEF2FF;
}

.user-card {
  display: flex;
  align-items: center;
  background: linear-gradient(135deg, #818CF8, #4F46E5);
  border-radius: 24rpx;
  padding: 40rpx;
  margin-bottom: 30rpx;
  box-shadow: 4rpx 4rpx 16rpx rgba(79, 70, 229, 0.25), inset 0 2rpx 4rpx rgba(255, 255, 255, 0.2);
}

.avatar {
  font-size: 80rpx;
  margin-right: 24rpx;
}

.user-info {
  flex: 1;
}

.nickname {
  font-size: 36rpx;
  font-weight: bold;
  color: #fff;
  display: block;
  margin-bottom: 8rpx;
}

.login-status {
  font-size: 26rpx;
  color: rgba(255, 255, 255, 0.7);
}

.logged { color: #4CAF50; }

.section {
  background: #fff;
  border-radius: 24rpx;
  padding: 30rpx;
  margin-bottom: 24rpx;
  border: 3rpx solid #E0E7FF;
  box-shadow: 4rpx 4rpx 12rpx rgba(79, 70, 229, 0.06), inset -2rpx -2rpx 6rpx rgba(79, 70, 229, 0.03);
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20rpx;
}

.section-title {
  font-size: 30rpx;
  font-weight: bold;
  color: #312E81;
}

.add-btn {
  font-size: 28rpx;
  color: #4F46E5;
  font-weight: bold;
}

.empty-tip {
  text-align: center;
  padding: 30rpx;
  font-size: 26rpx;
  color: #999;
}

.student-card {
  display: flex;
  align-items: center;
  padding: 20rpx;
  border-radius: 12rpx;
  margin-bottom: 12rpx;
  background: #f8f9fa;
}

.student-card.active {
  background: #e3f2fd;
  border: 2rpx solid #4F46E5;
}

.student-avatar {
  font-size: 48rpx;
  margin-right: 20rpx;
}

.student-info {
  flex: 1;
}

.student-name {
  font-size: 30rpx;
  font-weight: bold;
  color: #333;
  display: block;
}

.student-grade {
  font-size: 26rpx;
  color: #999;
}

.active-tag {
  background: #4F46E5;
  color: #fff;
  font-size: 22rpx;
  padding: 4rpx 12rpx;
  border-radius: 8rpx;
}

.student-edit {
  margin-left: 16rpx;
  font-size: 24rpx;
  color: #4F46E5;
  padding: 6rpx 16rpx;
  border: 2rpx solid #C7D2FE;
  border-radius: 999rpx;
}

.reminder-card {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16rpx 0;
}

.reminder-label {
  font-size: 28rpx;
  color: #555;
}

.reminder-time {
  font-size: 28rpx;
  color: #4F46E5;
  font-weight: bold;
}

.notify-btn {
  padding: 10rpx 28rpx;
  border-radius: 28rpx;
  font-size: 24rpx;
  font-weight: 600;
}

.notify-on {
  background: linear-gradient(135deg, #86EFAC, #22C55E);
}

.notify-off {
  background: linear-gradient(135deg, #818CF8, #4F46E5);
}

.notify-btn-text {
  color: #fff;
}

.menu-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 24rpx 0;
  border-bottom: 1rpx solid #f0f0f0;
  font-size: 30rpx;
  color: #333;
}

.arrow {
  color: #ccc;
  font-size: 28rpx;
}

.logout {
  color: #FF6B6B;
  justify-content: center;
  border: none;
}

.modal-mask {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 999;
}

.modal-content {
  background: #fff;
  border-radius: 20rpx;
  padding: 40rpx;
  width: 80%;
}

.modal-title {
  font-size: 34rpx;
  font-weight: bold;
  text-align: center;
  display: block;
  margin-bottom: 30rpx;
}

.modal-input {
  border: 2rpx solid #e0e0e0;
  border-radius: 12rpx;
  padding: 20rpx;
  font-size: 30rpx;
  margin-bottom: 20rpx;
}

.grade-picker {
  display: flex;
  gap: 12rpx;
  margin-bottom: 30rpx;
}

.grade-btn {
  flex: 1;
  text-align: center;
  padding: 16rpx 0;
  background: #EEF2FF;
  border-radius: 12rpx;
  font-size: 28rpx;
  color: #666;
}

.grade-btn.active {
  background: #4F46E5;
  color: #fff;
}

.avatar-picker {
  display: flex;
  gap: 16rpx;
  margin-bottom: 24rpx;
}

.avatar-option {
  width: 72rpx;
  height: 72rpx;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 40rpx;
  border-radius: 50%;
  border: 2rpx solid #e0e0e0;
}

.avatar-option.active {
  border-color: #4F46E5;
  border-width: 4rpx;
  background: #EEF2FF;
}

.modal-actions {
  display: flex;
  gap: 20rpx;
}

.btn-cancel, .btn-confirm {
  flex: 1;
  text-align: center;
  padding: 20rpx 0;
  border-radius: 12rpx;
  font-size: 30rpx;
}

.btn-cancel {
  background: #EEF2FF;
  color: #666;
}

.btn-confirm {
  background: #4F46E5;
  color: #fff;
  font-weight: bold;
}

.growth-stats {
  display: flex;
  gap: 16rpx;
  margin-top: 16rpx;
}

.growth-item {
  flex: 1;
  text-align: center;
  padding: 24rpx 0;
  border-radius: 16rpx;
  background: #EEF2FF;
}

.growth-num {
  display: block;
  font-size: 44rpx;
  font-weight: 800;
  color: #4F46E5;
}

.growth-label {
  display: block;
  font-size: 24rpx;
  color: #6B7280;
  margin-top: 4rpx;
}

.badge-list {
  display: flex;
  flex-wrap: wrap;
  gap: 12rpx;
  margin-top: 18rpx;
}

.badge-chip {
  padding: 10rpx 18rpx;
  border-radius: 999rpx;
  background: #FEF3C7;
  color: #B45309;
  font-size: 24rpx;
  font-weight: 700;
}

.badge-empty {
  display: block;
  margin-top: 16rpx;
  font-size: 24rpx;
  color: #9CA3AF;
}

.preview-stat {
  display: block;
  margin-top: 14rpx;
  font-size: 26rpx;
  color: #374151;
}

.preview-tips {
  margin-top: 14rpx;
  padding: 18rpx;
  background: #F5F3FF;
  border-radius: 14rpx;
}

.preview-tips-title {
  display: block;
  font-size: 24rpx;
  font-weight: 700;
  color: #7C3AED;
  margin-bottom: 6rpx;
}

.preview-tip {
  display: block;
  font-size: 24rpx;
  color: #4B5563;
  line-height: 1.7;
}
</style>
