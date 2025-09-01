<template>
  <div class="member-main-bg">
    <div class="main-header">
      <button class="back-btn" @click="goBack">
        <svg width="28" height="28" viewBox="0 0 24 24">
          <path d="M15 18l-6-6 6-6" stroke="#fff" stroke-width="2" fill="none" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>
      </button>
      <div>
        註冊新會員
        <div class="main-header-desc">請填寫基本資料</div>
      </div>
    </div>

    <div class="member-form-wrap">
      <form class="member-form" @submit.prevent="handleRegister">
        <label class="member-label" for="email">Email (選填)</label>
        <input
        class="member-input"
        id="email"
        v-model="email"
        type="text"
        placeholder="可不填"
        />

        <label class="member-label" for="phone">手機號碼</label>
        <input
          class="member-input"
          id="phone"
          v-model="phone"
          type="text"
          placeholder="請輸入手機號碼"
          required
        />

        <label class="member-label" for="password">密碼</label>
        <input
          class="member-input"
          id="password"
          v-model="password"
          type="password"
          placeholder="請設定密碼"
          required
        />

        <button class="member-btn" type="submit" :disabled="loading">
          {{ loading ? '註冊中...' : '註冊' }}
        </button>
      </form>
    </div>

    <div class="tip">
      已有帳號？<a href="#" @click.prevent="toLogin">返回登入</a>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'

const router = useRouter()
const email = ref('')
const phone = ref('')
const password = ref('')
const loading = ref(false)

function goBack() {
  if (window.history.length > 1) router.back()
  else router.push('/member')
}
function toLogin() {
  router.push('/member')
}

async function handleRegister() {
  if (!phone.value || !password.value) {
    alert('手機號碼和密碼必填')
    return
  }
  loading.value = true
  try {
    // 直接呼叫API建立帳號
    const res = await fetch('/api/auth/register', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        email: email.value,
        phone: phone.value,
        password: password.value
      })
    })
    const result = await res.json()
    if (res.ok && result.success) {
      alert('註冊成功！')
      router.push('/member')
    } else {
      alert(result.detail || '註冊失敗')
    }
  } catch (e) {
    alert('連線失敗，請重試')
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
/* 同你前面的設計 */
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
  gap: 14px;
  box-sizing: border-box;
  align-items: center;
}
.member-label {
  font-size: 1.18rem;
  color: #ea732c;
  font-weight: bold;
  margin-bottom: 2px;
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
  margin-bottom: 7px;
  background: #fff6ef;
  transition: border 0.15s;
  box-sizing: border-box;
}
.member-input:focus {
  border-color: #ffa76b;
}
.member-btn {
  width: 100%;
  max-width: 340px;
  padding: 15px 0;
  margin-top: 12px;
  background: linear-gradient(90deg, #ffaf8b, #ffc3a0 90%);
  color: #fff;
  font-size: 1.30rem;
  border: none;
  border-radius: 16px;
  font-weight: bold;
  letter-spacing: 3px;
  box-shadow: 0 2px 12px #ffc3a022;
  transition: filter 0.14s, background 0.13s;
  margin-bottom: 6px;
  cursor: pointer;
}
.member-btn:active {
  filter: brightness(0.96);
}
.tip {
  color: #e49560;
  text-align: center;
  margin-top: 24px;
  font-size: 1.04rem;
}
.tip a {
  color: #ff8542;
  text-decoration: underline;
  font-weight: bold;
  cursor: pointer;
}
</style>
