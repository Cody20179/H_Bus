// src/router/index.js
import { createRouter, createWebHistory } from 'vue-router'
import Home from '../views/Home.vue'
import Search from '../views/Search.vue'
import Detail from '../views/Detail.vue'

const routes = [
  { path: '/', name: 'Home', component: Home },
  { path: '/search', name: 'Search', component: Search },
  { path: '/detail/:id', name: 'Detail', component: Detail, props: true }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router
