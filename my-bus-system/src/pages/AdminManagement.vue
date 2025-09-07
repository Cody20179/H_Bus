<template>
  <div class="admin-management">
    <!-- 頁面標題 -->
    <div class="page-header">
      <div class="header-left">
        <h1 class="page-title">管理員帳號管理</h1>
        <p class="page-description">管理系統管理員帳號和權限</p>
      </div>
      <div class="admin-header">
        <button 
          @click="openCreateModal" 
          class="btn-primary"
          :disabled="!(isSuperAdmin || isAdmin)"
          :class="{ disabled: !(isSuperAdmin || isAdmin) }"
          v-if="isSuperAdmin || isAdmin"
        >
          <i class="icon-plus"></i>
          新增管理員
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
            placeholder="搜尋管理員用戶名..."
            class="search-input"
          />
        </div>
      </div>
      
      <div class="filter-controls">
        <div class="filter-group">
          <label class="filter-label">狀態篩選：</label>
          <select v-model="statusFilter" @change="loadAdminUsers" class="status-select">
            <option value="">全部狀態</option>
            <option value="active">啟用</option>
            <option value="inactive">停用</option>
          </select>
        </div>
        
        <div class="filter-group">
          <label class="filter-label">每頁顯示：</label>
          <select v-model="pageSize" @change="handlePageSizeChange" class="page-size-select">
            <option :value="10">10 筆</option>
            <option :value="30">30 筆</option>
            <option :value="50">50 筆</option>
          </select>
        </div>
      </div>
    </div>

    <!-- 資料表格 -->
    <div class="table-container">
      <div v-if="loading" class="loading-overlay">
        <div class="spinner"></div>
        <span>載入中...</span>
      </div>
      
      <table v-else class="admin-table">
        <thead>
          <tr>
            <th>ID</th>
            <th>用戶名</th>
            <th>角色</th>
            <th>狀態</th>
            <th>最後登入</th>
            <th>建立時間</th>
            <th class="actions-column">操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="admin in adminUsers" :key="admin.admin_id" class="table-row">
            <td>{{ admin.admin_id }}</td>
            <td class="username-cell">
              <div class="user-info">
                <span class="username">{{ admin.username }}</span>
              </div>
            </td>
            <td>
              <span class="role-badge" :class="getRoleClass(admin.role_name)">
                {{ admin.role_description || admin.role_name }}
              </span>
            </td>
            <td>
              <span class="status-badge" :class="admin.status">
                {{ getStatusText(admin.status) }}
              </span>
            </td>
            <td class="date-cell">
              {{ formatDate(admin.last_login) || '從未登入' }}
            </td>
            <td class="date-cell">
              {{ formatDate(admin.created_at) }}
            </td>
            <td class="actions-cell">
              <div class="action-buttons">
                <button 
                  @click="editAdmin(admin)" 
                  class="btn-edit" 
                  title="編輯"
                  :disabled="!canEditUser(admin)"
                  :class="{ disabled: !canEditUser(admin) }"
                >
                  ✏️
                </button>
                <button 
                  @click="deleteAdmin(admin)" 
                  class="btn-delete" 
                  title="刪除"
                  :disabled="!canDeleteUser(admin)"
                  :class="{ disabled: !canDeleteUser(admin) }"
                  v-if="isSuperAdmin"
                >
                  🗑️
                </button>
              </div>
            </td>
          </tr>
        </tbody>
      </table>

      <!-- 空狀態 -->
      <div v-if="!loading && adminUsers.length === 0" class="empty-state">
        <div class="empty-icon">👥</div>
        <h3>沒有找到管理員</h3>
        <p>{{ searchQuery ? '沒有符合搜尋條件的管理員' : '目前沒有管理員資料' }}</p>
      </div>
    </div>

    <!-- 分頁控制器 -->
    <div v-if="!loading && adminUsers.length > 0" class="pagination-container">
      <div class="pagination-info">
        顯示第 {{ (currentPage - 1) * pageSize + 1 }} 到 
        {{ Math.min(currentPage * pageSize, totalCount) }} 筆，
        共 {{ totalCount }} 筆資料
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

    <!-- 新增/編輯管理員模態框 -->
    <div v-if="showCreateModal || showEditModal" class="modal-overlay" @click="closeModals">
      <div class="modal-content" @click.stop>
        <div class="modal-header">
          <h3>{{ showCreateModal ? '新增管理員' : '編輯管理員' }}</h3>
          <button @click="closeModals" class="modal-close">✕</button>
        </div>
        
        <form @submit.prevent="showCreateModal ? createAdmin() : updateAdmin()" class="admin-form">
          <div class="form-group">
            <label for="username" class="form-label">用戶名 *</label>
            <input
              id="username"
              v-model="formData.username"
              type="text"
              required
              class="form-input"
              placeholder="請輸入用戶名"
            />
          </div>
          
          <div v-if="showCreateModal || (showEditModal && isSuperAdmin && editingAdmin && editingAdmin.role_name === 'admin')" class="form-group">
            <label for="password" class="form-label">
              {{ showCreateModal ? '密碼 *' : '新密碼 (留空表示不修改)' }}
            </label>
            <input
              id="password"
              v-model="formData.password"
              type="password"
              :required="showCreateModal"
              class="form-input"
              :placeholder="showCreateModal ? '請輸入密碼' : '請輸入新密碼'"
            />
            <div v-if="showEditModal" class="form-hint">
              留空表示不修改密碼，輸入內容則更新為新密碼
            </div>
          </div>
          
          <div class="form-group">
            <label for="role_id" class="form-label">角色 *</label>
            <select
              id="role_id"
              v-model="formData.role_id"
              required
              class="form-select"
              :disabled="isRoleSelectDisabled"
            >
              <option value="">請選擇角色</option>
              <option 
                v-for="role in availableRoles" 
                :key="role.role_id" 
                :value="role.role_id"
              >
                {{ role.role_description }}
              </option>
            </select>
            <div v-if="!isSuperAdmin" class="form-hint">
              普通管理員只能創建/修改 Admin 角色帳號，且無法修改角色和狀態
            </div>
            <div v-else-if="showEditModal && editingAdmin && editingAdmin.admin_id === currentUser?.user_id" class="form-hint">
              Super Admin 不能修改自己的角色權限（包括降級為 Admin）
            </div>
            <div v-else-if="showEditModal && editingAdmin && editingAdmin.role_name === 'super_admin'" class="form-hint">
              不能將其他 Super Admin 降級為 Admin 角色
            </div>
            <div v-else-if="showCreateModal && adminUsers.some(user => user.role_name === 'super_admin')" class="form-hint">
              系統已有 Super Admin，只能創建 Admin 角色帳號
            </div>
          </div>
          
                    <div class="form-group">
            <label for="status" class="form-label">狀態 *</label>
            <select
              id="status"
              v-model="formData.status"
              required
              class="form-select"
              :disabled="isStatusSelectDisabled"
            >
              <option value="active">啟用</option>
              <option value="inactive">停用</option>
            </select>
            <div v-if="!isSuperAdmin" class="form-hint">
              普通管理員無法修改用戶狀態
            </div>
            <div v-else-if="showEditModal && editingAdmin && editingAdmin.admin_id === currentUser?.user_id" class="form-hint">
              Super Admin 不能停用自己的帳號
            </div>
          </div>
          
          <div class="form-actions">
            <button type="button" @click="closeModals" class="btn-cancel">
              取消
            </button>
            <button type="submit" class="btn-submit" :disabled="submitting">
              {{ submitting ? '處理中...' : (showCreateModal ? '新增' : '更新') }}
            </button>
          </div>
        </form>
      </div>
    </div>

    <!-- 刪除確認模態框 -->
    <div v-if="showDeleteModal" class="modal-overlay" @click="showDeleteModal = false">
      <div class="modal-content delete-modal" @click.stop>
        <div class="modal-header">
          <h3>確認刪除</h3>
          <button @click="showDeleteModal = false" class="modal-close">✕</button>
        </div>
        
        <div class="delete-content">
          <div class="warning-icon">⚠️</div>
          <p>您確定要刪除管理員 <strong>{{ adminToDelete?.username }}</strong> 嗎？</p>
          <p class="warning-text">此操作無法復原！</p>
        </div>
        
        <div class="form-actions">
          <button @click="showDeleteModal = false" class="btn-cancel">
            取消
          </button>
          <button @click="confirmDelete" class="btn-delete-confirm" :disabled="submitting">
            {{ submitting ? '刪除中...' : '確認刪除' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'

// 響應式數據
const adminUsers = ref<any[]>([])
const roles = ref<any[]>([])
const loading = ref(false)
const submitting = ref(false)
const currentUserRole = ref('')
const currentUser = ref<any>(null)

// 分頁相關
const currentPage = ref(1)
const pageSize = ref(10)
const totalCount = ref(0)
const totalPages = computed(() => Math.ceil(totalCount.value / pageSize.value))

// 搜尋和篩選
const searchQuery = ref('')
const statusFilter = ref('')
const searchTimeout = ref<ReturnType<typeof setTimeout> | null>(null)

// 檢查是否為超級管理員
const isSuperAdmin = computed(() => currentUserRole.value === 'super_admin')

// 檢查是否為普通管理員
const isAdmin = computed(() => currentUserRole.value === 'admin')

// 檢查是否可以編輯用戶
const canEditUser = computed(() => (admin: any) => {
  // Super admin 可以編輯其他用戶，但有限制
  if (isSuperAdmin.value) {
    // 不能編輯自己
    if (admin.admin_id === currentUser.value?.user_id) return false
    // Super Admin 不能編輯其他 Super Admin
    if (admin.role_name === 'super_admin') return false
    return true
  }
  // 普通 admin 不能編輯 super_admin 用戶
  return admin.role_name !== 'super_admin'
})

// 檢查是否可以刪除用戶
const canDeleteUser = computed(() => (admin: any) => {
  // 只有 super_admin 可以刪除用戶
  if (!isSuperAdmin.value) return false
  // 不能刪除自己
  if (admin.admin_id === currentUser.value?.user_id) return false
  // Super Admin 不能刪除其他 Super Admin
  if (admin.role_name === 'super_admin') return false
  return true
})

// 模態框控制
const showCreateModal = ref(false)
const showEditModal = ref(false)
const showDeleteModal = ref(false)
const adminToDelete = ref<any>(null)
const editingAdmin = ref<any>(null)

// 表單資料
const formData = ref({
  username: '',
  password: '',
  role_id: '',
  status: 'active'
})

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

// 可用角色列表 - 根據權限和現有super_admin數量決定
const availableRoles = computed(() => {
  if (isSuperAdmin.value) {
    // Super admin 可以選擇所有角色，但需要檢查是否已有super_admin
    if (showCreateModal.value) {
      // 創建模式：檢查是否已有super_admin
      const hasSuperAdmin = adminUsers.value.some(user => user.role_name === 'super_admin')
      if (hasSuperAdmin) {
        // 已有super_admin，只能選擇admin角色
        return roles.value.filter(role => role.role_id === 2)
      } else {
        // 沒有super_admin，可以選擇所有角色
        return roles.value
      }
    } else {
      // 編輯模式：如果是編輯自己，不能修改角色；編輯他人時需要檢查角色
      if (editingAdmin.value && editingAdmin.value.admin_id === currentUser.value?.user_id) {
        // 編輯自己：只顯示當前角色，不能修改
        return roles.value.filter(role => role.role_id === editingAdmin.value.role_id)
      } else if (editingAdmin.value && editingAdmin.value.role_name === 'super_admin') {
        // 編輯其他 Super Admin：不能降級為 Admin，只能保持 Super Admin
        return roles.value.filter(role => role.role_id === 1) // 只顯示 Super Admin 角色
      } else {
        // 編輯 Admin 用戶：可以選擇所有角色
        return roles.value
      }
    }
  } else {
    // 普通 admin 只能選擇 admin 角色 (role_id = 2)
    return roles.value.filter(role => role.role_id === 2)
  }
})

// 檢查角色選擇框是否應該被禁用
const isRoleSelectDisabled = computed(() => {
  // 普通 admin 不能修改角色
  if (!isSuperAdmin.value) return true
  
  // Super admin 編輯自己時不能修改角色
  if (showEditModal.value && editingAdmin.value && editingAdmin.value.admin_id === currentUser.value?.user_id) {
    return true
  }
  
  // Super admin 編輯其他 Super admin 時不能降級（角色選擇框禁用）
  if (showEditModal.value && editingAdmin.value && editingAdmin.value.role_name === 'super_admin') {
    return true
  }
  
  return false
})

// 檢查狀態選擇框是否應該被禁用
const isStatusSelectDisabled = computed(() => {
  // 普通 admin 不能修改狀態
  if (!isSuperAdmin.value) return true
  
  // Super admin 編輯自己時不能把狀態改為停用
  if (showEditModal.value && editingAdmin.value && editingAdmin.value.admin_id === currentUser.value?.user_id) {
    return true
  }
  
  return false
})

// 載入管理員用戶列表
async function loadAdminUsers() {
  try {
    loading.value = true
    
    const params = new URLSearchParams({
      page: currentPage.value.toString(),
      limit: pageSize.value.toString(),
    })
    
    if (searchQuery.value.trim()) {
      params.append('search', searchQuery.value.trim())
    }
    
    if (statusFilter.value) {
      params.append('status', statusFilter.value)
    }
    
    const response = await fetch(`http://localhost:8500/api/admin/users?${params}`, {
      headers: {
        'Authorization': `Bearer ${localStorage.getItem('token')}`
      }
    })
    const result = await response.json()
    
    if (result.success) {
      adminUsers.value = result.data.admin_users
      totalCount.value = result.data.pagination.total
    } else {
      console.error('載入管理員列表失敗:', result.message)
    }
  } catch (error) {
    console.error('載入管理員列表錯誤:', error)
  } finally {
    loading.value = false
  }
}

// 載入角色列表
async function loadRoles() {
  try {
    const response = await fetch('http://localhost:8500/api/admin/roles', {
      headers: {
        'Authorization': `Bearer ${localStorage.getItem('token')}`
      }
    })
    const result = await response.json()
    
    if (result.success) {
      roles.value = result.data
    }
  } catch (error) {
    console.error('載入角色列表錯誤:', error)
  }
}

// 搜尋處理（防抖）
function handleSearch() {
  if (searchTimeout.value) {
    clearTimeout(searchTimeout.value)
  }
  
  searchTimeout.value = setTimeout(() => {
    currentPage.value = 1
    loadAdminUsers()
  }, 500)
}

// 分頁大小改變
function handlePageSizeChange() {
  currentPage.value = 1
  loadAdminUsers()
}

// 切換頁面
function goToPage(page: number) {
  if (page >= 1 && page <= totalPages.value) {
    currentPage.value = page
    loadAdminUsers()
  }
}

// 重置表單
function resetForm() {
  formData.value = {
    username: '',
    password: '',
    role_id: isSuperAdmin.value ? '' : '2', // 普通管理員自動設為admin角色
    status: 'active'
  }
}

// 關閉所有模態框
function closeModals() {
  showCreateModal.value = false
  showEditModal.value = false
  showDeleteModal.value = false
  resetForm()
  editingAdmin.value = null
}

// 開啟新增模態框
function openCreateModal() {
  resetForm() // 重置表單，會根據權限設置默認角色
  showCreateModal.value = true
}

// 編輯管理員
function editAdmin(admin: any) {
  // 檢查權限
  if (!canEditUser.value(admin)) {
    alert('您沒有權限編輯此用戶')
    return
  }
  
  editingAdmin.value = admin
  formData.value = {
    username: admin.username,
    password: '',
    role_id: admin.role_id,
    status: admin.status
  }
  showEditModal.value = true
}

// 刪除管理員
function deleteAdmin(admin: any) {
  // 檢查權限
  if (!canDeleteUser.value(admin)) {
    if (!isSuperAdmin.value) {
      alert('只有超級管理員可以刪除用戶')
    } else {
      alert('不能刪除自己的帳號')
    }
    return
  }
  
  adminToDelete.value = admin
  showDeleteModal.value = true
}

// 新增管理員
async function createAdmin() {
  try {
    submitting.value = true
    
    const response = await fetch('http://localhost:8500/api/admin/users', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${localStorage.getItem('token')}`
      },
      body: JSON.stringify(formData.value),
    })
    
    const result = await response.json()
    
    if (result.success) {
      closeModals()
      loadAdminUsers()
      alert('管理員新增成功')
    } else {
      alert('新增失敗: ' + result.message)
    }
  } catch (error) {
    console.error('新增管理員錯誤:', error)
    alert('新增管理員時發生錯誤')
  } finally {
    submitting.value = false
  }
}

// 更新管理員
async function updateAdmin() {
  try {
    submitting.value = true
    
    const updateData: any = {
      username: formData.value.username,
      role_id: formData.value.role_id,
      status: formData.value.status
    }
    
    // 只有在提供密碼時才包含密碼
    if (formData.value.password && formData.value.password.trim()) {
      updateData.password = formData.value.password
    }
    
    const response = await fetch(`http://localhost:8500/api/admin/users/${editingAdmin.value.admin_id}`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${localStorage.getItem('token')}`
      },
      body: JSON.stringify(updateData),
    })
    
    const result = await response.json()
    
    if (result.success) {
      closeModals()
      loadAdminUsers()
      alert('管理員更新成功')
    } else {
      alert('更新失敗: ' + result.message)
    }
  } catch (error) {
    console.error('更新管理員錯誤:', error)
    alert('更新管理員時發生錯誤')
  } finally {
    submitting.value = false
  }
}

// 確認刪除
async function confirmDelete() {
  try {
    submitting.value = true
    
    const response = await fetch(`http://localhost:8500/api/admin/users/${adminToDelete.value.admin_id}`, {
      method: 'DELETE',
      headers: {
        'Authorization': `Bearer ${localStorage.getItem('token')}`
      }
    })
    
    const result = await response.json()
    
    if (result.success) {
      showDeleteModal.value = false
      loadAdminUsers()
      alert('管理員刪除成功')
    } else {
      alert('刪除失敗: ' + result.message)
    }
  } catch (error) {
    console.error('刪除管理員錯誤:', error)
    alert('刪除管理員時發生錯誤')
  } finally {
    submitting.value = false
    adminToDelete.value = null
  }
}

// 格式化日期
function formatDate(dateString: string | null) {
  if (!dateString) return null
  
  const date = new Date(dateString)
  return date.toLocaleString('zh-TW', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  })
}

// 取得狀態文字
function getStatusText(status: string) {
  const statusMap: { [key: string]: string } = {
    active: '啟用',
    inactive: '停用'
  }
  return statusMap[status] || status
}

// 取得角色樣式類別
function getRoleClass(roleName: string) {
  const roleClassMap: { [key: string]: string } = {
    super_admin: 'super-admin',
    admin: 'admin',
    user: 'user'
  }
  return roleClassMap[roleName] || 'default'
}

// 獲取當前用戶資訊
async function getCurrentUser() {
  try {
    // 從 localStorage 獲取用戶資訊（簡化實現）
    const userInfo = localStorage.getItem('user')
    if (userInfo) {
      const user = JSON.parse(userInfo)
      currentUserRole.value = user.role || ''
      currentUser.value = user
    }
  } catch (error) {
    console.error('獲取當前用戶資訊錯誤:', error)
  }
}

// 組件掛載時載入資料
onMounted(() => {
  getCurrentUser()
  loadAdminUsers()
  loadRoles()
})
</script>

<style scoped>
/* 基本樣式 */
.admin-management {
  padding: 0;
  max-width: none;
  margin: 0;
  width: 100%;
}

/* 頁面標題 */
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 32px;
  padding-bottom: 16px;
  border-bottom: 2px solid #e5e7eb;
}

.header-left {
  flex: 1;
}

.page-title {
  font-size: 28px;
  font-weight: 700;
  color: #111827;
  margin: 0 0 8px 0;
}

.page-description {
  font-size: 16px;
  color: #6b7280;
  margin: 0;
}

.header-right {
  margin-left: 24px;
}

.btn-primary {
  display: flex;
  align-items: center;
  gap: 8px;
  background: linear-gradient(135deg, #3b82f6, #1d4ed8);
  color: white;
  border: none;
  border-radius: 12px;
  padding: 12px 24px;
  font-size: 16px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s ease;
  box-shadow: 0 4px 12px rgba(59, 130, 246, 0.3);
}

.btn-primary:hover {
  background: linear-gradient(135deg, #2563eb, #1e40af);
  transform: translateY(-2px);
  box-shadow: 0 6px 16px rgba(59, 130, 246, 0.4);
}

.btn-primary:disabled,
.btn-primary.disabled {
  opacity: 0.5;
  cursor: not-allowed;
  background: #9ca3af !important;
  transform: none !important;
  box-shadow: none !important;
  pointer-events: none;
}

.btn-primary:disabled:hover,
.btn-primary.disabled:hover {
  transform: none;
  background: #9ca3af !important;
  box-shadow: none !important;
}

.icon {
  font-size: 18px;
}

/* 搜尋和篩選區域 */
.filters-section {
  background: #f8fafc;
  border-radius: 16px;
  padding: 24px;
  margin-bottom: 24px;
  border: 1px solid #e2e8f0;
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
  left: 16px;
  top: 50%;
  transform: translateY(-50%);
  color: #6b7280;
  font-size: 16px;
}

.search-input {
  width: 100%;
  padding: 12px 16px 12px 48px;
  border: 2px solid #e2e8f0;
  border-radius: 12px;
  font-size: 16px;
  background: white;
  transition: border-color 0.3s ease;
}

.search-input:focus {
  outline: none;
  border-color: #3b82f6;
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
}

.filter-controls {
  display: flex;
  gap: 24px;
  flex-wrap: wrap;
}

.filter-group {
  display: flex;
  align-items: center;
  gap: 8px;
}

.filter-label {
  font-weight: 600;
  color: #374151;
  white-space: nowrap;
}

.status-select,
.page-size-select {
  padding: 8px 12px;
  border: 2px solid #e2e8f0;
  border-radius: 8px;
  font-size: 14px;
  background: white;
  cursor: pointer;
  transition: border-color 0.3s ease;
}

.status-select:focus,
.page-size-select:focus {
  outline: none;
  border-color: #3b82f6;
}

/* 表格容器 */
.table-container {
  background: white;
  border-radius: 16px;
  overflow: hidden;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.08);
  border: 1px solid #e5e7eb;
  position: relative;
  margin-bottom: 24px;
}

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

/* 表格樣式 */
.admin-table {
  width: 100%;
  border-collapse: collapse;
}

.admin-table thead {
  background: linear-gradient(135deg, #f8fafc, #e2e8f0);
}

.admin-table th {
  padding: 16px;
  text-align: left;
  font-weight: 600;
  color: #374151;
  border-bottom: 2px solid #e5e7eb;
  white-space: nowrap;
}

.admin-table td {
  padding: 16px;
  border-bottom: 1px solid #f1f5f9;
  vertical-align: middle;
}

.table-row:hover {
  background: #f8fafc;
}

.actions-column {
  width: 120px;
  text-align: center;
}

.username-cell {
  font-weight: 600;
}

.user-info {
  display: flex;
  align-items: center;
  gap: 12px;
}

.username {
  color: #111827;
}

/* 狀態和角色標籤 */
.status-badge,
.role-badge {
  display: inline-block;
  padding: 4px 12px;
  border-radius: 20px;
  font-size: 12px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.status-badge.active {
  background: #d1fae5;
  color: #065f46;
}

.status-badge.inactive {
  background: #fef3c7;
  color: #92400e;
}

.role-badge.super-admin {
  background: #ede9fe;
  color: #5b21b6;
}

.role-badge.admin {
  background: #dbeafe;
  color: #1e40af;
}

.role-badge.user {
  background: #f0f9ff;
  color: #0369a1;
}

.role-badge.default {
  background: #f3f4f6;
  color: #374151;
}

.date-cell {
  color: #6b7280;
  font-size: 14px;
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

/* 禁用按鈕樣式 */
.btn-edit:disabled,
.btn-edit.disabled,
.btn-delete:disabled,
.btn-delete.disabled {
  opacity: 0.5;
  cursor: not-allowed;
  background: #f3f4f6;
  color: #9ca3af;
}

.btn-edit:disabled:hover,
.btn-edit.disabled:hover,
.btn-delete:disabled:hover,
.btn-delete.disabled:hover {
  transform: none;
  background: #f3f4f6;
}

.btn-delete:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* 禁用狀態的通用樣式 */
.btn-edit.disabled,
.btn-delete.disabled {
  opacity: 0.3;
  cursor: not-allowed;
  pointer-events: none;
  background-color: #f3f4f6 !important;
  color: #9ca3af !important;
}

.btn-edit.disabled:hover,
.btn-delete.disabled:hover {
  transform: none;
  background-color: #f3f4f6 !important;
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

/* 分頁控制器 */
.pagination-container {
  display: flex;
  justify-content: space-between;
  align-items: center;
  background: white;
  padding: 20px 24px;
  border-radius: 16px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
  border: 1px solid #e5e7eb;
}

.pagination-info {
  color: #6b7280;
  font-size: 14px;
}

.pagination-controls {
  display: flex;
  align-items: center;
  gap: 8px;
}

.pagination-btn {
  padding: 8px 16px;
  border: 2px solid #e2e8f0;
  background: white;
  color: #374151;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s ease;
}

.pagination-btn:hover:not(:disabled) {
  background: #f8fafc;
  border-color: #3b82f6;
  color: #3b82f6;
}

.pagination-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.page-numbers {
  display: flex;
  gap: 4px;
  margin: 0 8px;
}

.page-number {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 36px;
  height: 36px;
  border: 2px solid transparent;
  background: white;
  color: #374151;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s ease;
}

.page-number:hover {
  background: #f8fafc;
  color: #3b82f6;
}

.page-number.active {
  background: #3b82f6;
  color: white;
  border-color: #3b82f6;
}

/* 模態框樣式 */
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.6);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  padding: 24px;
}

.modal-content {
  background: white;
  border-radius: 16px;
  max-width: 500px;
  width: 100%;
  max-height: 90vh;
  overflow-y: auto;
  box-shadow: 0 20px 40px rgba(0, 0, 0, 0.15);
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 24px 24px 16px 24px;
  border-bottom: 1px solid #e5e7eb;
}

.modal-header h3 {
  font-size: 20px;
  font-weight: 700;
  color: #111827;
  margin: 0;
}

.modal-close {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  border: none;
  background: #f3f4f6;
  color: #6b7280;
  border-radius: 50%;
  cursor: pointer;
  font-size: 18px;
  transition: all 0.3s ease;
}

.modal-close:hover {
  background: #e5e7eb;
  color: #374151;
}

/* 表單樣式 */
.admin-form {
  padding: 24px;
}

.form-group {
  margin-bottom: 20px;
}

.form-label {
  display: block;
  font-weight: 600;
  color: #374151;
  margin-bottom: 8px;
  font-size: 14px;
}

.form-input,
.form-select {
  width: 100%;
  padding: 12px 16px;
  border: 2px solid #e2e8f0;
  border-radius: 8px;
  font-size: 16px;
  background: white;
  transition: border-color 0.3s ease;
  box-sizing: border-box;
}

.form-input:focus,
.form-select:focus {
  outline: none;
  border-color: #3b82f6;
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
}

/* 禁用狀態的表單元素樣式 */
.form-input:disabled,
.form-select:disabled {
  background-color: #f9fafb;
  color: #9ca3af;
  cursor: not-allowed;
  opacity: 0.6;
}

.form-input:disabled:focus,
.form-select:disabled:focus {
  border-color: #e2e8f0;
  box-shadow: none;
}

.form-hint {
  font-size: 12px;
  color: #6b7280;
  margin-top: 4px;
  line-height: 1.4;
}

.form-actions {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  margin-top: 32px;
  padding-top: 20px;
  border-top: 1px solid #e5e7eb;
}

.btn-cancel,
.btn-submit,
.btn-delete-confirm {
  padding: 12px 24px;
  border: none;
  border-radius: 8px;
  font-size: 16px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s ease;
}

.btn-cancel {
  background: #f3f4f6;
  color: #374151;
}

.btn-cancel:hover {
  background: #e5e7eb;
}

.btn-submit {
  background: linear-gradient(135deg, #10b981, #059669);
  color: white;
}

.btn-submit:hover:not(:disabled) {
  background: linear-gradient(135deg, #059669, #047857);
  transform: translateY(-1px);
}

.btn-submit:disabled {
  opacity: 0.6;
  cursor: not-allowed;
  transform: none;
}

.btn-delete-confirm {
  background: linear-gradient(135deg, #ef4444, #dc2626);
  color: white;
}

.btn-delete-confirm:hover:not(:disabled) {
  background: linear-gradient(135deg, #dc2626, #b91c1c);
  transform: translateY(-1px);
}

.btn-delete-confirm:disabled {
  opacity: 0.6;
  cursor: not-allowed;
  transform: none;
}

/* 刪除模態框 */
.delete-modal {
  max-width: 400px;
}

.delete-content {
  padding: 24px;
  text-align: center;
}

.warning-icon {
  font-size: 48px;
  margin-bottom: 16px;
  color: #ef4444;
}

.delete-content p {
  font-size: 16px;
  color: #374151;
  margin: 0 0 8px 0;
}

.warning-text {
  color: #ef4444 !important;
  font-weight: 600;
}

/* 響應式設計 */
@media (max-width: 1024px) {
  .admin-management {
    padding: 16px;
  }
  
  .page-header {
    flex-direction: column;
    gap: 16px;
    align-items: stretch;
  }
  
  .header-right {
    margin-left: 0;
  }
  
  .filter-controls {
    flex-direction: column;
    gap: 16px;
  }
  
  .filter-group {
    flex-direction: column;
    align-items: flex-start;
    gap: 4px;
  }
  
  .pagination-container {
    flex-direction: column;
    gap: 16px;
    text-align: center;
  }
}

@media (max-width: 768px) {
  .admin-table {
    font-size: 14px;
  }
  
  .admin-table th,
  .admin-table td {
    padding: 12px 8px;
  }
  
  .modal-overlay {
    padding: 16px;
  }
  
  .page-numbers {
    display: none;
  }
  
  .search-input-wrapper {
    max-width: none;
  }
}
</style>
