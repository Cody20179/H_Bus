// src/services/authService.ts
import api from './api'

// 定義登入請求的資料類型
export interface LoginRequest {
  username: string
  password: string
}

// 定義登入回應的資料類型
export interface LoginResponse {
  access_token: string
  token_type: string
  user_id: number
  username: string
  role?: string
}

// 登入 API 函數
export async function login(credentials: LoginRequest): Promise<LoginResponse> {
  try {
    console.log('開始登入請求...', { username: credentials.username })
    
    // 使用 JSON 格式發送請求（配合 FastAPI 的 Pydantic 模型）
    const response = await api.post('/auth/login', {
      username: credentials.username,
      password: credentials.password
    })

    console.log('登入 API 請求成功！', response.data)
    console.log('回應狀態:', response.status)
    console.log('回應資料:', response.data)

    return response.data
  } catch (error: any) {
    // 處理錯誤並拋出有意義的錯誤訊息
    console.error('登入錯誤詳細資訊:', error)
    console.error('錯誤狀態:', error.response?.status)
    console.error('錯誤資料:', error.response?.data)
    
    if (error.response?.status === 401) {
      throw new Error('帳號或密碼錯誤')
    } else if (error.response?.status >= 500) {
      throw new Error('伺服器錯誤，請稍後再試')
    } else {
      throw new Error(`登入失敗: ${error.response?.data?.detail || error.message}`)
    }
  }
}

// 登出函數（清除本地儲存的認證資訊）
export function logout(): void {
  localStorage.removeItem('token')
  localStorage.removeItem('user')
}

// 檢查是否已登入
export function isLoggedIn(): boolean {
  return !!localStorage.getItem('token')
}

// 取得當前用戶資訊
export function getCurrentUser(): any {
  const userStr = localStorage.getItem('user')
  return userStr ? JSON.parse(userStr) : null
}
