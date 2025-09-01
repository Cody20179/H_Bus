<template>
  <div class="detail-main-bg">
    <!-- Header 區塊 -->
    <div class="detail-header">
      <button class="back-btn" @click="goBack">←</button>
      {{ routeTitle }}
    </div>

    <!-- 去回程切換按鈕 -->
    <div class="stop-tabs">
      <button
        class="stop-tab"
        :class="{ active: direction === 0 }"
        @click="changeDirection(0)"
      >路線表</button>
      <!-- <button
        v-if="hasReturn"
        class="stop-tab"
        :class="{ active: direction === 1 }"
        @click="changeDirection(1)"
      >回程</button> -->
    </div>

    <!-- 站點列表 -->
    <div class="stop-list-wrap" v-if="routeDetail && routeDetail.stations && routeDetail.stations.length">
      <div
        v-for="(stop, idx) in routeDetail.stations"
        :key="idx"
        :class="[
          'stop-row',
          { current: idx === currentIndex, next: idx === currentIndex + 1 }
        ]"
      >
        <div>
          <div class="stop-title">
            {{ stop.station_name }}
            <span v-if="idx === currentIndex" class="at-stop-badge">到站中</span>
            <span v-else-if="idx === currentIndex + 1" class="next-stop-badge">下一站</span>
          </div>
          <div class="stop-subtitle" v-if="stop.note">{{ stop.note }}</div>
        </div>
        <div class="stop-time">
          <span v-if="stop.interval_minutes">間隔 {{ stop.interval_minutes }} 分</span>
        </div>
      </div>
    </div>

  </div>
</template>

<script setup lang="ts">
import { ref, watch, onMounted, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'

const route = useRoute()
const router = useRouter()
const routeDetail = ref<any>(null)
const direction = ref(0)  // 0: 去程, 1: 回程
const hasReturn = ref(false)  // 是否有回程
const currentIndex = ref(0) // 可根據實際需求做當前站計算

const routeTitle = computed(() => {
  if (!routeDetail.value || !routeDetail.value.stations || routeDetail.value.stations.length === 0) {
    return '路線詳情'
  }
  const first = routeDetail.value.stations[0]?.station_name
  const last = routeDetail.value.stations[routeDetail.value.stations.length - 1]?.station_name
  return `${first} - ${last}`
})


function goBack() {
  router.push('/search')
}

function changeDirection(dir: number) {
  if (direction.value !== dir) {
    direction.value = dir
    fetchDetail()
  }
}

async function checkHasReturn() {
  const id = route.params.route
  const res = await fetch(`/api/bus/detail/${id}?direction=1`)
  hasReturn.value = false
  if (res.ok) {
    const data = await res.json()
    // 如果 direction=1 有資料就顯示回程按鈕
    if (data && Array.isArray(data.stations) && data.stations.length > 0) {
      hasReturn.value = true
    }
  }
}

async function fetchDetail() {
  // 用 route.params.route
  const routeKey = route.params.route
  if (!routeKey) return
  const res = await fetch(`/api/bus/detail/${routeKey}?direction=${direction.value}`)
  if (res.ok) {
    routeDetail.value = await res.json()
  } else {
    routeDetail.value = { stations: [] }
  }
}

watch(() => route.params.route, () => {
  fetchDetail()
  checkHasReturn()
})
watch(direction, fetchDetail)
onMounted(() => {
  fetchDetail()
  checkHasReturn()
})
</script>


<style scoped>
.detail-main-bg {
  background: #f7f3ee;
  min-height: 100vh;
  padding: 0;
}
.detail-header {
  position: relative;
  background: linear-gradient(90deg, #ff9364, #ff784b);
  color: #fff;
  border-radius: 0 0 18px 18px;
  padding: 24px 0 17px 0;
  box-shadow: 0 3px 14px rgba(255,150,120,0.10);
  font-weight: bold;
  text-align: center;
  letter-spacing: 1.2px;
  font-size: 22px;
}
.back-btn {
  position: absolute;
  left: 12px;
  top: 20px;
  font-size: 22px;
  background: none;
  border: none;
  color: #fff;
  cursor: pointer;
  z-index: 10;
}

.info-bar {
  background: #fff;
  border-radius: 16px;
  box-shadow: 0 2px 14px rgba(255,150,120,0.10);
  margin: 20px auto 18px auto;
  max-width: 97%;
  display: flex;
  flex-direction: row;
  align-items: stretch;
  justify-content: space-between;
  padding: 20px 23px 20px 23px;
  gap: 18px;
  min-height: 100px;
}

.info-text {
  flex: 1 1 auto;
  display: flex;
  flex-direction: column;
  justify-content: center;
  gap: 7px;
}
.info-label {
  color: #e9601e;
  font-size: 17.5px;
  font-weight: bold;
  margin-right: 2px;
  letter-spacing: 1.5px;
}
.info-current {
  color: #e9601e;
  font-size: 19px;
  font-weight: bold;
}
.info-next {
  color: #ff9542;
  font-size: 18px;
  font-weight: bold;
}
.info-bus {
  color: #a86b2d;
  margin-top: 5px;
  font-size: 16px;
  font-weight: bold;
}

.detail-map-btn {
  align-self: flex-start;
  background: linear-gradient(90deg, #fff8f3 70%, #ffe6d8 120%);
  color: #e4673c;
  border: none;
  border-radius: 11px;
  font-size: 16px;
  font-weight: bold;
  box-shadow: 0 2px 10px rgba(255,170,120,0.09);
  padding: 9px 24px;
  cursor: pointer;
  transition: background 0.18s;
  margin-top: 6px;
  min-width: 100px;
}

.route-switch-wrap {
  width: 97%;
  margin: 0 auto 17px auto;
  display: flex;
  justify-content: flex-start;
}

.route-switch {
  background: #ff9364;
  color: #fff;
  font-weight: bold;
  font-size: 18px;
  border-radius: 10px;
  border: 2px solid #ff9364;
  min-width: 120px;
  padding: 10px 0;
  transition: all 0.18s;
  box-shadow: 0 2px 8px rgba(255,160,90,0.07);
  cursor: pointer;
}
.route-switch:not(.active) {
  background: #ffe9db;
  color: #e4673c;
  border: 2px solid #ff9364;
}
.route-switch:active {
  filter: brightness(0.95);
}

.stop-list-wrap {
  margin: 0 auto;
  max-width: 97%;
}
.stop-row {
  background: #fff;
  border-radius: 14px;
  box-shadow: 0 1px 10px rgba(255,170,120,0.07);
  padding: 18px 16px;
  margin-bottom: 14px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  transition: box-shadow 0.17s, background 0.14s;
}
.stop-row.current {
  background: #ff725b !important;
  border-left: 8px solid #ff3a18 !important;
  color: #fff !important;
}
.stop-row.current .stop-title, .stop-row.current .stop-subtitle, .stop-row.current .stop-time {
  color: #fff !important;
}
.stop-row.next {
  background: #ffe49b !important;
  border-left: 8px solid #ffd85c !important;
  color: #bf7600 !important;
}
.stop-row.next .stop-title, .stop-row.next .stop-subtitle, .stop-row.next .stop-time {
  color: #bf7600 !important;
}
.stop-row .stop-time {
  min-width: 44px;
  text-align: center;
  font-size: 18px;
  font-weight: bold;
  margin-left: 6px;
}
.stop-title {
  font-weight: bold;
  color: #ff7f50;
  font-size: 18.5px;
  margin-bottom: 4px;
}
.stop-subtitle {
  color: #a59b93;
  font-size: 15px;
}
.at-stop-badge {
  display: inline-block;
  background: #fff;
  color: #ff3a18;
  border-radius: 9px;
  font-size: 12px;
  font-weight: bold;
  margin-left: 7px;
  padding: 1px 9px;
  box-shadow: 0 1px 5px rgba(255,170,120,0.06);
  vertical-align: middle;
}
.stop-tabs {
  display: flex;
  gap: 0;
  margin-bottom: 12px;
  margin-top: 10px;
  border-radius: 14px;
  overflow: hidden;
  width: 100%;
  background: none;
}
.stop-tab {
  flex: 1 1 0;
  background: #fff3ea;
  border: none;
  border-radius: 0;
  padding: 16px 0;
  color: #ff9650;
  font-weight: bold;
  font-size: 22px;
  transition: all 0.16s;
  cursor: pointer;
  box-shadow: none;
  border-bottom: 2px solid transparent;
  letter-spacing: 2.5px;
}
.stop-tab.active {
  background: linear-gradient(90deg, #ff9364 80%, #ffb588);
  color: #fff;
  border-radius: 18px;
  border: 2.2px solid #222;
  box-shadow: 0 2px 12px rgba(255,150,100,0.08);
}
.stop-tab:not(.active) {
  color: #e88c52;
  background: #fff3ea;
}

.next-stop-badge {
  display: inline-block;
  background: #ffe49b;
  color: #bf7600;
  border-radius: 9px;
  font-size: 12px;
  font-weight: bold;
  margin-left: 7px;
  padding: 1px 9px;
  box-shadow: 0 1px 5px rgba(255,170,120,0.06);
  vertical-align: middle;
}
@media (max-width: 600px) {
  .detail-main-bg, .info-bar, .stop-list-wrap {
    max-width: 100%;
    padding: 0 0;
  }
  .info-bar, .stop-list-wrap {
    margin-left: 3vw;
    margin-right: 3vw;
  }
}
</style>
