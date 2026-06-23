<script setup lang="ts">
import { onLaunch, onShow, onHide } from "@dcloudio/uni-app";

async function silentLogin() {
  const token = uni.getStorageSync('token')
  if (token) return  // 已登录，跳过

  return new Promise<void>((resolve) => {
    uni.login({
      success: async (res) => {
        if (!res.code) { resolve(); return }
        try {
          const { wxLogin } = await import('@/api/auth')
          const result = await wxLogin(res.code)
          uni.setStorageSync('token', result.token)
          uni.setStorageSync('db_user_id', result.user_id)
          uni.setStorageSync('nickname', result.nickname)
        } catch {
          // 静默失败，用户仍可匿名使用
        }
        resolve()
      },
      fail: () => resolve(),
    })
  })
}

onLaunch(() => {
  silentLogin()
});
onShow(() => {});
onHide(() => {});
</script>
<style>
/* ===== 全局字体：偏圆润、儿童友好的系统字体栈 =====
   page 用于微信小程序，body/uni-page-body 用于 H5，双端覆盖 */
page,
body,
uni-page-body {
  font-family: "PingFang SC", "MiSans", "HarmonyOS Sans SC",
    "Source Han Sans CN", "Microsoft YaHei", system-ui, -apple-system, sans-serif;
  background-color: #EEF2FF;
}

/* ===== Claymorphism 软按压反馈 =====
   用法：<view class="clay-tap" hover-class="clay-pressed" hover-stay-time="100">
   clay-tap 提供平滑过渡，clay-pressed 在按下时由 uni-app 自动添加 */
.clay-tap {
  transition: transform 0.16s ease-out, box-shadow 0.16s ease-out, opacity 0.16s ease-out;
}
.clay-pressed {
  transform: scale(0.965);
  opacity: 0.94;
}

/* ===== 尊重"减少动态效果"无障碍偏好 ===== */
@media (prefers-reduced-motion: reduce) {
  .clay-tap {
    transition: none;
  }
  .clay-pressed {
    transform: none;
  }
}
</style>
