// src/router/index.js
import { createRouter, createWebHistory } from 'vue-router'
import Home from '../views/Home.vue'
import Search from '../views/Search.vue'
import Detail from '../views/Detail.vue'
import Map from '../views/Map.vue'
import Member from '../views/Member.vue'
import Register from '../views/Register.vue'  // 這裡正確命名

const routes = [
  { path: '/', name: 'Home', component: Home },
  { path: '/search', name: 'Search', component: Search },
  { path: '/detail/:route', name: 'Detail', component: Detail, props: true },
  { path: '/map', name: 'Map', component: Map },
  { path: '/member', name: 'Member', component: Member },
  { path: '/register', name: 'Register', component: Register }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router
