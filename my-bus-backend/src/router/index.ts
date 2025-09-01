// src/router/index.ts
import { createRouter, createWebHistory } from 'vue-router'
import LoginPage from '../pages/LoginPage.vue'
import HomePage from '../pages/HomePage.vue'

const routes = [
  { path: '/', component: LoginPage },
  { path: '/home', component: HomePage },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

export default router
