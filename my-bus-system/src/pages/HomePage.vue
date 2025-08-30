<template>
  <div class="app-root" :class="{ 'sidebar-hidden': hidden }">
    <!-- Sidebar -->
    <aside class="sidebar" :aria-hidden="hidden ? 'true' : 'false'">
      <div class="logo">
        <div class="logo-title">H-Bus</div>
        <div class="logo-sub">管理系統</div>
      </div>

      <nav class="nav">
        <ul>
          <li @click="goTo('dashboard')">系統總覽</li>
          <li @click="goTo('admin')">管理員帳號管理</li>
          <li @click="goTo('member')">會員帳號管理</li>
          <li @click="goTo('reservation')">預約管理</li>
          <li @click="goTo('route')">路線管理</li>
        </ul>
      </nav>
    </aside>

    <!-- small expand button shown when hidden -->
    <button
      v-if="hidden"
      class="expand-btn"
      @click="showSidebar"
      aria-label="展開選單"
      title="展開選單"
    >
      ☰
    </button>

    <!-- overlay for mobile when sidebar shown -->
    <div v-if="isMobile && !hidden" class="overlay" @click="hideSidebar"></div>

    <!-- Main area -->
    <div class="main-area">
      <header class="topbar">
        <div class="left-controls">
          <button class="hamburger" @click="toggleSidebar" :title="hidden ? '展開選單' : '收合選單'">
            <span v-if="hidden">☰</span>
            <span v-else>☰</span>
          </button>
          <div class="page-title">後台首頁</div>
        </div>

        <div class="user-area">
          <span class="welcome">歡迎, Admin</span>
          <button class="logout" @click="logout">登出</button>
        </div>
      </header>

      <main class="content">
        <section class="stats">
          <div class="card">
            <div class="card-label">管理員數量</div>
            <div class="card-num">12</div>
          </div>

          <div class="card">
            <div class="card-label">會員數量</div>
            <div class="card-num">530</div>
          </div>

          <div class="card">
            <div class="card-label">本月預約</div>
            <div class="card-num">87</div>
          </div>

          <div class="card">
            <div class="card-label">路線數量</div>
            <div class="card-num">14</div>
          </div>
        </section>

        <section class="table-section">
          <h2>管理員列表</h2>
          <table class="simple-table">
            <thead>
              <tr><th>ID</th><th>名稱</th><th>狀態</th><th>操作</th></tr>
            </thead>
            <tbody>
              <tr v-for="item in data" :key="item.id">
                <td>{{item.id}}</td>
                <td>{{item.name}}</td>
                <td><span :class="['status', item.active ? 'on':'off']">{{ item.active ? '啟用':'停用' }}</span></td>
                <td>
                  <button class="action-btn edit" @click="edit(item)">編輯</button>
                  <button class="action-btn delete" @click="del(item)">刪除</button>
                </td>
              </tr>
            </tbody>
          </table>
        </section>
      </main>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'

const router = useRouter()
const hidden = ref(false)

// 判斷是否為窄螢幕（mobile）
const isMobile = computed(() => window.innerWidth <= 900)

// 初次載入從 localStorage 讀取（若有）
onMounted(() => {
  try {
    const v = localStorage.getItem('hb_sidebar_hidden')
    if (v === '1') hidden.value = true
  } catch (e) { /* ignore */ }

  // 若在載入時是 mobile，預設隱藏（可自訂）
  if (isMobile.value) {
    hidden.value = true
  }

  // 監聽 resize 以更新 isMobile 行為（不使用 reactive resize lib，簡單方案）
  window.addEventListener('resize', onResize)
})

function onResize() {
  // 若變成 mobile 且 sidebar 沒隱藏，保留顯示（但我們不強制改變）
}

function toggleSidebar() {
  hidden.value = !hidden.value
  try { localStorage.setItem('hb_sidebar_hidden', hidden.value ? '1' : '0') } catch {}
}
function hideSidebar() {
  if (!hidden.value) {
    hidden.value = true
    try { localStorage.setItem('hb_sidebar_hidden', '1') } catch {}
  }
}
function showSidebar() {
  if (hidden.value) {
    hidden.value = false
    try { localStorage.setItem('hb_sidebar_hidden', '0') } catch {}
  }
}

function goTo(page:string){ alert(`跳到 ${page}（尚未實作）`) }
function logout(){ router.push('/') }

const data = [
  {id:1,name:'管理員 A',active:true},
  {id:2,name:'管理員 B',active:false},
  {id:3,name:'管理員 C',active:true},
]

function edit(it:any){ alert('編輯 '+it.name) }
function del(it:any){ alert('刪除 '+it.name) }
</script>

<style scoped>
/* 基本 layout */
.app-root { position:relative; min-height:100vh; background:#f3f4f6; display:flex; }

/* ------- Sidebar ------- */
.sidebar {
  width: 260px;
  background:#0f172a;
  color:#f8fafc;
  padding:24px;
  box-shadow: 2px 0 8px rgba(2,6,23,0.4);
  position:fixed;
  left:0; top:0; bottom:0;
  overflow:auto;
  z-index:40;
  transform: translateX(0);
  transition: transform 260ms ease;
}

/* 當 .sidebar-hidden 加上時，把 sidebar 完全隱藏（往左滑出畫面） */
.sidebar-hidden .sidebar {
  transform: translateX(-105%); /* 完全推出畫面 */
}

/* expand button (顯示在左邊邊緣) */
.expand-btn {
  position: fixed;
  left: 12px;
  top: 14px;
  z-index: 65;
  background: #0b5d7a; /* 同 topbar 主色，易辨識 */
  color: #fff;
  border: none;
  padding: 10px 12px;
  border-radius: 10px;
  cursor: pointer;
  box-shadow: 0 8px 20px rgba(2,6,23,0.25);
}

/* overlay (手機抽屜用) */
.overlay{
  position:fixed;
  inset:0;
  background: rgba(0,0,0,0.35);
  z-index:38;
}

/* sidebar 內容 */
.logo { margin-bottom:22px; text-align:center; }
.logo-title{ font-size:34px; font-weight:700; color:#fff; }
.logo-sub{ color:#9ca3af; font-size:13px; margin-top:6px; }

/* nav */
.nav ul{ list-style:none; padding:0; margin:0; }
.nav li{
  padding:14px 18px;
  margin-bottom:12px;
  background: rgba(255,255,255,0.02);
  border-radius:10px;
  cursor:pointer;
  display:flex;
  align-items:center;
  gap:10px;
}
.nav li:hover{ background: rgba(255,255,255,0.05); }

/* ------- Main area ------- */
/* main-area 使用 margin-left 來留空間給 sidebar，當隱藏時變成 0 */
.main-area{
  flex:1;
  margin-left:260px; /* 與 sidebar 寬度一致 */
  transition: margin-left 260ms ease;
  min-height:100vh;
}
.sidebar-hidden .main-area{
  margin-left:0;
}

/* topbar */
.topbar{
  position: fixed;
  left: 260px;  /* 當側欄存在時的起點 */
  right: 0;
  top: 0;
  height: 64px;
  display:flex;
  align-items:center;
  justify-content:space-between;
  padding: 0 18px;
  z-index: 50;   /* 比 hamburger 低一點，避免覆蓋漢堡按鈕 */
  transition: left 260ms ease;
}

.sidebar-hidden .topbar{ left:0; }

/* left controls */
.left-controls{ display:flex; align-items:center; gap:12px; }
.hamburger{
  background: rgba(255,255,255,0.06);  /* 半透明底，比較柔和 */
  border: none;                         /* 移除明顯外框 */
  color: #ffffff;
  padding: 8px 10px;
  border-radius: 8px;
  cursor: pointer;
  font-size: 18px;
  line-height: 1;
  display:inline-flex;
  align-items:center;
  justify-content:center;
  box-shadow: 0 6px 14px rgba(2,6,23,0.12);
  z-index: 60;            /* 高於 topbar 裝飾但低於 sidebar/overlay */
}

.hamburger:hover {
  background: rgba(255,255,255,0.10);
}

.page-title{ font-weight:700; font-size:18px; color:#fff; }

/* user area */
.user-area{ display:flex; align-items:center; gap:12px; }
.logout{ background:#093a45; color:#fff; border:none; padding:8px 12px; border-radius:6px; cursor:pointer; }

/* content */
.content{
  margin-top:64px;
  padding:28px;
  height: calc(100vh - 64px);
  overflow:auto;
}

/* cards grid */
.stats{
  display:grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap:28px;
  align-items:start;
  margin-bottom:28px;
  max-width:1100px;
  margin-left:auto;
  margin-right:auto;
}
.card{
  background:#fff;
  border-radius:12px;
  padding:22px;
  box-shadow:0 8px 24px rgba(2,6,23,0.06);
  display:flex;
  flex-direction:column;
  align-items:center;
  justify-content:center;
  min-height:120px;
  text-align:center;
}
.card-label{ color:#374151; font-size:16px; margin-bottom:10px; }
.card-num{ color:#0b5d7a; font-size:28px; font-weight:700; }

/* table */
.table-section, .table-section h2 { max-width:1100px; margin:32px auto 16px; }
.simple-table{ width:100%; border-collapse:collapse; background:#fff; border-radius:8px; overflow:hidden; }
.simple-table th, .simple-table td{ padding:14px 18px; border-bottom:1px solid #edf2f7; text-align:left; }
.simple-table thead th{ background:#f8fafc; font-weight:700; }

/* status */
.status.on{ color:#0f5132; background:#d1fae5; padding:6px 8px; border-radius:6px; }
.status.off{ color:#7f1d1d; background:#fee2e2; padding:6px 8px; border-radius:6px; }

/* button base */
button{ background:#0b5d7a; color:#fff; border:none; padding:8px 12px; border-radius:8px; cursor:pointer; }
button:hover{ opacity:0.95; }

/* Responsive: 在窄螢幕把 sidebar 當抽屜 */
@media (max-width: 900px) {
  .sidebar { transform: translateX(-105%); }       /* 隱藏預設 */
  .sidebar-hidden .sidebar { transform: translateX(-105%); }
  /* 當非 hidden（即 open）時把 sidebar 拉出 */
  :not(.sidebar-hidden) .sidebar { transform: translateX(0); }
  .main-area { margin-left:0; }
  .topbar { left:0; }
  .expand-btn { left: 10px; top: 10px; } /* 小螢幕 expand button 位置 */
}
</style>
