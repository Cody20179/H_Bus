<template>
  <div class="home-screen">
    <header class="topbar" role="banner" aria-label="網站標題">
      <div class="brand">
        <div class="app-name">小巴動態</div>
      </div>
    </header>

    <main class="main" role="main">
      <!-- 單一大型搜尋欄 -->
      <section class="search-area" aria-label="搜尋路線或站牌">
        <div class="search-box">
          <input
            id="q"
            v-model="q"
            type="search"
            inputmode="search"
            placeholder="輸入路線或站牌（例如：公車A、站A）"
            aria-label="輸入路線或站牌"
            @keyup.enter="doSearch"
          />
          <button class="btn-search" @click="doSearch" aria-label="搜尋">搜尋</button>
        </div>

        <div class="member-actions">
          <button class="btn-search" @click="$router.push('/search')">所有路線</button>
          <button class="btn-login" @click="goLogin">會員登入</button>
        </div>

        <div class="quick-note">只需輸入一個關鍵字即可快速查詢</div>
      </section>

      <!-- 熱門兩條 -->
      <section class="popular" aria-label="熱門路線">
        <h2 class="section-title">熱門路線</h2>

        <ul class="popular-list">
          <li v-for="r in topRoutes" :key="r.id" class="popular-item">
            <button class="route-card" @click="openDetail(r)" :aria-label="`查看 ${r.name}`">
              <!-- ===== Live info (放在站牌上方) ===== -->
              <div class="live-box" :class="`live-${r.live.status}`" role="status" aria-live="polite">
                <div class="live-left">
                  <svg class="bus-icon" viewBox="0 0 24 24" aria-hidden="true">
                    <rect x="3" y="4" width="18" height="12" rx="2" />
                    <circle cx="7.5" cy="18.5" r="1.4" />
                    <circle cx="16.5" cy="18.5" r="1.4" />
                  </svg>
                  <div class="live-text">
                    <div class="live-status">{{ liveLabel(r.live.status) }}</div>
                    <div class="live-sub">{{ r.live.subtitle }}</div>
                  </div>
                </div>
                <div class="live-right">
                  <div class="arrival-small" v-if="r.live.nextArrivals?.length">
                    {{ r.live.nextArrivals[0] }}
                    <span class="next-more" v-if="r.live.nextArrivals.length>1"> • {{ r.live.nextArrivals.length-1 }} more</span>
                  </div>
                </div>
              </div>

              <!-- 主要內容 -->
              <div class="route-body">
                <div class="route-left">
                  <div class="route-name">{{ r.name }}</div>
                  <div class="route-desc">{{ r.from }} → {{ r.to }}</div>
                  <div class="route-next">下一班：{{ r.next }}（約 {{ r.eta }} 分）</div>
                </div>
                <div class="route-action">
                  <span class="chev">詳細 ➜</span>
                </div>
              </div>
            </button>
          </li>
        </ul>
      </section>
    </main>

    <!-- 底部廣告 / 超連結欄（請放 public/ad.jpg 或改 src） -->
    <footer class="ad-footer" role="contentinfo">
      <a class="ad-link" :href="adUrl" target="_blank" rel="noopener noreferrer" aria-label="點擊查看廣告">
        <img src="/ad.jpg" alt="活動廣告" class="ad-image" />
      </a>
    </footer>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, reactive, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'

const router = useRouter()
const q = ref('')

/* 範例路線含 live info（real app 請改為後端回傳） */
const allRoutes = reactive([
  {
    id: 'A',
    name: '公車 A',
    from: '站A',
    to: '站B',
    next: '11:20',
    eta: 5,
    live: { status: 'approaching', subtitle: '2站外 • 約 4 分', nextArrivals: ['11:20', '11:35'] }
  },
  {
    id: 'B',
    name: '公車 B',
    from: '站C',
    to: '站D',
    next: '11:27',
    eta: 12,
    live: { status: 'normal', subtitle: '正常 • 依班表', nextArrivals: ['11:27', '11:40'] }
  },
  {
    id: 'C',
    name: '公車 C',
    from: '站E',
    to: '站F',
    next: '11:34',
    eta: 21,
    live: { status: 'delayed', subtitle: '延誤中 • +8 分', nextArrivals: ['11:42'] }
  }
])

const topRoutes = computed(() => allRoutes.slice(0, 2))
const adUrl = 'https://example.com'

function doSearch() {
  const v = q.value.trim()
  if (!v) {
    alert('請輸入路線或站牌，例如：公車A 或 站A')
    return
  }
  router.push({ path: '/search', query: { q: v } })
}

function openDetail(r: any) {
  router.push({ name: 'Detail', params: { id: r.id } })
}
function goRegister() { router.push('/register') }
function goLogin() { router.push('/login') }

/* liveLabel helper */
function liveLabel(status: string) {
  if (status === 'approaching') return '即將進站'
  if (status === 'arrived') return '進站中'
  if (status === 'delayed') return '延誤'
  return '正常'
}

/* -- Demo: mock auto-change live statuses every 6s --
   在真實專案把這段改為 fetch / websocket 訂閱即可 */
let timer: number | null = null
onMounted(() => {
  timer = window.setInterval(() => {
    // 亂數模擬狀態改變（示範）
    allRoutes.forEach((r, i) => {
      const chance = Math.random()
      if (chance < 0.2) {
        r.live.status = 'arrived'
        r.live.subtitle = `${Math.floor(Math.random()*2)+1} 站外 • 即將到站`
        r.live.nextArrivals = ['進站中']
      } else if (chance < 0.6) {
        r.live.status = 'approaching'
        r.live.subtitle = `${Math.floor(Math.random()*3)+1} 站外 • 約 ${Math.floor(Math.random()*6)+2} 分`
        r.live.nextArrivals = ['11:20','11:35']
      } else if (chance < 0.85) {
        r.live.status = 'normal'
        r.live.subtitle = '正常 • 依班表'
        r.live.nextArrivals = ['11:27']
      } else {
        r.live.status = 'delayed'
        r.live.subtitle = `延誤 +${Math.floor(Math.random()*10)+3} 分`
        r.live.nextArrivals = ['12:00']
      }
    })
  }, 6000)
})
onUnmounted(() => {
  if (timer) window.clearInterval(timer)
})
</script>

<style scoped>

.app-name{
  font-size:24px;
  font-weight:700;
  color: #1a293a; /* ← 改這裡，直接深藍或深灰 */
  letter-spacing:0.2px;
}


.home-screen{
  --bg-900: #f7fafc;           /* 頁面背景 */
  --bg-800: #f1f5f9;
  --card: #fff;                /* 卡片白 */
  --glass: rgba(255,255,255,0.78);
  --accent: #ff7a30;           /* 強調橘 */
  --accent-hover: #f05c00;
  --accent-2: #257baf;         /* 補色-科技藍 */
  --ok: #38b000;
  --warn: #ffd600;
  --danger: #f94c57;
  --text: #181f2a;             /* 主文字 */
  --muted: #8c9cab;
  --border: #e6ecf2;
  --shadow-1: 0 4px 24px 0 rgba(24,31,42,0.07);
  --shadow-2: 0 1.5px 6px 0 rgba(0,0,0,0.03);

  min-height:100vh;
  background: var(--bg-900);
  color: var(--text);
  font-family: "Inter", "Noto Sans TC", system-ui, -apple-system, Arial, "PingFang TC";
  -webkit-font-smoothing:antialiased;
}

.topbar{
  padding:18px 0 12px 0;
  background: transparent;
  display:flex;
  align-items:center;
  justify-content:center;
  border-bottom: 1.5px solid var(--border);
}
.app-name{
  font-size:36px;
  font-weight:700;
  color: #1a293a !important;
  letter-spacing:0.2px;
}

/* main */
.main{
  padding:24px 0 0 0;
  display:flex;
  flex-direction:column;
  gap:18px;
  align-items:center;
}

/* search */
.search-area{ width:100%; display:flex; flex-direction:column; gap:12px; align-items:center; }
.search-box{
  width:100%;
  max-width:760px;
  display:flex;
  gap:10px;
  align-items:center;
  background: var(--card);
  border-radius: 12px;
  box-shadow: var(--shadow-1);
  border:1.5px solid var(--border);
  padding:6px 8px;
}
.search-box input{
  flex:1;
  font-size:17px;
  padding:12px 16px;
  border:none;
  border-radius:10px;
  background:transparent;
  color: var(--text);
}
.search-box input::placeholder{ color: var(--muted); font-size:16px; }
.search-box input:focus{ outline: none; background: #f3f5f8; }

.btn-search{
  min-width:108px;
  border-radius:10px;
  padding:11px 0;
  font-weight:700;
  font-size:15px;
  color:#fff;
  background: var(--accent);
  border:none;
  cursor:pointer;
  box-shadow: 0 4px 20px rgba(255,122,48,0.09);
  transition: background .15s, transform .12s;
}
.btn-search:hover{ background: var(--accent-hover); transform: translateY(-1.5px);}
.btn-search:active{ background: var(--accent-2); }

.member-actions{
  width:100%; max-width:760px; display:flex; gap:10px; justify-content:center;
}
.btn-register, .btn-login{
  flex:1;
  padding:12px 0;
  border-radius:10px;
  font-size:15px;
  font-weight:700;
  color: var(--accent-2);
  border: 1.5px solid var(--border);
  background: #f3f8fa;
  cursor:pointer;
  box-shadow: var(--shadow-2);
  transition: background .13s, color .13s;
}
.btn-register{
  background: var(--accent);
  color: #fff;
  border: none;
}
.btn-register:hover{ background: var(--accent-hover);}
.btn-login:hover{ color: var(--accent-hover); background: #e9f3fa;}
.section-title{
  width:100%; max-width:760px;
  font-size:18px; font-weight:700;
  color: var(--accent-2);
  margin-top:14px;
  margin-bottom:0;
}

/* 卡片與熱門路線列表 */
.popular-list{
  width:100%; /* ← 這樣就會撐滿 */
}

.route-card{
  width:100%;
  padding:18px 16px 14px 16px;
  border-radius:14px;
  background: var(--card);
  border: 1.5px solid var(--border);
  box-shadow: var(--shadow-2);
  display:flex;
  flex-direction:column;
  gap:10px;
  cursor:pointer;
  transition: box-shadow .13s, border-color .13s, transform .13s;
}
.route-card:hover{
  box-shadow: 0 6px 24px rgba(37,123,175,0.10), 0 2.5px 10px 0 rgba(0,0,0,0.06);
  border-color: var(--accent-2);
  transform:translateY(-2.5px) scale(1.01);
}
.route-card:active{ transform: scale(0.99); }

.route-body{ display:flex; justify-content:space-between; align-items:center; gap:12px; }

.live-box{
  display:flex; align-items:center; gap:12px; min-width:0;
  padding:6px 0 0 0; border-radius:8px;
  background: none;
  border:none;
}
.bus-icon{ width:28px; height:28px; fill:var(--accent-2); flex-shrink:0;}
.live-text{ display:flex; flex-direction:column; min-width:0; }
.live-status{ font-size:16px; font-weight:700; color:var(--text); white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
.live-sub{ font-size:13px; color:var(--muted); margin-top:2px; }
.arrival-small{
  font-size:14.5px; font-weight:700;
  color: #fff;
  background: var(--accent);
  padding:10px 16px; border-radius:10px;
  min-width:72px; text-align:center;
  box-shadow: 0 8px 18px rgba(255,122,48,0.10);
  border: none;
}

.status-chip{
  display:inline-block;
  margin-left:10px; padding:4px 10px; border-radius:8px;
  font-size:12px; font-weight:700;
  background: #f4f8fb;
  color: var(--accent-2);
  border: 1px solid var(--border);
}

.live-approaching .status-chip{ background: #fff7ee; color: var(--accent); border-color: #ffe4d1;}
.live-arrived .status-chip{ background: #fff4f4; color: var(--danger); border-color: #fbd1d1;}
.live-normal .status-chip{ background: #effbf0; color: var(--ok); border-color: #baf6cc;}
.live-delayed .status-chip{ background: #fff4f4; color: var(--danger); border-color: #fbd1d1;}

.route-left{ display:flex; flex-direction:column; gap:6px; min-width:0; }
.route-name{ font-size:16.5px; font-weight:800; color:var(--text); overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
.route-desc, .route-next{ font-size:13.5px; color:var(--muted); line-height:1.3; }

.route-action{ display:flex; align-items:center; justify-content:flex-end; gap:8px; }
.chev{ color:var(--muted); font-size:14px; }

.ad-footer{
  padding:24px 12px 32px;
  display:flex; justify-content:center; align-items:center; background:transparent; width:100%;
}
.ad-link{
  display:block; width:100%; max-width:760px; border-radius:12px; overflow:hidden;
  box-shadow: 0 10px 32px rgba(24,31,42,0.08);
  border:1.5px solid var(--border);
  background: #f9fafc;
}
.ad-image{ width:100%; height:112px; object-fit:cover; display:block; transition: transform .17s; }
.ad-link:hover .ad-image{ transform: scale(1.015); }

button, .route-card{ min-height:54px; }
@media (max-width:420px){
  .search-box input{ font-size:15px; padding:10px; }
  .btn-search{ min-width:88px; padding:10px; font-size:13px; }
  .ad-image{ height:84px; }
  .route-name{ font-size:15px; }
  .arrival-small{ min-width:54px; padding:8px 6px; font-size:12.5px; }
}
</style>
