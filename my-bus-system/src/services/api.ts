// src/services/api.ts
import axios, { type AxiosResponse } from 'axios'

const api = axios.create({
  baseURL: '',
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json',
  },
})

api.interceptors.request.use(
  (config) => {
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

api.interceptors.response.use(
  (response) => {
    return response
  },
  (error) => {
    console.error('API Error:', error)
    return Promise.reject(error)
  }
)

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

export interface ReservationTrendWeek {
  week: number
  label: string
  start_date: string
  end_date: string
  count: number
}

export interface ReservationTrendMonth {
  month: string
  label: string
  count: number
}

export interface ReservationTrendData {
  mode: 'monthly' | 'range'
  year?: number
  month?: number
  start_month?: string
  end_month?: string
  weeks?: ReservationTrendWeek[]
  months?: ReservationTrendMonth[]
  total: number
}

export interface ReservationTrendResponse {
  success: boolean
  data: ReservationTrendData
  error?: string
}

export interface ReservationStatusBreakdown {
  [status: string]: number
}

export interface ReservationStatusWeek {
  week: number
  label: string
  start_date: string
  end_date: string
  total: number
  reservation_status: ReservationStatusBreakdown
  review_status: ReservationStatusBreakdown
}

export interface ReservationStatusMonth {
  month: string
  label: string
  total: number
  reservation_status: ReservationStatusBreakdown
  review_status: ReservationStatusBreakdown
}

export interface ReservationStatusData {
  mode: 'monthly' | 'range'
  year?: number
  month?: number
  start_month?: string
  end_month?: string
  weeks?: ReservationStatusWeek[]
  months?: ReservationStatusMonth[]
  total: number
  reservation_status_keys?: string[]
  review_status_keys?: string[]
}

export interface ReservationStatusResponse {
  success: boolean
  data: ReservationStatusData
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

export const dashboardApi = {
  getMemberStats: async (): Promise<MemberStatsResponse> => {
    try {
      const response = await api.get<MemberStatsResponse>('/api/dashboard/member-stats')
      return response.data
    } catch (error) {
      console.error('getMemberStats error:', error)
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

  getAdminStats: async (): Promise<AdminStatsResponse> => {
    try {
      const response = await api.get<AdminStatsResponse>('/api/dashboard/admin-stats')
      return response.data
    } catch (error) {
      console.error('getAdminStats error:', error)
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

  getDatabaseStats: async (): Promise<DatabaseStatsResponse> => {
    try {
      const response = await api.get<DatabaseStatsResponse>('/api/dashboard/database-stats')
      return response.data
    } catch (error) {
      console.error('getDatabaseStats error:', error)
      return {
        success: false,
        error: '無法取得資料庫統計資料',
        data: {
          status: '未知',
          connection_time: 9999,
          total_tables: 0,
          health: '未知'
        }
      }
    }
  },

  getReservationStats: async (): Promise<ReservationStatsResponse> => {
    try {
      const response = await api.get<ReservationStatsResponse>('/api/dashboard/reservation-stats')
      return response.data
    } catch (error) {
      console.error('getReservationStats error:', error)
      return {
        success: false,
        error: '無法取得預約統計資料',
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

  getReservationTrendMonthly: async (year: number, month: number): Promise<ReservationTrendResponse> => {
    try {
      const response = await api.get<ReservationTrendResponse>('/api/dashboard/reservations/trend', {
        params: { mode: 'monthly', year, month }
      })
      return response.data
    } catch (error) {
      console.error('getReservationTrendMonthly error:', error)
      return {
        success: false,
        error: '無法取得預約趨勢(月)',
        data: {
          mode: 'monthly',
          year,
          month,
          weeks: [],
          total: 0
        }
      }
    }
  },

  getReservationTrendRange: async (startMonth: string, endMonth: string): Promise<ReservationTrendResponse> => {
    try {
      const response = await api.get<ReservationTrendResponse>('/api/dashboard/reservations/trend', {
        params: { mode: 'range', start_month: startMonth, end_month: endMonth }
      })
      return response.data
    } catch (error) {
      console.error('getReservationTrendRange error:', error)
      return {
        success: false,
        error: '無法取得預約趨勢(區間)',
        data: {
          mode: 'range',
          start_month: startMonth,
          end_month: endMonth,
          months: [],
          total: 0
        }
      }
    }
  },

  getReservationStatusMonthly: async (year: number, month: number): Promise<ReservationStatusResponse> => {
    try {
      const response = await api.get<ReservationStatusResponse>('/api/dashboard/reservations/status', {
        params: { mode: 'monthly', year, month }
      })
      return response.data
    } catch (error) {
      console.error('getReservationStatusMonthly error:', error)
      return {
        success: false,
        error: '無法取得預約狀態(月)',
        data: {
          mode: 'monthly',
          year,
          month,
          weeks: [],
          total: 0,
          reservation_status_keys: [],
          review_status_keys: []
        }
      }
    }
  },

  getReservationStatusRange: async (startMonth: string, endMonth: string): Promise<ReservationStatusResponse> => {
    try {
      const response = await api.get<ReservationStatusResponse>('/api/dashboard/reservations/status', {
        params: { mode: 'range', start_month: startMonth, end_month: endMonth }
      })
      return response.data
    } catch (error) {
      console.error('getReservationStatusRange error:', error)
      return {
        success: false,
        error: '無法取得預約狀態(區間)',
        data: {
          mode: 'range',
          start_month: startMonth,
          end_month: endMonth,
          months: [],
          total: 0,
          reservation_status_keys: [],
          review_status_keys: []
        }
      }
    }
  },

  getRouteStats: async (): Promise<RouteStatsResponse> => {
    try {
      const response = await api.get<RouteStatsResponse>('/api/dashboard/route-stats')
      return response.data
    } catch (error) {
      console.error('getRouteStats error:', error)
      return {
        success: false,
        error: '無法取得路線統計資料',
        data: { total: 0, active: 0, inactive: 0, on_time_rate: 0 }
      }
    }
  }
}

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

export interface MemberPayload {
  username?: string
  line_id?: string | null
  email?: string | null
  phone?: string | null
  status?: 'active' | 'inactive'
  preferences?: string | null
  privacy_settings?: string | null
  password?: string
}

export type MemberUpdatePayload = MemberPayload

export const memberApi = {
  getMembers: async (queryString: string = ''): Promise<AxiosResponse<MemberListResponse>> => {
    const response = await api.get<MemberListResponse>(`/api/members${queryString ? '?' + queryString : ''}`)
    return response
  },

  createMember: async (memberData: MemberPayload): Promise<AxiosResponse<any>> => {
    const response = await api.post('/Create_users', memberData)
    return response
  },

  updateMember: async (memberId: number, memberData: MemberUpdatePayload): Promise<AxiosResponse<any>> => {
    const response = await api.put(`/users/${memberId}`, memberData)
    return response
  },

  deleteMember: async (memberId: number) => {
    const response = await api.delete(`/users/${memberId}`)
    return response
  },

  getMember: async (memberId: number): Promise<AxiosResponse<Member>> => {
    const response = await api.get<Member>(`/users/${memberId}`)
    return response
  }
}

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

export interface GenerateQrCodesPayload {
  base_url: string
  route_id: number
  stop_count: number
  output_prefix?: string
}

export const toolsApi = {
  generateQrCodes: async (payload: GenerateQrCodesPayload): Promise<Blob> => {
    const response = await api.post('/api/tools/qr-codes', payload, { responseType: 'blob' })
    return response.data
  }
}

export default api

export interface EmailReminderConfig {
  enabled: boolean
  hour: number
  minute: number
  timezone: string
  next_run_at?: string | null
  last_run_at?: string | null
  last_run_status?: string | null
  last_error?: string | null
  last_run_summary?: EmailReminderRunSummary | null
}

export interface EmailReminderRunSummary {
  run_id: number
  status: string
  started_at?: string | null
  finished_at?: string | null
  total_emails: number
  success_emails: number
  failed_emails: number
  message?: string | null
  error_message?: string | null
}

export interface EmailReminderRunResult {
  status: string
  run_id?: number
  total_emails?: number
  success_emails?: number
  failed_emails?: number
  message?: string | null
  error?: string | null
}

export interface EmailReminderRunResponse {
  status: string
  result: EmailReminderRunResult
  config: EmailReminderConfig
}

export const emailReminderApi = {
  getConfig: async (): Promise<EmailReminderConfig> => {
    const { data } = await api.get<EmailReminderConfig>('/api/reservation-reminder/config')
    return data
  },
  updateConfig: async (payload: { enabled: boolean; hour: number; minute: number; timezone: string }): Promise<EmailReminderConfig> => {
    const { data } = await api.put<EmailReminderConfig>('/api/reservation-reminder/config', payload)
    return data
  },
  runNow: async (): Promise<EmailReminderRunResponse> => {
    const { data } = await api.post<EmailReminderRunResponse>('/api/reservation-reminder/run')
    return data
  }
}
