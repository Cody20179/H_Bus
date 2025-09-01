<template>
  <div class="login-root">
    <div class="login-card">
      <div class="brand">
        <h1>H-Bus 管理系統</h1>
        <p class="sub">請登入以進入管理後台</p>
      </div>

      <div class="form">
        <label>帳號</label>
        <input
          v-model="username"
          type="text"
          placeholder="請輸入帳號"
          @keyup.enter="login"
        />

        <label>密碼</label>
        <input
          v-model="password"
          type="password"
          placeholder="請輸入密碼"
          @keyup.enter="login"
        />

        <button :disabled="loading" @click="login">
          <span v-if="loading">登入中…</span>
          <span v-else>登入</span>
        </button>

        <p v-if="error" class="error">{{ error }}</p>

        <p v-if="info" class="info">{{ info }}</p>
      </div>

      <div class="footer">
        需協助請聯絡系統管理員
      </div>
    </div>
  </div>
</template>

<script setup>
/*
  這裡採用 Vue 3 Composition API (script setup)
  功能：
  - 發 POST /api/auth/login 將 username/password 傳到後端
  - 使用 credentials:'include'（如果後端用 httpOnly cookie）
  - 處理回應：若成功，儲存 user info（範例存 localStorage），並導頁
  - 錯誤處理與 loading 狀態
*/

import { ref } from 'vue'
import { useRouter } from 'vue-router'

const username = ref('')
const password = ref('')
const loading = ref(false)
const error = ref('')
const info = ref('')
const router = useRouter()

// 你可以在這裡調整 API_URL（例如在 .env 中配置）
const API_LOGIN = '/api/auth/login' // 若後端位於其他 host: e.g. 'https://api.example.com/api/auth/login'

async function login() {
  error.value = ''
  info.value = ''
  if (!username.value || !password.value) {
    error.value = '請輸入帳號與密碼'
    return
  }

  loading.value = true
  try {
    const res = await fetch(API_LOGIN, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      // 如果後端以 httpOnly cookie 回傳 refresh token / session，請保留 credentials
      // 如果你後端回傳 accessToken 並希望前端接收（不推薦存在 localStorage），可以視需求移除 credentials
      credentials: 'include',
      body: JSON.stringify({
        username: username.value,
        password: password.value
      })
    })

    // 先處理非 2xx
    if (!res.ok) {
      // 嘗試解析錯誤訊息
      let body = {}
      try { body = await res.json() } catch(e) { /* ignore */ }
      throw new Error(body.message || `登入失敗（狀態 ${res.status}）`)
    }

    const body = await res.json()

    // 預期後端回傳格式 (範例)：
    // { success: true, user: { id, username, role, permissions: [...] }, accessToken?: '...' }
    if (!body.success) {
      throw new Error(body.message || '登入失敗')
    }

    // 範例：把 user 資訊放到 localStorage（建議改用 Pinia/Vuex）
    // 如果你後端使用 httpOnly cookie 並且沒有回傳 token，仍可由 body.user 取得權限資訊
    if (body.user) {
      localStorage.setItem('user', JSON.stringify(body.user))
    }
    // 如果後端回傳 accessToken (不推薦放 localStorage)，請斟酌儲存位置
    if (body.accessToken) {
      // 例如：localStorage.setItem('accessToken', body.accessToken)
      // 我們不在此範例自動儲存 accessToken，建議採 httpOnly cookie + /api/auth/me 機制
    }

    // 導頁：可改成你要的路由
    info.value = '登入成功，正在導向…'
    // 等短暫提示後導頁（可直接 router.push）
    setTimeout(() => router.push({ name: 'Dashboard' }), 300)

  } catch (e) {
    error.value = e.message || '登入失敗'
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-root{
  width:100%;
  height:100vh;
  display:flex;
  align-items:center;
  justify-content:center;
  background:linear-gradient(180deg,#f8fafc,#eef2f7);
}
.login-card{
  width:360px;
  padding:18px;
  border-radius:12px;
  background:white;
  box-shadow:0 6px 20px rgba(10,10,10,0.08);
}
.brand h1{ margin:0; font-size:20px; color:#0f172a; }
.brand .sub{ margin:4px 0 12px; color:#6b7280; font-size:13px; }

.form{ display:flex; flex-direction:column; gap:8px; }
.form label{ font-size:13px; color:#374151; }
.form input{
  padding:10px 12px;
  border-radius:8px;
  border:1px solid #e6e9ee;
  outline:none;
  font-size:14px;
}
.form button{
  margin-top:6px;
  padding:10px;
  border-radius:8px;
  border:none;
  background:#0ea5a4;
  color:white;
  font-weight:600;
  cursor:pointer;
}
.error{ color:#dc2626; margin-top:6px; font-size:13px; }
.info{ color:#0f766e; margin-top:6px; font-size:13px; }
.footer{ margin-top:12px; font-size:12px; color:#9ca3af; text-align:center; }
</style>
