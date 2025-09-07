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
          <label class="filter-label">每頁顯示：</label>
          <select v-model="pageSize" @change="loadStations" class="page-size-select">
            <option value="10">10 筆</option>
            <option value="20">20 筆</option>
            <option value="50">50 筆</option>
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
                  @click="editStation(station)"
                  class="btn-edit"
                  title="編輯"
                >
                  ✏️
                </button>
                <button
                  @click="deleteStation(station)"
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
}

interface Route {
  route_id: number
  route_name: string
}

// 響應式數據
const stations = ref<Station[]>([])
const availableRoutes = ref<Route[]>([])
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
const pageSize = ref(10)
const currentPage = ref(1)
const totalStations = ref(0)

// 搜尋防抖
let searchTimeout: ReturnType<typeof setTimeout> | null = null

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

// 計算屬性
const totalPages = computed(() => Math.ceil(totalStations.value / pageSize.value))

const visiblePages = computed(() => {
  const pages = []
  const start = Math.max(1, currentPage.value - 2)
  const end = Math.min(totalPages.value, currentPage.value + 2)

  for (let i = start; i <= end; i++) {
    pages.push(i)
  }

  return pages
})

// 監視 route_id 變化，自動設置 route_name
import { watch } from 'vue'

watch(() => currentStation.value.route_id, (newRouteId) => {
  if (newRouteId && availableRoutes.value.length > 0) {
    const selectedRoute = availableRoutes.value.find(route => route.route_id === newRouteId)
    if (selectedRoute) {
      currentStation.value.route_name = selectedRoute.route_name
    }
  }
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
    // 獲取所有可用路線
    const response = await fetch('/api/routes')
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
  currentStation.value = { ...station }
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
    address: ''
  }
}

const saveStation = async () => {
  isSubmitting.value = true
  try {
    const url = isEditMode.value ? '/api/route-stations/update' : '/api/route-stations/create'
    const method = isEditMode.value ? 'PUT' : 'POST'

    const response = await fetch(url, {
      method,
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(currentStation.value)
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
        'Content-Type': 'application/json'
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

// 生命週期
onMounted(() => {
  loadAvailableRoutes()
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
</style>
