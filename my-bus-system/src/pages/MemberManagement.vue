<template>
  <div class="admin-management">
    <!-- 頁面標題 -->
    <div class="page-header">
      <div class="header-left">
        <h1 class="page-title">會員帳號管理</h1>
        <p class="page-description">管理系統會員帳號和狀態</p>
      </div>
      <div class="admin-header">
        <button 
          @click="openCreateModal" 
          class="btn-primary"
          :disabled="!canManageMembers"
        >
          <i class="icon-plus"></i>
          新增會員
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
            placeholder="搜尋：ID、用戶名、LINE ID、Email、電話"
            class="search-input"
          />
        </div>
      </div>
      
      <div class="filter-controls">
        <div class="filter-group">
          <label class="filter-label">狀態篩選：</label>
          <select v-model="statusFilter" @change="loadMembers" class="status-select">
            <option value="">全部狀態</option>
            <option value="active">啟用</option>
            <option value="inactive">停用</option>
          </select>
        </div>
        
        <div class="filter-group">
          <label class="filter-label">ID排序：</label>
          <select v-model="idSortOrder" @change="loadMembers" class="page-size-select">
            <option value="desc">由新到舊</option>
            <option value="asc">由舊到新</option>
          </select>
        </div>
        <div class="filter-group">
          <label class="filter-label">每頁顯示：</label>
          <select v-model="pageSize" @change="loadMembers" class="page-size-select">
            <option value="10">10 筆</option>
            <option value="20">20 筆</option>
            <option value="50">50 筆</option>
            <option value="100">100 筆</option>
          </select>
        </div>
      </div>
    </div>

    <!-- 會員列表 -->
    <!-- 資料表格 -->
    <div class="table-container">
      <div v-if="isLoading" class="loading-overlay">
        <div class="spinner"></div>
        <span>載入中...</span>
      </div>
      
      <table v-else class="admin-table">
        <thead>
          <tr>
            <th>ID</th>
            <th>用戶名</th>
            <th>LINE ID</th>
            <th>Email</th>
            <th>電話</th>
            <th>狀態</th>
            <th>預約狀態</th>
            <th>最後登入</th>
            <th>建立時間</th>
            <th class="actions-column">操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="member in members" :key="member.user_id" class="table-row">
            <td>{{ member.user_id }}</td>
            <td class="username-cell">
              <div class="user-info">
                <span class="username">{{ member.username || '未設定' }}</span>
              </div>
            </td>
            <td>{{ member.line_id || '未綁定' }}</td>
            <td>{{ member.email || '未設定' }}</td>
            <td>{{ member.phone || '未設定' }}</td>
            <td>
              <span class="status-badge" :class="member.status">
                {{ member.status === 'active' ? '啟用' : '停用' }}
              </span>
            </td>
            <td>
              <span class="reservation-badge" :class="reservationClass(member.reservation_status)">
                {{ reservationLabel(member.reservation_status) }}
              </span>
            </td>
            <td class="date-cell">{{ formatDate(member.last_login) || '從未登入' }}</td>
            <td class="date-cell">{{ formatDate(member.created_at) }}</td>
            <td class="actions-cell">
              <div class="action-buttons">
                <button 
                  @click="editMember(member)" 
                  class="btn-edit" 
                  title="編輯"
                  :disabled="!canManageMembers"
                >
                  ✏️
                </button>
                <button 
                  @click="deleteMember(member)" 
                  class="btn-delete" 
                  title="刪除"
                  :disabled="!canManageMembers"
                >
                  🗑️
                </button>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
      
      <!-- 空狀態 -->
      <div v-if="!isLoading && members.length === 0" class="empty-state">
        <div class="empty-icon">👥</div>
        <h3>沒有找到會員</h3>
        <p>{{ searchQuery ? '沒有符合搜尋條件的會員' : '目前沒有會員資料' }}</p>
      </div>
    </div>    <!-- 分頁控制器 -->
    <div v-if="!isLoading && members.length > 0" class="pagination-container">
      <div class="pagination-info">
        顯示第 {{ (currentPage - 1) * pageSize + 1 }} 到 
        {{ Math.min(currentPage * pageSize, totalMembers) }} 筆，
        共 {{ totalMembers }} 筆資料
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

    <!-- 新增/編輯會員 Modal -->
    <div v-if="showModal" class="modal-overlay" @click="closeModal">
      <div class="modal-content" @click.stop>
        <div class="modal-header">
          <h2>{{ isEditMode ? '編輯會員' : '新增會員' }}</h2>
          <button @click="closeModal" class="btn-close">×</button>
        </div>
        
        <form @submit.prevent="saveMemberV2" class="member-form" novalidate>
          <div class="form-row">
            <div class="form-group">
              <label class="form-label">用戶名 *</label>
              <input 
                v-model="currentMember.username"
                type="text" 
                class="form-input"
                required
                placeholder="請輸入用戶名"
              />
            </div>
            <div class="form-group">
              <label class="form-label">LINE ID</label>
              <input 
                v-model="currentMember.line_id"
                type="text" 
                class="form-input"
                placeholder="請輸入 LINE ID"
              />
            </div>
          </div>

          <div class="form-row">
            <div class="form-group">
              <label class="form-label">Email</label>
              <input 
                v-model="currentMember.email"
                type="email" 
                class="form-input"
                placeholder="請輸入 Email"
              />
            </div>
            <div class="form-group">
              <label class="form-label">電話 *</label>
              <input 
                v-model="currentMember.phone"
                type="text" 
                class="form-input"
                :required="!isEditMode"
                placeholder="請輸入電話號碼"
              />
            </div>
          </div>

                    <!-- 新增：可選的密碼欄位（留空則不變更） -->
          <div class="form-row">
            <div class="form-group">
              <label class="form-label">新密碼 *</label>
              <div class="password-input">
                <input
                  v-model="currentMember.password"
                  :type="showPassword ? 'text' : 'password'"
                  class="form-input"
                  :placeholder="isEditMode ? '留空不變更' : '請輸入新密碼'"
                  :required="!isEditMode"
                  autocomplete="new-password"
                />
                <button
                  type="button"
                  class="toggle-visibility"
                  :aria-label="showPassword ? '隱藏密碼' : '顯示密碼'"
                  @click="showPassword = !showPassword"
                >
                  <!-- 小眼睛圖示 -->
                  <svg v-if="!showPassword" xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"></path>
                    <circle cx="12" cy="12" r="3"></circle>
                  </svg>
                  <svg v-else xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <path d="M17.94 17.94A10.94 10.94 0 0 1 12 20c-7 0-11-8-11-8a21.77 21.77 0 0 1 5.06-6.94"></path>
                    <path d="M1 1l22 22"></path>
                    <path d="M9.88 9.88A3 3 0 0 0 12 15a3 3 0 0 0 2.12-.88"></path>
                  </svg>
                </button>
              </div>
            </div>
            <div class="form-group">
              <label class="form-label">確認新密碼 *</label>
              <div class="password-input">
                <input
                  v-model="currentMember.confirmPassword"
                  :type="showConfirmPassword ? 'text' : 'password'"
                  class="form-input"
                  placeholder="再次輸入新密碼"
                  :required="!isEditMode"
                  autocomplete="new-password"
                />
                <button
                  type="button"
                  class="toggle-visibility"
                  :aria-label="showConfirmPassword ? '隱藏密碼' : '顯示密碼'"
                  @click="showConfirmPassword = !showConfirmPassword"
                >
                  <svg v-if="!showConfirmPassword" xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"></path>
                    <circle cx="12" cy="12" r="3"></circle>
                  </svg>
                  <svg v-else xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <path d="M17.94 17.94A10.94 10.94 0 0 1 12 20c-7 0-11-8-11-8a21.77 21.77 0 0 1 5.06-6.94"></path>
                    <path d="M1 1l22 22"></path>
                    <path d="M9.88 9.88A3 3 0 0 0 12 15a3 3 0 0 0 2.12-.88"></path>
                  </svg>
                </button>
              </div>
            </div>
          </div>
          
          <div class="form-row">
            <div class="form-group">
              <label class="form-label">狀態</label>
              <select v-model="currentMember.status" class="form-select">
                <option value="active">啟用</option>
                <option value="inactive">停用</option>
              </select>
            </div>
          </div>

          <div class="form-row">
            <div class="form-group full-width">
              <label class="form-label">偏好設定</label>
              <textarea 
                v-model="currentMember.preferences"
                class="form-textarea"
                rows="3"
                placeholder="偏好設定"
              ></textarea>
            </div>
          </div>

          <div class="form-row">
            <div class="form-group full-width">
              <label class="form-label">隱私設定</label>
              <textarea 
                v-model="currentMember.privacy_settings"
                class="form-textarea"
                rows="3"
                placeholder="隱私設定"
              ></textarea>
            </div>
          </div>

          <div class="form-actions">
            <button type="button" @click="closeModal" class="btn-secondary">取消</button>
            <button type="submit" class="btn-primary" :disabled="isSaving">
              {{ isSaving ? '儲存中...' : (isEditMode ? '更新' : '建立') }}
            </button>
          </div>
        </form>
      </div>
    </div>

    <!-- 刪除確認 Modal -->
    <div v-if="showDeleteModal" class="modal-overlay" @click="closeDeleteModal">
      <div class="modal-content delete-modal" @click.stop>
        <div class="modal-header">
          <h2>確認刪除</h2>
          <button @click="closeDeleteModal" class="btn-close">×</button>
        </div>
        
        <div class="delete-content">
          <p>確定要刪除會員 <strong>{{ memberToDelete?.username || '未設定' }}</strong> 嗎？</p>
          <p class="warning-text">此操作無法復原！</p>
        </div>

        <div class="form-actions">
          <button @click="closeDeleteModal" class="btn-secondary">取消</button>
          <button @click="confirmDelete" class="btn-danger" :disabled="isDeleting">
            {{ isDeleting ? '刪除中...' : '確定刪除' }}
          </button>
        </div>
      </div>
    </div>

    <!-- Toast 通知 -->
    <div v-if="toast.show" :class="['toast', toast.type]">
      {{ toast.message }}
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed, watch } from 'vue'
import { memberApi } from '../services/api'

// 資料狀態
const members = ref<any[]>([])
const isLoading = ref(false)
const searchQuery = ref('')
const statusFilter = ref('')
const idSortOrder = ref<'desc' | 'asc'>('desc')
const pageSize = ref(10)
const currentPage = ref(1)
const totalMembers = ref(0)
const totalPages = ref(0)

// Modal 狀態
const showModal = ref(false)
const showDeleteModal = ref(false)
const isEditMode = ref(false)
const isSaving = ref(false)
const isDeleting = ref(false)
const memberToDelete = ref<any>(null)

// 當前會員資料
const currentMember = ref({
  user_id: null,
  username: '',
  line_id: '',
  email: '',
  phone: '',
  status: 'active',
  reservation_status: 'no_reservation',
  preferences: '',
  privacy_settings: '',
  // 新增：編輯/新增時可填入的新密碼（選填）
  password: '',
  // 新增：確認新密碼（僅前端檢核用，不送出）
  confirmPassword: ''
})

// Toast 通知
const toast = ref({
  show: false,
  message: '',
  type: 'success' // 'success', 'error', 'warning', 'info'
})

// 密碼欄位顯示切換
const showPassword = ref(false)
const showConfirmPassword = ref(false)

// 當前登入的管理員（從 localStorage 取）
const currentUser = ref<any>(null)
const currentUserRole = ref<string>('')
const isSuperAdmin = computed(() => currentUserRole.value === 'super_admin')
const isAdmin = computed(() => currentUserRole.value === 'admin')
// 是否可以管理會員（超管/高管）
const canManageMembers = computed(() => isSuperAdmin.value || isAdmin.value)

// 計算分頁顯示的頁碼
const visiblePages = computed(() => {
  const pages = []
  const start = Math.max(1, currentPage.value - 2)
  const end = Math.min(totalPages.value, start + 4)
  
  for (let i = start; i <= end; i++) {
    pages.push(i)
  }
  
  return pages
})

// 載入會員資料
async function loadMembers() {
  isLoading.value = true
  try {
    const params = new URLSearchParams({
      page: currentPage.value.toString(),
      limit: pageSize.value.toString()
    })
    
    if (searchQuery.value) {
      params.append('search', searchQuery.value)
    }
    
    if (statusFilter.value) {
      params.append('status', statusFilter.value)
    }
    if (idSortOrder.value) {
      params.append('order', idSortOrder.value)
    }
    
    const response = await memberApi.getMembers(params.toString())
    members.value = response.data.users || []
    totalMembers.value = response.data.total || 0
    totalPages.value = response.data.total_pages || Math.ceil(totalMembers.value / pageSize.value)
    
  } catch (error: any) {
    console.error('載入會員資料失敗:', error)
    showToast('載入會員資料失敗', 'error')
    members.value = []
  } finally {
    isLoading.value = false
  }
}

// 搜尋處理
let searchTimeout: ReturnType<typeof setTimeout> | null = null
function handleSearch() {
  if (searchTimeout) {
    clearTimeout(searchTimeout)
  }
  
  searchTimeout = setTimeout(() => {
    currentPage.value = 1
    loadMembers()
  }, 500)
}

// 分頁處理
function goToPage(page: number) {
  if (page >= 1 && page <= totalPages.value) {
    currentPage.value = page
    loadMembers()
  }
}

// 開啟新增 Modal
function openCreateModal() {
  if (!canManageMembers.value) return
  isEditMode.value = false
  currentMember.value = {
    user_id: null,
    username: '',
    line_id: '',
    email: '',
    phone: '',
    status: 'active',
    reservation_status: 'no_reservation',
    preferences: '',
    privacy_settings: '',
    password: '',
    confirmPassword: ''
  }
  showModal.value = true
}

// 開啟編輯 Modal
function editMember(member: any) {
  if (!canManageMembers.value) return
  isEditMode.value = true
  currentMember.value = {
    user_id: member.user_id,
    username: member.username || '',
    line_id: member.line_id || '',
    email: member.email || '',
    phone: member.phone || '',
    status: member.status || 'active',
    reservation_status: member.reservation_status || 'no_reservation',
    preferences: member.preferences || '',
    privacy_settings: member.privacy_settings || '',
    // 打開編輯視窗時不帶出既有密碼，需另行輸入
    password: '',
    confirmPassword: ''
  }
  showModal.value = true
}

// 關閉 Modal
function closeModal() {
  showModal.value = false
  isEditMode.value = false
  isSaving.value = false
}

// 刪除會員
function deleteMember(member: any) {
  if (!canManageMembers.value) return
  memberToDelete.value = member
  showDeleteModal.value = true
}

// 關閉刪除 Modal
function closeDeleteModal() {
  showDeleteModal.value = false
  memberToDelete.value = null
  isDeleting.value = false
}

// 確認刪除
async function confirmDelete() {
  if (!memberToDelete.value) return
  
  isDeleting.value = true
  try {
    await memberApi.deleteMember(memberToDelete.value.user_id)
    showToast('會員刪除成功', 'success')
    closeDeleteModal()
    loadMembers()
  } catch (error: any) {
    console.error('刪除會員失敗:', error)
    const message = error.response?.data?.detail || '刪除失敗'
    showToast(message, 'error')
  } finally {
    isDeleting.value = false
  }
}

// 載入當前使用者資訊（供權限控管）
function loadCurrentUser() {
  try {
    const userInfo = localStorage.getItem('user')
    if (userInfo) {
      currentUser.value = JSON.parse(userInfo)
      currentUserRole.value = currentUser.value?.role || ''
    }
  } catch (e) {
    // ignore
  }
}

// 格式化日期
function formatDate(dateString: string | null) {
  if (!dateString) return '從未'
  
  try {
    const date = new Date(dateString)
    return date.toLocaleString('zh-TW', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit'
    })
  } catch {
    return '無效日期'
  }
}

// 顯示 Toast
function showToast(message: string, type: 'success' | 'error' | 'warning' | 'info' = 'success') {
  toast.value = { show: true, message, type }
  setTimeout(() => {
    toast.value.show = false
  }, 3000)
}

// 預約狀態顯示
function reservationLabel(val: string | null | undefined) {
  const map: Record<string, string> = {
    no_reservation: '未預約',
    pending: '審核中',
    approved: '已核准',
    rejected: '已拒絕',
    completed: '已完成'
  }
  return map[(val || 'no_reservation') as string] || '未預約'
}

function reservationClass(val: string | null | undefined) {
  const map: Record<string, string> = {
    no_reservation: 'none',
    pending: 'pending',
    approved: 'approved',
    rejected: 'rejected',
    completed: 'completed'
  }
  return map[(val || 'no_reservation') as string] || 'none'
}

// 監聽頁面大小變化
watch(pageSize, () => {
  currentPage.value = 1
  loadMembers()
})

// 初始化
onMounted(() => {
  loadCurrentUser()
  loadMembers()
})

// 驗證工具
function isValidEmail(email: string) {
  const re = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
  return re.test((email || '').trim())
}

function isValidPhone(phone: string) {
  const digits = (phone || '').replace(/\D/g, '')
  return digits.length >= 8 && digits.length <= 15
}

// 新送出邏輯：Email 非必填，但若有填需檢核格式
async function saveMemberV2() {
  isSaving.value = true
  try {
    const basePayload: any = {
      username: currentMember.value.username,
      line_id: currentMember.value.line_id,
      email: currentMember.value.email,
      phone: currentMember.value.phone,
      status: currentMember.value.status,
      preferences: currentMember.value.preferences,
      privacy_settings: currentMember.value.privacy_settings
    }

    // 若 Email 為空字串則不送出此欄位，避免存空字串
    if (!currentMember.value.email || !currentMember.value.email.trim()) {
      delete basePayload.email
    }
    // 若 LINE ID 為空字串，移除欄位（避免 unique '' 衝突）
    if (!currentMember.value.line_id || !currentMember.value.line_id.trim()) {
      delete basePayload.line_id
    }
    // 偏好/隱私若為空白則移除
    if (!currentMember.value.preferences || !currentMember.value.preferences.trim()) {
      delete basePayload.preferences
    }
    if (!currentMember.value.privacy_settings || !currentMember.value.privacy_settings.trim()) {
      delete basePayload.privacy_settings
    }


    if (!isEditMode.value) {
      // 新增：必填
      if (!currentMember.value.username || !currentMember.value.username.trim()) {
        showToast('請輸入用戶名', 'error')
        return
      }
      if (!currentMember.value.phone || !currentMember.value.phone.trim()) {
        showToast('請輸入電話', 'error')
        return
      }
      if (!isValidPhone(currentMember.value.phone)) {
        showToast('電話格式不正確', 'error')
        return
      }
      // Email 非必填，但若有填需格式正確
      if (currentMember.value.email && !isValidEmail(currentMember.value.email)) {
        showToast('Email 格式不正確', 'error')
        return
      }
      // 密碼必填
      if (!currentMember.value.password || !currentMember.value.password.trim()) {
        showToast('請輸入密碼', 'error')
        return
      }
      if (currentMember.value.password.length < 8) {
        showToast('密碼至少 8 碼', 'error')
        return
      }
      if (currentMember.value.password !== currentMember.value.confirmPassword) {
        showToast('兩次輸入的密碼不一致', 'error')
        return
      }
      basePayload.password = currentMember.value.password
      await memberApi.createMember(basePayload)
      showToast('會員建立成功', 'success')
    } else {
      // 編輯：Email 若有填需格式正確
      if (currentMember.value.email && !isValidEmail(currentMember.value.email)) {
        showToast('Email 格式不正確', 'error')
        return
      }
      if (currentMember.value.phone && !isValidPhone(currentMember.value.phone)) {
        showToast('電話格式不正確', 'error')
        return
      }
      // 有填密碼才更新
      if (currentMember.value.password && currentMember.value.password.trim()) {
        if (currentMember.value.password.length < 8) {
          showToast('密碼至少 8 碼', 'error')
          return
        }
        if (currentMember.value.password !== currentMember.value.confirmPassword) {
          showToast('兩次輸入的密碼不一致', 'error')
          return
        }
        basePayload.password = currentMember.value.password
      }
      await memberApi.updateMember(currentMember.value.user_id!, basePayload)
      showToast('會員更新成功', 'success')
    }

    closeModal()
    loadMembers()
  } catch (error: any) {
    console.error('儲存會員失敗:', error)
    const message = error?.response?.data?.detail || '儲存失敗'
    showToast(message, 'error')
  } finally {
    isSaving.value = false
  }
}
</script>

<style scoped>
/* 使用與 AdminManagement.vue 完全相同的樣式 */
.admin-management {
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

.admin-header {
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

.status-select, .page-size-select {
  padding: 8px 12px;
  border: 2px solid #e9ecef;
  border-radius: 6px;
  font-size: 14px;
  background: white;
  cursor: pointer;
  transition: border-color 0.2s ease;
}

.status-select:focus, .page-size-select:focus {
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

.admin-row:hover {
  background: #f8f9fa;
}

.username-cell {
  font-weight: 500;
  color: #2c3e50;
}

.status-badge {
  display: inline-block;
  padding: 4px 12px;
  border-radius: 20px;
  font-size: 12px;
  font-weight: 500;
  text-align: center;
}

.status-badge.active {
  background: #d4edda;
  color: #155724;
}

.status-badge.inactive {
  background: #f8d7da;
  color: #721c24;
}

/* 預約狀態徽章（沿用既有風格） */
.reservation-badge {
  display: inline-block;
  padding: 4px 12px;
  border-radius: 20px;
  font-size: 12px;
  font-weight: 500;
  text-align: center;
}
.reservation-badge.none {
  background: #e9ecef;
  color: #495057;
}
.reservation-badge.pending {
  background: #fff3cd; /* 黃色 */
  color: #856404;
}
.reservation-badge.approved {
  background: #d4edda; /* 綠色 */
  color: #155724;
}
.reservation-badge.completed {
  background: #cfe2ff; /* 藍色偏淡 */
  color: #084298;
}
.reservation-badge.rejected {
  background: #f8d7da; /* 紅色 */
  color: #721c24;
}

/* 操作按鈕 */
.actions-cell {
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

.loading-row, .empty-row {
  text-align: center;
}

.loading-cell, .empty-cell {
  padding: 40px;
  color: #6c757d;
  font-style: italic;
}

.loading-content {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12px;
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

.btn-close {
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
  border-radius: 50%;
  transition: all 0.2s ease;
}

.btn-close:hover {
  background: #f8f9fa;
  color: #495057;
}

.member-form {
  padding: 24px;
}

.form-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 20px;
  margin-bottom: 20px;
}

.form-group {
  display: flex;
  flex-direction: column;
}

.form-group.full-width {
  grid-column: 1 / -1;
}

.form-label {
  margin-bottom: 6px;
  font-weight: 500;
  color: #495057;
  font-size: 14px;
}

.form-input, .form-select, .form-textarea {
  padding: 10px 12px;
  border: 2px solid #e9ecef;
  border-radius: 6px;
  font-size: 14px;
  transition: border-color 0.2s ease;
}

/* 密碼輸入與小眼睛圖示（維持既有配色，最小樣式） */
.password-input {
  position: relative;
}
.password-input .form-input {
  padding-right: 40px; /* 預留圖示空間 */
}
.toggle-visibility {
  position: absolute;
  right: 10px;
  top: 50%;
  transform: translateY(-50%);
  border: none;
  background: transparent;
  padding: 0;
  cursor: pointer;
  color: #6c757d; /* 與系統次級色一致 */
  display: inline-flex;
  align-items: center;
  justify-content: center;
}
.toggle-visibility:hover {
  color: #007bff; /* 沿用焦點藍色 */
}

.form-input:focus, .form-select:focus, .form-textarea:focus {
  outline: none;
  border-color: #007bff;
  box-shadow: 0 0 0 3px rgba(0, 123, 255, 0.1);
}

.form-textarea {
  resize: vertical;
  font-family: inherit;
}

.form-actions {
  display: flex;
  gap: 12px;
  justify-content: center;
  padding: 0 24px 24px;
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

.btn-primary:disabled, .btn-danger:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.delete-modal {
  max-width: 400px;
}

.delete-content {
  padding: 24px;
  text-align: center;
}

.warning-text {
  color: #dc3545;
  font-weight: 500;
  font-size: 14px;
}

/* Toast 通知 */
.toast {
  position: fixed;
  top: 20px;
  right: 20px;
  padding: 12px 20px;
  border-radius: 8px;
  color: white;
  font-weight: 500;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
  z-index: 1001;
  animation: slideIn 0.3s ease;
}

.toast.success {
  background: #28a745;
}

.toast.error {
  background: #dc3545;
}

.toast.warning {
  background: #ffc107;
  color: #212529;
}

.toast.info {
  background: #17a2b8;
}

@keyframes slideIn {
  from {
    transform: translateX(100%);
    opacity: 0;
  }
  to {
    transform: translateX(0);
    opacity: 1;
  }
}

/* 響應式設計 */
@media (max-width: 768px) {
  .page-header {
    flex-direction: column;
    gap: 16px;
  }
  
  .filters-section {
    flex-direction: column;
    gap: 16px;
  }
  
  .filter-controls {
    flex-direction: column;
    width: 100%;
  }
  
  .form-row {
    grid-template-columns: 1fr;
  }
  
  .form-actions {
    flex-direction: column;
  }

  .pagination-container {
    flex-direction: column;
    gap: 12px;
  }
  
  .table-container {
    border-radius: 8px;
  }
  
  .admin-table {
    min-width: 1200px; /* 在移動設備上保持更大的最小寬度 */
  }
}
</style>
