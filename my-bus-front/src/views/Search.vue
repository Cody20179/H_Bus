<template>
  <div class="screen search-screen">
    <header class="topbar">
      <button class="btn-back" @click="back">←</button>
      <div class="title">公車查詢</div>
      <div class="spacer"></div>
    </header>

    <main class="main">
      <form class="search-box" @submit.prevent="onSearch">
        <input v-model="q" type="text" placeholder="輸入路線或站牌，例如：公車A / 站A" />
        <button class="btn-primary" type="submit">搜尋</button>
      </form>

      <section class="route-grid">
        <div v-for="r in filteredRoutes" :key="r.id" class="route-card" @click="openDetail(r)">
          <div class="left">
            <div class="name">{{ r.name }}</div>
            <div class="desc">{{ r.from }} → {{ r.to }}</div>
            <div class="meta">下一班：{{ r.next }}（約 {{ r.eta }} 分）</div>
          </div>
          <div class="right">
            <div class="thumb"></div>
            <button class="btn-detail" @click.stop="openDetail(r)">詳細</button>
          </div>
        </div>

        <div v-if="filteredRoutes.length === 0" class="empty">找不到符合 "<strong>{{ q }}</strong>" 的路線</div>
      </section>
    </main>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed } from 'vue'
import { useRouter } from 'vue-router'

const router = useRouter()
const q = ref('')

const routes = reactive([
  { id: 'A', name: '公車 A', from: '站A', to: '站B', next: '11:20', eta: 5 },
  { id: 'B', name: '公車 B', from: '站C', to: '站D', next: '11:27', eta: 12 },
  { id: 'C', name: '公車 C', from: '站E', to: '站F', next: '11:34', eta: 21 },
  { id: 'D', name: '公車 D', from: '站G', to: '站H', next: '11:40', eta: 30 },
  { id: 'E', name: '公車 E', from: '站I', to: '站J', next: '11:50', eta: 45 },
  { id: 'F', name: '公車 F', from: '站K', to: '站L', next: '12:00', eta: 60 }
])

const filteredRoutes = computed(() => {
  const v = q.value.trim().toLowerCase()
  if (!v) return routes
  return routes.filter(r => `${r.name} ${r.from} ${r.to}`.toLowerCase().includes(v))
})

function back(){ router.back() }
function onSearch(){ /* just local filter */ }
function openDetail(r:any){ router.push({ name:'Detail', params:{ id: r.id } }) }
</script>

<style scoped>
.screen{--bg:#0f2e36;--accent:#2bb0c5;--card:#0e3f45;--muted:#cfeef6;min-height:100vh;display:flex;flex-direction:column;color:#fff}
.topbar{display:flex;align-items:center;padding:12px;background:var(--accent);color:#062b33}
.btn-back{background:transparent;border:none;color:#062b33;font-size:18px;padding:6px}
.title{flex:1;text-align:center;font-weight:700}
.main{padding:12px;flex:1;display:flex;flex-direction:column;gap:12px}
.search-box{display:flex;gap:8px}
.search-box input{flex:1;padding:10px;border-radius:10px;border:none;background:#e6fbff11;color:#fff}
.btn-primary{background:#1aa0ab;color:#fff;border:none;padding:10px 12px;border-radius:10px;cursor:pointer}
.route-grid{display:flex;flex-direction:column;gap:12px}
.route-card{display:flex;justify-content:space-between;align-items:center;padding:12px;border-radius:12px;background:linear-gradient(180deg,#0d3b44,#092b33);box-shadow:0 8px 20px rgba(0,0,0,0.25);cursor:pointer}
.left{flex:1}
.name{font-weight:700}
.desc{font-size:13px;opacity:.9;margin-top:4px}
.meta{font-size:12px;color:var(--muted);margin-top:6px}
.right{display:flex;flex-direction:column;align-items:flex-end;gap:8px;margin-left:12px}
.thumb{width:84px;height:48px;border-radius:8px;background:linear-gradient(180deg,#082b31,#06303a)}
.btn-detail{background:#1aa0ab;color:#fff;border:none;padding:8px 10px;border-radius:8px;cursor:pointer}
.empty{padding:20px;text-align:center;color:#bfeefb}
@media(min-width:700px){ .main{max-width:420px;margin:0 auto} }
</style>
