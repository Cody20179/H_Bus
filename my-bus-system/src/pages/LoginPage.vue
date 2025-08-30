<template>
  <div class="login-root">
    <div class="login-card">
      <div class="brand">
        <h1>H-Bus 管理系統</h1>
        <p class="sub">請登入以進入管理後台</p>
      </div>

      <div class="form">
        <label>帳號</label>
        <input v-model="username" type="text" placeholder="請輸入帳號" />

        <label>密碼</label>
        <input v-model="password" type="password" placeholder="請輸入密碼" />

        <button @click="login">登入</button>
      </div>

      <div class="footer">© 2025 H-Bus System</div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
const router = useRouter()

const username = ref('')
const password = ref('')

function login() {
  if (username.value === 'admin' && password.value === '1234') {
    router.push('/home')
  } else {
    alert('帳號或密碼錯誤')
  }
}
</script>

<style scoped>
.login-root{
  min-height:100vh;
  display:flex;
  align-items:center;
  justify-content:center;
  background: linear-gradient(135deg,#1f2937,#111827); /* dark bg */
  padding:20px;
}
.login-card{
  width:360px;
  background:#fff;
  border-radius:10px;
  box-shadow:0 8px 24px rgba(0,0,0,0.3);
  padding:24px;
}
.brand h1{ margin:0; font-size:20px; color:#0f172a; }
.brand .sub{ color:#6b7280; margin-top:6px; font-size:13px; }

.form{ margin-top:16px; display:flex; flex-direction:column; gap:10px; }
.form label{ font-size:13px; color:#374151; }
.form input{
  padding:10px 12px;
  border:1px solid #e5e7eb;
  border-radius:6px;
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
.footer{ margin-top:12px; font-size:12px; color:#9ca3af; text-align:center; }
</style>
