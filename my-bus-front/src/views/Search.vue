<template>
  <div class="route-bg">
    <header class="route-header">
      <button class="route-back" @click="goBack">
        <svg width="28" height="28" viewBox="0 0 24 24">
          <path d="M15 18l-6-6 6-6" stroke="#fff" stroke-width="2" fill="none" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>
      </button>
      <div class="route-header-title">花蓮市民小巴路線</div>
      <div style="width:38px;"></div>
    </header>
    <main class="route-list">
      <div
        v-for="route in routes"
        :key="route.id"
        class="route-block"
        @click="goDetail(route.id)"
        tabindex="0"
      >
        <div class="route-main">{{ route.name }}</div>
        <div class="route-path">
          <span class="route-from">{{ route.from_ }}</span>
          <span class="route-arrow">
            <svg width="20" height="20" viewBox="0 0 24 24">
              <path d="M7 12h10m-3-3 3 3-3 3" stroke="#4f8cff" stroke-width="2" fill="none" stroke-linecap="round" stroke-linejoin="round"/>
            </svg>
          </span>
          <span class="route-to">{{ route.to }}</span>
        </div>
      </div>
    </main>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'

interface RouteSimple {
  id: string
  name: string
  from_: string
  to: string
  desc?: string
}
const routes = ref<RouteSimple[]>([])
const router = useRouter()

function goBack() {
  router.push('/')   // 回到首頁
}

function goDetail(id: string) { router.push(`/detail/${id}`) }
async function fetchRoutes() {
  try {
    const res = await fetch('/api/bus/routes/all')
    routes.value = await res.json()
  } catch { routes.value = [] }
}
onMounted(fetchRoutes)
</script>

<style scoped>
/* -------- 完全新設計：暖淺風格（直接替換你原本的 <style scoped>） -------- */

/* 全局基底 */
:global(body) {
  margin: 0 !important;
  padding: 0 !important;
  background: #f4efe7 !important; /* 溫暖淺米色背景 */
  width: 100vw !important;
  box-sizing: border-box;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}

/* 整體容器：模擬你圖中窄列手機版的外觀 */
.route-bg {
  min-height: 100vh;
  width: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 18px 12px;
  box-sizing: border-box;
}

/* 中央內容卡殼 — 讓整體看起來像圖示的窄列卡片，並加圓角與陰影 */
.route-bg > .inner-shell {
  /* 注意：若你的 HTML 沒有 inner-shell 容器也沒關係，
     這裡只是為了示意；主要視覺由下方 route-header/route-list 負責 */
}

/* 標題列：圓潤、暖色漸層（與舊版藍系完全不同） */
.route-header {
  width: 100%;
  max-width: 380px;                /* 與圖示窄版相仿 */
  height: 74px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 14px;
  border-radius: 18px;            /* 圓角外形 */
  background: linear-gradient(180deg, #ff8a65 0%, #ff6f3d 100%); /* 橘紅漸層 */
  color: #fff;
  box-shadow: 0 8px 28px rgba(44,23,16,0.08);
  margin-bottom: 18px;
  box-sizing: border-box;
  position: sticky;
  top: 12px;
  z-index: 30;
}

/* 返回鍵 */
.route-back {
  width: 46px;
  height: 46px;
  display: flex; align-items: center; justify-content: center;
  border-radius: 10px;
  background: rgba(255,255,255,0.08);
  border: none;
  cursor: pointer;
  transition: transform .12s, background .12s;
}
.route-back:hover { transform: translateX(-2px); background: rgba(255,255,255,0.12); }

/* 標題文字更大 */
.route-header-title {
  flex: 1;
  text-align: center;
  font-weight: 800;
  font-size: 1.45rem;    /* 放大標題 */
  color: #fff;
  letter-spacing: 0.02em;
  font-family: 'Noto Sans TC', 'Segoe UI', Arial, sans-serif;
}

/* 列表容器：左右內距、窄列寬度 */
.route-list {
  width: 100%;
  max-width: 380px;   /* 與 header 一致，模擬你圖中窄列 */
  display: flex;
  flex-direction: column;
  gap: 14px;          /* 卡片之間略微間距 */
  padding: 6px 12px 36px 12px;
  box-sizing: border-box;
  margin: 0 auto;
}

/* 每張路線卡：淺灰白底 + 微陰影，並加左側圓形凹槽裝飾 */
.route-block {
  display: flex;
  flex-direction: column;   /* 讓標題與細節上下排列 */
  justify-content: center;
  gap: 8px;
  min-height: 96px;        /* 提升每張卡高度（比你原來大） */
  padding: 14px 18px;
  background: #ffffff;      /* 卡片底色：白，與背景區別明顯 */
  border-radius: 12px;
  border: 1px solid rgba(32,32,32,0.06);
  box-shadow: 0 6px 20px rgba(11,22,26,0.04);
  position: relative;
  overflow: visible;
  cursor: pointer;
  transition: transform .12s ease, box-shadow .14s ease;
}

/* 卡片 hover 效果 */
.route-block:hover {
  transform: translateY(-6px);
  box-shadow: 0 18px 46px rgba(11,22,26,0.08);
}

/* 左側圓角裝飾（類似你圖中卡片與背景的對比區）*/
.route-block::before{
  content: "";
  position: absolute;
  left: -10px;
  top: 12px;
  width: 28px;
  height: calc(100% - 24px);
  border-radius: 12px;
  background: linear-gradient(180deg,#ffd9c2,#ffd0b3); /* 暖系條帶 */
  box-shadow: 0 2px 8px rgba(255,120,70,0.06);
  pointer-events: none;
}

/* 路線名稱（第一行）：大、白底上的深色 */
.route-main {
  font-size: 1.18rem;
  font-weight: 800;
  color: #1f2933;   /* 深炭色，對比白卡背景 */
  margin: 0;
  line-height: 1.05;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  padding-left: 12px; /* 避開左側裝飾 */
}

/* 細節（第二行）：較小、偏灰、固定位於第二行 */
.route-path {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 0.95rem;
  color: #5b636e;   /* 較柔和的灰色文字 */
  font-weight: 600;
  padding-left: 12px; /* 與標題對齊 */
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

/* 從與到的欄位（仍保留原 class 名）*/
.route-from, .route-to {
  max-width: calc(100% - 80px);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  color: #2b3440;
}

/* 箭頭顏色與大小（顯眼但不突兀） */
.route-arrow svg { width: 16px; height: 16px; }
.route-arrow path { stroke: #ff6f3d; stroke-width: 2; }

/* 如果你希望卡片裡另加小描述，可用此 */
.route-desc {
  font-size: 0.88rem;
  color: #7b8188;
  margin-top: 4px;
  padding-left: 12px;
}

/* 底部留白或弧形效果（參考圖示底部弧形） */
.route-list::after{
  content: "";
  display: block;
  height: 22px;
  width: 100%;
  max-width: 380px;
  margin: 8px auto 60px auto;
  border-bottom-left-radius: 16px;
  border-bottom-right-radius: 16px;
  background: linear-gradient(180deg, transparent, rgba(0,0,0,0.02));
  pointer-events: none;
}

/* 手機響應：寬度改為 100%，字體微縮 */
@media (max-width: 420px){
  .route-header { max-width: 100%; height: 72px; padding: 8px 10px; border-radius: 14px; }
  .route-header-title { font-size: 1.28rem; }
  .route-list { max-width: 100%; padding: 10px; gap: 12px; }
  .route-block { min-height: 86px; padding: 12px 14px; border-radius: 10px; }
  .route-block::before { left: -8px; width: 22px; top: 10px; height: calc(100% - 20px); border-radius: 10px; }
  .route-main { font-size: 1.02rem; padding-left: 10px; }
  .route-path { font-size: 0.9rem; padding-left: 10px; }
  .route-from, .route-to { max-width: 68%; }
}
</style>
