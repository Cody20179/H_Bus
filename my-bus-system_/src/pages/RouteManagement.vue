<template>
  <div class="route-management">
    <!-- 頁面標題 -->
    <div class="page-header">
      <div class="header-left">
        <h1 class="page-title">路線站點管理</h1>
        <p class="page-description">管理公車路線和站點資訊</p>
      </div>
      <div class="header-right">
        <button
          @click="openCreateModal"
          class="btn-primary"
        >
          <i class="icon-plus"></i>
          新增站點
        </button>
        <button
          @click="openCreateRouteModal"
          class="btn-primary"
          style="background: linear-gradient(135deg,#10b981 0%,#059669 100%); margin-left:8px;"
        >
          <i class="icon-plus"></i>
          新增路線
        </button>
      </div>
    </div>

    <!-- 路線總覽表格（與站點表格樣式一致） -->
    <div class="routes-overview" style="margin-top:16px; margin-bottom:16px; background:white; padding:16px; border-radius:12px;">
      <h3 style="margin:0 0 12px 0;">路線總覽</h3>

      <!-- 搜尋欄（路線） -->
      <div class="routes-filter-row">
        <div class="search-input-wrapper routes-search">
          <span class="search-icon">🔍</span>
          <input
            v-model="routeSearchQuery"
            @input="handleRouteSearch"
            type="text"
            placeholder="搜尋路線名稱..."
            class="search-input"
          />
        </div>
        <div class="filter-inline">
          <label class="filter-label">ID排序：</label>
          <select v-model="routeSortOrder" class="page-size-select routes-order-select">
            <option value="desc">由新到舊</option>
            <option value="asc">由舊到新</option>
          </select>
        </div>
      </div>

      <div class="table-container">
        <table class="admin-table">
          <thead>
            <tr>
              <th>ID</th>
              <th>路線名稱</th>
              <th>方向</th>
              <th>起點</th>
              <th>終點</th>
              <th>站數</th>
              <th>狀態</th>
              <th class="actions-column">操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="r in filteredRoutes" :key="r.route_id" class="table-row">
              <td>{{ r.route_id }}</td>
              <td class="route-cell">
                <div class="route-info">
                  <span class="route-name">{{ r.route_name }}</span>
                </div>
              </td>
              <td>
                <span class="direction-badge">{{ r.direction || '-' }}</span>
              </td>
              <td>{{ r.start_stop || '-' }}</td>
              <td>{{ r.end_stop || '-' }}</td>
              <td>{{ r.stop_count || 0 }}</td>
              <td>
                <button @click="toggleRouteStatus(r)" :class="['status-btn', r.status === 1 ? 'on' : 'off']">
                  {{ r.status === 1 ? '啟用' : '停用' }}
                </button>
              </td>
              <td class="actions-cell">
                <div class="action-buttons">
                  <button @click.stop="openEditRoute(r)" class="btn-edit" title="編輯">✏️</button>
                  <button @click.stop="deleteRoute(r, $event)" class="btn-delete" title="刪除">🗑️</button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>

        <div v-if="filteredRoutes.length === 0" class="empty-state" style="margin-top:12px;">
          <div class="empty-icon">🚌</div>
          <h3>沒有找到路線</h3>
          <p>{{ routeSearchQuery ? '沒有符合搜尋條件的路線' : '目前沒有路線資料' }}</p>
        </div>
      </div>
    </div>

    <!-- 搜尋和篩選區域 -->
    <div class="filters-section">
      <div class="search-container">
        <div class="search-input-wrapper">
          <span class="search-icon">🔍</span>
          <input
            v-model="searchQuery"
            @input="handleSearch"
            type="text"
            placeholder="搜尋站點名稱..."
            class="search-input"
          />
        </div>
      </div>

      <div class="filter-controls">
        <div class="filter-group">
          <label class="filter-label">路線篩選：</label>
          <select v-model="routeFilter" @change="loadStations" class="route-select">
            <option value="">全部路線</option>
            <option v-for="route in availableRoutes" :key="route.route_id" :value="route.route_id">
              {{ route.route_name }}
            </option>
          </select>
        </div>

        <div class="filter-group">
          <label class="filter-label">方向篩選：</label>
          <select v-model="directionFilter" @change="loadStations" class="direction-select">
            <option value="">全部方向</option>
            <option value="去程">去程</option>
            <option value="回程">回程</option>
          </select>
        </div>

        <div class="filter-group">
          <label class="filter-label">ID排序：</label>
          <select v-model="stationSortOrder" @change="loadStations" class="page-size-select">
            <option value="desc">由新到舊</option>
            <option value="asc">由舊到新</option>
          </select>
        </div>
        <div class="filter-group">
          <label class="filter-label">每頁顯示：</label>
          <select v-model.number="pageSize" @change="onPageSizeChange" class="page-size-select">
            <option :value="10">10 筆</option>
            <option :value="20">20 筆</option>
            <option :value="50">50 筆</option>
          </select>
        </div>
      </div>
    </div>

    <!-- 站點列表 -->
    <div class="table-container">
      <div v-if="isLoading" class="loading-overlay">
        <div class="spinner"></div>
        <span>載入中...</span>
      </div>

      <table v-else class="admin-table">
        <thead>
          <tr>
            <th>ID</th>
            <th>路線名稱</th>
            <th>方向</th>
            <th>站點名稱</th>
            <th>緯度</th>
            <th>經度</th>
            <th>順序</th>
            <th>地址</th>
            <th>到站時間(分鐘)</th>
            <th class="actions-column">操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="station in stations" :key="`${station.route_id}-${station.stop_order}`" class="table-row">
            <td>{{ station.route_id }}</td>
            <td class="route-cell">
              <div class="route-info">
                <span class="route-name">{{ station.route_name }}</span>
              </div>
            </td>
            <td>
              <span class="direction-badge" :class="station.direction">
                {{ station.direction }}
              </span>
            </td>
            <td class="station-cell">
              <div class="station-info">
                <span class="station-name">{{ station.stop_name }}</span>
              </div>
            </td>
            <td class="coord-cell">{{ station.latitude }}</td>
            <td class="coord-cell">{{ station.longitude }}</td>
            <td class="order-cell">{{ station.stop_order }}</td>
            <td class="address-cell" :title="station.address">
              {{ station.address ? station.address.substring(0, 20) + '...' : '未設定' }}
            </td>
            <td class="eta-cell">{{ station.eta_from_start }} 分鐘</td>
            <td class="actions-cell">
              <div class="action-buttons">
                <button
                  @click.stop="editStation(station)"
                  class="btn-edit"
                  title="編輯"
                >
                  ✏️
                </button>
                <button
                  @click.stop="deleteStation(station)"
                  class="btn-delete"
                  title="刪除"
                >
                  🗑️
                </button>
              </div>
            </td>
          </tr>
        </tbody>
      </table>

      <!-- 空狀態 -->
      <div v-if="!isLoading && stations.length === 0" class="empty-state">
        <div class="empty-icon">🚌</div>
        <h3>沒有找到站點</h3>
        <p>{{ searchQuery ? '沒有符合搜尋條件的站點' : '目前沒有站點資料' }}</p>
      </div>
    </div>

    <!-- 分頁控制器 -->
    <div v-if="!isLoading && stations.length > 0" class="pagination-container">
      <div class="pagination-info">
        顯示第 {{ (currentPage - 1) * pageSize + 1 }} 到
        {{ Math.min(currentPage * pageSize, totalStations) }} 筆，
        共 {{ totalStations }} 筆資料
      </div>

      <div class="pagination-controls">
        <button
          @click="goToPage(currentPage - 1)"
          :disabled="currentPage === 1"
          class="pagination-btn"
        >
          上一頁
        </button>

        <div class="page-numbers">
          <button
            v-for="page in visiblePages"
            :key="page"
            @click="goToPage(page)"
            :class="['page-number', { active: page === currentPage }]"
          >
            {{ page }}
          </button>
        </div>

        <button
          @click="goToPage(currentPage + 1)"
          :disabled="currentPage === totalPages"
          class="pagination-btn"
        >
          下一頁
        </button>
      </div>
    </div>

    <!-- 新增/編輯模態框 -->
    <div v-if="showModal" class="modal-overlay" @click="closeModal">
      <div class="modal-content" @click.stop>
        <div class="modal-header">
          <h2>{{ isEditMode ? '編輯站點' : '新增站點' }}</h2>
          <button @click="closeModal" class="close-btn">&times;</button>
        </div>

        <form @submit.prevent="saveStation" class="modal-form">
          <div class="form-row">
            <div class="form-group">
              <label class="form-label">路線 *</label>
              <select v-model="currentStation.route_id" class="form-select" required>
                <option value="">請選擇路線</option>
                <option v-for="route in availableRoutes" :key="route.route_id" :value="route.route_id">
                  {{ route.route_name }}
                </option>
              </select>
            </div>
            <div class="form-group">
              <label class="form-label">方向 *</label>
              <select v-model="currentStation.direction" class="form-select" required>
                <option value="">請選擇方向</option>
                <option value="去程">去程</option>
                <option value="回程">回程</option>
              </select>
            </div>
          </div>

          <div class="form-row">
            <div class="form-group">
              <label class="form-label">站點名稱 *</label>
              <input
                v-model="currentStation.stop_name"
                type="text"
                class="form-input"
                required
                placeholder="請輸入站點名稱"
              />
            </div>
            <div class="form-group">
              <label class="form-label">順序 *</label>
              <input
                v-model.number="currentStation.stop_order"
                type="number"
                class="form-input"
                required
                placeholder="請輸入站點順序"
                min="1"
              />
            </div>
          </div>

          <div class="form-row">
            <div class="form-group">
              <label class="form-label">緯度 *</label>
              <input
                v-model.number="currentStation.latitude"
                type="number"
                class="form-input"
                required
                placeholder="請輸入緯度"
                step="0.000001"
              />
            </div>
            <div class="form-group">
              <label class="form-label">經度 *</label>
              <input
                v-model.number="currentStation.longitude"
                type="number"
                class="form-input"
                required
                placeholder="請輸入經度"
                step="0.000001"
              />
            </div>
          </div>

          <div class="form-row">
            <div class="form-group">
              <label class="form-label">到站時間(分鐘)</label>
              <input
                v-model.number="currentStation.eta_from_start"
                type="number"
                class="form-input"
                placeholder="請輸入到站時間"
                min="0"
              />
            </div>
          </div>

          <div class="form-row">
            <div class="form-group full-width">
              <label class="form-label">地址</label>
              <textarea
                v-model="currentStation.address"
                class="form-textarea"
                placeholder="請輸入站點地址"
                rows="3"
              ></textarea>
            </div>
          </div>

          <div class="form-actions">
            <button type="button" @click="closeModal" class="btn-secondary">
              取消
            </button>
            <button type="submit" :disabled="isSubmitting" class="btn-primary">
              {{ isSubmitting ? '儲存中...' : (isEditMode ? '更新' : '新增') }}
            </button>
          </div>
        </form>
      </div>
    </div>

    <!-- 刪除確認模態框 -->
    <div v-if="showDeleteModal" class="modal-overlay" @click="cancelDelete">
      <div class="modal-content delete-modal" @click.stop>
        <div class="modal-header">
          <h2>確認刪除</h2>
          <button @click="cancelDelete" class="close-btn">&times;</button>
        </div>

        <div class="modal-body">
          <p>確定要刪除站點「{{ currentStation.stop_name }}」嗎？</p>
          <p class="warning-text">此操作無法復原。</p>
        </div>

        <div class="modal-actions">
          <button @click="cancelDelete" class="btn-secondary">取消</button>
          <button @click="confirmDelete" :disabled="isDeleting" class="btn-danger">
            {{ isDeleting ? '刪除中...' : '確認刪除' }}
          </button>
        </div>
      </div>
    </div>

    <!-- 路線刪除確認模態框（獨立於路線編輯模態） -->
    <div v-if="showRouteDeleteModal" class="modal-overlay" @click="cancelRouteDelete">
      <div class="modal-content delete-modal" @click.stop>
        <div class="modal-header">
          <h2>確認刪除路線</h2>
          <button @click="cancelRouteDelete" class="close-btn">&times;</button>
        </div>

        <div class="modal-body">
          <p>確定要刪除路線「{{ (routeToDelete && routeToDelete.route_name) || '未命名' }}」嗎？</p>
          <p class="warning-text">此操作會移除路線以及相關站點資料，無法復原。</p>
        </div>

        <div class="modal-actions">
          <button @click="cancelRouteDelete" class="btn-secondary">取消</button>
          <button @click="confirmRouteDelete" :disabled="isDeletingRoute" class="btn-danger">{{ isDeletingRoute ? '刪除中...' : '確認刪除' }}</button>
        </div>
      </div>
    </div>

    <!-- 新增路線模態框 -->
    <div v-if="showRouteModal" class="modal-overlay" @click="closeRouteModal">
      <div class="modal-content" @click.stop>
        <div class="modal-header">
          <h2>新增路線</h2>
          <button @click="closeRouteModal" class="close-btn">&times;</button>
        </div>

        <form @submit.prevent="saveRoute" class="modal-form">
          <div class="form-row">
            <div class="form-group">
              <label class="form-label">路線名稱 *</label>
              <input v-model="currentRoute.route_name" type="text" class="form-input" required placeholder="請輸入路線名稱" />
            </div>
            <div class="form-group">
              <label class="form-label">方向</label>
              <select v-model="currentRoute.direction" class="form-select">
                <option value="">(未指定)</option>
                <option value="單向">單向</option>
                <option value="雙向">雙向</option>
              </select>
            </div>
          </div>

            

          <div class="form-row">
            <div class="form-group">
              <label class="form-label">起點</label>
              <input v-model="currentRoute.start_stop" type="text" class="form-input" placeholder="起點站名" />
            </div>
            <div class="form-group">
              <label class="form-label">終點</label>
              <input v-model="currentRoute.end_stop" type="text" class="form-input" placeholder="終點站名" />
            </div>
          </div>

          <div class="form-row">
            <div class="form-group full-width">
              <label class="form-label">狀態</label>
              <select v-model.number="currentRoute.status" class="form-select">
                <option :value="1">啟用</option>
                <option :value="0">停用</option>
              </select>
            </div>
          </div>

          <div class="form-actions">
            <button type="button" @click="closeRouteModal" class="btn-secondary">取消</button>
            <button type="submit" :disabled="isSubmittingRoute" class="btn-primary">{{ isSubmittingRoute ? '儲存中...' : '新增' }}</button>
          </div>
        </form>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'

// 定義類型
interface Station {
  route_id: number
  route_name: string
  direction: string
  stop_name: string
  latitude: number
  longitude: number
  stop_order: number
  eta_from_start: number
  address: string
  // optional 原始識別欄位，用於安全更新
  original_stop_name?: string
  original_stop_order?: number
}

interface Route {
  route_id: number
  route_name: string
}

// 響應式數據
const stations = ref<Station[]>([])
const availableRoutes = ref<Route[]>([])
const routeList = ref<any[]>([])
const routeSearchQuery = ref('')
const routeSortOrder = ref<'desc' | 'asc'>('desc')
const isLoading = ref(false)
const isSubmitting = ref(false)
const isDeleting = ref(false)
const showModal = ref(false)
const showDeleteModal = ref(false)
const isEditMode = ref(false)

// 搜尋和篩選
const searchQuery = ref('')
const routeFilter = ref('')
const directionFilter = ref('')
const stationSortOrder = ref<'desc' | 'asc'>('desc')
const pageSize = ref<number>(10)
const currentPage = ref(1)
const totalStations = ref(0)

// 搜尋防抖
let searchTimeout: ReturnType<typeof setTimeout> | null = null
let routeSearchTimeout: ReturnType<typeof setTimeout> | null = null

// 當前編輯的站點
const currentStation = ref<Station>({
  route_id: 0,
  route_name: '',
  direction: '',
  stop_name: '',
  latitude: 0,
  longitude: 0,
  stop_order: 0,
  eta_from_start: 0,
  address: ''
})

// 新增路線狀態
const showRouteModal = ref(false)
const isSubmittingRoute = ref(false)
const currentRoute = ref({
  route_id: undefined as number | undefined,
  route_name: '',
  direction: '',
  start_stop: '',
  end_stop: '',
  status: 1
})

// 刪除路線狀態
const showRouteDeleteModal = ref(false)
const isDeletingRoute = ref(false)
const routeToDelete = ref<any>(null)

const deleteRoute = (r: any, ev?: Event) => {
  try { ev && (ev.stopPropagation(), ev.preventDefault()) } catch {}
  routeToDelete.value = r
  showRouteDeleteModal.value = true
}

const cancelRouteDelete = () => {
  showRouteDeleteModal.value = false
  routeToDelete.value = null
}

const confirmRouteDelete = async () => {
  if (!routeToDelete.value) return
  isDeletingRoute.value = true
  try {
    const res = await fetch('/api/routes/delete', {
      method: 'DELETE',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${localStorage.getItem('token') || ''}`
      },
      body: JSON.stringify({ route_id: routeToDelete.value.route_id })
    })
    if (res.ok) {
      await loadRouteList()
      await loadAvailableRoutes()
      showRouteDeleteModal.value = false
      routeToDelete.value = null
      alert('路線已刪除')
    } else {
      let msg = '刪除失敗'
      try { const err = await res.json(); msg = err.detail || err.message || msg } catch(e){}
      alert(msg)
    }
  } catch (e) {
    console.error('刪除路線失敗', e)
    alert('網路錯誤，無法刪除')
  } finally {
    isDeletingRoute.value = false
  }
}

const openEditRoute = (r: any) => {
  currentRoute.value = {
    route_id: r.route_id,
    route_name: r.route_name || '',
    direction: r.direction || '',
    start_stop: r.start_stop || '',
    end_stop: r.end_stop || '',
    status: r.status || 0
  }
  showRouteModal.value = true
}

const loadRouteList = async () => {
  try {
    const res = await fetch('/All_Route')
    let data: any = null
    if (res.ok) {
      try {
        data = await res.json()
      } catch (e) {
        // 解析失敗，可能是 HTML 回應（開發環境 proxy 問題），使用後端 fallback
        data = null
      }
    }

    // 如果沒有拿到有效的 JSON，嘗試直接呼叫後端完整 URL（開發時常見跨埠 proxy 問題）
    if (!data) {
      try {
        const backend = (import.meta && (import.meta as any).env && (import.meta as any).env.VITE_API_URL) || 'http://127.0.0.1:8500'
        const r = await fetch(`${backend}/All_Route`)
        if (r.ok) data = await r.json()
      } catch (e) {
        // ignore
      }
    }

    if (data) {
      // 支援多種回傳形狀：直接陣列、{ records: [] }, { routes: [] }, { data: [] }
      if (Array.isArray(data)) {
        routeList.value = data
      } else if (data && Array.isArray((data as any).records)) {
        routeList.value = (data as any).records
      } else if (data && Array.isArray((data as any).routes)) {
        routeList.value = (data as any).routes
      } else if (data && Array.isArray((data as any).data)) {
        routeList.value = (data as any).data
      } else {
        // 最後嘗試把 object 的 values 轉成陣列
        try {
          const vals = Object.values(data || {})
          routeList.value = vals.flat().filter((v: any) => v && v.route_id)
        } catch (ex) {
          routeList.value = []
        }
      }
      return
    }
    // fallback to older endpoint (try relative first, then backend host)
    if (!routeList.value.length) {
      try {
        let r2 = await fetch('/api/routes')
        let d2: any = null
        if (r2.ok) {
          try { d2 = await r2.json() } catch (e) { d2 = null }
        }
        if (!d2) {
          const backend = (import.meta && (import.meta as any).env && (import.meta as any).env.VITE_API_URL) || 'http://127.0.0.1:8500'
          const r3 = await fetch(`${backend}/api/routes`)
          if (r3.ok) d2 = await r3.json()
        }
        if (Array.isArray(d2)) {
          routeList.value = d2
        } else if (d2 && Array.isArray(d2.routes)) {
          routeList.value = d2.routes
        } else if (d2 && Array.isArray(d2.data)) {
          routeList.value = d2.data
        } else {
          routeList.value = []
        }
      } catch (e) {
        // ignore
      }
    }
  } catch (e) {
    console.error('載入路線列表失敗', e)
    routeList.value = []
  }
}

const toggleRouteStatus = async (r: any) => {
  try {
    const newStatus = r.status === 1 ? 0 : 1
    const payload: any = { route_id: r.route_id, status: newStatus }
    const res = await fetch('/api/routes/update', {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${localStorage.getItem('token') || ''}`
      },
      body: JSON.stringify(payload)
    })
    if (res.ok) {
      await loadRouteList()
      await loadAvailableRoutes()
      alert('狀態更新成功')
    } else {
      const err = await res.json()
      alert(err.detail || '更新失敗')
    }
  } catch (e) {
    console.error(e)
    alert('更新失敗')
  }
}

const openCreateRouteModal = () => {
  currentRoute.value = { route_id: undefined, route_name: '', direction: '', start_stop: '', end_stop: '', status: 1 }
  showRouteModal.value = true
}

const closeRouteModal = () => {
  showRouteModal.value = false
  currentRoute.value = { route_id: undefined, route_name: '', direction: '', start_stop: '', end_stop: '', status: 1 }
}

const saveRoute = async () => {
  if (!currentRoute.value.route_name || currentRoute.value.route_name.trim() === '') {
    alert('請輸入路線名稱')
    return
  }
  isSubmittingRoute.value = true
  try {
    let response: Response
    if (currentRoute.value.route_id) {
      response = await fetch('/api/routes/update', {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('token') || ''}`
        },
        body: JSON.stringify(currentRoute.value)
      })
    } else {
      response = await fetch('/api/routes/create', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('token') || ''}`
        },
        body: JSON.stringify(currentRoute.value)
      })
    }

    if (response.ok) {
    const data = await response.json()
    closeRouteModal()
    await loadRouteList()
    await loadAvailableRoutes()
    alert(data.message || '路線處理成功')
    } else {
      let msg = '新增路線失敗'
      try {
        const err = await response.json()
        msg = err.detail || err.message || msg
      } catch (e) {
        // ignore
      }
      alert(msg)
    }
  } catch (e) {
    console.error('saveRoute error', e)
    alert('網路錯誤，無法新增路線')
  } finally {
    isSubmittingRoute.value = false
  }
}

const handleRouteSearch = () => {
  if (routeSearchTimeout) clearTimeout(routeSearchTimeout)
  routeSearchTimeout = setTimeout(() => {
    // no server call here, we use computed filteredRoutes based on routeList
  }, 300)
}

const filteredRoutes = computed(() => {
  const q = routeSearchQuery.value.trim().toLowerCase()
  const list = Array.isArray(routeList.value) ? [...routeList.value] : []
  list.sort((a: any, b: any) => {
    const aId = Number(a?.route_id || 0)
    const bId = Number(b?.route_id || 0)
    return routeSortOrder.value === 'desc' ? bId - aId : aId - bId
  })
  if (!q) return list
  return list.filter((r: any) => (r.route_name || '').toLowerCase().includes(q))
})

// 方法
const loadStations = async () => {
  isLoading.value = true
  try {
    // 建構查詢參數
    const params = new URLSearchParams()
    if (routeFilter.value) {
      params.append('route_id', routeFilter.value)
    }
    if (directionFilter.value) {
      params.append('direction', directionFilter.value)
    }
    if (searchQuery.value) {
      params.append('search', searchQuery.value)
    }
    params.append('page', currentPage.value.toString())
    params.append('page_size', pageSize.value.toString())
    if (stationSortOrder.value) {
      params.append('order', stationSortOrder.value)
    }

    const url = `/api/route-stations${params.toString() ? '?' + params.toString() : ''}`
    
    const response = await fetch(url, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json'
      }
    })

    if (response.ok) {
      const data = await response.json()
      stations.value = data.stations || []
      totalStations.value = data.total || 0
    } else {
      console.error('API 回應錯誤:', response.status)
      stations.value = []
      totalStations.value = 0
    }
  } catch (error) {
    console.error('載入站點失敗:', error)
    stations.value = []
    totalStations.value = 0
  } finally {
    isLoading.value = false
  }
}

const loadAvailableRoutes = async () => {
  try {
    // 優先從 bus_routes_total (/All_Route) 取得路線（與新增路線來源一致）
    let response = await fetch('/All_Route')
    let data: any = null
    if (response.ok) {
      try { data = await response.json() } catch (e) { data = null }
    }
    if (!data) {
      try {
        const backend = (import.meta && (import.meta as any).env && (import.meta as any).env.VITE_API_URL) || 'http://127.0.0.1:8500'
        const r = await fetch(`${backend}/All_Route`)
        if (r.ok) data = await r.json()
      } catch (e) {
        data = null
      }
    }
    if (data) {
      let rows: any[] = []
      if (Array.isArray(data)) rows = data
      else if (data && Array.isArray((data as any).records)) rows = (data as any).records
      else if (data && Array.isArray((data as any).routes)) rows = (data as any).routes
      else if (data && Array.isArray((data as any).data)) rows = (data as any).data

      availableRoutes.value = rows.map((r: any) => ({ route_id: r.route_id, route_name: r.route_name }))
      return
    }

    // 若 /All_Route 不可用，退回到舊的 /api/routes
    response = await fetch('/api/routes')
    if (response.ok) {
      const data = await response.json()
      availableRoutes.value = data.routes || []
    }
  } catch (error) {
    console.error('載入路線失敗:', error)
    // 使用模擬資料
    availableRoutes.value = [
      { route_id: 1, route_name: '市民小巴5(洽公直達線)' },
      { route_id: 2, route_name: '市民小巴6(醫療照護線)' },
      { route_id: 3, route_name: '市民小巴7(市區夜環線)' },
      { route_id: 4, route_name: '市民小巴-行動遊花蓮' }
    ] as Route[]
  }
}

const handleSearch = () => {
  // 實現搜尋邏輯（帶防抖）
  if (searchTimeout) {
    clearTimeout(searchTimeout)
  }
  
  searchTimeout = setTimeout(() => {
    currentPage.value = 1
    loadStations()
  }, 500)
}

// 當 pageSize 改變時重置頁碼並重新載入
const onPageSizeChange = () => {
  currentPage.value = 1
  loadStations()
}

const openCreateModal = () => {
  isEditMode.value = false
  currentStation.value = {
    route_id: 0,
    route_name: '',
    direction: '',
    stop_name: '',
    latitude: 0,
    longitude: 0,
    stop_order: 0,
    eta_from_start: 0,
    address: ''
  }
  showModal.value = true
}

const editStation = (station: Station) => {
  isEditMode.value = true
  // 保留原始識別欄位以便安全更新（避免使用者修改後找不到原始記錄）
  currentStation.value = { ...station, original_stop_name: station.stop_name, original_stop_order: station.stop_order }
  showModal.value = true
}

const deleteStation = (station: Station) => {
  currentStation.value = { ...station }
  showDeleteModal.value = true
}

const closeModal = () => {
  showModal.value = false
  currentStation.value = {
    route_id: 0,
    route_name: '',
    direction: '',
    stop_name: '',
    latitude: 0,
    longitude: 0,
    stop_order: 0,
    eta_from_start: 0,
  address: '',
  original_stop_name: undefined,
  original_stop_order: undefined
  }
}

const saveStation = async () => {
  isSubmitting.value = true
  try {
    // 在送出前，若使用者只選了 route_id，則從 availableRoutes 填入對應的 route_name
    try {
      if (currentStation.value.route_id && (!currentStation.value.route_name || currentStation.value.route_name.toString().trim() === '')) {
        const found = (availableRoutes.value || []).find((r: any) => Number(r.route_id) === Number(currentStation.value.route_id))
        currentStation.value.route_name = found ? (found.route_name || '') : ''
      }
    } catch (e) {
      console.warn('填入 route_name 時發生錯誤', e)
    }

    const url = isEditMode.value ? '/api/route-stations/update' : '/api/route-stations/create'
    const method = isEditMode.value ? 'PUT' : 'POST'

    const payload = isEditMode.value
      ? JSON.stringify({ ...currentStation.value, original_stop_name: currentStation.value.original_stop_name, original_stop_order: currentStation.value.original_stop_order })
      : JSON.stringify(currentStation.value)

    const response = await fetch(url, {
      method,
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${localStorage.getItem('token') || ''}`
      },
      body: payload
    })

    if (response.ok) {
      const result = await response.json()
      closeModal()
      loadStations()
      alert(result.message || (isEditMode.value ? '站點更新成功！' : '站點新增成功！'))
    } else {
      let errorMessage = '操作失敗，請重試'
      try {
        const errorData = await response.json()
        errorMessage = errorData.detail || errorData.message || errorMessage
      } catch (parseError) {
        // 如果無法解析JSON，使用預設錯誤訊息
        console.error('解析錯誤回應失敗:', parseError)
      }
      alert(errorMessage)
    }
  } catch (error) {
    console.error('儲存失敗:', error)
    alert('操作失敗，請檢查網路連線')
  } finally {
    isSubmitting.value = false
  }
}

const cancelDelete = () => {
  showDeleteModal.value = false
  currentStation.value = {
    route_id: 0,
    route_name: '',
    direction: '',
    stop_name: '',
    latitude: 0,
    longitude: 0,
    stop_order: 0,
    eta_from_start: 0,
    address: ''
  }
}

const confirmDelete = async () => {
  isDeleting.value = true
  try {
    const response = await fetch(`/api/route-stations/delete?route_id=${currentStation.value.route_id}&stop_order=${currentStation.value.stop_order}`, {
      method: 'DELETE',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${localStorage.getItem('token') || ''}`
      }
    })

    if (response.ok) {
      const result = await response.json()
      showDeleteModal.value = false
      loadStations()
      alert(result.message || '站點刪除成功！')
    } else {
      const errorData = await response.json()
      alert(errorData.detail || '刪除失敗，請重試')
    }
  } catch (error) {
    console.error('刪除失敗:', error)
    alert('刪除失敗，請檢查網路連線')
  } finally {
    isDeleting.value = false
  }
}

const goToPage = (page: number) => {
  currentPage.value = page
  loadStations()
}

// 分頁相關計算
const totalPages = computed(() => Math.ceil(totalStations.value / pageSize.value))

const visiblePages = computed(() => {
  const pages: number[] = []
  const maxPagesToShow = 5
  let start = Math.max(1, currentPage.value - Math.floor(maxPagesToShow / 2))
  let end = Math.min(totalPages.value, start + maxPagesToShow - 1)
  if (end - start < maxPagesToShow - 1) {
    start = Math.max(1, end - maxPagesToShow + 1)
  }
  for (let i = start; i <= end; i++) {
    pages.push(i)
  }
  return pages
})

// 生命週期
onMounted(() => {
  loadAvailableRoutes()
  loadRouteList()
  loadStations()
})
</script>

<style scoped>
/* 使用與 AdminManagement.vue 完全相同的樣式 */
.route-management {
  padding: 24px;
  background-color: #f8f9fa;
  min-height: calc(100vh - 60px);
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 32px;
  padding: 24px;
  background: white;
  border-radius: 12px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.header-left h1 {
  color: #2c3e50;
  margin: 0 0 8px 0;
  font-size: 28px;
  font-weight: 600;
}

.header-left p {
  color: #6c757d;
  margin: 0;
  font-size: 14px;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 12px;
}

.btn-primary {
  background: linear-gradient(135deg, #007bff 0%, #0056b3 100%);
  color: white;
  border: none;
  padding: 12px 20px;
  border-radius: 8px;
  cursor: pointer;
  font-weight: 500;
  display: flex;
  align-items: center;
  gap: 8px;
  transition: all 0.2s ease;
  font-size: 14px;
}

.btn-primary:hover {
  background: linear-gradient(135deg, #0056b3 0%, #004085 100%);
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(0, 123, 255, 0.3);
}

.btn-primary:active {
  transform: translateY(0);
}

.filters-section {
  background: white;
  padding: 20px 24px;
  border-radius: 12px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  margin-bottom: 24px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 20px;
}

.search-container {
  flex: 1;
  max-width: 400px;
}

.search-input-wrapper {
  position: relative;
}

.search-icon {
  position: absolute;
  left: 12px;
  top: 50%;
  transform: translateY(-50%);
  color: #6c757d;
  font-size: 16px;
}

.search-input {
  width: 100%;
  padding: 10px 16px 10px 40px;
  border: 2px solid #e9ecef;
  border-radius: 8px;
  font-size: 14px;
  transition: border-color 0.2s ease;
}

.search-input:focus {
  outline: none;
  border-color: #007bff;
  box-shadow: 0 0 0 3px rgba(0, 123, 255, 0.1);
}

.filter-controls {
  display: flex;
  gap: 20px;
  align-items: center;
}

.filter-group {
  display: flex;
  align-items: center;
  gap: 8px;
}

.filter-label {
  color: #495057;
  font-weight: 500;
  font-size: 14px;
  white-space: nowrap;
}

.route-select, .direction-select, .page-size-select {
  padding: 8px 12px;
  border: 2px solid #e9ecef;
  border-radius: 6px;
  font-size: 14px;
  background: white;
  cursor: pointer;
  transition: border-color 0.2s ease;
}

.route-select:focus, .direction-select:focus, .page-size-select:focus {
  outline: none;
  border-color: #007bff;
}

/* 表格容器 - 支援橫向和縱向滾動 */
.table-container {
  background: white;
  border-radius: 16px;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.08);
  border: 1px solid #e5e7eb;
  position: relative;
  margin-bottom: 24px;
  max-height: 600px; /* 限制最大高度，支援縱向滾動 */
  overflow: auto; /* 同時支援上下左右滾動 */
}

.admin-table {
  width: 100%;
  border-collapse: collapse;
  min-width: 1000px; /* 設定最小寬度，確保橫向滾動 */
}

.admin-table th {
  background: #f8f9fa;
  padding: 16px 12px;
  text-align: left;
  font-weight: 600;
  color: #495057;
  border-bottom: 2px solid #e9ecef;
  font-size: 14px;
  position: sticky;
  top: 0; /* 固定表頭 */
  z-index: 1;
}

.admin-table td {
  padding: 16px 12px;
  border-bottom: 1px solid #e9ecef;
  font-size: 14px;
  white-space: nowrap; /* 防止文字換行 */
}

.table-row:hover {
  background: #f8f9fa;
}

.route-cell {
  font-weight: 500;
  color: #2c3e50;
}

.station-cell {
  max-width: 200px;
}

.station-name {
  font-weight: 500;
  color: #2c3e50;
}

.direction-badge {
  display: inline-block;
  padding: 4px 12px;
  border-radius: 20px;
  font-size: 12px;
  font-weight: 500;
  text-align: center;
}

.direction-badge.去程 {
  background: #d4edda;
  color: #155724;
}

.direction-badge.回程 {
  background: #fff3cd;
  color: #856404;
}

.coord-cell {
  font-family: 'Courier New', monospace;
  font-size: 13px;
}

.order-cell {
  text-align: center;
  font-weight: 500;
}

.address-cell {
  max-width: 200px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.eta-cell {
  text-align: center;
}

.actions-column {
  width: 100px;
  text-align: center;
}

.action-buttons {
  display: flex;
  justify-content: center;
  gap: 8px;
}

.btn-edit,
.btn-delete {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 36px;
  height: 36px;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  font-size: 14px;
  transition: all 0.3s ease;
}

.btn-edit {
  background: #dbeafe;
  color: #1e40af;
}

.btn-edit:hover {
  background: #bfdbfe;
  transform: translateY(-1px);
}

.btn-delete {
  background: #fecaca;
  color: #991b1b;
}

.btn-delete:hover:not(:disabled) {
  background: #fca5a5;
  transform: translateY(-1px);
}

/* 載入覆蓋層 */
.loading-overlay {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(255, 255, 255, 0.9);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 16px;
  z-index: 10;
}

.spinner {
  width: 40px;
  height: 40px;
  border: 4px solid #e5e7eb;
  border-top: 4px solid #3b82f6;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

/* 空狀態 */
.empty-state {
  text-align: center;
  padding: 64px 24px;
  color: #6b7280;
}

.empty-icon {
  font-size: 64px;
  margin-bottom: 16px;
  opacity: 0.5;
}

.empty-state h3 {
  font-size: 20px;
  font-weight: 600;
  margin: 0 0 8px 0;
  color: #374151;
}

.empty-state p {
  font-size: 16px;
  margin: 0;
}

/* 分頁樣式 - 完全參照 AdminManagement.vue */
.pagination-container {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 20px 24px;
  background: white;
  border-radius: 12px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  margin-top: 24px;
}

.pagination-info {
  color: #6c757d;
  font-size: 14px;
}

.pagination-controls {
  display: flex;
  align-items: center;
  gap: 12px;
}

.pagination-btn {
  padding: 8px 16px;
  border: 2px solid #dee2e6;
  background: white;
  border-radius: 6px;
  cursor: pointer;
  font-size: 14px;
  transition: all 0.2s ease;
  color: #495057;
}

.pagination-btn:hover:not(:disabled) {
  background: #f8f9fa;
  border-color: #007bff;
  color: #007bff;
}

.pagination-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.page-numbers {
  display: flex;
  gap: 4px;
}

.page-number {
  padding: 8px 12px;
  border: 2px solid #dee2e6;
  background: white;
  border-radius: 6px;
  cursor: pointer;
  font-size: 14px;
  transition: all 0.2s ease;
  color: #495057;
}

.page-number:hover {
  background: #f8f9fa;
  border-color: #007bff;
  color: #007bff;
}

.page-number.active {
  background: #007bff;
  border-color: #007bff;
  color: white;
}

/* Modal 樣式保持不變... */
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.6);
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 1000;
}

.modal-content {
  background: white;
  border-radius: 12px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.15);
  width: 90%;
  max-width: 600px;
  max-height: 90vh;
  overflow-y: auto;
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 20px 24px;
  border-bottom: 1px solid #e9ecef;
}

.modal-header h2 {
  margin: 0;
  color: #2c3e50;
  font-size: 20px;
  font-weight: 600;
}

.close-btn {
  background: none;
  border: none;
  font-size: 24px;
  cursor: pointer;
  color: #6c757d;
  padding: 0;
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 4px;
  transition: background-color 0.2s ease;
}

.close-btn:hover {
  background: #f8f9fa;
  color: #495057;
}

.modal-form {
  padding: 24px;
}

.form-row {
  display: flex;
  gap: 16px;
  margin-bottom: 16px;
}

.form-group {
  flex: 1;
}

.form-group.full-width {
  flex: none;
  width: 100%;
}

.form-label {
  display: block;
  margin-bottom: 6px;
  font-weight: 500;
  color: #374151;
  font-size: 14px;
}

.form-input,
.form-select,
.form-textarea {
  width: 100%;
  padding: 10px 12px;
  border: 2px solid #e5e7eb;
  border-radius: 6px;
  font-size: 14px;
  transition: border-color 0.2s ease;
}

.form-input:focus,
.form-select:focus,
.form-textarea:focus {
  outline: none;
  border-color: #667eea;
}

.form-textarea {
  resize: vertical;
  min-height: 80px;
}

.form-actions {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  margin-top: 24px;
  padding-top: 20px;
  border-top: 1px solid #e9ecef;
}

.btn-secondary {
  padding: 10px 20px;
  border: 2px solid #6c757d;
  background: white;
  color: #6c757d;
  border-radius: 6px;
  cursor: pointer;
  font-size: 14px;
  font-weight: 500;
  transition: all 0.2s ease;
}

.btn-secondary:hover {
  background: #6c757d;
  color: white;
}

.btn-danger {
  padding: 10px 20px;
  border: 2px solid #dc3545;
  background: #dc3545;
  color: white;
  border-radius: 6px;
  cursor: pointer;
  font-size: 14px;
  font-weight: 500;
  transition: all 0.2s ease;
}

.btn-danger:hover {
  background: #c82333;
  border-color: #c82333;
}

.delete-modal {
  max-width: 400px;
}

.modal-body {
  padding: 24px;
  text-align: center;
}

.warning-text {
  color: #dc2626;
  font-weight: 500;
  margin-top: 8px;
}

.modal-actions {
  display: flex;
  gap: 12px;
  justify-content: center;
  padding: 0 24px 24px;
}

/* 響應式設計 */
@media (max-width: 768px) {
  .route-management {
    padding: 10px;
  }

  .page-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 15px;
  }

  .filters-section {
    flex-direction: column;
    align-items: stretch;
  }

  .filter-controls {
    flex-direction: column;
    align-items: stretch;
  }

  .form-row {
    flex-direction: column;
    gap: 12px;
  }

  .form-actions {
    flex-direction: column;
  }

  .pagination-container {
    flex-direction: column;
    gap: 15px;
    text-align: center;
  }

  .admin-table {
    font-size: 12px;
  }

  .admin-table th,
  .admin-table td {
    padding: 8px 6px;
  }
}

.routes-filter-row { display:flex; gap:16px; align-items:center; justify-content:space-between; margin-bottom:12px; flex-wrap:wrap; }
.routes-filter-row .routes-search { flex:1; min-width:220px; }
.routes-filter-row .filter-inline { display:flex; align-items:center; gap:8px; }
.routes-order-select { min-width:140px; }
</style>
