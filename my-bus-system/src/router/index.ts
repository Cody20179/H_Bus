// src/router/index.ts
import { createRouter, createWebHistory } from 'vue-router'
import LoginPage from '../pages/LoginPage.vue'
import HomePage from '../pages/HomePage.vue'
import AdminManagement from '../pages/AdminManagement.vue'
import MemberManagement from '../pages/MemberManagement.vue'
import RouteManagement from '../pages/RouteManagement.vue'
import EmailReminderManagement from '../pages/EmailReminderManagement.vue'
import QrCodeGenerator from '../pages/QrCodeGenerator.vue'
import ReservationManagement from '../pages/ReservationManagement.vue'
import CarManagement from '../pages/CarManagement.vue'
import { isLoggedIn } from '../services/authService'

const routes = [
  { path: '/', component: LoginPage },
  { 
    path: '/home', 
    component: HomePage,
    meta: { requiresAuth: true },
    children: [
      {
        path: 'admin-management',
        component: AdminManagement,
        meta: { requiresAuth: true }
      },
      {
        path: 'member-management',
        component: MemberManagement,
        meta: { requiresAuth: true }
      },
      {
        path: 'reservation-management',
        component: ReservationManagement,
        meta: { requiresAuth: true }
      },
      {
        path: 'car-management',
        component: CarManagement,
        meta: { requiresAuth: true }
      },
      {
        path: 'route-management',
        component: RouteManagement,
        meta: { requiresAuth: true }
      },
      {
        path: 'email-reminder',
        component: EmailReminderManagement,
        meta: { requiresAuth: true }
      },
      {
        path: 'qr-generator',
        component: QrCodeGenerator,
        meta: { requiresAuth: true }
      }
    ]
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.beforeEach((to, _from, next) => {
  console.log('路由導航觸發:', to.path)
  
  if (to.meta.requiresAuth) {
    if (isLoggedIn()) {
      console.log('已登入，進入:', to.path)
      next()
    } else {
      console.log('未登入，導回登入頁')
      next('/')
    }
  } else {
    if (to.path === '/' && isLoggedIn()) {
      console.log('已登入，直接導向首頁')
      next('/home')
    } else {
      next()
    }
  }
})

export default router
