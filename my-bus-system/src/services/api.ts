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
    // 自動夾帶管理端 Authorization Token（若存在）
    try {
      const token = localStorage.getItem('token')
      if (token) {
        (config.headers as any).Authorization = `Bearer ${token}`
      }
    } catch (e) {
      // ignore
    }
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

export interface ReservationStatsResponse {
  success: boolean
  data: {
    this_month: number
    today_new: number
    pending: number
    completed: number
    last_month: number
    growth_rate: number
  }
  error?: string
}

export interface RouteStatsResponse {
  success: boolean
  data: {
    total: number
    active: number
    inactive: number
    on_time_rate: number
    routes_with_stations?: number
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
  },

  // 取得預約統計
  getReservationStats: async (): Promise<ReservationStatsResponse> => {
    try {
      const response = await api.get<ReservationStatsResponse>('/api/dashboard/reservation-stats')
      return response.data
    } catch (error) {
      console.error('取得預約統計失敗:', error)
      return {
        success: false,
        error: '無法取得預約統計',
        data: {
          this_month: 0,
          today_new: 0,
          pending: 0,
          completed: 0,
          last_month: 0,
          growth_rate: 0
        }
      }
    }
  },

  // 取得路線統計
  getRouteStats: async (): Promise<RouteStatsResponse> => {
    try {
      const response = await api.get<RouteStatsResponse>('/api/dashboard/route-stats')
      return response.data
    } catch (error) {
      console.error('取得路線統計失敗:', error)
      return {
        success: false,
        error: '無法取得路線統計',
        data: { total: 0, active: 0, inactive: 0, on_time_rate: 0 }
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
  success?: boolean
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
    const response = await api.get<MemberListResponse>(`/api/members${queryString ? '?' + queryString : ''}`)
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

// 車輛資源 API 型別
export interface CarResource {
  car_id: number
  car_licence: string
  max_passengers: number
  car_status: 'service' | 'paused' | 'maintenance' | 'retired'
  commission_date?: string | null
  last_service_date?: string | null
}

export interface CarListResponse {
  success: boolean
  data: CarResource[]
  pagination: {
    page: number
    limit: number
    total: number
    pages: number
  }
}

export interface CarResourcePayload {
  car_licence: string
  max_passengers: number
  car_status?: 'service' | 'paused' | 'maintenance' | 'retired'
  commission_date?: string | null
  last_service_date?: string | null
}

export type CarResourceUpdatePayload = Partial<CarResourcePayload>

// 車輛統計回應
export interface CarStatsResponse {
  success: boolean
  data: {
    total: number
    new_this_month: number
    status_counts: {
      service: number
      paused: number
      maintenance: number
      retired: number
    }
  }
}
export const carApi = {
  getCars: async (queryString: string = ''): Promise<AxiosResponse<CarListResponse>> => {
    const response = await api.get<CarListResponse>(`/api/cars${queryString ? '?' + queryString : ''}`)
    return response
  },
  createCar: async (payload: CarResourcePayload): Promise<AxiosResponse<any>> => {
    const response = await api.post('/api/cars', payload)
    return response
  },
  updateCar: async (carId: number, payload: CarResourceUpdatePayload): Promise<AxiosResponse<any>> => {
    const response = await api.put(`/api/cars/${carId}`, payload)
    return response
  },
  deleteCar: async (carId: number): Promise<AxiosResponse<any>> => {
    const response = await api.delete(`/api/cars/${carId}`)
    return response
  },
  getCarStats: async (): Promise<AxiosResponse<CarStatsResponse>> => {
    const response = await api.get<CarStatsResponse>('/api/cars/stats')
    return response
  }
}

export default api
