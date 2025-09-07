// src/services/api.ts
import axios, { type AxiosResponse } from 'axios'

// 建立 axios 實例，設定基本配置
const api = axios.create({
  baseURL: '', // 使用相對路徑，讓 Vite 代理處理
  timeout: 10000, // 請求超時時間 10 秒
  headers: {
    'Content-Type': 'application/json',
  },
})

// 請求攔截器 - 可以在這裡加入 token 等認證資訊
api.interceptors.request.use(
  (config) => {
    // 未來可以在這裡加入 Authorization token
    // const token = localStorage.getItem('token')
    // if (token) {
    //   config.headers.Authorization = `Bearer ${token}`
    // }
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// 回應攔截器 - 統一處理錯誤
api.interceptors.response.use(
  (response) => {
    return response
  },
  (error) => {
    // 統一錯誤處理
    console.error('API Error:', error)
    return Promise.reject(error)
  }
)

// 定義 API 回應的型別
export interface MemberStatsResponse {
  success: boolean
  data: {
    total_members: number
    active_members: number
    new_members_this_month: number
    growth_rate: number
  }
  error?: string
}

export interface AdminStatsResponse {
  success: boolean
  data: {
    total_admins: number
    online_admins: number
    total_roles: number
    active_today: number
  }
  error?: string
}

export interface DatabaseStatsResponse {
  success: boolean
  data: {
    status: string
    connection_time: number
    total_tables: number
    health: string
  }
  error?: string
}

// 儀表板相關 API
export const dashboardApi = {
  // 取得會員統計資料
  getMemberStats: async (): Promise<MemberStatsResponse> => {
    try {
      const response = await api.get<MemberStatsResponse>('/api/dashboard/member-stats')
      return response.data
    } catch (error) {
      console.error('取得會員統計失敗:', error)
      // 回傳預設值以避免前端錯誤
      return {
        success: false,
        error: '無法取得會員統計資料',
        data: {
          total_members: 0,
          active_members: 0,
          new_members_this_month: 0,
          growth_rate: 0
        }
      }
    }
  },

  // 取得管理員統計資料
  getAdminStats: async (): Promise<AdminStatsResponse> => {
    try {
      const response = await api.get<AdminStatsResponse>('/api/dashboard/admin-stats')
      return response.data
    } catch (error) {
      console.error('取得管理員統計失敗:', error)
      return {
        success: false,
        error: '無法取得管理員統計資料',
        data: {
          total_admins: 0,
          online_admins: 0,
          total_roles: 0,
          active_today: 0
        }
      }
    }
  },

  // 取得資料庫狀況統計
  getDatabaseStats: async (): Promise<DatabaseStatsResponse> => {
    try {
      const response = await api.get<DatabaseStatsResponse>('/api/dashboard/database-stats')
      return response.data
    } catch (error) {
      console.error('取得資料庫統計失敗:', error)
      return {
        success: false,
        error: '無法取得資料庫統計資料',
        data: {
          status: '異常',
          connection_time: 9999,
          total_tables: 0,
          health: '異常'
        }
      }
    }
  }
}

// 會員管理 API 型別
export interface Member {
  user_id: number
  username: string | null
  line_id: string | null
  email: string | null
  phone: string | null
  status: 'active' | 'inactive'
  preferences?: string | null
  privacy_settings?: string | null
  created_at?: string | null
  updated_at?: string | null
  last_login?: string | null
}

export interface MemberListResponse {
  users: Member[]
  total: number
  page: number
  limit: number
  total_pages: number
}

// 建立/更新會員可帶的欄位（密碼為選填；留空不變更）
export interface MemberPayload {
  username?: string
  line_id?: string | null
  email?: string | null
  phone?: string | null
  status?: 'active' | 'inactive'
  preferences?: string | null
  privacy_settings?: string | null
  password?: string // 新增：可選密碼
}

export type MemberUpdatePayload = MemberPayload

// 會員管理 API
export const memberApi = {
  // 取得會員列表
  getMembers: async (queryString: string = ''): Promise<AxiosResponse<MemberListResponse>> => {
    const response = await api.get<MemberListResponse>(`/users${queryString ? '?' + queryString : ''}`)
    return response
  },

  // 新增會員
  createMember: async (memberData: MemberPayload): Promise<AxiosResponse<any>> => {
    const response = await api.post('/Create_users', memberData)
    return response
  },

  // 更新會員
  updateMember: async (memberId: number, memberData: MemberUpdatePayload): Promise<AxiosResponse<any>> => {
    const response = await api.put(`/users/${memberId}`, memberData)
    return response
  },

  // 刪除會員
  deleteMember: async (memberId: number) => {
    const response = await api.delete(`/users/${memberId}`)
    return response
  },

  // 取得單一會員資料
  getMember: async (memberId: number): Promise<AxiosResponse<Member>> => {
    const response = await api.get<Member>(`/users/${memberId}`)
    return response
  }
}

export default api
