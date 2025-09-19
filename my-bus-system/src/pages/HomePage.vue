<template>
  <div class="app-root" :class="{ 'sidebar-hidden': hidden }">
    <!-- Sidebar -->
    <aside class="sidebar" :aria-hidden="hidden ? 'true' : 'false'">
      <div class="logo">
        <div class="logo-title">H-Bus</div>
        <div class="logo-sub">管理系統</div>
      </div>

      <nav class="nav">
        <ul>
          <li @click="goTo('dashboard')">系統總覽</li>
          <li @click="goTo('admin')">管理員帳號管理</li>
          <li @click="goTo('member')">會員帳號管理</li>
          <li @click="goTo('reservation')">預約管理</li>
          <li @click="goTo('car')">車輛管理</li>
          <li @click="goTo('route')">路線管理</li>
        </ul>
      </nav>
    </aside>

    <!-- small expand button shown when hidden -->
    <button
      v-if="hidden"
      class="expand-btn"
      @click="showSidebar"
      aria-label="展開選單"
      title="展開選單"
    >
      ☰
    </button>

    <!-- overlay for mobile when sidebar shown -->
    <div v-if="isMobile && !hidden" class="overlay" @click="hideSidebar"></div>

    <!-- Main area -->
    <div class="main-area">
      <header class="topbar">
        <div class="left-controls">
          <button class="hamburger" @click="toggleSidebar" :title="hidden ? '展開選單' : '收合選單'">
            <span v-if="hidden">☰</span>
            <span v-else>☰</span>
          </button>
          <div class="page-title" v-if="$route.path === '/home'">後台首頁</div>
        </div>

        <div class="user-area">
          <span class="welcome">歡迎, {{ currentUserDisplay }}</span>
          <span class="current-time">{{ currentTime }}</span>
          <button class="logout" @click="logout">登出</button>
        </div>
      </header>

      <main class="content">
        <!-- 子路由內容 -->
        <router-view v-if="$route.path !== '/home'" />
        
        <!-- 儀表板內容（首頁） -->
        <div v-else>
          <!-- 儀表板指標卡片區域 -->
          <section class="dashboard-stats">
          <!-- 第一排 -->
          <div class="stats-row">
            <!-- 會員數量卡片 -->
            <div class="stat-card members">
              <div class="card-header">
                <div class="card-icon">👥</div>
                <div class="card-title">會員數量</div>
              </div>
              <div class="card-content">
                <div v-if="isLoading" class="loading-state">
                  <div class="spinner"></div>
                  <span>載入中...</span>
                </div>
                <div v-else-if="loadError" class="error-state">
                  <span class="error-text">{{ loadError }}</span>
                  <button @click="loadDashboardData" class="retry-btn">重試</button>
                </div>
                <div v-else>
                  <div class="main-number">{{ dashboardData.members.total.toLocaleString() }}</div>
                  <div class="sub-info">
                    <span class="growth positive">{{ dashboardData.members.growth }}</span>
                    <span class="period">本月新增 {{ dashboardData.members.todayNew }}</span>
                  </div>
                  <div class="extra-info">活躍會員 {{ dashboardData.members.vipCount }} 人</div>
                </div>
              </div>
            </div>

            <!-- 本月預約卡片 -->
            <div class="stat-card reservations">
              <div class="card-header">
                <div class="card-icon">📅</div>
                <div class="card-title">本月預約</div>
              </div>
              <div class="card-content">
                <div class="main-number">{{ dashboardData.reservations.thisMonth }}</div>
                <div class="sub-info">
                  <span class="growth positive">{{ dashboardData.reservations.growth }}</span>
                  <span class="period">今日新增 {{ dashboardData.reservations.todayNew }}</span>
                </div>
                <div class="extra-info">待審核 {{ dashboardData.reservations.pending }} 筆</div>
              </div>
            </div>

            <!-- 營收概況卡片 -->
            <div class="stat-card revenue">
              <div class="card-header">
                <div class="card-icon">�</div>
                <div class="card-title">營收狀況</div>
              </div>
              <div class="card-content">
                <div class="main-number">₹{{ dashboardData.revenue.today.toLocaleString() }}</div>
                <div class="sub-info">
                  <span class="growth positive">{{ dashboardData.revenue.growth }}</span>
                  <span class="period">今日營收</span>
                </div>
                <div class="extra-info">本月 ₹{{ dashboardData.revenue.thisMonth.toLocaleString() }}</div>
              </div>
            </div>

            <!-- 資料庫狀況卡片 -->
            <div class="stat-card database">
              <div class="card-header">
                <div class="card-icon">🗄️</div>
                <div class="card-title">資料庫狀況</div>
              </div>
              <div class="card-content">
                <div class="main-number">{{ dashboardData.database.status }}</div>
                <div class="sub-info">
                  <span class="status-text">{{ dashboardData.database.connectionTime }}ms</span>
                  <span class="period">連線時間</span>
                </div>
                <div class="extra-info">{{ dashboardData.database.totalTables }} 個資料表</div>
              </div>
            </div>
          </div>

          <!-- 第二排 -->
          <div class="stats-row">
            <!-- 管理員數量卡片 -->
            <div class="stat-card admins">
              <div class="card-header">
                <div class="card-icon">👨‍💼</div>
                <div class="card-title">管理員數量</div>
              </div>
              <div class="card-content">
                <div class="main-number">{{ dashboardData.admins.total.toLocaleString() }}</div>
                <div class="sub-info">
                  <span class="status-text">{{ dashboardData.admins.online }} 人在線</span>
                  <span class="period">活躍狀態</span>
                </div>
                <div class="extra-info">{{ dashboardData.admins.roles }} 種角色</div>
              </div>
            </div>

            <!-- 車輛數量卡片 -->
            <div class="stat-card vehicle-count">
              <div class="card-header">
                <div class="card-icon">🚐</div>
                <div class="card-title">車輛數量</div>
              </div>
              <div class="card-content">
                <div class="main-number">{{ dashboardData.vehicleCount.total }}</div>
                <div class="sub-info">
                  <span class="growth positive">+{{ dashboardData.vehicleCount.newThisMonth }}</span>
                  <span class="period">本月新增</span>
                </div>
                <div class="extra-info">{{ dashboardData.vehicleCount.available }} 輛可用</div>
              </div>
            </div>

            <!-- 路線數量卡片 -->
            <div class="stat-card routes">
              <div class="card-header">
                <div class="card-icon">🚌</div>
                <div class="card-title">路線數量</div>
              </div>
              <div class="card-content">
                <div class="main-number">{{ dashboardData.routes.active }}/{{ dashboardData.routes.total }}</div>
                <div class="sub-info">
                  <span class="status-text">上線中</span>
                 <!-- <span class="period">準點率 {{ dashboardData.routes.onTime }}</span> -->
                </div>
                <div class="extra-info">{{ dashboardData.routes.inactive }} 條路線暫停</div>
              </div>
            </div>

            <!-- 車輛狀態卡片 -->
            <div class="stat-card vehicles">
              <div class="card-header">
                <div class="card-icon">�</div>
                <div class="card-title">車輛狀態</div>
              </div>
              <div class="card-content">
                <div class="main-number">{{ dashboardData.vehicles.online }}/{{ dashboardData.vehicles.total }}</div>
                <div class="sub-info">
                  <span class="status-text">在線中</span>
                  <span class="period">{{ dashboardData.vehicles.offline }} 輛離線</span>
                </div>
                <div class="extra-info">{{ dashboardData.vehicles.maintenance }} 輛維護中</div>
              </div>
            </div>
          </div>
        </section>

        <!-- 數據可視化圖表區域 -->
        <section class="charts-section">
          <!-- 標籤頁導航 -->
          <div class="tabs-navigation">
            <button 
              v-for="tab in chartTabs" 
              :key="tab.id"
              :class="['tab-button', { active: activeTab === tab.id }]"
              @click="activeTab = tab.id"
            >
              <span class="tab-icon">{{ tab.icon }}</span>
              <span class="tab-label">{{ tab.label }}</span>
            </button>
          </div>

          <!-- 標籤頁內容 -->
          <div class="tab-content">
            <!-- 會員分析標籤頁 -->
            <div v-show="activeTab === 'members'" class="tab-panel">
              <div class="charts-grid">
                <!-- 會員增長趨勢圖 -->
                <div class="chart-card">
                  <div class="chart-header">
                    <h3>會員增長趨勢</h3>
                    <div class="chart-controls">
                      <select v-model="memberGrowthPeriod" @change="loadMemberGrowthData" class="period-selector">
                        <option value="1">最近1天</option>
                        <option value="7">近7天</option>
                        <option value="30">近30天</option>
                      </select>
                    </div>
                  </div>
                  <div class="chart-content">
                    <div v-if="isLoadingGrowth" class="loading-state">
                      <div class="spinner"></div>
                      <span>載入增長數據...</span>
                    </div>
                    <div v-else class="line-chart-with-axis">
                      <div class="chart-wrapper">
                        <!-- Y軸標籤 (左側) -->
                        <div class="y-axis-labels">
                          <div 
                            v-for="tick in yAxisTicks" 
                            :key="tick.value"
                            class="y-tick-label"
                            :style="{ bottom: tick.position + '%' }"
                          >
                            {{ tick.label }}
                          </div>
                        </div>
                        
                        <!-- 圖表區域 -->
                        <div class="chart-area">
                          <svg viewBox="0 0 280 120" class="chart-svg">
                            <!-- 背景網格線 -->
                            <g class="grid-lines">
                              <line 
                                v-for="tick in yAxisTicks" 
                                :key="'grid-' + tick.value"
                                x1="0" 
                                x2="280" 
                                :y1="120 - (tick.position / 100 * 100)"
                                :y2="120 - (tick.position / 100 * 100)"
                                stroke="#f1f5f9" 
                                stroke-width="1"
                              />
                            </g>
                            
                            <!-- 趨勢線 -->
                            <polyline 
                              v-if="!isLoadingGrowth && realMemberGrowthData.chartData.length > 0"
                              :points="realMemberGrowthPoints" 
                              fill="none" 
                              stroke="#8b5cf6" 
                              stroke-width="3"
                            />
                            
                            <!-- 數據點 -->
                            <g class="data-points" v-if="!isLoadingGrowth && realMemberGrowthData.chartData.length > 0">
                              <circle 
                                v-for="(point, index) in realMemberGrowthCircles" 
                                :key="index"
                                :cx="point.x" 
                                :cy="point.y" 
                                r="6"
                                fill="#8b5cf6"
                                stroke="white"
                                stroke-width="2"
                                class="data-point"
                                @mouseenter="handlePointHover(point)"
                                @mouseleave="handlePointLeave"
                              />
                            </g>
                            
                            <!-- X 軸標籤 -->
                            <g class="x-axis-labels" v-if="!isLoadingGrowth && realMemberGrowthData.chartData.length > 0">
                              <text 
                                v-for="(point, index) in realMemberGrowthCircles" 
                                :key="index"
                                v-show="shouldShowLabel(index, realMemberGrowthCircles.length)"
                                :x="point.x" 
                                y="115" 
                                text-anchor="middle"
                                fill="#6b7280"
                                font-size="12"
                                font-family="system-ui, -apple-system, sans-serif"
                              >
                                {{ point.date }}
                              </text>
                            </g>
                            
                            <!-- 互動式懸停圓圈 -->
                            <circle 
                              v-if="showTooltip && hoveredPoint"
                              :cx="hoveredPoint.x" 
                              :cy="hoveredPoint.y" 
                              r="8" 
                              fill="none"
                              stroke="#8b5cf6"
                              stroke-width="2"
                              class="hover-circle"
                            />
                          </svg>
                          
                          <!-- 工具提示 -->
                          <div 
                            v-if="showTooltip && hoveredPoint" 
                            class="chart-tooltip"
                            :style="{ 
                              left: (hoveredPoint.x + 15) + 'px', 
                              top: (hoveredPoint.y - 15) + 'px' 
                            }"
                          >
                            <div class="tooltip-date">{{ hoveredPoint.date }}</div>
                            <div class="tooltip-value">{{ hoveredPoint.value }} 人</div>
                          </div>
                        </div>
                      </div>
                    </div>
                    
                    <!-- 改進的統計數據設計 -->
                    <div class="growth-stats">
                      <div class="stats-grid">
                        <div class="stat-card">
                          <div class="stat-icon">📈</div>
                          <div class="stat-content">
                            <div class="stat-label">總增長</div>
                            <div class="stat-value">+{{ realMemberGrowthData.totalGrowth || 0 }}</div>
                          </div>
                        </div>
                        <div class="stat-card">
                          <div class="stat-icon">📊</div>
                          <div class="stat-content">
                            <div class="stat-label">平均每日</div>
                            <div class="stat-value">+{{ (realMemberGrowthData.avgDaily || 0).toFixed(1) }}</div>
                          </div>
                        </div>
                        <div class="stat-card">
                          <div class="stat-icon">👥</div>
                          <div class="stat-content">
                            <div class="stat-label">目前總數</div>
                            <div class="stat-value">{{ realMemberGrowthData.currentTotal || 0 }}</div>
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>

                <!-- 會員活躍度分析 -->
                <div class="chart-card">
                  <div class="chart-header">
                    <h3>會員活躍度</h3>
                    <div class="chart-controls">
                      <select v-model="memberActivityPeriod" @change="updateMemberActivityChart" class="period-selector">
                        <option value="1">最近1天</option>
                        <option value="7">近7天</option>
                        <option value="30">近30天</option>
                      </select>
                    </div>
                  </div>
                  <div class="chart-content">
                    <div v-if="isLoadingActivity" class="loading-state">
                      <div class="spinner"></div>
                      <span>載入中...</span>
                    </div>
                    <div v-else class="activity-chart">
                      <div class="chart-bars">
                        <div 
                          v-for="(item, index) in memberActivityData" 
                          :key="index"
                          :class="['activity-bar', `activity-${index}`]"
                          :style="{ height: item.percentage + '%' }"
                        >
                          <span class="bar-value">{{ item.count }}</span>
                          <div class="bar-label">{{ item.label }}</div>
                        </div>
                      </div>
                      <div class="activity-summary">
                        <div class="summary-item">
                          <span class="summary-label">活躍率</span>
                          <span class="summary-value">{{ memberActivitySummary.activeRate }}%</span>
                        </div>
                        <div class="summary-item">
                          <span class="summary-label">活躍會員</span>
                          <span class="summary-value">{{ memberActivitySummary.activeMembers }}</span>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            <!-- 預約分析標籤頁 -->
            <div v-show="activeTab === 'reservations'" class="tab-panel">
              <div class="charts-grid">
                <!-- 本月預約趨勢圖 -->
                <div class="chart-card">
                  <div class="chart-header">
                    <h3>本月預約趨勢</h3>
                    <span class="chart-period">2025年9月</span>
                  </div>
                  <div class="chart-content">
                    <div class="simple-chart">
                      <div class="chart-bars">
                        <div class="bar" style="height: 60%"><span>15</span></div>
                        <div class="bar" style="height: 80%"><span>24</span></div>
                        <div class="bar" style="height: 45%"><span>12</span></div>
                        <div class="bar" style="height: 90%"><span>31</span></div>
                        <div class="bar" style="height: 70%"><span>22</span></div>
                        <div class="bar" style="height: 85%"><span>28</span></div>
                        <div class="bar" style="height: 65%"><span>18</span></div>
                      </div>
                      <div class="chart-labels">
                        <span>週一</span><span>週二</span><span>週三</span><span>週四</span><span>週五</span><span>週六</span><span>週日</span>
                      </div>
                    </div>
                  </div>
                </div>

                <!-- 預約狀態分布 -->
                <div class="chart-card">
                  <div class="chart-header">
                    <h3>預約狀態分布</h3>
                    <span class="chart-period">本月統計</span>
                  </div>
                  <div class="chart-content">
                    <div class="status-distribution">
                      <div class="status-bar">
                        <div class="bar-segment completed" style="width: 70%">
                          <span class="segment-label">已完成 70%</span>
                        </div>
                        <div class="bar-segment pending" style="width: 20%">
                          <span class="segment-label">進行中 20%</span>
                        </div>
                        <div class="bar-segment cancelled" style="width: 10%">
                          <span class="segment-label">已取消 10%</span>
                        </div>
                      </div>
                      <div class="status-legend">
                        <div class="legend-item">
                          <span class="legend-color completed"></span>
                          <span>已完成 ({{ dashboardData.reservations.completed }})</span>
                        </div>
                        <div class="legend-item">
                          <span class="legend-color pending"></span>
                          <span>進行中 ({{ dashboardData.reservations.pending }})</span>
                        </div>
                        <div class="legend-item">
                          <span class="legend-color cancelled"></span>
                          <span>已取消 (8)</span>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            <!-- 營收分析標籤頁 -->
            <div v-show="activeTab === 'revenue'" class="tab-panel">
              <div class="charts-grid">
                <!-- 營收趨勢圖 -->
                <div class="chart-card">
                  <div class="chart-header">
                    <h3>營收趨勢分析</h3>
                    <span class="chart-period">近 30 天</span>
                  </div>
                  <div class="chart-content">
                    <div class="revenue-chart">
                      <div class="revenue-lines">
                        <div class="revenue-line current">
                          <span class="line-label">本月營收</span>
                          <span class="line-value">₹{{ dashboardData.revenue.thisMonth.toLocaleString() }}</span>
                        </div>
                        <div class="revenue-line previous">
                          <span class="line-label">上月營收</span>
                          <span class="line-value">₹{{ dashboardData.revenue.lastMonth.toLocaleString() }}</span>
                        </div>
                        <div class="revenue-growth">
                          <span class="growth-label">成長率</span>
                          <span class="growth-value positive">{{ dashboardData.revenue.growth }}</span>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>

                <!-- 收入來源分析 -->
                <div class="chart-card">
                  <div class="chart-header">
                    <h3>收入來源分析</h3>
                    <span class="chart-period">本月數據</span>
                  </div>
                  <div class="chart-content">
                    <div class="income-sources">
                      <div class="source-item">
                        <div class="source-header">
                          <span class="source-name">一般預約</span>
                          <span class="source-percent">65%</span>
                        </div>
                        <div class="source-bar">
                          <div class="bar-fill" style="width: 65%; background: #0ea5e9;"></div>
                        </div>
                        <div class="source-amount">₹185,250</div>
                      </div>
                      <div class="source-item">
                        <div class="source-header">
                          <span class="source-name">VIP預約</span>
                          <span class="source-percent">25%</span>
                        </div>
                        <div class="source-bar">
                          <div class="bar-fill" style="width: 25%; background: #8b5cf6;"></div>
                        </div>
                        <div class="source-amount">₹71,250</div>
                      </div>
                      <div class="source-item">
                        <div class="source-header">
                          <span class="source-name">其他服務</span>
                          <span class="source-percent">10%</span>
                        </div>
                        <div class="source-bar">
                          <div class="bar-fill" style="width: 10%; background: #f59e0b;"></div>
                        </div>
                        <div class="source-amount">₹28,500</div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            <!-- 運營分析標籤頁 -->
            <div v-show="activeTab === 'operations'" class="tab-panel">
              <div class="charts-grid">
                <!-- 路線使用率圓餅圖 -->
                <div class="chart-card">
                  <div class="chart-header">
                    <h3>熱門路線分布</h3>
                    <span class="chart-period">本週數據</span>
                  </div>
                  <div class="chart-content">
                    <div class="pie-chart">
                      <div class="pie-slice" style="--percentage: 35; --color: #0ea5e9;">
                        <span class="pie-label">花蓮車站線<br>35%</span>
                      </div>
                      <div class="route-stats">
                        <div class="route-item">
                          <span class="route-color" style="background: #0ea5e9;"></span>
                          <span class="route-name">花蓮車站線</span>
                          <span class="route-percent">35%</span>
                        </div>
                        <div class="route-item">
                          <span class="route-color" style="background: #10b981;"></span>
                          <span class="route-name">太魯閣線</span>
                          <span class="route-percent">28%</span>
                        </div>
                        <div class="route-item">
                          <span class="route-color" style="background: #f59e0b;"></span>
                          <span class="route-name">七星潭線</span>
                          <span class="route-percent">22%</span>
                        </div>
                        <div class="route-item">
                          <span class="route-color" style="background: #8b5cf6;"></span>
                          <span class="route-name">其他路線</span>
                          <span class="route-percent">15%</span>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>

                <!-- 即時車輛狀態 -->
                <div class="chart-card">
                  <div class="chart-header">
                    <h3>車輛即時狀態</h3>
                    <span class="chart-period">即時更新</span>
                  </div>
                  <div class="chart-content">
                    <div class="vehicle-status">
                      <div class="status-item online">
                        <div class="status-dot"></div>
                        <div class="status-info">
                          <span class="status-label">運行中</span>
                          <span class="status-count">{{ dashboardData.vehicles.online }} 輛</span>
                        </div>
                      </div>
                      <div class="status-item offline">
                        <div class="status-dot"></div>
                        <div class="status-info">
                          <span class="status-label">離線</span>
                          <span class="status-count">{{ dashboardData.vehicles.offline }} 輛</span>
                        </div>
                      </div>
                      <div class="status-item maintenance">
                        <div class="status-dot"></div>
                        <div class="status-info">
                          <span class="status-label">維護中</span>
                          <span class="status-count">{{ dashboardData.vehicles.maintenance }} 輛</span>
                        </div>
                      </div>
                    </div>
                    <div class="vehicle-map-placeholder">
                      <div class="map-text">🗺️ 車輛位置地圖</div>
                      <div class="map-subtitle">點擊查看詳細位置</div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </section>
        </div> <!-- 儀表板內容結束 -->
      </main>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed, watch } from 'vue'
import { useRouter } from 'vue-router'
import { logout as authLogout, getCurrentUser } from '../services/authService'
import { dashboardApi, carApi } from '../services/api'

const router = useRouter()
const hidden = ref(false)

// 載入狀態
const isLoading = ref(false)
const loadError = ref('')

// 用戶資訊
const currentUser = ref<any>(null)

// 計算屬性：顯示當前用戶資訊
const currentUserDisplay = computed(() => {
  if (!currentUser.value) return 'Admin'
  
  const username = currentUser.value.username || 'Admin'
  const role = currentUser.value.role || ''
  
  // 根據角色顯示中文
  const roleDisplay = role === 'SUPER_ADMIN' ? '超級管理員' : 
                     role === 'ADMIN' ? '管理員' : 
                     role

  return roleDisplay ? `${username} (${roleDisplay})` : username
})

// 標籤頁狀態
const activeTab = ref('members')
const chartTabs = ref([
  { id: 'members', label: '會員分析', icon: '👥' },
  { id: 'reservations', label: '預約分析', icon: '📅' },
  { id: 'revenue', label: '營收分析', icon: '💰' },
  { id: 'operations', label: '運營分析', icon: '🚐' }
])

// 會員圖表相關數據
const memberGrowthPeriod = ref<1 | 7 | 30>(7) // 預設 7 天
const memberActivityPeriod = ref<1 | 7 | 30>(7) // 預設 7 天

// 真實會員增長數據
const realMemberGrowthData = ref({
  totalGrowth: 0,
  avgDaily: 0,
  currentTotal: 0,
  chartData: [] as { date: string; value: number }[]
})
const isLoadingGrowth = ref(false)
const memberGrowthStats = ref({
  maxValue: 0,
  minValue: 0,
  yAxisTicks: [] as { value: number; label: string; position: number }[]
})

// 互動式圖表狀態
const hoveredPoint = ref<{ x: number; y: number; value: number; date: string } | null>(null)
const showTooltip = ref(false)

// 會員活躍度數據
const memberActivityData = ref([
  { label: '高活躍', count: 0, percentage: 0 },
  { label: '中活躍', count: 0, percentage: 0 },
  { label: '低活躍', count: 0, percentage: 0 },
  { label: '不活躍', count: 0, percentage: 0 }
])

const memberActivitySummary = ref({
  activeRate: 0,
  activeMembers: 0
})

// 會員活躍度載入狀態
const isLoadingActivity = ref(false)

// 計算 Y 軸刻度
const yAxisTicks = computed(() => {
  return memberGrowthStats.value.yAxisTicks
})

// 計算真實會員增長圖表的點座標
const realMemberGrowthPoints = computed(() => {
  const data = realMemberGrowthData.value.chartData
  if (!data || data.length === 0) return ''
  
  const values = data.map(d => d.value)
  if (values.length === 0) return ''
  
  const maxValue = Math.max(...values)
  const minValue = Math.min(...values)
  
  // 如果所有值都相同，創建一個合理的範圍
  let adjustedMin = minValue
  let adjustedMax = maxValue
  if (maxValue === minValue) {
    adjustedMin = Math.max(0, minValue - 5)
    adjustedMax = maxValue + 5
  }
  
  const range = adjustedMax - adjustedMin || 1
  const chartWidth = 240  // SVG 可用寬度 (280 - 40 padding)
  const chartHeight = 80  // SVG 可用高度 (120 - 40 padding)
  const yOffset = 20      // 頂部邊距
  
  return data.map((item, index) => {
    // 使用與 X 軸標籤相同的位置計算邏輯
    const x = data.length === 1 ? 140 : 20 + (index * (chartWidth / (data.length - 1)))
    const y = yOffset + ((adjustedMax - item.value) / range) * chartHeight
    
    return `${isNaN(x) ? 20 : x},${isNaN(y) ? yOffset : y}`
  }).join(' ')
})

// 計算真實會員增長圖表的圓點座標
const realMemberGrowthCircles = computed(() => {
  const data = realMemberGrowthData.value.chartData
  if (!data || data.length === 0) return []
  
  const values = data.map(d => d.value)
  if (values.length === 0) return []
  
  const maxValue = Math.max(...values)
  const minValue = Math.min(...values)
  
  // 如果所有值都相同，創建一個合理的範圍
  let adjustedMin = minValue
  let adjustedMax = maxValue
  if (maxValue === minValue) {
    adjustedMin = Math.max(0, minValue - 5)
    adjustedMax = maxValue + 5
  }
  
  const range = adjustedMax - adjustedMin || 1
  const chartWidth = 240  // SVG 可用寬度 (280 - 40 padding)
  const chartHeight = 80  // SVG 可用高度 (120 - 40 padding)
  const yOffset = 20      // 頂部邊距
  
  return data.map((item, index) => {
    // 使用與趨勢線完全相同的位置計算邏輯
    const x = data.length === 1 ? 140 : 20 + (index * (chartWidth / (data.length - 1)))
    const y = yOffset + ((adjustedMax - item.value) / range) * chartHeight
    
    return {
      x: isNaN(x) ? 20 : x,
      y: isNaN(y) ? yOffset : y,
      value: item.value,
      date: item.date
    }
  })
})

// 互動函數
function handlePointHover(point: { x: number; y: number; value: number; date: string }) {
  hoveredPoint.value = point
  showTooltip.value = true
}

// （保留原本靜態預約分析區塊，無額外資料載入）

function handlePointLeave() {
  showTooltip.value = false
  hoveredPoint.value = null
}

// 載入會員增長數據
async function loadMemberGrowthData() {
  if (isLoadingGrowth.value) return
  
  try {
    isLoadingGrowth.value = true
    console.log('載入會員增長數據，時間範圍:', memberGrowthPeriod.value)
    
    const response = await fetch(`/api/dashboard/member-growth?days=${memberGrowthPeriod.value}`)
    const result = await response.json()
    
    if (result.success) {
      // 映射 API 數據結構到前端格式
      realMemberGrowthData.value = {
        totalGrowth: result.data.total_growth,
        avgDaily: result.data.avg_daily,
        currentTotal: result.data.growth_data.length > 0 ? result.data.growth_data[result.data.growth_data.length - 1].cumulative : 0,
        chartData: result.data.growth_data.map((item: any) => ({
          date: item.period,
          value: item.cumulative
        }))
      }
      
      // 計算 Y 軸刻度
      const values = realMemberGrowthData.value.chartData.map(d => d.value)
      const maxValue = Math.max(...values)
      const minValue = Math.min(...values)
      
      memberGrowthStats.value.maxValue = maxValue
      memberGrowthStats.value.minValue = minValue
      
      // 生成 Y 軸刻度，包含 position 和 label 屬性
      const tickCount = 5
      
      // 如果所有值都相同，創建一個合理的範圍
      let adjustedMin = minValue
      let adjustedMax = maxValue
      if (maxValue === minValue) {
        adjustedMin = Math.max(0, minValue - 5)
        adjustedMax = maxValue + 5
      }
      
      const tickInterval = (adjustedMax - adjustedMin) / (tickCount - 1)
      memberGrowthStats.value.yAxisTicks = Array.from({ length: tickCount }, (_, i) => {
        const value = Math.round(adjustedMin + i * tickInterval)
        // position 從底部 (0%) 到頂部 (100%)，但順序是從小到大
        const position = (i / (tickCount - 1)) * 100
        return {
          value,
          label: value.toString(),
          position
        }
      })
      
      console.log('會員增長數據載入成功:', realMemberGrowthData.value)
    } else {
      console.error('會員增長數據載入失敗:', result.error)
    }
  } catch (error) {
    console.error('載入會員增長數據時發生錯誤:', error)
  } finally {
    isLoadingGrowth.value = false
  }
}

// 當前時間顯示
const currentTime = ref('')

// 更新時間函數
function updateCurrentTime() {
  const now = new Date()
  const taipeiTime = now.toLocaleString('zh-TW', {
    timeZone: 'Asia/Taipei',
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit'
  })
  currentTime.value = taipeiTime
}

// 載入會員活躍度數據
async function loadMemberActivityData() {
  if (isLoadingActivity.value) return
  
  try {
    isLoadingActivity.value = true
    console.log('載入會員活躍度數據，時間範圍:', memberActivityPeriod.value)
    
    const response = await fetch(`/api/dashboard/member-activity?days=${memberActivityPeriod.value}`)
    const result = await response.json()
    
    if (result.success) {
      memberActivityData.value = result.data.activity_data
      memberActivitySummary.value = {
        activeRate: result.data.summary.active_rate,
        activeMembers: result.data.summary.active_members
      }
      console.log('會員活躍度數據載入成功:', result.data)
    } else {
      console.error('會員活躍度數據載入失敗:', result.message)
    }
  } catch (error) {
    console.error('會員活躍度數據載入錯誤:', error)
  } finally {
    isLoadingActivity.value = false
  }
}

// 更新會員活躍度圖表
function updateMemberActivityChart() {
  loadMemberActivityData()
}

// 控制 X 軸標籤顯示的函數
function shouldShowLabel(index: number, totalCount: number): boolean {
  // 如果數據點少於等於8個，全部顯示
  if (totalCount <= 8) {
    return true
  }
  
  // 如果數據點多於8個，只顯示部分標籤以避免擁擠
  if (totalCount <= 15) {
    // 顯示每隔一個
    return index % 2 === 0
  } else if (totalCount <= 24) {
    // 24小時數據，只顯示每4小時的標籤 (0, 4, 8, 12, 16, 20)
    return index % 4 === 0
  } else {
    // 更多數據點，顯示每6個
    return index % 6 === 0 || index === totalCount - 1  // 包含最後一個點
  }
}

// 儀表板數據 - 第一步：建立響應式數據
const dashboardData = ref({
  // 會員相關數據
  members: {
    total: 0,
    todayNew: 0,
    vipCount: 0,
    growth: '+0%'
  },
  // 預約相關數據 (暫時保持模擬資料)
  reservations: {
    thisMonth: 87,
    todayNew: 15,
    pending: 3,
    completed: 84,
    growth: '+12.5%'
  },
  // 營收相關數據 (暫時保持模擬資料)
  revenue: {
    today: 12450,
    thisMonth: 285000,
    lastMonth: 267000,
    growth: '+6.7%'
  },
  // 資料庫狀況 (新增)
  database: {
    status: '正常',
    connectionTime: 45,
    totalTables: 6,
    health: '良好'
  },
  // 管理員數量 (新增)
  admins: {
    total: 0,
    online: 1,
    roles: 2,
    activeToday: 1
  },
  // 車輛數量 (新增)
  vehicleCount: {
    total: 0,
    newThisMonth: 0,
    available: 0,
    inUse: 0
  },
  // 路線相關數據 (暫時保持模擬資料)
  routes: {
    total: 14,
    active: 12,
    inactive: 2,
    onTime: '96.8%'
  },
  // 車輛狀態相關數據 (暫時保持模擬資料)
  vehicles: {
    total: 0,
    online: 0,
    offline: 0,
    maintenance: 0
  }
})

// 判斷是否為窄螢幕（mobile）
const isMobile = computed(() => window.innerWidth <= 900)

// 載入會員統計資料
async function loadMemberStats() {
  try {
    console.log('載入會員統計資料...')
    const response = await dashboardApi.getMemberStats()
    
    if (response.success) {
      const { total_members, active_members, new_members_this_month, growth_rate } = response.data
      
      // 更新會員數據
      dashboardData.value.members = {
        total: total_members,
        todayNew: new_members_this_month,
        vipCount: active_members,
        growth: `${growth_rate >= 0 ? '+' : ''}${growth_rate}%`
      }
      
      console.log('會員統計資料載入完成:', response.data)
    } else {
      console.error('會員統計資料載入失敗:', response.error)
      loadError.value = response.error || '載入會員統計失敗'
    }
  } catch (error) {
    console.error('載入會員統計資料時發生錯誤:', error)
    loadError.value = '網路連線錯誤'
  }
}

// 載入管理員統計資料
async function loadAdminStats() {
  try {
    console.log('載入管理員統計資料...')
    const response = await dashboardApi.getAdminStats()
    
    if (response.success) {
      const { total_admins, online_admins, total_roles, active_today } = response.data
      
      // 更新管理員數據
      dashboardData.value.admins = {
        total: total_admins,
        online: online_admins,
        roles: total_roles,
        activeToday: active_today
      }
      
      console.log('管理員統計資料載入完成:', response.data)
    } else {
      console.error('管理員統計資料載入失敗:', response.error)
    }
  } catch (error) {
    console.error('載入管理員統計資料時發生錯誤:', error)
  }
}

// 載入資料庫統計資料
async function loadDatabaseStats() {
  try {
    console.log('載入資料庫統計資料...')
    const response = await dashboardApi.getDatabaseStats()
    
    if (response.success) {
      const { status, connection_time, total_tables, health } = response.data
      
      // 更新資料庫數據
      dashboardData.value.database = {
        status: status,
        connectionTime: connection_time,
        totalTables: total_tables,
        health: health
      }
      
      console.log('資料庫統計資料載入完成:', response.data)
    } else {
      console.error('資料庫統計資料載入失敗:', response.error)
    }
  } catch (error) {
    console.error('載入資料庫統計資料時發生錯誤:', error)
  }
}

// 載入預約統計資料（本月/今日/待審核/完成）
async function loadReservationStats() {
  try {
    console.log('載入預約統計資料...')
    const response = await dashboardApi.getReservationStats()
    if (response.success) {
      const d = response.data
      dashboardData.value.reservations = {
        thisMonth: d.this_month,
        todayNew: d.today_new,
        pending: d.pending,
        completed: d.completed,
        growth: `${d.growth_rate >= 0 ? '+' : ''}${d.growth_rate}%`
      }
      console.log('預約統計資料載入完成:', d)
    } else {
      console.error('預約統計資料載入失敗:', (response as any).error)
    }
  } catch (e) {
    console.error('載入預約統計資料時發生錯誤:', e)
  }
}

// 載入路線統計資料（總數/啟用/停用/覆蓋率）
async function loadVehicleStats() {
  try {
    const response = await carApi.getCarStats()
    const result = response.data
    if (result?.success) {
      const data = result.data || {}
      const counts = data.status_counts || {}
      const service = Number(counts.service || 0)
      const paused = Number(counts.paused || 0)
      const maintenance = Number(counts.maintenance || 0)
      const retired = Number(counts.retired || 0)
      const total = Number(data.total || 0)
      const offline = paused + retired
      const available = service
      const inUse = Math.max(total - service, 0)
      dashboardData.value.vehicleCount = {
        total,
        newThisMonth: Number(data.new_this_month || 0),
        available,
        inUse
      }
      dashboardData.value.vehicles = {
        total,
        online: service,
        offline,
        maintenance
      }
    } else {
      console.warn('車輛統計資料載入失敗', result)
    }
  } catch (error) {
    console.error('載入車輛統計資料時發生錯誤:', error)
  }
}

async function loadRouteStats() {
  try {
    console.log('載入路線統計資料...')
    const response = await dashboardApi.getRouteStats()
    if (response.success) {
      const d = response.data
      dashboardData.value.routes = {
        total: d.total,
        active: d.active,
        inactive: d.inactive,
        onTime: `${d.on_time_rate}%`
      }
      console.log('路線統計資料載入完成:', d)
    } else {
      console.error('路線統計資料載入失敗:', (response as any).error)
    }
  } catch (e) {
    console.error('載入路線統計資料時發生錯誤:', e)
  }
}

// 載入儀表板數據
async function loadDashboardData() {
  console.log('載入儀表板數據...')
  isLoading.value = true
  loadError.value = ''
  
  try {
    // 並行載入所有統計資料
    await Promise.all([
      loadMemberStats(),    // 會員統計 (真實資料)
      loadAdminStats(),     // 管理員統計 (真實資料)
      loadDatabaseStats(),  // 資料庫統計 (真實資料)
      loadReservationStats(), // 本月預約 (接資料庫)
      loadRouteStats(),      // 路線數量 (接資料庫)
      loadVehicleStats()     // 車輛統計 (car_resource)
    ])
    
    console.log('儀表板數據載入完成')
  } catch (error) {
    console.error('載入儀表板數據失敗:', error)
    loadError.value = '載入儀表板數據失敗'
  } finally {
    isLoading.value = false
  }
}

// 初次載入從 localStorage 讀取（若有）
onMounted(() => {
  try {
    const v = localStorage.getItem('hb_sidebar_hidden')
    if (v === '1') hidden.value = true
  } catch (e) { /* ignore */ }

  // 載入當前用戶資訊
  currentUser.value = getCurrentUser()

  // 若在載入時是 mobile，預設隱藏（可自訂）
  if (isMobile.value) {
    hidden.value = true
  }

  // 監聽 resize 以更新 isMobile 行為
  window.addEventListener('resize', onResize)
  
  // 初始化時間顯示
  updateCurrentTime()
  // 每秒更新時間
  setInterval(updateCurrentTime, 1000)
  
  // 載入儀表板數據
  loadDashboardData()
  
  // 載入會員增長數據
  loadMemberGrowthData()
  
  // 載入會員活躍度數據
  loadMemberActivityData()

  // （預約分析圖表為靜態示意，無需載入）
})

// 監聽會員增長時間範圍變更
watch(memberGrowthPeriod, () => {
  loadMemberGrowthData()
})

function onResize() {
  // 若變成 mobile 且 sidebar 沒隱藏，保留顯示（但我們不強制改變）
}

function toggleSidebar() {
  hidden.value = !hidden.value
  try { localStorage.setItem('hb_sidebar_hidden', hidden.value ? '1' : '0') } catch {}
}
function hideSidebar() {
  if (!hidden.value) {
    hidden.value = true
    try { localStorage.setItem('hb_sidebar_hidden', '1') } catch {}
  }
}
function showSidebar() {
  if (hidden.value) {
    hidden.value = false
    try { localStorage.setItem('hb_sidebar_hidden', '0') } catch {}
  }
}

function goTo(page: string) {
  switch (page) {
    case 'dashboard':
      router.push('/home')
      break
    case 'admin':
      router.push('/home/admin-management')
      break
    case 'member':
      router.push('/home/member-management')
      break
    case 'reservation':
      router.push('/home/reservation-management')
      break
    case 'car':
      router.push('/home/car-management')
      break
    case 'route':
      router.push('/home/route-management')
      break
    default:
      console.warn('未知的頁面:', page)
  }
}

function logout(){ 
  console.log('正在登出...')
  
  // 1. 清除本地儲存的認證資訊
  authLogout()
  
  console.log('已清除本地認證資訊')
  console.log('跳轉到登入頁面')
  
  // 2. 跳轉到登入頁面
  router.push('/')
}

</script>

<style scoped>
/* 基本 layout */
.app-root { position:relative; min-height:100vh; background:#f3f4f6; display:flex; }

/* ------- Sidebar ------- */
.sidebar {
  width: 260px;
  background:#0f172a;
  color:#f8fafc;
  padding:24px;
  box-shadow: 2px 0 8px rgba(2,6,23,0.4);
  position:fixed;
  left:0; top:0; bottom:0;
  overflow:auto;
  z-index:40;
  transform: translateX(0);
  transition: transform 260ms ease;
}

/* 當 .sidebar-hidden 加上時，把 sidebar 完全隱藏（往左滑出畫面） */
.sidebar-hidden .sidebar {
  transform: translateX(-105%); /* 完全推出畫面 */
}

/* expand button (顯示在左邊邊緣) */
.expand-btn {
  position: fixed;
  left: 12px;
  top: 14px;
  z-index: 65;
  background: #0b5d7a; /* 同 topbar 主色，易辨識 */
  color: #fff;
  border: none;
  padding: 10px 12px;
  border-radius: 10px;
  cursor: pointer;
  box-shadow: 0 8px 20px rgba(2,6,23,0.25);
}

/* overlay (手機抽屜用) */
.overlay{
  position:fixed;
  inset:0;
  background: rgba(0,0,0,0.35);
  z-index:38;
}

/* sidebar 內容 */
.logo { margin-bottom:22px; text-align:center; }
.logo-title{ font-size:34px; font-weight:700; color:#fff; }
.logo-sub{ color:#9ca3af; font-size:13px; margin-top:6px; }

/* nav */
.nav ul{ list-style:none; padding:0; margin:0; }
.nav li{
  padding:14px 18px;
  margin-bottom:12px;
  background: rgba(255,255,255,0.02);
  border-radius:10px;
  cursor:pointer;
  display:flex;
  align-items:center;
  gap:10px;
}
.nav li:hover{ background: rgba(255,255,255,0.05); }

/* ------- Main area ------- */
/* main-area 使用 margin-left 來留空間給 sidebar，當隱藏時變成 0 */
.main-area{
  flex:1;
  margin-left:260px; /* 與 sidebar 寬度一致 */
  transition: margin-left 260ms ease;
  min-height:100vh;
}
.sidebar-hidden .main-area{
  margin-left:0;
}

/* topbar */
.topbar{
  position: fixed;
  left: 260px;  /* 當側欄存在時的起點 */
  right: 0;
  top: 0;
  height: 64px;
  display:flex;
  align-items:center;
  justify-content:space-between;
  padding: 0 18px;
  z-index: 50;   /* 比 hamburger 低一點，避免覆蓋漢堡按鈕 */
  transition: left 260ms ease;
}

.sidebar-hidden .topbar{ left:0; }

/* left controls */
.left-controls{ display:flex; align-items:center; gap:12px; }
.hamburger{
  background: rgba(255,255,255,0.06);  /* 半透明底，比較柔和 */
  border: none;                         /* 移除明顯外框 */
  color: #ffffff;
  padding: 8px 10px;
  border-radius: 8px;
  cursor: pointer;
  font-size: 18px;
  line-height: 1;
  display:inline-flex;
  align-items:center;
  justify-content:center;
  box-shadow: 0 6px 14px rgba(2,6,23,0.12);
  z-index: 60;            /* 高於 topbar 裝飾但低於 sidebar/overlay */
}

.hamburger:hover {
  background: rgba(255,255,255,0.10);
}

.page-title{ font-weight:700; font-size:18px; color:#fff; }

/* user area */
.user-area{ display:flex; align-items:center; gap:12px; }
.current-time { 
  background: #f0f9ff; 
  color: #0369a1; 
  padding: 6px 12px; 
  border-radius: 6px; 
  font-size: 13px; 
  font-weight: 500;
  border: 1px solid #bae6fd;
}
.logout{ background:#093a45; color:#fff; border:none; padding:8px 12px; border-radius:6px; cursor:pointer; }

/* content */
.content{
  margin-top:64px;
  padding:28px;
  height: calc(100vh - 64px);
  overflow:auto;
}

/* 儀表板統計卡片區域 */
.dashboard-stats {
  display: flex;
  flex-direction: column;
  gap: 24px;
  margin-bottom: 32px;
  max-width: 1400px;
  margin-left: auto;
  margin-right: auto;
}

/* 統計卡片排 */
.stats-row {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: 20px;
}

/* 響應式設計 */
@media (min-width: 1200px) {
  .stats-row {
    grid-template-columns: repeat(4, 1fr);
  }
}

@media (max-width: 768px) {
  .stats-row {
    grid-template-columns: 1fr;
  }
}

/* 統計卡片樣式 */
.stat-card {
  background: #ffffff;
  border-radius: 16px;
  padding: 24px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05);
  border: 1px solid #e5e7eb;
  transition: all 0.3s ease;
  position: relative;
  overflow: hidden;
}

.stat-card:hover {
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.1);
  transform: translateY(-2px);
}

/* 卡片頭部 */
.card-header {
  display: flex;
  align-items: center;
  margin-bottom: 16px;
}

.card-icon {
  font-size: 24px;
  margin-right: 12px;
  width: 48px;
  height: 48px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 12px;
  background: linear-gradient(135deg, #0ea5e9, #0284c7);
}

.card-title {
  font-size: 16px;
  font-weight: 600;
  color: #374151;
}

/* 卡片內容 */
.card-content {
  display: flex;
  flex-direction: column;
}

.main-number {
  font-size: 32px;
  font-weight: 700;
  color: #0f172a;
  margin-bottom: 8px;
  line-height: 1.2;
}

.sub-info {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}

.growth {
  font-size: 14px;
  font-weight: 600;
  padding: 4px 8px;
  border-radius: 6px;
}

.growth.positive {
  color: #059669;
  background: #d1fae5;
}

.growth.negative {
  color: #dc2626;
  background: #fee2e2;
}

.period {
  font-size: 14px;
  color: #6b7280;
}

.status-text {
  font-size: 14px;
  color: #059669;
  font-weight: 500;
}

.extra-info {
  font-size: 13px;
  color: #9ca3af;
  margin-top: 4px;
}

/* 載入狀態和錯誤狀態樣式 */
.loading-state {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12px;
  padding: 20px;
  color: #6b7280;
  font-size: 14px;
}

.spinner {
  width: 20px;
  height: 20px;
  border: 2px solid #e5e7eb;
  border-top: 2px solid #3b82f6;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.error-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  padding: 20px;
}

.error-text {
  color: #dc2626;
  font-size: 14px;
  text-align: center;
}

.retry-btn {
  background: #3b82f6;
  color: white;
  border: none;
  padding: 6px 12px;
  border-radius: 6px;
  font-size: 12px;
  cursor: pointer;
  transition: background-color 0.2s;
}

.retry-btn:hover {
  background: #2563eb;
}

/* 不同卡片的個性化顏色 */
.stat-card.members .card-icon {
  background: linear-gradient(135deg, #8b5cf6, #7c3aed);
}

.stat-card.reservations .card-icon {
  background: linear-gradient(135deg, #06b6d4, #0891b2);
}

.stat-card.revenue .card-icon {
  background: linear-gradient(135deg, #ef4444, #dc2626);
}

.stat-card.database .card-icon {
  background: linear-gradient(135deg, #6366f1, #4f46e5);
}

.stat-card.admins .card-icon {
  background: linear-gradient(135deg, #14b8a6, #0d9488);
}

.stat-card.vehicle-count .card-icon {
  background: linear-gradient(135deg, #f59e0b, #d97706);
}

.stat-card.routes .card-icon {
  background: linear-gradient(135deg, #10b981, #059669);
}

.stat-card.vehicles .card-icon {
  background: linear-gradient(135deg, #84cc16, #65a30d);
}

/* 圖表區域樣式 */
.charts-section {
  max-width: 1400px;
  margin: 0 auto 32px;
}

/* 標籤頁導航樣式 */
.tabs-navigation {
  display: flex;
  background: #ffffff;
  border-radius: 12px;
  padding: 6px;
  margin-bottom: 24px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
  border: 1px solid #e5e7eb;
  gap: 4px;
}

.tab-button {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 12px 16px;
  background: transparent;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.3s ease;
  font-size: 14px;
  font-weight: 500;
  color: #6b7280;
  position: relative;
}

.tab-button:hover {
  background: #f9fafb;
  color: #374151;
}

.tab-button.active {
  background: linear-gradient(135deg, #0ea5e9, #0284c7);
  color: #ffffff;
  box-shadow: 0 4px 12px rgba(14, 165, 233, 0.3);
}

.tab-icon {
  font-size: 16px;
}

.tab-label {
  font-weight: 600;
}

/* 標籤頁內容 */
.tab-content {
  min-height: 400px;
  max-width: 1400px;
  margin-left: auto;
  margin-right: auto;
  display: flex;
  flex-direction: column;
}

.tab-panel {
  animation: fadeIn 0.3s ease-in-out;
}

@keyframes fadeIn {
  from {
    opacity: 0;
    transform: translateY(10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

/* 圖表網格 */
.charts-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: 20px;
}

/* 響應式調整 - 圖表通常比統計卡片內容更豐富，用 2 列更合適 */
@media (min-width: 1200px) {
  .charts-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (min-width: 768px) and (max-width: 1199px) {
  .charts-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (max-width: 768px) {
  .tabs-navigation {
    flex-direction: column;
    gap: 2px;
  }
  
  .tab-button {
    flex: none;
    justify-content: flex-start;
  }
  
  .charts-grid {
    grid-template-columns: 1fr;
    gap: 16px;
  }
}

.chart-card {
  background: #ffffff;
  border-radius: 16px;
  padding: 24px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05);
  border: 1px solid #e5e7eb;
  min-height: 400px;
  display: flex;
  flex-direction: column;
}

.chart-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  justify-content: center;
}

.chart-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
  padding-bottom: 12px;
  border-bottom: 1px solid #f3f4f6;
}

.chart-header h3 {
  font-size: 18px;
  font-weight: 600;
  color: #111827;
  margin: 0;
}

.chart-period {
  font-size: 14px;
  color: #6b7280;
}

/* 簡單長條圖 */
.simple-chart {
  height: 200px;
  display: flex;
  flex-direction: column;
}

.chart-bars {
  display: flex;
  align-items: end;
  gap: 8px;
  height: 160px;
  padding: 0 8px;
}

.bar {
  flex: 1;
  background: linear-gradient(to top, #0ea5e9, #0284c7);
  border-radius: 4px 4px 0 0;
  min-height: 20px;
  position: relative;
  transition: all 0.3s ease;
  cursor: pointer;
}

.bar:hover {
  opacity: 0.8;
}

.bar span {
  position: absolute;
  top: -24px;
  left: 50%;
  transform: translateX(-50%);
  font-size: 12px;
  font-weight: 600;
  color: #374151;
}

.chart-labels {
  display: flex;
  justify-content: space-around;
  margin-top: 12px;
  font-size: 12px;
  color: #6b7280;
}

.chart-labels-container {
  position: relative;
  height: 20px;
  margin-top: 12px;
  width: 280px; /* 與 SVG viewBox 寬度一致 */
}

.chart-label {
  font-size: 12px;
  color: #6b7280;
  white-space: nowrap;
}

/* 路線統計 */
.route-stats {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.route-item {
  display: flex;
  align-items: center;
  gap: 12px;
}

.route-color {
  width: 16px;
  height: 16px;
  border-radius: 50%;
}

.route-name {
  flex: 1;
  font-size: 14px;
  color: #374151;
}

.route-percent {
  font-size: 14px;
  font-weight: 600;
  color: #111827;
}

/* 車輛狀態 */
.vehicle-status {
  display: flex;
  flex-direction: column;
  gap: 16px;
  margin-bottom: 20px;
}

.status-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px;
  border-radius: 8px;
  background: #f9fafb;
}

.status-dot {
  width: 12px;
  height: 12px;
  border-radius: 50%;
}

.status-item.online .status-dot {
  background: #10b981;
  animation: pulse 2s infinite;
}

.status-item.offline .status-dot {
  background: #ef4444;
}

.status-item.maintenance .status-dot {
  background: #f59e0b;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

.status-info {
  display: flex;
  justify-content: space-between;
  width: 100%;
}

.status-label {
  font-size: 14px;
  color: #374151;
}

.status-count {
  font-size: 14px;
  font-weight: 600;
  color: #111827;
}

.vehicle-map-placeholder {
  background: #f3f4f6;
  border-radius: 8px;
  padding: 40px 20px;
  text-align: center;
  border: 2px dashed #d1d5db;
}

.map-text {
  font-size: 16px;
  color: #6b7280;
  margin-bottom: 4px;
}

.map-subtitle {
  font-size: 12px;
  color: #9ca3af;
}

/* 新增圖表類型樣式 */

/* 會員增長趨勢線圖 */
.line-chart {
  height: 200px;
  display: flex;
  flex-direction: column;
}

.chart-area {
  position: relative;
  height: 120px;
  margin-bottom: 16px;
}

.chart-svg {
  width: 100%;
  height: 100%;
}

.data-point {
  cursor: pointer;
  transition: all 0.2s ease;
}

.data-point:hover {
  r: 8;
  filter: drop-shadow(0 2px 4px rgba(139, 92, 246, 0.3));
}

.hover-circle {
  animation: pulse 2s infinite;
}

@keyframes pulse {
  0% {
    opacity: 1;
  }
  50% {
    opacity: 0.5;
  }
  100% {
    opacity: 1;
  }
}

/* 工具提示樣式 */
.chart-tooltip {
  position: absolute;
  background: rgba(0, 0, 0, 0.8);
  color: white;
  padding: 8px 12px;
  border-radius: 6px;
  font-size: 12px;
  pointer-events: none;
  z-index: 10;
  white-space: nowrap;
}

.chart-tooltip::after {
  content: '';
  position: absolute;
  top: 50%;
  left: -4px;
  transform: translateY(-50%);
  width: 0;
  height: 0;
  border-top: 4px solid transparent;
  border-bottom: 4px solid transparent;
  border-right: 4px solid rgba(0, 0, 0, 0.8);
}

.tooltip-date {
  font-weight: 500;
  margin-bottom: 2px;
}

.tooltip-value {
  color: #8b5cf6;
  font-weight: bold;
}

/* 成長統計樣式 */
.growth-stats {
  margin-top: 16px;
  padding: 16px;
  background: #f8fafc;
  border-radius: 8px;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
}

.stats-grid .stat-card {
  background: white;
  border-radius: 8px;
  padding: 12px;
  display: flex;
  align-items: center;
  gap: 12px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
  border: 1px solid #e2e8f0;
}

.stats-grid .stat-icon {
  font-size: 20px;
}

.stats-grid .stat-content {
  flex: 1;
}

.stats-grid .stat-value {
  font-size: 18px;
  font-weight: 700;
  color: #0f172a;
  margin-bottom: 2px;
}

.stats-grid .stat-label {
  font-size: 12px;
  color: #64748b;
}

/* 會員活躍度甜甜圈圖 */
.donut-chart {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 20px;
}

.donut-center {
  text-align: center;
}

.donut-value {
  font-size: 28px;
  font-weight: 700;
  color: #0f172a;
}

.donut-label {
  font-size: 14px;
  color: #6b7280;
  margin-top: 4px;
}

.donut-stats {
  display: flex;
  flex-direction: column;
  gap: 8px;
  width: 100%;
}

.stat-item {
  display: flex;
  align-items: center;
  gap: 8px;
}

.stat-color {
  width: 12px;
  height: 12px;
  border-radius: 50%;
}

.stat-color.active {
  background: #8b5cf6;
}

.stat-color.inactive {
  background: #d1d5db;
}

.stat-text {
  font-size: 14px;
  color: #374151;
}

/* 預約狀態分布條形圖 */
.status-distribution {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.status-bar {
  display: flex;
  height: 40px;
  border-radius: 20px;
  overflow: hidden;
  background: #f3f4f6;
}

.bar-segment {
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
  transition: all 0.3s ease;
}

.bar-segment.completed {
  background: linear-gradient(135deg, #10b981, #059669);
}

.bar-segment.pending {
  background: linear-gradient(135deg, #f59e0b, #d97706);
}

.bar-segment.cancelled {
  background: linear-gradient(135deg, #ef4444, #dc2626);
}

.segment-label {
  font-size: 12px;
  font-weight: 600;
  color: #ffffff;
  text-shadow: 0 1px 2px rgba(0, 0, 0, 0.1);
}

.status-legend {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
}

.legend-item {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  color: #374151;
}

.legend-color {
  width: 10px;
  height: 10px;
  border-radius: 50%;
}

.legend-color.completed {
  background: #10b981;
}

.legend-color.pending {
  background: #f59e0b;
}

.legend-color.cancelled {
  background: #ef4444;
}

/* 營收趨勢分析 */
.revenue-chart {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.revenue-lines {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.revenue-line {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px;
  border-radius: 12px;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
}

.revenue-line.current {
  background: linear-gradient(135deg, #f0f9ff, #e0f2fe);
  border-color: #0ea5e9;
}

.revenue-line.previous {
  background: linear-gradient(135deg, #fafafa, #f5f5f5);
  border-color: #d1d5db;
}

.line-label {
  font-size: 14px;
  color: #64748b;
  font-weight: 500;
}

.line-value {
  font-size: 18px;
  font-weight: 700;
  color: #0f172a;
}

.revenue-growth {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  border-radius: 8px;
  background: #ecfdf5;
  border: 1px solid #bbf7d0;
}

.growth-label {
  font-size: 14px;
  color: #059669;
  font-weight: 500;
}

.growth-value {
  font-size: 16px;
  font-weight: 700;
}

.growth-value.positive {
  color: #059669;
}

.growth-value.negative {
  color: #dc2626;
}

/* 收入來源分析 */
.income-sources {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.source-item {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.source-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.source-name {
  font-size: 14px;
  font-weight: 500;
  color: #374151;
}

.source-percent {
  font-size: 14px;
  font-weight: 600;
  color: #0f172a;
}

.source-bar {
  height: 8px;
  background: #f3f4f6;
  border-radius: 4px;
  overflow: hidden;
}

.bar-fill {
  height: 100%;
  transition: width 0.8s ease;
  border-radius: 4px;
}

.source-amount {
  font-size: 16px;
  font-weight: 700;
  color: #0f172a;
  text-align: right;
}

/* 圓餅圖改進 */
.pie-chart {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 20px;
  height: 200px;
}

.pie-slice {
  width: 120px;
  height: 120px;
  border-radius: 50%;
  background: conic-gradient(
    from 0deg,
    #0ea5e9 0deg 126deg,
    #10b981 126deg 226deg,
    #f59e0b 226deg 306deg,
    #8b5cf6 306deg 360deg
  );
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
  margin-bottom: 8px;
}

.pie-slice::before {
  content: '';
  width: 60px;
  height: 60px;
  background: #ffffff;
  border-radius: 50%;
  position: absolute;
}

.pie-label {
  position: absolute;
  z-index: 1;
  font-size: 12px;
  font-weight: 600;
  text-align: center;
  color: #0f172a;
  line-height: 1.2;
}

/* table */
.table-section, .table-section h2 { max-width:1100px; margin:32px auto 16px; }
.simple-table{ width:100%; border-collapse:collapse; background:#fff; border-radius:8px; overflow:hidden; }
.simple-table th, .simple-table td{ padding:14px 18px; border-bottom:1px solid #edf2f7; text-align:left; }
.simple-table thead th{ background:#f8fafc; font-weight:700; }

/* status */
.status.on{ color:#0f5132; background:#d1fae5; padding:6px 8px; border-radius:6px; }
.status.off{ color:#7f1d1d; background:#fee2e2; padding:6px 8px; border-radius:6px; }

/* button base */
button{ background:#0b5d7a; color:#fff; border:none; padding:8px 12px; border-radius:8px; cursor:pointer; }
button:hover{ opacity:0.95; }

/* Responsive: 在窄螢幕把 sidebar 當抽屜 */
@media (max-width: 900px) {
  .sidebar { transform: translateX(-105%); }       /* 隱藏預設 */
  .sidebar-hidden .sidebar { transform: translateX(-105%); }
  /* 當非 hidden（即 open）時把 sidebar 拉出 */
  :not(.sidebar-hidden) .sidebar { transform: translateX(0); }
  .main-area { margin-left:0; }
  .topbar { left:0; }
  .expand-btn { left: 10px; top: 10px; } /* 小螢幕 expand button 位置 */
}

/* 新增會員圖表相關樣式 */

/* 圖表控制器樣式 */
.chart-controls {
  display: flex;
  align-items: center;
  gap: 8px;
}

.period-selector {
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 6px;
  padding: 6px 12px;
  font-size: 13px;
  color: #475569;
  cursor: pointer;
  transition: all 0.3s ease;
}

.period-selector:hover {
  border-color: #0ea5e9;
  background: #f0f9ff;
}

.period-selector:focus {
  outline: none;
  border-color: #0ea5e9;
  box-shadow: 0 0 0 3px rgba(14, 165, 233, 0.1);
}

/* 圖表統計信息 */
.chart-stats {
  display: flex;
  justify-content: space-around;
  margin-top: 16px;
  padding-top: 16px;
  border-top: 1px solid #f1f5f9;
}

.chart-stats .stat-item {
  text-align: center;
}

.chart-stats .stat-label {
  display: block;
  font-size: 12px;
  color: #64748b;
  margin-bottom: 4px;
}

.chart-stats .stat-value {
  font-size: 16px;
  font-weight: 700;
  color: #0f172a;
}

/* 會員活躍度長條圖 */
.activity-chart {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

/* 會員增長圖表樣式 */
.line-chart-with-axis {
  padding: 16px;
}

.chart-wrapper {
  display: flex;
  align-items: stretch;
  height: 120px;
  position: relative;
}

.y-axis-labels {
  width: 40px;
  position: relative;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  padding-right: 8px;
}

.y-tick-label {
  position: absolute;
  right: 8px;
  font-size: 11px;
  color: #64748b;
  transform: translateY(-50%);
  text-align: right;
  line-height: 1;
}

.chart-area {
  flex: 1;
  position: relative;
}

.chart-svg {
  width: 100%;
  height: 120px;
}

.grid-lines line {
  stroke: #f1f5f9;
  stroke-width: 1;
}

.data-point {
  cursor: pointer;
  transition: r 0.2s ease;
}

.data-point:hover {
  r: 6;
}

.chart-labels {
  display: flex;
  justify-content: space-between;
  margin-top: 8px;
  margin-left: 40px;
}

.chart-labels span {
  font-size: 11px;
  color: #64748b;
  text-align: center;
  min-width: 0;
  flex: 1;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.loading-state {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 120px;
  color: #64748b;
  font-size: 14px;
}

/* SVG 圖表樣式 */
.chart-svg {
  width: 100%;
  height: 120px;
}

.y-tick-label {
  font-size: 11px;
  fill: #64748b;
  font-family: system-ui, -apple-system, sans-serif;
}

.grid-lines line {
  stroke: #f1f5f9;
  stroke-width: 1;
}

.data-point {
  cursor: pointer;
  transition: r 0.2s ease;
}

.data-point:hover {
  r: 6;
}

.chart-bars {
  display: flex;
  align-items: end;
  gap: 12px;
  height: 160px;
  padding: 0 8px;
}

.activity-bar {
  flex: 1;
  border-radius: 6px 6px 0 0;
  min-height: 20px;
  position: relative;
  transition: all 0.3s ease;
  cursor: pointer;
  display: flex;
  flex-direction: column;
  justify-content: flex-end;
  align-items: center;
}

/* 高活躍 - 綠色系 */
.activity-bar.activity-0 {
  background: linear-gradient(to top, #059669, #10b981);
}

.activity-bar.activity-0:hover {
  background: linear-gradient(to top, #047857, #059669);
  transform: translateY(-2px);
}

/* 中活躍 - 藍色系 */
.activity-bar.activity-1 {
  background: linear-gradient(to top, #2563eb, #3b82f6);
}

.activity-bar.activity-1:hover {
  background: linear-gradient(to top, #1d4ed8, #2563eb);
  transform: translateY(-2px);
}

/* 低活躍 - 橙色系 */
.activity-bar.activity-2 {
  background: linear-gradient(to top, #ea580c, #f97316);
}

.activity-bar.activity-2:hover {
  background: linear-gradient(to top, #c2410c, #ea580c);
  transform: translateY(-2px);
}

/* 不活躍 - 紅色系 */
.activity-bar.activity-3 {
  background: linear-gradient(to top, #dc2626, #ef4444);
}

.activity-bar.activity-3:hover {
  background: linear-gradient(to top, #b91c1c, #dc2626);
  transform: translateY(-2px);
}

.activity-bar:hover {
  transform: translateY(-2px);
}

.bar-value {
  position: absolute;
  top: -24px;
  font-size: 12px;
  font-weight: 600;
  color: #374151;
  background: #ffffff;
  padding: 2px 6px;
  border-radius: 4px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.bar-label {
  position: absolute;
  bottom: -28px;
  font-size: 11px;
  color: #6b7280;
  text-align: center;
  width: 100%;
  white-space: nowrap;
}

/* 活躍度摘要 */
.activity-summary {
  display: flex;
  justify-content: space-around;
  background: #f8fafc;
  border-radius: 8px;
  padding: 16px;
}

.summary-item {
  text-align: center;
}

.summary-label {
  display: block;
  font-size: 13px;
  color: #64748b;
  margin-bottom: 4px;
}

.summary-value {
  font-size: 18px;
  font-weight: 700;
  color: #8b5cf6;
}

/* 響應式設計調整 */
@media (max-width: 768px) {
  .chart-controls {
    flex-direction: column;
    align-items: stretch;
  }
  
  .period-selector {
    width: 100%;
  }
  
  .chart-stats {
    flex-direction: column;
    gap: 8px;
  }
  
  .activity-summary {
    flex-direction: column;
    gap: 12px;
  }
}
</style>
