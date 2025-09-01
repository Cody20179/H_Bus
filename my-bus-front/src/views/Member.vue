<template>
  <div class="member-main-bg">
    <!-- Header -->
    <div class="main-header">
      <button class="back-btn" @click="goBack">
        <svg width="28" height="28" viewBox="0 0 24 24">
          <path d="M15 18l-6-6 6-6" stroke="#fff" stroke-width="2" fill="none" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>
      </button>
      <div>
        會員系統
        <div class="main-header-desc">專屬會員功能入口</div>
      </div>
    </div>

    <div class="member-form-wrap">
      <form class="member-form" @submit.prevent="handleLogin">
        <label class="member-label" for="phone">手機號碼</label>
        <input
          class="member-input"
          id="phone"
          v-model="phone"
          type="text"
          placeholder="請輸入手機號碼"
          autocomplete="username"
        />

        <label class="member-label" for="password">密碼</label>
        <input
          class="member-input"
          id="password"
          v-model="password"
          type="password"
          placeholder="請輸入密碼"
          autocomplete="current-password"
        />

        <div class="member-remember-row">
          <input type="checkbox" id="remember" v-model="rememberMe" />
          <label for="remember" class="remember-label">記住密碼</label>
        </div>
        <div class="tip">
          忘記密碼？
          <a href="#" @click.prevent="toForgetPwd">點此重設</a>
        </div>


        <button class="member-btn" type="submit">登入</button>
        <button class="member-btn" type="button" @click="goRegister">註冊</button>
      </form>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'

const router = useRouter()
const phone = ref('')
const password = ref('')
const rememberMe = ref(false)

onMounted(() => {
  // 進入頁面自動填入本地記錄
  if (localStorage.getItem('rememberPhone')) {
    phone.value = localStorage.getItem('rememberPhone') || ''
  }
  if (localStorage.getItem('rememberPassword')) {
    password.value = localStorage.getItem('rememberPassword') || ''
    rememberMe.value = true
  }
})
function toForgetPwd() {
  router.push('/forget') // 你可以另外寫一個 Forget.vue 頁面
}

function handleLogin() {
  // 登入驗證請自己串API
  if (rememberMe.value) {
    localStorage.setItem('rememberPhone', phone.value)
    localStorage.setItem('rememberPassword', password.value)
  } else {
    localStorage.removeItem('rememberPhone')
    localStorage.removeItem('rememberPassword')
  }
  alert(`登入功能開發中\n手機：${phone.value}\n密碼：${password.value}\n記住密碼：${rememberMe.value ? '是' : '否'}`)
}

function goRegister() {
  router.push('/register')
}

function goBack() {
  // 回上一頁 or 預設首頁
  if (window.history.length > 1) {
    router.back()
  } else {
    router.push('/')
  }
}
</script>

<style scoped>
.member-main-bg {
  min-height: 100vh;
  background: #f7f2ea;
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 24px 0;
  box-sizing: border-box;
}
.main-header {
  width: 94%;
  background: linear-gradient(90deg, #ff9e6e, #ffc3a0 95%);
  border-radius: 18px;
  color: #fff;
  font-weight: bold;
  font-size: 2rem;
  padding: 18px 0 8px 0;
  text-align: center;
  box-shadow: 0 2px 16px #e0876755;
  margin-bottom: 28px;
  display: flex;
  align-items: center;
  gap: 10px;
  position: relative;
}
.back-btn {
  background: transparent;
  border: none;
  padding: 0 6px 0 6px;
  cursor: pointer;
  position: absolute;
  left: 8px;
  top: 16px;
}
.main-header > div {
  width: 100%;
}
.main-header-desc {
  font-size: 1.02rem;
  margin-top: 4px;
  opacity: 0.92;
  font-weight: normal;
  letter-spacing: 1px;
}
.member-form-wrap {
  width: 100%;
  display: flex;
  justify-content: center;
}
.member-form {
  width: 100%;
  max-width: 400px;
  background: #fff;
  border-radius: 22px;
  box-shadow: 0 2px 18px #ffc3a044;
  padding: 28px 24px 32px 24px;
  display: flex;
  flex-direction: column;
  gap: 12px;
  box-sizing: border-box;
  align-items: center;
}
.member-label {
  font-size: 1.20rem;
  color: #ea732c;
  font-weight: bold;
  margin-bottom: 3px;
  margin-left: 2px;
  align-self: flex-start;
}
.member-input {
  width: 100%;
  max-width: 340px;
  font-size: 1.08rem;
  padding: 13px 18px;
  border: 2px solid #ffbc8b;
  border-radius: 14px;
  outline: none;
  margin-bottom: 6px;
  background: #fff6ef;
  transition: border 0.15s;
  box-sizing: border-box;
}
.member-input:focus {
  border-color: #ffa76b;
}
.member-remember-row {
  display: flex;
  align-items: center;
  gap: 7px;
  width: 100%;
  max-width: 340px;
  margin: 4px 0 7px 0;
}
.remember-label {
  color: #e08b3c;
  font-size: 1rem;
  font-weight: normal;
}
.member-btn {
  width: 100%;
  max-width: 340px;
  padding: 15px 0;
  margin-top: 8px;
  background: linear-gradient(90deg, #ffaf8b, #ffc3a0 90%);
  color: #fff;
  font-size: 1.30rem;
  border: none;
  border-radius: 16px;
  font-weight: bold;
  letter-spacing: 3px;
  box-shadow: 0 2px 12px #ffc3a022;
  transition: filter 0.14s, background 0.13s;
  margin-bottom: 18px;
  cursor: pointer;
}
.member-btn:last-child {
  margin-bottom: 0;
}
.member-btn:active {
  filter: brightness(0.96);
}
</style>
