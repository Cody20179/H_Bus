<template>
  <div class="route-management">
    <!-- 頁面標題 -->
    <div class="page-header">
      <div class="header-left">
        <h1 class="page-title">排班調度管理</h1>
        <p class="page-description">管理公車排班與調度安排</p>
      </div>
      <div class="header-right">
        <button
          @click="openCreateModal"
          class="btn-primary"
          :disabled="!canWrite"
        >
          <i class="icon-plus"></i>
          新增排班
        </button>
      </div>
    </div>

    <!-- 篩選區塊 -->
    <div class="filters-section">
      <div class="filter-controls-row">
        <div class="search-container">
          <div class="search-input-wrapper">
            <span class="search-icon">🔍</span>
            <input 
              v-model="keyword" 
              @input="debouncedSearch" 
              type="text" 
              placeholder="搜尋路線、車牌、駕駛員..." 
              class="search-input" 
            />
          </div>
        </div>

        <div class="filter-group">
          <label class="filter-label">路線：</label>
          <select v-model="filters.route_no" @change="refresh" class="page-size-select">
            <option value="">全部路線</option>
            <option v-for="route in availableRoutes" :key="route.route_id" :value="route.route_id">
              {{ route.route_id }} - {{ route.route_name }}
            </option>
          </select>
        </div>
        
        <div class="filter-group">
          <label class="filter-label">營運狀態：</label>
          <select v-model="filters.operation_status" @change="refresh" class="page-size-select">
            <option value="">全部</option>
            <option value="正常營運">正常營運</option>
            <option value="暫停營運">暫停營運</option>
            <option value="維護中">維護中</option>
          </select>
        </div>

        <div class="filter-group">
          <label class="filter-label">排序：</label>
          <select v-model="sortOrder" @change="refresh" class="page-size-select">
            <option value="route_asc">路線編號由小到大</option>
            <option value="route_desc">路線編號由大到小</option>
            <option value="departure_desc">發車時間由晚到早</option>
            <option value="departure_asc">發車時間由早到晚</option>
            <option value="date_desc">日期由新到舊</option>
            <option value="date_asc">日期由舊到新</option>
          </select>
        </div>

        <div class="filter-group">
          <label class="filter-label">每頁：</label>
          <select v-model="pageSize" @change="refresh" class="page-size-select">
            <option value="10">10</option>
            <option value="20">20</option>
            <option value="50">50</option>
          </select>
        </div>
      </div>
    </div>

    <!-- 主要表格 -->
    <div class="table-container">
      <table class="admin-table">
        <thead>
          <tr>
            <th>ID</th>
            <th>路線編號</th>
            <th>路線名稱</th>
            <th>往/返/其他</th>
            <th>特殊營運型態</th>
            <th>營運狀態</th>
            <th>日期</th>
            <th>發車時間</th>
            <th>牌照號碼</th>
            <th>車輛狀態</th>
            <th>駕駛員</th>
            <th>員工編號</th>
            <th class="actions-column">操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="schedule in schedules" :key="schedule.id" class="table-row">
            <td>{{ schedule.id }}</td>
            <td class="route-cell">
              <span class="route-name">{{ schedule.route_no }}</span>
            </td>
            <td>{{ schedule.route_name || '-' }}</td>
            <td>
              <span class="direction-badge">{{ schedule.direction || '-' }}</span>
            </td>
            <td>{{ schedule.special_type || '-' }}</td>
            <td>
              <span :class="['status-badge', getOperationStatusClass(schedule.operation_status)]">
                {{ schedule.operation_status || '-' }}
              </span>
            </td>
            <td>{{ schedule.date || '-' }}</td>
            <td>{{ schedule.departure_time || '-' }}</td>
            <td class="license-cell">
              <span class="license-plate">{{ schedule.license_plate }}</span>
            </td>
            <td>
              <span :class="['status-badge', getCarStatusClass(schedule.car_status)]">
                {{ schedule.car_status || '-' }}
              </span>
            </td>
            <td>{{ schedule.driver_name }}</td>
            <td>{{ schedule.employee_id }}</td>
            <td class="actions-cell">
              <div class="action-buttons">
                <button @click="openEditModal(schedule)" class="btn-edit" :disabled="!canWrite" title="編輯">✏️</button>
              </div>
            </td>
          </tr>
        </tbody>
      </table>

      <!-- 空狀態 -->
      <div v-if="!loading && schedules.length === 0" class="empty-state">
        <div class="empty-icon">📅</div>
        <h3>暫無排班資料</h3>
        <p>目前沒有找到符合條件的排班記錄</p>
      </div>

      <!-- 載入狀態 -->
      <div v-if="loading" class="loading-state">
        <div class="loading-spinner"></div>
        <p>載入中...</p>
      </div>
    </div>

    <!-- 分頁 -->
    <div v-if="pagination.total > 0" class="pagination-container">
      <div class="pagination-info">
        顯示第 {{ (pagination.page - 1) * pagination.limit + 1 }} 到 
        {{ Math.min(pagination.page * pagination.limit, pagination.total) }} 筆，
        共 {{ pagination.total }} 筆
      </div>
      <div class="pagination-controls">
        <button 
          @click="changePage(pagination.page - 1)" 
          :disabled="pagination.page <= 1"
          class="pagination-btn"
        >
          上一頁
        </button>
        <span class="pagination-numbers">
          <button 
            v-for="page in getPageNumbers()" 
            :key="page"
            @click="changePage(page)"
            :class="['pagination-number', { active: page === pagination.page }]"
          >
            {{ page }}
          </button>
        </span>
        <button 
          @click="changePage(pagination.page + 1)" 
          :disabled="pagination.page >= pagination.pages"
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
          <h2>{{ editMode ? '編輯排班' : '新增排班' }}</h2>
          <button @click="closeModal" class="close-btn">×</button>
        </div>

        <form @submit.prevent="save" class="modal-form">
          <div class="form-content">
            <!-- 第一行：路線和方向 -->
            <div class="form-row">
              <div class="form-group">
                <label class="form-label">路線編號 <span class="required">*</span></label>
                <select 
                  v-model="form.route_no" 
                  class="form-select" 
                  :class="{ 'readonly-field': editMode }"
                  :disabled="editMode"
                  required
                >
                  <option value="">請選擇路線</option>
                  <option v-for="route in availableRoutes" :key="route.route_id" :value="route.route_id">
                    {{ route.route_id }} - {{ route.route_name }}
                  </option>
                </select>
                <span v-if="editMode" class="readonly-indicator">🔒 編輯時無法修改</span>
              </div>
              <div class="form-group">
                <label class="form-label">往/返/其他</label>
                <select 
                  v-model="form.direction" 
                  class="form-select"
                  :class="{ 'readonly-field': editMode }"
                  :disabled="editMode"
                >
                  <option value="">請選擇</option>
                  <option value="去程">去程</option>
                  <option value="返程">返程</option>
                  <option value="其他">其他</option>
                </select>
                <span v-if="editMode" class="readonly-indicator">🔒 編輯時無法修改</span>
              </div>
            </div>

            <!-- 第二行：特殊營運型態和營運狀態 -->
            <div class="form-row">
              <div class="form-group">
                <label class="form-label">特殊營運型態</label>
                <input v-model="form.special_type" type="text" class="form-input" placeholder="如：假日班次、夜間專車等">
              </div>
              <div class="form-group">
                <label class="form-label">營運狀態</label>
                <select v-model="form.operation_status" class="form-select">
                  <option value="">請選擇</option>
                  <option value="正常營運">正常營運</option>
                  <option value="暫停營運">暫停營運</option>
                  <option value="維修中">維修中</option>
                </select>
              </div>
            </div>

            <!-- 第三行：日期和發車時間 (暫停營運或維修中時非必填) -->
            <div class="form-row" v-if="form.operation_status === '正常營運'">
              <div class="form-group">
                <label class="form-label">日期 <span class="required">*</span></label>
                <input v-model="form.date" type="date" class="form-input" :required="form.operation_status === '正常營運'">
              </div>
              <div class="form-group">
                <label class="form-label">發車時間 <span class="required">*</span></label>
                <input v-model="form.departure_time" type="time" class="form-input" :required="form.operation_status === '正常營運'">
              </div>
            </div>

            <!-- 第四行：牌照號碼 (暫停營運或維修中時非必填) -->
            <div class="form-row" v-if="form.operation_status === '正常營運'">
              <div class="form-group">
                <label class="form-label">牌照號碼 <span class="required">*</span></label>
                <select v-model="form.license_plate" class="form-select" :required="form.operation_status === '正常營運'">
                  <option value="">請選擇車輛</option>
                  <option v-for="car in availableCars" :key="car.car_licence" :value="car.car_licence">
                    {{ car.car_licence }} ({{ car.car_status }})
                  </option>
                </select>
              </div>
            </div>

            <!-- 第五行：駕駛員資訊 (暫停營運或維修中時非必填) -->
            <div class="form-row" v-if="form.operation_status === '正常營運'">
              <div class="form-group">
                <label class="form-label">駕駛員姓名 <span class="required">*</span></label>
                <input v-model="form.driver_name" type="text" class="form-input" placeholder="駕駛員姓名" :required="form.operation_status === '正常營運'">
              </div>
              <div class="form-group">
                <label class="form-label">員工編號 <span class="required">*</span></label>
                <input v-model="form.employee_id" type="text" class="form-input" placeholder="員工編號" :required="form.operation_status === '正常營運'">
              </div>
            </div>
          </div>

          <div class="form-actions">
            <button type="button" class="btn-secondary" @click="closeModal">取消</button>
            <button type="submit" class="btn-primary" :disabled="saving">
              {{ saving ? '儲存中...' : (editMode ? '更新' : '新增') }}
            </button>
          </div>
        </form>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed, watch } from 'vue'

// 類型定義
interface Schedule {
  id: number
  route_no: string
  route_name?: string
  direction?: string
  special_type?: string
  operation_status?: string
  date: string
  departure_time: string
  license_plate: string
  car_status?: string
  driver_name: string
  employee_id: string
}

interface Route {
  route_id: string
  route_name: string
}

interface Car {
  car_licence: string
  car_status: string
}

// 響應式數據
const schedules = ref<Schedule[]>([])
const availableRoutes = ref<Route[]>([])
const availableCars = ref<Car[]>([])
const loading = ref(false)
const showModal = ref(false)
const editMode = ref(false)
const saving = ref(false)

// 分頁
const pagination = ref({
  page: 1,
  limit: 20,
  total: 0,
  pages: 0
})

// 篩選條件
const keyword = ref('')
const pageSize = ref(10)
const sortOrder = ref('route_asc')
const filters = ref({
  route_no: '',
  operation_status: '',
  date_from: '',
  date_to: ''
})

// 表單數據
const form = ref({
  id: null as number | null,
  route_no: '',
  direction: '',
  special_type: '',
  operation_status: '',
  date: '',
  departure_time: '',
  license_plate: '',
  driver_name: '',
  employee_id: ''
})

// 計算屬性
const canWrite = computed(() => {
  // 檢查localStorage中是否有token，有的話就表示已登入
  const token = localStorage.getItem('token')
  return !!token
})

// 獲取認證token
const getAuthToken = () => {
  return localStorage.getItem('token') || 'admin_1_token'
}

// 監聽營運狀態變化，自動清空相關欄位
watch(() => form.value.operation_status, (newStatus) => {
  if (newStatus !== '正常營運') {
    // 暫停營運或維修中時清空日期、發車時間、車牌和駕駛員資料
    form.value.date = ''
    form.value.departure_time = ''
    form.value.license_plate = ''
    form.value.driver_name = ''
    form.value.employee_id = ''
  }
})

// 防抖搜尋
let searchTimeout: number | null = null
const debouncedSearch = () => {
  if (searchTimeout) clearTimeout(searchTimeout)
  searchTimeout = setTimeout(() => {
    pagination.value.page = 1
    fetchSchedules()
  }, 500)
}

// 取得營運狀態樣式類別
const getOperationStatusClass = (status: string | undefined) => {
  switch (status) {
    case '正常營運': return 'status-active'
    case '暫停營運': return 'status-warning'
    case '維修中': return 'status-danger'
    default: return 'status-secondary'
  }
}

// 取得車輛狀態樣式類別
const getCarStatusClass = (status: string | undefined) => {
  switch (status) {
    case 'service': return 'status-active'
    case 'paused': return 'status-warning'
    case 'maintenance': return 'status-danger'
    case 'retired': return 'status-secondary'
    default: return 'status-secondary'
  }
}

// API 調用函數
const fetchSchedules = async () => {
  loading.value = true
  try {
    const params = new URLSearchParams({
      page: pagination.value.page.toString(),
      limit: pageSize.value.toString()
    })
    
    if (keyword.value.trim()) params.append('search', keyword.value.trim())
    if (filters.value.route_no) params.append('route_no', filters.value.route_no)
    if (filters.value.operation_status) params.append('operation_status', filters.value.operation_status)
    if (filters.value.date_from) params.append('date_from', filters.value.date_from)
    if (filters.value.date_to) params.append('date_to', filters.value.date_to)
    if (sortOrder.value) params.append('sort', sortOrder.value)

    const response = await fetch(`/api/schedules?${params}`, {
      headers: { 'Authorization': `Bearer ${getAuthToken()}` }
    })
    
    if (!response.ok) throw new Error('Failed to fetch schedules')
    
    const data = await response.json()
    schedules.value = data.data
    pagination.value = data.pagination
  } catch (error) {
    console.error('Error fetching schedules:', error)
    alert('載入排班資料失敗')
  } finally {
    loading.value = false
  }
}

const fetchRoutes = async () => {
  try {
    const response = await fetch('/api/schedules/routes', {
      headers: { 'Authorization': `Bearer ${getAuthToken()}` }
    })
    if (response.ok) {
      const data = await response.json()
      availableRoutes.value = data.data
    }
  } catch (error) {
    console.error('Error fetching routes:', error)
  }
}

const fetchCars = async () => {
  try {
    const response = await fetch('/api/schedules/cars', {
      headers: { 'Authorization': `Bearer ${getAuthToken()}` }
    })
    if (response.ok) {
      const data = await response.json()
      availableCars.value = data.data
    }
  } catch (error) {
    console.error('Error fetching cars:', error)
  }
}

// 模態框操作
const openCreateModal = () => {
  if (!canWrite.value) return
  editMode.value = false
  resetForm()
  showModal.value = true
}

const openEditModal = (schedule: Schedule) => {
  if (!canWrite.value) return
  editMode.value = true
  form.value = {
    id: schedule.id,
    route_no: schedule.route_no,
    direction: schedule.direction || '',
    special_type: schedule.special_type || '',
    operation_status: schedule.operation_status || '',
    date: schedule.date,
    departure_time: schedule.departure_time,
    license_plate: schedule.license_plate,
    driver_name: schedule.driver_name,
    employee_id: schedule.employee_id
  }
  showModal.value = true
}

const closeModal = () => {
  showModal.value = false
  resetForm()
}

const resetForm = () => {
  form.value = {
    id: null,
    route_no: '',
    direction: '',
    special_type: '',
    operation_status: '',
    date: '',
    departure_time: '',
    license_plate: '',
    driver_name: '',
    employee_id: ''
  }
}

// 檢查衝突
const checkConflicts = () => {
  const conflicts = []
  
  // 檢查相同路線、方向、日期的排班是否已存在
  const existingSchedule = schedules.value.find(s => 
    s.id !== form.value.id && // 編輯時排除自己
    s.route_no === form.value.route_no &&
    s.direction === form.value.direction &&
    s.date === form.value.date
  )
  
  if (existingSchedule) {
    conflicts.push(`路線 ${form.value.route_no} 在 ${form.value.date} 的 ${form.value.direction} 已有排班`)
  }
  
  // 只有正常營運才檢查車牌和駕駛員衝突
  if (form.value.operation_status === '正常營運') {
    // 檢查相同車牌、日期的衝突（同一天不能在多條路線）
    const carConflict = schedules.value.find(s =>
      s.id !== form.value.id &&
      s.license_plate === form.value.license_plate &&
      s.date === form.value.date
    )
    
    if (carConflict) {
      conflicts.push(`車牌 ${form.value.license_plate} 在 ${form.value.date} 當天已有其他路線排班`)
    }
    
    // 檢查相同駕駛員、日期的衝突（同一天不能在多條路線）
    const driverConflict = schedules.value.find(s =>
      s.id !== form.value.id &&
      s.driver_name === form.value.driver_name &&
      s.date === form.value.date
    )
    
    if (driverConflict) {
      conflicts.push(`駕駛員 ${form.value.driver_name} 在 ${form.value.date} 當天已有其他路線排班`)
    }
    
    // 檢查相同員工編號、日期的衝突（同一天不能在多條路線）
    const employeeConflict = schedules.value.find(s =>
      s.id !== form.value.id &&
      s.employee_id === form.value.employee_id &&
      s.date === form.value.date
    )
    
    if (employeeConflict) {
      conflicts.push(`員工編號 ${form.value.employee_id} 在 ${form.value.date} 當天已有其他路線排班`)
    }
  }
  
  return conflicts
}

// 儲存操作
const save = async () => {
  if (!canWrite.value) return
  
  // 新增模式下檢查衝突
  if (!editMode.value) {
    const conflicts = checkConflicts()
    if (conflicts.length > 0) {
      alert('發現衝突：\n' + conflicts.join('\n'))
      return
    }
  }
  
  saving.value = true
  
  try {
    const method = editMode.value ? 'PUT' : 'POST'
    const url = editMode.value ? `/api/schedules/${form.value.id}` : '/api/schedules'
    
    // 建立 payload，根據營運狀態決定欄位
    const isNormalOperation = form.value.operation_status === '正常營運'
    
    // 建立基本 payload
    const basePayload: any = {}
    
    if (editMode.value) {
      // 編輯模式下：路線編號、方向、往/返/其他 不可修改
      if (form.value.special_type) basePayload.special_type = form.value.special_type
      if (form.value.operation_status) basePayload.operation_status = form.value.operation_status
    } else {
      // 新增模式下：基本欄位都需要
      basePayload.route_no = String(form.value.route_no)  // 確保是字符串類型
      if (form.value.direction) basePayload.direction = form.value.direction
      if (form.value.special_type) basePayload.special_type = form.value.special_type
      if (form.value.operation_status) basePayload.operation_status = form.value.operation_status
    }
    
    // 只有正常營運才需要日期、發車時間、車牌和駕駛員資料
    if (isNormalOperation) {
      if (form.value.date) basePayload.schedule_date = form.value.date
      if (form.value.departure_time) basePayload.departure_time = form.value.departure_time
      if (form.value.license_plate) basePayload.license_plate = form.value.license_plate
      if (form.value.driver_name) basePayload.driver_name = form.value.driver_name
      if (form.value.employee_id) basePayload.employee_id = form.value.employee_id
    }
    
    const payload = basePayload
    
    const response = await fetch(url, {
      method,
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${getAuthToken()}`
      },
      body: JSON.stringify(payload)
    })
    
    if (!response.ok) {
      const error = await response.json()
      throw new Error(error.detail || '操作失敗')
    }
    
    alert(editMode.value ? '更新成功' : '新增成功')
    closeModal()
    fetchSchedules()
  } catch (error: any) {
    console.error('Error saving schedule:', error)
    alert(error.message || '操作失敗')
  } finally {
    saving.value = false
  }
}



// 分頁操作
const changePage = (page: number) => {
  if (page < 1 || page > pagination.value.pages) return
  pagination.value.page = page
  fetchSchedules()
}

const getPageNumbers = () => {
  const current = pagination.value.page
  const total = pagination.value.pages
  const pages: number[] = []
  
  const start = Math.max(1, current - 2)
  const end = Math.min(total, current + 2)
  
  for (let i = start; i <= end; i++) {
    pages.push(i)
  }
  
  return pages
}

const refresh = () => {
  pagination.value.page = 1
  pagination.value.limit = parseInt(pageSize.value.toString())
  fetchSchedules()
}

// 生命週期
onMounted(() => {
  fetchSchedules()
  fetchRoutes()
  fetchCars()
})
</script>

<style scoped>
/* 沿用RouteManagement的完整樣式 */
.route-management {
  padding: 20px;
  min-height: 100vh;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
  background: white;
  padding: 24px;
  border-radius: 12px;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
}

.header-left h1 {
  margin: 0 0 8px 0;
  color: #2c3e50;
  font-size: 28px;
  font-weight: 600;
}

.header-left p {
  margin: 0;
  color: #6c757d;
  font-size: 14px;
}

.btn-primary {
  background: linear-gradient(135deg, #007bff 0%, #0056b3 100%);
  color: white;
  border: none;
  padding: 12px 20px;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 8px;
  transition: all 0.3s ease;
}

.btn-primary:hover:not(:disabled) {
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(0, 123, 255, 0.3);
}

.btn-primary:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.filters-section {
  background: white;
  padding: 20px;
  border-radius: 12px;
  margin-bottom: 20px;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
}

.search-container {
  margin-bottom: 16px;
}

.search-input-wrapper {
  position: relative;
  max-width: 400px;
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
  padding: 12px 12px 12px 40px;
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
  flex-wrap: wrap;
}

.filter-controls-row {
  display: flex;
  gap: 20px;
  align-items: center;
  flex-wrap: wrap;
}

.filter-group {
  display: flex;
  align-items: center;
  gap: 8px;
}

.filter-label {
  font-size: 14px;
  font-weight: 500;
  color: #495057;
  white-space: nowrap;
}

.page-size-select {
  padding: 8px 12px;
  border: 2px solid #e9ecef;
  border-radius: 6px;
  font-size: 14px;
  background: white;
  cursor: pointer;
  transition: border-color 0.2s ease;
}

.page-size-select:focus {
  outline: none;
  border-color: #007bff;
}

.table-container {
  background: white;
  border-radius: 12px;
  overflow: hidden;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
}

.admin-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 14px;
}

.admin-table th {
  background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
  padding: 16px 12px;
  text-align: left;
  font-weight: 600;
  color: #495057;
  border-bottom: 1px solid #dee2e6;
}

.admin-table td {
  padding: 16px 12px;
  border-bottom: 1px solid #f1f3f4;
  vertical-align: middle;
}

.table-row:hover {
  background: rgba(0, 123, 255, 0.05);
}

.route-cell, .license-cell {
  font-weight: 500;
}

.route-name, .license-plate {
  color: #007bff;
  font-weight: 600;
}

.direction-badge {
  background: #e3f2fd;
  color: #1976d2;
  padding: 4px 8px;
  border-radius: 4px;
  font-size: 12px;
  font-weight: 500;
}

.status-badge {
  padding: 4px 8px;
  border-radius: 4px;
  font-size: 12px;
  font-weight: 500;
}

.status-active {
  background: #d4edda;
  color: #155724;
}

.status-warning {
  background: #fff3cd;
  color: #856404;
}

.status-danger {
  background: #f8d7da;
  color: #721c24;
}

.status-secondary {
  background: #e2e3e5;
  color: #383d41;
}

.actions-cell {
  width: 120px;
}

.action-buttons {
  display: flex;
  gap: 8px;
}

.btn-edit, .btn-delete {
  width: 32px;
  height: 32px;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-size: 14px;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s ease;
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
  background: #f8d7da;
  color: #721c24;
}

.btn-delete:hover:not(:disabled) {
  background: #f5c6cb;
  transform: translateY(-1px);
}

.btn-edit:disabled, .btn-delete:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.empty-state {
  text-align: center;
  padding: 60px 20px;
  color: #6c757d;
}

.empty-icon {
  font-size: 48px;
  margin-bottom: 16px;
}

.empty-state h3 {
  margin: 0 0 8px 0;
  color: #495057;
}

.loading-state {
  text-align: center;
  padding: 40px 20px;
  color: #6c757d;
}

.loading-spinner {
  width: 32px;
  height: 32px;
  border: 3px solid #f3f3f3;
  border-top: 3px solid #007bff;
  border-radius: 50%;
  animation: spin 1s linear infinite;
  margin: 0 auto 16px;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

.pagination-container {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 20px;
  padding: 16px 24px;
  background: white;
  border-radius: 12px;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
}

.pagination-info {
  font-size: 14px;
  color: #6c757d;
}

.pagination-controls {
  display: flex;
  align-items: center;
  gap: 8px;
}

.pagination-btn {
  padding: 8px 16px;
  border: 1px solid #dee2e6;
  background: white;
  border-radius: 6px;
  cursor: pointer;
  font-size: 14px;
  transition: all 0.2s ease;
}

.pagination-btn:hover:not(:disabled) {
  background: #f8f9fa;
  border-color: #007bff;
}

.pagination-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.pagination-numbers {
  display: flex;
  gap: 4px;
}

.pagination-number {
  width: 36px;
  height: 36px;
  border: 1px solid #dee2e6;
  background: white;
  border-radius: 6px;
  cursor: pointer;
  font-size: 14px;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s ease;
}

.pagination-number:hover {
  background: #f8f9fa;
  border-color: #007bff;
}

.pagination-number.active {
  background: #007bff;
  color: white;
  border-color: #007bff;
}

/* 模態框樣式 */
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.modal-content {
  background: white;
  border-radius: 12px;
  width: 90%;
  max-width: 800px;
  max-height: 90vh;
  overflow-y: auto;
  box-shadow: 0 10px 30px rgba(0, 0, 0, 0.2);
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 24px;
  border-bottom: 1px solid #e9ecef;
}

.modal-header h2 {
  margin: 0;
  color: #2c3e50;
  font-size: 20px;
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
  border-radius: 6px;
  transition: all 0.2s ease;
}

.close-btn:hover {
  background: #f8f9fa;
  color: #495057;
}

.modal-form {
  padding: 24px;
}

.form-content {
  margin-bottom: 24px;
}

.form-row {
  display: flex;
  gap: 16px;
  margin-bottom: 16px;
}

.form-group {
  flex: 1;
  display: flex;
  flex-direction: column;
}

.form-group.full-width {
  flex: 100%;
}

.form-label {
  margin-bottom: 8px;
  font-weight: 500;
  color: #495057;
  font-size: 14px;
}

.required {
  color: #dc3545;
}

.form-input, .form-select {
  padding: 12px;
  border: 2px solid #e9ecef;
  border-radius: 6px;
  font-size: 14px;
  transition: border-color 0.2s ease;
}

.form-input:focus, .form-select:focus {
  outline: none;
  border-color: #007bff;
  box-shadow: 0 0 0 3px rgba(0, 123, 255, 0.1);
}

/* 只讀欄位樣式 */
.readonly-field {
  background: #f8f9fa !important;
  color: #6c757d !important;
  cursor: not-allowed !important;
  border-color: #dee2e6 !important;
}

.readonly-indicator {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
  color: #6c757d;
  margin-top: 4px;
  font-style: italic;
}

.form-actions {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  padding-top: 24px;
  border-top: 1px solid #e9ecef;
}

.btn-secondary {
  background: #6c757d;
  color: white;
  border: none;
  padding: 12px 20px;
  border-radius: 8px;
  font-size: 14px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.btn-secondary:hover {
  background: #5a6268;
  transform: translateY(-1px);
}

@media (max-width: 768px) {
  .route-management {
    padding: 10px;
  }
  
  .page-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 16px;
  }
  
  .filter-controls {
    flex-direction: column;
    align-items: stretch;
  }
  
  .form-row {
    flex-direction: column;
  }
  
  .pagination-container {
    flex-direction: column;
    gap: 16px;
  }
  
  .admin-table {
    font-size: 12px;
  }
  
  .admin-table th,
  .admin-table td {
    padding: 8px;
  }
}
</style>