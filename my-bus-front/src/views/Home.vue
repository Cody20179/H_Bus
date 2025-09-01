<template>
  <div class="home-main">
    <!-- 標題區 -->
    <div class="home-header">
      <div class="home-title">花蓮市民小巴</div>
      <div class="home-contact">聯絡資訊: 03-1234567</div>
    </div>

    <!-- 功能按鈕區 -->
    <div class="home-action-row">
      <button class="home-btn" @click="goAllRoutes">ALL</button>
      <button class="home-btn" @click="goMember">會員專區</button>
    </div>

    <!-- 小巴動態 -->
    <div class="home-dynamic">
      {{ dynamicText }}
    </div>

    <!-- 熱門路線 (自動撐滿空間) -->
<div class="home-route-list">
  <div
    v-for="route in routes"
    :key="route.id"
    class="home-route-card"
    @click="goDetail(route.id)"
    
    style="cursor:pointer"
  >
    <div class="route-leftbar"></div>
    <div class="route-main">
      <div class="route-title">{{ route.name }}</div>
      <div class="route-stops">
        <span class="route-stop route-from">{{ route.from_ }}</span>
        <span class="route-arrow">➔</span>
        <span class="route-stop route-to">{{ route.to }}</span>
      </div>
    </div>
  </div>
</div>


    <!-- Footer image -->
    <div class="home-footer-image">
      <img src="/ad.jpg" alt="Footer" />
    </div>
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
const dynamicText = ref('小巴動態：今日所有路線正常運行')
const router = useRouter()

function goDetail(id: string) { router.push(`/detail/${id}`) }

function goMember() {
  router.push('/member')  // 跳到會員頁（請確認路由名稱對應）
}


function goAllRoutes() {
  router.push('/Search')
}

async function fetchRoutes() {
  try {
    const res = await fetch('/api/bus/routes')
    console.log(res)
    if (!res.ok) throw new Error('Fetch failed')
    const data = await res.json()
    console.log(data)
    routes.value = data.slice(0, 2)  // 只取前2個
  } catch {
    routes.value = []
  }
}


onMounted(fetchRoutes)
</script>

<style scoped>
body {
  background: #f7f3ee;
  margin: 0;
  font-family: 'Noto Sans TC', Arial, sans-serif;
}

/* 主容器 */
.home-main {
  width: 100%;
  max-width: 410px;
  min-height: 100vh;
  margin: 0 auto;
  padding: 18px 10px 0 10px;
  display: flex;
  flex-direction: column;
  align-items: center;
  background: #f7f3ee;
  box-sizing: border-box;
}

/* 標題區塊 */
.home-header {
  width: 100%;
  background: linear-gradient(90deg, #ff9364, #ff784b);
  border-radius: 15px;
  margin-bottom: 18px;
  padding: 22px 0 10px 0;
  box-shadow: 0 3px 14px rgba(255,150,120,0.08);
  text-align: center;
}

.home-title {
  font-size: 22px;
  color: #fff;
  font-weight: bold;
  margin-bottom: 3px;
  letter-spacing: 1.5px;
}
.home-contact {
  font-size: 14px;
  color: #fff;
  opacity: 0.84;
  letter-spacing: 0.8px;
}

/* 按鈕列 */
.home-action-row {
  display: flex;
  width: 100%;
  gap: 14px;
  margin-bottom: 14px;
}
.home-btn {
  flex: 1;
  background: linear-gradient(90deg, #fff8f3 70%, #ffe6d8 120%);
  color: #e74c3c;
  font-weight: bold;
  font-size: 17px;
  border: none;
  border-radius: 13px;
  padding: 13px 0;
  box-shadow: 0 2px 10px rgba(255,170,120,0.09);
  cursor: pointer;
  transition: background 0.17s, box-shadow 0.13s;
}

/* 小巴動態 */
.home-dynamic {
  width: 100%;
  background: #ffe9db;
  color: #de8538;
  border-radius: 11px;
  padding: 11px 0;
  text-align: center;
  font-size: 16px;
  margin-bottom: 18px;
  box-shadow: 0 2px 12px rgba(255,180,110,0.09);
  font-weight: 500;
}

/* 熱門路線外層，自動撐滿剩餘空間，卡片均分 */
.home-route-list {
  width: 100%;
  flex: 1 1 auto;
  display: flex;
  flex-direction: column;
  gap: 19px;
  justify-content: stretch;
}

/* 熱門路線卡片 - 高度自動均分剩餘空間，左條+卡片感 */
.home-route-card {
  height: 150px;
  position: relative;
  background: #fff;
  border-radius: 15px;
  box-shadow: 0 2px 14px rgba(255,150,120,0.10);
  display: flex;
  flex-direction: row;
  align-items: stretch;
  margin-bottom: 17px;
  overflow: hidden;
  cursor: pointer;
  transition: box-shadow 0.15s, background 0.13s;
}

.home-route-card:hover {
  background: #fff3ea;
  box-shadow: 0 8px 32px rgba(255,140,70,0.15);
}

.route-leftbar {
  width: 10px;
  background: #ffd8c5;
  border-radius: 10px 0 0 10px;
  margin-right: 0;
}

.route-main {
  flex: 1;
  display: flex;
  flex-direction: column;
  justify-content: center;
  padding: 18px 18px 14px 18px;
  min-width: 0;
}

.route-title {
  color: #ff7f50;
  font-weight: bold;
  font-size: 32px;
  margin-bottom: 6px;
  letter-spacing: 0.5px;
}

.route-stops {
  display: flex;
  align-items: center;
  font-size: 15px;
  gap: 6px;
  font-weight: 500;
}

.route-stop {
  color: #ef914b;
  font-size: 14.7px;
  font-weight: 600;
  max-width: 120px;
  text-overflow: ellipsis;
  overflow: hidden;
  white-space: nowrap;
}

.route-arrow {
  color: #ffb489;
  font-size: 17px;
  margin: 0 3px;
  font-weight: 700;
}
.home-route-desc {
  color: #8d8c89;
  font-size: 15.3px;
  font-weight: 500;
}

/* Footer 圖片 */
.home-footer-image {
  width: 100%;
  margin-top: 18px;
  margin-bottom: 12px;
  display: flex;
  justify-content: center;
}
.home-footer-image img {
  width: 90%;
  max-width: 270px;
  border-radius: 11px;
  object-fit: contain;
}


/* 手機響應 (RWD) */
@media (max-width: 600px) {
  .home-main {
    max-width: 98vw;
    padding: 10px 2vw 0 2vw;
  }
  .home-header, .home-action-row, .home-dynamic, .home-route-list, .home-footer-image {
    width: 100%;
    min-width: 0;
    max-width: 100%;
  }
  .home-footer-image img {
    width: 98vw;
    max-width: 100vw;
  }
  
}
</style>
