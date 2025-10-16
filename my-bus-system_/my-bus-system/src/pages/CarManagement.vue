<template>
  <div class="route-management">
    <div class="page-header">
      <div class="header-left">
        <h1 class="page-title">車輛管理</h1>
        <p class="page-description">管理車輛資料與維護狀態</p>
      </div>
      <div class="header-right">
        <button class="btn-primary" @click="openCreate" :disabled="!canWrite">
          <i class="icon-plus"></i>
          新增車輛
        </button>
      </div>
    </div>

    <div class="filters-section">
      <div class="search-container">
        <div class="search-input-wrapper">
          <span class="search-icon">🔍</span>
          <input
            v-model="keyword"
            @input="debouncedSearch"
            type="text"
            placeholder="搜尋車牌號碼..."
            class="search-input"
          />
        </div>
      </div>

      <div class="filter-controls">
        <div class="filter-group">
          <label class="filter-label">車輛狀態：</label>
          <select v-model="filters.car_status" @change="refresh" class="page-size-select">
            <option value="">全部</option>
            <option value="service">營運中</option>
            <option value="paused">暫停營運</option>
            <option value="maintenance">維護中</option>
            <option value="retired">退役</option>
          </select>
        </div>
        <div class="filter-group">
          <label class="filter-label">ID排序：</label>
          <select v-model="sortOrder" @change="refresh" class="page-size-select">
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

    <div class="table-container">
      <div v-if="loading" class="loading-overlay">
        <div class="spinner"></div>
        <span>載入中...</span>
      </div>

      <table v-else class="admin-table">
        <thead>
          <tr>
            <th>ID</th>
            <th>車牌號碼</th>
            <th>可載人數</th>
            <th>車輛狀態</th>
            <th>啟用日期</th>
            <th>最近維護</th>
            <th class="actions-column">操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="car in cars" :key="car.car_id" class="table-row">
            <td>{{ car.car_id }}</td>
            <td>{{ car.car_licence }}</td>
            <td>{{ car.max_passengers ?? '-' }}</td>
            <td>
              <span class="status-badge" :class="car.car_status">
                {{ mapStatus(car.car_status) }}
              </span>
            </td>
            <td class="date-cell">{{ fmtDate(car.commission_date) }}</td>
            <td class="date-cell">{{ fmtDate(car.last_service_date) }}</td>
            <td class="actions-cell">
              <div class="action-buttons">
                <button class="btn-edit" title="編輯" @click.stop="openEdit(car)" :disabled="!canWrite">✏️</button>
                <button class="btn-delete" title="刪除" @click.stop="askDelete(car)" :disabled="!canWrite">🗑️</button>
              </div>
            </td>
          </tr>
        </tbody>
      </table>

      <div v-if="!loading && cars.length === 0" class="empty-state">
        <div class="empty-icon">🚐</div>
        <h3>沒有找到車輛</h3>
        <p>{{ keyword ? '沒有符合搜尋條件的車輛' : '目前沒有車輛資料' }}</p>
      </div>
    </div>

    <div v-if="!loading && cars.length > 0" class="pagination-container">
      <div class="pagination-info">
        顯示第 {{ (page - 1) * pageSize + 1 }} 到 {{ Math.min(page * pageSize, total) }} 筆，共 {{ total }} 筆
      </div>
      <div class="pagination-controls">
        <button class="pagination-btn" @click="go(page - 1)" :disabled="page === 1">上一頁</button>
        <div class="page-numbers">
          <button
            v-for="p in pages"
            :key="p"
            class="page-number"
            :class="{ active: p === page }"
            @click="go(p)"
          >
            {{ p }}
          </button>
        </div>
        <button class="pagination-btn" @click="go(page + 1)" :disabled="page === totalPages">下一頁</button>
      </div>
    </div>

    <div v-if="showModal" class="modal-overlay" @click="closeModal">
      <div class="modal-content" @click.stop>
        <div class="modal-header">
          <h2>{{ editMode ? '編輯車輛' : '新增車輛' }}</h2>
          <button class="close-btn" @click="closeModal">×</button>
        </div>
        <form class="modal-form" @submit.prevent="save">
          <div class="form-row">
            <div class="form-group">
              <label class="form-label">車牌號碼</label>
              <input v-model="form.car_licence" type="text" class="form-input" placeholder="例如 ABC-1234" />
            </div>
            <div class="form-group">
              <label class="form-label">可載人數</label>
              <input v-model.number="form.max_passengers" type="number" min="1" class="form-input" />
            </div>
          </div>
          <div class="form-row">
            <div class="form-group">
              <label class="form-label">車輛狀態</label>
              <select v-model="form.car_status" class="form-select">
                <option value="service">營運中</option>
                <option value="paused">暫停營運</option>
                <option value="maintenance">維護中</option>
                <option value="retired">退役</option>
              </select>
            </div>
            <div class="form-group">
              <label class="form-label">啟用日期</label>
              <input v-model="form.commission_date" type="date" class="form-input" />
            </div>
          </div>
          <div class="form-row">
            <div class="form-group">
              <label class="form-label">最近維護日期</label>
              <input v-model="form.last_service_date" type="date" class="form-input" />
            </div>
          </div>
          <div class="form-actions">
            <button type="button" class="btn-secondary" @click="closeModal">取消</button>
            <button type="submit" class="btn-primary" :disabled="saving">{{ saving ? '儲存中...' : (editMode ? '更新' : '新增') }}</button>
          </div>
        </form>
      </div>
    </div>

    <div v-if="showDelete" class="modal-overlay" @click="cancelDelete">
      <div class="modal-content delete-modal" @click.stop>
        <div class="modal-header">
          <h2>確認刪除</h2>
          <button class="close-btn" @click="cancelDelete">×</button>
        </div>
        <div class="modal-body">
          <p>確定要刪除車輛「{{ toDelete?.car_licence }}」嗎？</p>
          <p class="warning-text">此操作無法復原。</p>
        </div>
        <div class="form-actions">
          <button class="btn-secondary" @click="cancelDelete">取消</button>
          <button class="btn-danger" @click="confirmDelete" :disabled="deleting">{{ deleting ? '刪除中...' : '確認刪除' }}</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'

type CarStatus = 'service' | 'paused' | 'maintenance' | 'retired'

interface CarRecord {
  car_id: number
  car_licence: string
  max_passengers: number | null
  car_status: CarStatus
  commission_date?: string | null
  last_service_date?: string | null
}

interface CarFormState {
  car_id: number | null
  car_licence: string
  max_passengers: number | null
  car_status: CarStatus
  commission_date: string
  last_service_date: string
}

const loading = ref(false)
const saving = ref(false)
const deleting = ref(false)
const cars = ref<CarRecord[]>([])
const page = ref(1)
const pageSize = ref(10)
const total = ref(0)
const totalPages = computed(() => Math.ceil(total.value / pageSize.value) || 1)
const keyword = ref('')
const filters = ref<{ car_status: CarStatus | '' }>({ car_status: '' })
const sortOrder = ref<'desc' | 'asc'>('desc')

const currentUser = ref<any>(null)
const role = computed(() => (currentUser.value?.role || '').toLowerCase())
const canWrite = computed(() => role.value === 'super_admin' || role.value === 'admin')

const pages = computed(() => {
  const ps: number[] = []
  const max = 5
  let s = Math.max(1, page.value - 2)
  let e = Math.min(totalPages.value, s + max - 1)
  if (e - s + 1 < max) s = Math.max(1, e - max + 1)
  for (let i = s; i <= e; i++) ps.push(i)
  return ps
})

function fmtDate(value: any) {
  if (!value) return '-'
  if (typeof value === 'string') {
    if (value.length >= 10) return value.slice(0, 10)
    return value
  }
  try {
    const d = new Date(value)
    if (!Number.isNaN(d.getTime())) {
      const local = new Date(d.getTime() - d.getTimezoneOffset() * 60000)
      return local.toISOString().slice(0, 10)
    }
  } catch (err) {
    console.warn('fmtDate error', err)
  }
  return String(value)
}

function toDateInput(value: any) {
  if (!value) return ''
  if (typeof value === 'string' && value.length >= 10) return value.slice(0, 10)
  try {
    const d = new Date(value)
    if (!Number.isNaN(d.getTime())) {
      const local = new Date(d.getTime() - d.getTimezoneOffset() * 60000)
      return local.toISOString().slice(0, 10)
    }
  } catch {}
  return ''
}

function mapStatus(status: CarStatus) {
  return (
    {
      service: '營運中',
      paused: '暫停營運',
      maintenance: '維護中',
      retired: '退役'
    } as const
  )[status] || status
}

async function fetchList() {
  loading.value = true
  try {
    const params = new URLSearchParams()
    params.append('page', String(page.value))
    params.append('limit', String(pageSize.value))
    if (keyword.value.trim()) params.append('search', keyword.value.trim())
    if (filters.value.car_status) params.append('status', filters.value.car_status)
    if (sortOrder.value) params.append('order', sortOrder.value)

    const res = await fetch(`/api/cars?${params.toString()}`, {
      headers: {
        Authorization: `Bearer ${localStorage.getItem('token') || ''}`
      }
    })
    const data = await res.json()
    if (data.success) {
      cars.value = (data.data || []).map((item: any) => ({
        car_id: item.car_id,
        car_licence: item.car_licence,
        max_passengers: item.max_passengers,
        car_status: item.car_status,
        commission_date: item.commission_date || null,
        last_service_date: item.last_service_date || null
      }))
      total.value = data.pagination?.total || 0
    } else {
      cars.value = []
      total.value = 0
    }
  } catch (err) {
    console.error('載入車輛資料失敗', err)
    cars.value = []
    total.value = 0
  } finally {
    loading.value = false
  }
}

let timer: ReturnType<typeof setTimeout> | null = null
function debouncedSearch() {
  if (timer) clearTimeout(timer)
  timer = setTimeout(() => {
    page.value = 1
    fetchList()
  }, 500)
}

function onPageSizeChange() {
  page.value = 1
  fetchList()
}

function refresh() {
  page.value = 1
  fetchList()
}

function go(p: number) {
  if (p >= 1 && p <= totalPages.value) {
    page.value = p
    fetchList()
  }
}

const showModal = ref(false)
const editMode = ref(false)
const form = ref<CarFormState>({
  car_id: null,
  car_licence: '',
  max_passengers: null,
  car_status: 'service',
  commission_date: '',
  last_service_date: ''
})

function resetForm() {
  form.value = {
    car_id: null,
    car_licence: '',
    max_passengers: null,
    car_status: 'service',
    commission_date: '',
    last_service_date: ''
  }
}

function openCreate() {
  if (!canWrite.value) return
  editMode.value = false
  resetForm()
  showModal.value = true
}

function openEdit(car: CarRecord) {
  if (!canWrite.value) return
  editMode.value = true
  form.value = {
    car_id: car.car_id,
    car_licence: car.car_licence,
    max_passengers: car.max_passengers,
    car_status: car.car_status,
    commission_date: toDateInput(car.commission_date),
    last_service_date: toDateInput(car.last_service_date)
  }
  showModal.value = true
}

function closeModal() {
  showModal.value = false
  editMode.value = false
}

async function save() {
  if (!canWrite.value) return
  const licence = (form.value.car_licence || '').trim()
  if (!licence) {
    alert('請輸入車牌號碼')
    return
  }
  const passengers = form.value.max_passengers ? Number(form.value.max_passengers) : 0
  if (!passengers || passengers < 1) {
    alert('請輸入有效的可載人數')
    return
  }

  const payload: Record<string, any> = {
    car_licence: licence,
    max_passengers: passengers,
    car_status: form.value.car_status || 'service'
  }
  if (form.value.commission_date) payload.commission_date = form.value.commission_date
  if (form.value.last_service_date) payload.last_service_date = form.value.last_service_date

  saving.value = true
  try {
    const url = editMode.value ? `/api/cars/${form.value.car_id}` : '/api/cars'
    const method = editMode.value ? 'PUT' : 'POST'
    const res = await fetch(url, {
      method,
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${localStorage.getItem('token') || ''}`
      },
      body: JSON.stringify(payload)
    })
    const data = await res.json().catch(() => ({}))
    if (!res.ok || data?.success === false) {
      alert(data?.detail || data?.message || '處理失敗')
      return
    }
    closeModal()
    fetchList()
    alert('處理成功')
  } catch (err) {
    console.error('儲存車輛失敗', err)
    alert('儲存失敗，請稍後再試')
  } finally {
    saving.value = false
  }
}

const showDelete = ref(false)
const toDelete = ref<CarRecord | null>(null)

function askDelete(car: CarRecord) {
  if (!canWrite.value) return
  toDelete.value = car
  showDelete.value = true
}

function cancelDelete() {
  showDelete.value = false
  toDelete.value = null
}

async function confirmDelete() {
  if (!toDelete.value) return
  deleting.value = true
  try {
    const res = await fetch(`/api/cars/${toDelete.value.car_id}`, {
      method: 'DELETE',
      headers: {
        Authorization: `Bearer ${localStorage.getItem('token') || ''}`
      }
    })
    const data = await res.json().catch(() => ({}))
    if (!res.ok || data?.success === false) {
      alert(data?.detail || data?.message || '刪除失敗')
      return
    }
    showDelete.value = false
    toDelete.value = null
    fetchList()
    alert('刪除成功')
  } catch (err) {
    console.error('刪除車輛失敗', err)
    alert('刪除失敗，請稍後再試')
  } finally {
    deleting.value = false
  }
}

onMounted(() => {
  try {
    const u = localStorage.getItem('user')
    if (u) currentUser.value = JSON.parse(u)
  } catch (err) {
    console.warn('解析使用者資訊失敗', err)
  }
  fetchList()
})
</script>

<style scoped>
/* 使用與 RouteManagement.vue 相同的樣式（複製核心樣式確保一致） */
.route-management { padding: 24px; background-color: #f8f9fa; min-height: calc(100vh - 60px); }
.page-header { display:flex; justify-content:space-between; align-items:flex-start; margin-bottom:32px; padding:24px; background:white; border-radius:12px; box-shadow:0 2px 8px rgba(0,0,0,.1); }
.header-left h1 { color:#2c3e50; margin:0 0 8px 0; font-size:28px; font-weight:600; }
.header-left p { color:#6c757d; margin:0; font-size:14px; }
.header-right { display:flex; align-items:center; gap:12px; }
.btn-primary { background: linear-gradient(135deg, #007bff 0%, #0056b3 100%); color:white; border:none; padding:12px 20px; border-radius:8px; cursor:pointer; font-weight:500; display:flex; align-items:center; gap:8px; transition:all .2s ease; font-size:14px; }
.btn-primary:hover { background: linear-gradient(135deg, #0056b3 0%, #004085 100%); transform: translateY(-1px); box-shadow: 0 4px 12px rgba(0,123,255,.3); }
.filters-section { background:white; padding:20px 24px; border-radius:12px; box-shadow:0 2px 8px rgba(0,0,0,.1); margin-bottom:24px; display:flex; justify-content:space-between; align-items:center; gap:20px; }
.search-container { flex:1; max-width:400px; }
.search-input-wrapper { position:relative; }
.search-icon { position:absolute; left:12px; top:50%; transform:translateY(-50%); color:#6c757d; font-size:16px; }
.search-input { width:100%; padding:10px 16px 10px 40px; border:2px solid #e9ecef; border-radius:8px; font-size:14px; transition:border-color .2s ease; }
.search-input:focus { outline:none; border-color:#007bff; box-shadow:0 0 0 3px rgba(0,123,255,.1); }
.filter-controls { display:flex; gap:20px; align-items:center; }
.filter-group { display:flex; align-items:center; gap:8px; }
.filter-label { color:#495057; font-weight:500; font-size:14px; white-space:nowrap; }
.page-size-select { padding:8px 12px; border:2px solid #e9ecef; border-radius:6px; font-size:14px; background:white; cursor:pointer; transition:border-color .2s ease; }
.page-size-select:focus { outline:none; border-color:#007bff; }
.table-container { background:white; border-radius:16px; box-shadow:0 4px 16px rgba(0,0,0,.08); border:1px solid #e5e7eb; position:relative; margin-bottom:24px; max-height:600px; overflow:auto; }
.admin-table { width:100%; border-collapse:collapse; min-width:1000px; }
.admin-table th { background:#f8f9fa; padding:16px 12px; text-align:left; font-weight:600; color:#495057; border-bottom:2px solid #e9ecef; font-size:14px; position:sticky; top:0; z-index:1; }
.admin-table td { padding:16px 12px; border-bottom:1px solid #e9ecef; font-size:14px; white-space:nowrap; }
.table-row:hover { background:#f8f9fa; }
.status-badge { display:inline-block; padding:4px 10px; border-radius:12px; font-size:12px; font-weight:600; }
.status-badge.pending { background:#fff3cd; color:#856404; }
.status-badge.paid { background:#d4edda; color:#155724; }
.status-badge.failed { background:#f8d7da; color:#721c24; }
.status-badge.refunded { background:#e2e3e5; color:#343a40; }
.status-badge.approved { background:#cfe2ff; color:#084298; }
.status-badge.rejected { background:#f8d7da; color:#721c24; }
.status-badge.canceled { background:#eee; color:#6b7280; }
.status-badge.assigned { background:#e0f2fe; color:#075985; }
.status-badge.not_assigned { background:#e9ecef; color:#495057; }
.actions-cell { text-align:center; }
.action-buttons { display:flex; justify-content:left; gap:8px; }
.btn-edit, .btn-delete { display:inline-flex; align-items:center; justify-content:center; width:36px; height:36px; border:none; border-radius:8px; cursor:pointer; font-size:14px; transition: all .3s ease; }
.btn-edit { background:#dbeafe; color:#1e40af; }
.btn-delete { background:#fecaca; color:#991b1b; }
.btn-edit:hover { background:#bfdbfe; transform: translateY(-1px); }
.btn-delete:hover { background:#fca5a5; transform: translateY(-1px); }
.empty-state { text-align:center; padding:64px 24px; color:#6b7280; }
.empty-icon { font-size:64px; margin-bottom:16px; opacity:.5; }
.pagination-container { display:flex; justify-content:space-between; align-items:center; background:white; padding:20px 24px; border-radius:16px; box-shadow:0 2px 8px rgba(0,0,0,.06); border:1px solid #e5e7eb; }
.pagination-info { color:#6b7280; font-size:14px; }
.pagination-controls { display:flex; align-items:center; gap:8px; }
.pagination-btn { padding:8px 16px; border:2px solid #e2e8f0; background:white; color:#374151; border-radius:8px; font-size:14px; font-weight:600; cursor:pointer; transition:all .3s ease; }
.pagination-btn:hover { background:#f8fafc; border-color:#3b82f6; color:#3b82f6; }
.page-numbers { display:flex; gap:4px; margin:0 8px; }
.page-number { display:flex; align-items:center; justify-content:center; width:36px; height:36px; border:2px solid transparent; background:white; color:#374151; border-radius:8px; font-size:14px; font-weight:600; cursor:pointer; transition:all .3s ease; }
.page-number.active { background:#3b82f6; color:white; border-color:#3b82f6; }

.modal-overlay { position:fixed; inset:0; background:rgba(0,0,0,.6); display:flex; align-items:center; justify-content:center; z-index:1000; padding:24px; }
.modal-content { background:white; border-radius:12px; max-width:600px; width:90%; max-height:90vh; overflow-y:auto; box-shadow: 0 4px 20px rgba(0, 0, 0, 0.15);}
.modal-header { display:flex; justify-content:space-between; align-items:center; padding:20px 24px; border-bottom:1px solid #e9ecef; }
.modal-header h2 {margin: 0; color: #2c3e50; font-size: 20px; font-weight: 600;}
.close-btn { display:flex; align-items:center; justify-content:center; width:32px; height:32px; border:none; background:#f3f4f6; color:#6b7280; border-radius:50%; cursor:pointer; font-size:24px; }
.btn-close {background: none; border: none; font-size: 24px; cursor: pointer; color: #6c757d; padding: 0; width: 32px; height: 32px; display: flex; align-items: center; justify-content: center; border-radius: 50%; transition: all 0.2s ease;}
.btn-close:hover {background: #f8f9fa; color: #495057;}
.modal-form { padding:24px; }
.form-row { display:flex; gap:20px; margin-bottom:20px; }
.form-group { flex:1; display:flex; flex-direction:column; }
.form-group.full-width { flex-basis:100%; }
.form-label { margin-bottom:6px; font-weight:500; color:#495057; font-size:14px; }
.form-input, .form-select, .form-textarea { padding:10px 12px; border:2px solid #e9ecef; border-radius:6px; font-size:14px; transition:border-color .2s ease; }
.form-textarea { resize:vertical; }
.form-input:focus, .form-select:focus, .form-textarea:focus { outline:none; border-color:#007bff; box-shadow:0 0 0 3px rgba(0,123,255,.1); }
.form-actions { display:flex; gap:12px; justify-content:center; padding: 0 24px 24px;}
.btn-secondary { padding:10px 20px; border:2px solid #6c757d; background:white; color:#6c757d; border-radius:6px; cursor:pointer; font-size:14px; font-weight:500; transition:all .2s ease; }
.btn-secondary:hover { background:#6c757d; color:white; }
.btn-danger { padding:10px 20px; border:2px solid #dc3545; background:#dc3545; color:white; border-radius:6px; cursor:pointer; font-size:14px; font-weight:500; transition:all .2s ease; }
.btn-danger:hover { background:#c82333; border-color:#c82333; }
.delete-modal { max-width:400px; }
.modal-body { padding:24px; text-align:center; }
.warning-text { color:#dc2626; font-weight:500; margin-top:8px; }

@media (max-width: 768px) {
  .route-management { padding:10px; }
  .page-header { flex-direction:column; align-items:flex-start; gap:15px; }
  .filters-section { flex-direction:column; align-items:stretch; }
  .filter-controls { flex-direction:column; align-items:stretch; }
  .form-row { flex-direction:column; gap:12px; }
  .form-actions { flex-direction:column; }
  .pagination-container { flex-direction:column; gap:15px; text-align:center; }
  .admin-table { font-size:12px; }
  .admin-table th, .admin-table td { padding:8px 6px; }
}

.status-badge.service { background:#dcfce7; color:#166534; }
.status-badge.paused { background:#e2e8f0; color:#475569; }
.status-badge.maintenance { background:#fef3c7; color:#92400e; }
.status-badge.retired { background:#f1f5f9; color:#64748b; }

</style>
