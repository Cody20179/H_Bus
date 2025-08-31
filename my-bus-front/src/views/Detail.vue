<template>
  <div class="screen detail-screen">
    <header class="topbar">
      <button class="btn-back" @click="back">←</button>
      <div class="title">{{ routeData?.name || '路線' }}</div>
      <div class="spacer"></div>
    </header>

    <main class="main">
      <section class="route-card">
        <div>
          <div class="route-title">{{ routeData?.name }}</div>
          <div class="route-line">{{ routeData?.from }} → {{ routeData?.to }}</div>
          <div class="next">下一班：{{ routeData?.next }}（約 {{ routeData?.eta }} 分）</div>
        </div>
        <div><button class="btn-outline" @click="openMap">查看地圖</button></div>
      </section>

      <section class="tabs">
        <button :class="{active: tab==='A'}" @click="tab='A'">往A</button>
        <button :class="{active: tab==='B'}" @click="tab='B'">往B</button>
      </section>

      <section class="rows-wrap" v-if="routeData">
        <div class="center-line" aria-hidden="true"></div>

        <div class="row" v-for="(stop, idx) in stopsToShow" :key="idx">
          <div class="cell stop-cell">
            <div class="stop-card" @click="onStopClick(idx)">
              <div class="stop-icon">
                <svg width="28" height="28" viewBox="0 0 24 24" fill="none"><rect x="2" y="4" width="20" height="11" rx="2" fill="rgba(0,0,0,0.04)"/><circle cx="8.5" cy="18" r="1.6" fill="#111"/><circle cx="15.5" cy="18" r="1.6" fill="#111"/></svg>
              </div>
              <div class="stop-name-wrap">
                <div class="stop-name">{{ stop }}</div>
                <div v-if="routeData?.stopNotes?.[idx]" class="stop-note">{{ routeData.stopNotes[idx] }}</div>
              </div>
            </div>
          </div>

          <div class="cell center-cell">
            <div class="circle-wrap">
              <template v-if="idx === currentIndex">
                <div class="vehicle-chip">🚍</div>
              </template>
              <template v-else>
                <div class="dot"></div>
              </template>
            </div>
          </div>

          <div class="cell time-cell">
            <div class="time-pill" :class="statusClass(times[idx])">{{ times[idx] || '--:--' }}</div>
          </div>
        </div>
      </section>
    </main>
  </div>
</template>

<script setup lang="ts">
import { computed, reactive, ref, onMounted, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'

const route = useRoute()
const router = useRouter()
const id = String(route.params.id || '')

const routes = reactive([
  { id:'A', name:'公車 A', from:'站A', to:'站B', next:'11:20', eta:5,
    stops:['站A','站X','站Y','站B','站C','站D','站E'], times:['11:20','11:24','11:27','11:30','11:34','11:40','11:45'], stopNotes:['首站','','轉乘','','','','末站'] },
  { id:'B', name:'公車 B', from:'站C', to:'站D', next:'11:27', eta:12,
    stops:['站C','站Y','站Z','站D'], times:['11:27','11:34','11:40','11:50'], stopNotes:['','快速班','','末站'] }
])

const routeData = computed(() => routes.find(r => r.id === id) || routes[0] || null)
const tab = ref<'A'|'B'>('A')
const currentIndex = ref(0)

const stopsToShow = computed(() => {
  if (!routeData.value) return []
  return tab.value === 'A' ? routeData.value.stops : [...routeData.value.stops].reverse()
})
const times = computed(() => {
  if (!routeData.value) return []
  return tab.value === 'A' ? routeData.value.times : [...routeData.value.times].reverse()
})

function back(){ router.back() }
function openMap(){ alert('查看地圖（示範）') }
function onStopClick(idx:number){ alert(`你點了 ${stopsToShow.value[idx]}`) }
function statusClass(val?: string){
  if (!val) return ''
  const v = String(val).toLowerCase()
  if (v.includes('進站')) return 'status-arrived'
  if (v.includes('即將')) return 'status-approach'
  if (/^\d{1,2}:\d{2}$/.test(v)) return 'status-on'
  return ''
}

/* demo auto-advance */
let timer: number | null = null
onMounted(() => {
  timer = window.setInterval(() => {
    currentIndex.value = (currentIndex.value + 1) % Math.max(stopsToShow.value.length, 1)
  }, 4000)
})
onUnmounted(() => {
  if (timer) window.clearInterval(timer)
})
</script>

<style scoped>
.screen{font-family:system-ui, -apple-system, "Noto Sans TC", Arial;min-height:100vh}
.detail-screen{--bg:#f6f7f8;--accent:#2bb0c5;--card:#fff;--line:#d9534f;--muted:#6b7680;background:var(--bg);color:#111;display:flex;flex-direction:column}
.topbar{display:flex;align-items:center;padding:12px;background:var(--accent);color:#fff}
.btn-back{background:transparent;border:none;color:#fff;font-size:18px;padding:6px}
.title{flex:1;text-align:center;font-weight:700}
.main{padding:12px;flex:1;display:flex;flex-direction:column;gap:12px;background:transparent}
.route-card{display:flex;justify-content:space-between;align-items:center;background:var(--card);padding:12px;border-radius:10px;box-shadow:0 6px 18px rgba(0,0,0,0.06)}
.route-title{font-weight:800}
.route-line{color:var(--muted);margin-top:6px}
.btn-outline{background:transparent;border:1px solid rgba(0,0,0,0.06);padding:8px 10px;border-radius:999px;color:var(--accent)}
.tabs{display:flex;gap:8px}
.tabs button{flex:1;padding:10px;border-radius:20px;border:none;background:transparent;color:var(--muted);font-weight:600}
.tabs button.active{background:linear-gradient(90deg,rgba(43,176,197,0.12),rgba(43,176,197,0.06));color:var(--accent)}
.rows-wrap{display:grid;grid-template-columns:170px 64px 1fr;row-gap:18px;position:relative;padding:8px 6px}
.center-line{grid-column:2;grid-row:1/-1;justify-self:center;align-self:stretch;position:relative;z-index:0}
.center-line::before{content:'';position:absolute;left:50%;top:0;bottom:0;transform:translateX(-50%);width:6px;border-radius:6px;background:var(--line);box-shadow:0 4px 12px rgba(0,0,0,0.06)}
.row{grid-column:1/-1;display:grid;grid-template-columns:170px 64px 1fr;align-items:center;gap:8px;z-index:1;min-height:56px}
.stop-card{display:flex;align-items:center;gap:10px;width:100%;padding:8px;border-radius:10px;background:var(--card);box-shadow:0 10px 24px rgba(0,0,0,0.06);border:1px solid rgba(0,0,0,0.04);cursor:pointer}
.stop-cell{display:flex;align-items:center;justify-content:center}
.stop-icon svg{width:32px;height:32px}
.stop-name-wrap{display:flex;flex-direction:column;align-items:center}
.stop-name{font-weight:700}
.stop-note{font-size:12px;color:var(--muted);margin-top:4px}
.center-cell{display:flex;align-items:center;justify-content:center}
.circle-wrap{width:100%;display:flex;justify-content:center;align-items:center}
.dot{width:12px;height:12px;border-radius:50%;background:#f6bfdc;border:3px solid #f6bfdc}
.vehicle-chip{display:inline-flex;align-items:center;justify-content:center;min-width:40px;height:28px;padding:0 8px;border-radius:16px;background:linear-gradient(180deg,#ff8aa3,#ff5b7f);color:#fff;font-weight:700;box-shadow:0 10px 24px rgba(0,0,0,0.12)}
.time-cell{display:flex;justify-content:flex-end}
.time-pill{padding:8px 14px;border-radius:999px;background:#f0f3f4;color:#111;min-width:72px;text-align:center;font-weight:700;box-shadow:0 8px 20px rgba(0,0,0,0.06)}
.time-pill.status-on{background:#46b97a;color:#fff}
.time-pill.status-approach{background:#f5a623;color:#111}
.time-pill.status-arrived{background:#e74c3c;color:#fff}
@media(min-width:900px){ .content{max-width:900px;margin:0 auto} .rows-wrap{grid-template-columns:220px 64px 1fr} .row{grid-template-columns:220px 64px 1fr;min-height:64px} }
</style>
