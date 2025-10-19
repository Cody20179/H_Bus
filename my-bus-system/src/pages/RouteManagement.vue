<template>
  <div class="route-management">
    <!-- 頁面標題 -->
    <div class="page-header">
      <div class="header-left">
        <h1 class="page-title">路線站點管理</h1>
        <p class="page-description">管理公車路線和站點資訊</p>
      </div>
      <div class="header-right">
        <button
          @click="openCreateModal"
          class="btn-primary"
        >
          <i class="icon-plus"></i>
          新增/編輯站點
        </button>
        <button
          @click="openCreateRouteModal"
          class="btn-primary"
          style="background: linear-gradient(135deg,#10b981 0%,#059669 100%); margin-left:8px;"
        >
          <i class="icon-plus"></i>
          新增路線
        </button>
        <button
          @click="openXMLImportModal"
          class="btn-primary"
          style="background: linear-gradient(135deg,#8b5cf6 0%,#7c3aed 100%); margin-left:8px;"
        >
          XML匯入
        </button>
      </div>
    </div>

    <!-- 路線總覽表格（與站點表格樣式一致） -->
    <div class="routes-overview" style="margin-top:16px; margin-bottom:16px; background:white; padding:16px; border-radius:12px;">
      <h3 style="margin:0 0 12px 0;">路線總覽</h3>

      <!-- 搜尋欄（路線） -->
      <div class="routes-filter-row">
        <div class="search-input-wrapper routes-search">
          <span class="search-icon">🔍</span>
          <input
            v-model="routeSearchQuery"
            @input="handleRouteSearch"
            type="text"
            placeholder="搜尋路線名稱..."
            class="search-input"
          />
        </div>
        <div class="filter-inline">
          <label class="filter-label">ID排序：</label>
          <select v-model="routeSortOrder" class="page-size-select routes-order-select">
            <option value="desc">由新到舊</option>
            <option value="asc">由舊到新</option>
          </select>
        </div>
      </div>

      <div class="table-container">
        <table class="admin-table">
          <thead>
            <tr>
              <th>ID</th>
              <th>路線名稱</th>
              <th>方向</th>
              <th>起點</th>
              <th>終點</th>
              <th>站數</th>
              <th>狀態</th>
              <th class="actions-column">操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="r in filteredRoutes" :key="r.route_id" class="table-row">
              <td>{{ r.route_id }}</td>
              <td class="route-cell">
                <div class="route-info">
                  <span class="route-name">{{ r.route_name }}</span>
                </div>
              </td>
              <td>
                <span class="direction-badge">{{ r.direction || '-' }}</span>
              </td>
              <td>{{ r.start_stop || '-' }}</td>
              <td>{{ r.end_stop || '-' }}</td>
              <td>{{ r.stop_count || 0 }}</td>
              <td>
                <button @click="toggleRouteStatus(r)" :class="['status-btn', r.status === 1 ? 'on' : 'off']">
                  {{ r.status === 1 ? '啟用' : '停用' }}
                </button>
              </td>
              <td class="actions-cell">
                <div class="action-buttons">
                  <button @click.stop="openEditRoute(r)" class="btn-edit" title="編輯">✏️</button>
                  <button @click.stop="deleteRoute(r, $event)" class="btn-delete" title="刪除">🗑️</button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>

        <div v-if="filteredRoutes.length === 0" class="empty-state" style="margin-top:12px;">
          <div class="empty-icon">🚌</div>
          <h3>沒有找到路線</h3>
          <p>{{ routeSearchQuery ? '沒有符合搜尋條件的路線' : '目前沒有路線資料' }}</p>
        </div>
      </div>
    </div>

    <!-- 搜尋和篩選區域 -->
    <div class="filters-section">
      <div class="search-container">
        <div class="search-input-wrapper">
          <span class="search-icon">🔍</span>
          <input
            v-model="searchQuery"
            @input="handleSearch"
            type="text"
            placeholder="搜尋站點名稱..."
            class="search-input"
          />
        </div>
      </div>

      <div class="filter-controls">
        <div class="filter-group">
          <label class="filter-label">路線篩選：</label>
          <select v-model="routeFilter" @change="loadStations" class="route-select">
            <option value="">全部路線</option>
            <option v-for="route in availableRoutes" :key="route.route_id" :value="route.route_id">
              {{ route.route_name }}
            </option>
          </select>
        </div>

        <div class="filter-group">
          <label class="filter-label">方向篩選：</label>
          <select v-model="directionFilter" @change="loadStations" class="direction-select">
            <option value="">全部方向</option>
            <option value="去程">去程</option>
            <option value="回程">回程</option>
          </select>
        </div>

        <div class="filter-group">
          <label class="filter-label">ID排序：</label>
          <select v-model="stationSortOrder" @change="loadStations" class="page-size-select">
            <option value="desc">由新到舊</option>
            <option value="asc">由舊到新</option>
          </select>
        </div>
        <div class="filter-group">
          <label class="filter-label">每頁顯示：</label>
          <select v-model.number="pageSize" @change="onPageSizeChange" class="page-size-select">
            <option :value="10">10 筆</option>
            <option :value="20">20 筆</option>
            <option :value="50">50 筆</option>
          </select>
        </div>
      </div>
    </div>

    <!-- 站點列表 -->
    <div class="table-container">
      <div v-if="isLoading" class="loading-overlay">
        <div class="spinner"></div>
        <span>載入中...</span>
      </div>

      <table v-else class="admin-table">
        <thead>
          <tr>
            <th>ID</th>
            <th>路線名稱</th>
            <th>方向</th>
            <th>站點名稱</th>
            <th>緯度</th>
            <th>經度</th>
            <th>順序</th>
            <th>地址</th>
            <th>到站時間(分鐘)</th>
            <th class="actions-column">操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="station in stations" :key="`${station.route_id}-${station.stop_order}`" class="table-row">
            <td>{{ station.route_id }}</td>
            <td class="route-cell">
              <div class="route-info">
                <span class="route-name">{{ station.route_name }}</span>
              </div>
            </td>
            <td>
              <span class="direction-badge" :class="station.direction">
                {{ station.direction }}
              </span>
            </td>
            <td class="station-cell">
              <div class="station-info">
                <span class="station-name">{{ station.stop_name }}</span>
              </div>
            </td>
            <td class="coord-cell">{{ station.latitude }}</td>
            <td class="coord-cell">{{ station.longitude }}</td>
            <td class="order-cell">{{ station.stop_order }}</td>
            <td class="address-cell" :title="station.address">
              {{ station.address ? station.address.substring(0, 20) + '...' : '未設定' }}
            </td>
            <td class="eta-cell">{{ station.eta_from_start }} 分鐘</td>
            <td class="actions-cell">
              <div class="action-buttons">
                <button
                  @click.stop="editStation(station)"
                  class="btn-edit"
                  title="編輯"
                >
                  ✏️
                </button>
                <button
                  @click.stop="deleteStation(station)"
                  class="btn-delete"
                  title="刪除"
                >
                  🗑️
                </button>
              </div>
            </td>
          </tr>
        </tbody>
      </table>

      <!-- 空狀態 -->
      <div v-if="!isLoading && stations.length === 0" class="empty-state">
        <div class="empty-icon">🚌</div>
        <h3>沒有找到站點</h3>
        <p>{{ searchQuery ? '沒有符合搜尋條件的站點' : '目前沒有站點資料' }}</p>
      </div>
    </div>

    <!-- 分頁控制器 -->
    <div v-if="!isLoading && stations.length > 0" class="pagination-container">
      <div class="pagination-info">
        顯示第 {{ (currentPage - 1) * pageSize + 1 }} 到
        {{ Math.min(currentPage * pageSize, totalStations) }} 筆，
        共 {{ totalStations }} 筆資料
      </div>

      <div class="pagination-controls">
        <button
          @click="goToPage(currentPage - 1)"
          :disabled="currentPage === 1"
          class="pagination-btn"
        >
          上一頁
        </button>

        <div class="page-numbers">
          <button
            v-for="page in visiblePages"
            :key="page"
            @click="goToPage(page)"
            :class="['page-number', { active: page === currentPage }]"
          >
            {{ page }}
          </button>
        </div>

        <button
          @click="goToPage(currentPage + 1)"
          :disabled="currentPage === totalPages"
          class="pagination-btn"
        >
          下一頁
        </button>
      </div>
    </div>

    <!-- 新增/編輯模態框 -->
    <div v-if="showModal" class="modal-overlay" @click="closeModal">
      <div class="modal-content" @click.stop>
        <div class="modal-header">
          <h2>{{ isEditMode ? '編輯站點' : '新增站點' }}</h2>
          <button @click="closeModal" class="close-btn">&times;</button>
        </div>

        <!-- 編輯模式提示 -->
        <div v-if="isEditMode" class="edit-mode-notice">
          <i class="icon">🔒</i>
          <span>編輯模式：路線、方向、順序已鎖定，無法修改</span>
        </div>

        <form @submit.prevent="saveStation" class="modal-form">
          <div class="form-row">
            <div class="form-group">
              <label :class="['form-label', { disabled: isEditMode }]">路線 *</label>
              <select 
                v-model="currentStation.route_id" 
                class="form-select" 
                required
                :disabled="isEditMode"
              >
                <option value="">請選擇路線</option>
                <option v-for="route in availableRoutes" :key="route.route_id" :value="route.route_id">
                  {{ route.route_name }}
                </option>
              </select>
            </div>
            <div class="form-group">
              <label :class="['form-label', { disabled: isEditMode }]">方向 *</label>
              <select 
                v-model="currentStation.direction" 
                class="form-select" 
                required
                :disabled="isEditMode"
              >
                <option value="">請選擇方向</option>
                <option value="去程">去程</option>
                <option value="回程">回程</option>
              </select>
            </div>
          </div>

          <div class="form-row">
            <div class="form-group">
              <label class="form-label">站點名稱 *</label>
              <input
                v-model="currentStation.stop_name"
                type="text"
                class="form-input"
                required
                placeholder="請輸入站點名稱"
              />
            </div>
            <div class="form-group">
              <label :class="['form-label', { disabled: isEditMode }]">順序 *</label>
              <input
                v-model.number="currentStation.stop_order"
                type="number"
                class="form-input"
                required
                placeholder="請輸入站點順序"
                min="1"
                :disabled="isEditMode"
              />
            </div>
          </div>

          <div class="form-row">
            <div class="form-group">
              <label class="form-label">緯度 *</label>
              <input
                v-model.number="currentStation.latitude"
                type="number"
                class="form-input"
                required
                placeholder="請輸入緯度"
                step="0.000001"
              />
            </div>
            <div class="form-group">
              <label class="form-label">經度 *</label>
              <input
                v-model.number="currentStation.longitude"
                type="number"
                class="form-input"
                required
                placeholder="請輸入經度"
                step="0.000001"
              />
            </div>
          </div>

          <div class="form-row">
            <div class="form-group">
              <label class="form-label">到站時間(分鐘)</label>
              <input
                v-model.number="currentStation.eta_from_start"
                type="number"
                class="form-input"
                placeholder="請輸入到站時間"
                min="0"
              />
            </div>
          </div>

          <div class="form-row">
            <div class="form-group full-width">
              <label class="form-label">地址</label>
              <textarea
                v-model="currentStation.address"
                class="form-textarea"
                placeholder="請輸入站點地址"
                rows="3"
              ></textarea>
            </div>
          </div>

          <div class="form-actions">
            <button type="button" @click="closeModal" class="btn-secondary">
              取消
            </button>
            <button type="submit" :disabled="isSubmitting" class="btn-primary">
              {{ isSubmitting ? '儲存中...' : (isEditMode ? '更新' : '新增') }}
            </button>
          </div>
        </form>
      </div>
    </div>

    <!-- 刪除確認模態框 -->
    <div v-if="showDeleteModal" class="modal-overlay" @click="cancelDelete">
      <div class="modal-content delete-modal" @click.stop>
        <div class="modal-header">
          <h2>確認刪除</h2>
          <button @click="cancelDelete" class="close-btn">&times;</button>
        </div>

        <div class="modal-body">
          <p>確定要刪除站點「{{ currentStation.stop_name }}」嗎？</p>
          <p class="warning-text">此操作無法復原。</p>
        </div>

        <div class="modal-actions">
          <button @click="cancelDelete" class="btn-secondary">取消</button>
          <button @click="confirmDelete" :disabled="isDeleting" class="btn-danger">
            {{ isDeleting ? '刪除中...' : '確認刪除' }}
          </button>
        </div>
      </div>
    </div>

    <!-- 路線刪除確認模態框（獨立於路線編輯模態） -->
    <div v-if="showRouteDeleteModal" class="modal-overlay" @click="cancelRouteDelete">
      <div class="modal-content delete-modal" @click.stop>
        <div class="modal-header">
          <h2>確認刪除路線</h2>
          <button @click="cancelRouteDelete" class="close-btn">&times;</button>
        </div>

        <div class="modal-body">
          <p>確定要刪除路線「{{ (routeToDelete && routeToDelete.route_name) || '未命名' }}」嗎？</p>
          <p class="warning-text">此操作會移除路線以及相關站點資料，無法復原。</p>
        </div>

        <div class="modal-actions">
          <button @click="cancelRouteDelete" class="btn-secondary">取消</button>
          <button @click="confirmRouteDelete" :disabled="isDeletingRoute" class="btn-danger">{{ isDeletingRoute ? '刪除中...' : '確認刪除' }}</button>
        </div>
      </div>
    </div>

    <!-- 新增路線模態框 -->
    <div v-if="showRouteModal" class="modal-overlay" @click="closeRouteModal">
      <div class="modal-content" @click.stop>
        <div class="modal-header">
          <h2>新增路線</h2>
          <button @click="closeRouteModal" class="close-btn">&times;</button>
        </div>

        <form @submit.prevent="saveRoute" class="modal-form">
          <div class="form-row">
            <div class="form-group">
              <label class="form-label">路線名稱 *</label>
              <input v-model="currentRoute.route_name" type="text" class="form-input" required placeholder="請輸入路線名稱" />
            </div>
            <div class="form-group">
              <label class="form-label">方向</label>
              <select v-model="currentRoute.direction" class="form-select">
                <option value="">(未指定)</option>
                <option value="單向">單向</option>
                <option value="雙向">雙向</option>
              </select>
            </div>
          </div>

            

          <div class="form-row">
            <div class="form-group">
              <label class="form-label">起點</label>
              <input v-model="currentRoute.start_stop" type="text" class="form-input" placeholder="起點站名" />
            </div>
            <div class="form-group">
              <label class="form-label">終點</label>
              <input v-model="currentRoute.end_stop" type="text" class="form-input" placeholder="終點站名" />
            </div>
          </div>

          <div class="form-row">
            <div class="form-group full-width">
              <label class="form-label">狀態</label>
              <select v-model.number="currentRoute.status" class="form-select">
                <option :value="1">啟用</option>
                <option :value="0">停用</option>
              </select>
            </div>
          </div>

          <div class="form-actions">
            <button type="button" @click="closeRouteModal" class="btn-secondary">取消</button>
            <button type="submit" :disabled="isSubmittingRoute" class="btn-primary">{{ isSubmittingRoute ? '儲存中...' : '新增' }}</button>
          </div>
        </form>
      </div>
    </div>

    <!-- 新增: 站點順序調整模態框 -->
    <div v-if="showOrderAdjustModal" class="modal-overlay" @click="showOrderAdjustModal = false">
      <div class="modal-content order-adjust-modal" @click.stop>
        <div class="modal-header">
          <h2>⚠️ 站點順序衝突</h2>
          <button @click="showOrderAdjustModal = false" class="close-btn">&times;</button>
        </div>

        <div class="modal-body">
          <div class="conflict-info">
            <p><strong>衝突詳情：</strong></p>
            <p>第 {{ currentStation.stop_order }} 站已被「{{ conflictingStation?.stop_name }}」佔用</p>
            <p>路線：{{ currentStation.route_name }} ({{ currentStation.direction }})</p>
          </div>

          <div class="adjustment-options">
            <h4>請選擇處理方式：</h4>
            
            <div class="option-card" @click="handleOrderAdjustment('replace')">
              <div class="option-header">
                <span class="option-icon">🔄</span>
                <strong>交換位置</strong>
              </div>
              <p>與「{{ conflictingStation?.stop_name }}」交換位置</p>
            </div>

            <div class="option-card" @click="handleOrderAdjustment('insert')">
              <div class="option-header">
                <span class="option-icon">➕</span>
                <strong>插入並調整</strong>
              </div>
              <p>在此位置插入，後續站點順序自動 +1</p>
            </div>

            <div class="option-card" @click="handleOrderAdjustment('manual')">
              <div class="option-header">
                <span class="option-icon">📍</span>
                <strong>使用建議順序</strong>
              </div>
              <p>使用建議的順序：第 {{ orderAdjustOptions.suggestedOrder }} 站</p>
            </div>
          </div>
        </div>

        <div class="form-actions">
          <button @click="showOrderAdjustModal = false" class="btn-secondary">取消</button>
        </div>
      </div>
    </div>

    <!-- XML匯入模態框 -->
    <div v-if="showXMLImportModal" class="modal-overlay" @click="closeXMLImportModal">
      <div class="modal-content xml-import-modal" @click.stop>
        <div class="modal-header">
          <h2>📁 XML路線匯入</h2>
          <button @click="closeXMLImportModal" class="close-btn">&times;</button>
        </div>

        <!-- 步驟1: 檔案上傳 -->
        <div v-if="xmlImportStep === 'upload'" class="modal-body">
          <div class="upload-section">
            <h4>步驟 1: 選擇XML檔案</h4>
            <p class="upload-description">請選擇包含路線和站點資料的XML檔案</p>
            
            <div class="file-upload-area">
              <input 
                type="file" 
                accept=".xml"
                @change="handleXMLFileSelect"
                id="xmlFileInput"
                class="file-input"
              />
              <label for="xmlFileInput" class="file-upload-label">
                <div class="upload-icon">📁</div>
                <div class="upload-text">
                  <span v-if="!xmlFile">點擊選擇XML檔案</span>
                  <span v-else>{{ xmlFile.name }}</span>
                </div>
              </label>
            </div>

            <div class="xml-format-info">
              <h5>支援的XML格式:</h5>
              <pre class="xml-example">&lt;bus_system&gt;
  &lt;routes&gt;
    &lt;route&gt;
      &lt;route_name&gt;路線名稱&lt;/route_name&gt;
      &lt;direction&gt;雙向&lt;/direction&gt;
      &lt;stations&gt;
        &lt;station direction="去程"&gt;
          &lt;stop_name&gt;站點名稱&lt;/stop_name&gt;
          &lt;latitude&gt;23.9930200&lt;/latitude&gt;
          &lt;longitude&gt;121.6032190&lt;/longitude&gt;
          &lt;stop_order&gt;1&lt;/stop_order&gt;
          ...
        &lt;/station&gt;
      &lt;/stations&gt;
    &lt;/route&gt;
  &lt;/routes&gt;
&lt;/bus_system&gt;</pre>
            </div>
          </div>

          <div class="modal-actions">
            <button @click="closeXMLImportModal" class="btn-secondary">取消</button>
            <button 
              @click="uploadXMLFile" 
              :disabled="!xmlFile || isUploadingXML" 
              class="btn-primary"
            >
              {{ isUploadingXML ? '解析中...' : '解析檔案' }}
            </button>
          </div>
        </div>

        <!-- 步驟2: 預覽結果 -->
        <div v-if="xmlImportStep === 'preview'" class="modal-body">
          <div class="preview-section">
            <h4>步驟 2: 解析結果預覽</h4>
            
            <div v-if="xmlParseResult" class="parse-summary">
              <div class="summary-cards">
                <div class="summary-card">
                  <div class="card-icon">🚌</div>
                  <div class="card-content">
                    <span class="card-number">{{ xmlParseResult.total_routes }}</span>
                    <span class="card-label">路線</span>
                  </div>
                </div>
                <div class="summary-card">
                  <div class="card-icon">🚏</div>
                  <div class="card-content">
                    <span class="card-number">{{ xmlParseResult.total_stations }}</span>
                    <span class="card-label">站點</span>
                  </div>
                </div>
              </div>

              <div v-if="xmlParseResult.warnings && xmlParseResult.warnings.length > 0" class="warnings-section">
                <h5>⚠️ 警告訊息:</h5>
                <ul class="warnings-list">
                  <li v-for="warning in xmlParseResult.warnings.slice(0, 5)" :key="warning">
                    {{ warning }}
                  </li>
                  <li v-if="xmlParseResult.warnings.length > 5">
                    ... 還有 {{ xmlParseResult.warnings.length - 5 }} 個警告
                  </li>
                </ul>
              </div>

              <div class="routes-preview">
                <h5>路線預覽:</h5>
                <div class="routes-list">
                  <div v-for="route in xmlParseResult.routes.slice(0, 3)" :key="route.route_name" class="route-preview-card">
                    <h6>{{ route.route_name }}</h6>
                    <p>方向: {{ route.direction }} | 站點數: {{ route.stations.length }}</p>
                  </div>
                  <div v-if="xmlParseResult.routes.length > 3" class="more-routes">
                    ... 還有 {{ xmlParseResult.routes.length - 3 }} 條路線
                  </div>
                </div>
              </div>
            </div>
          </div>

          <div class="modal-actions">
            <button @click="xmlImportStep = 'upload'" class="btn-secondary">返回</button>
            <button @click="previewXMLImport" class="btn-primary">
              檢查衝突
            </button>
          </div>
        </div>

        <!-- 步驟3: 確認匯入 -->
        <div v-if="xmlImportStep === 'confirm'" class="modal-body">
          <div class="confirm-section">
            <h4>
              <span class="step-icon">📋</span>
              步驟 3: 確認匯入
            </h4>
            
            <div v-if="xmlImportProgress" class="import-summary">
              <!-- 匯入統計卡片 -->
              <div class="import-stats-cards">
                <div class="stat-card routes-card">
                  <div class="stat-icon">🚌</div>
                  <div class="stat-content">
                    <div class="stat-number">{{ xmlImportProgress.total_routes }}</div>
                    <div class="stat-label">條路線</div>
                  </div>
                </div>
                <div class="stat-card stations-card">
                  <div class="stat-icon">📍</div>
                  <div class="stat-content">
                    <div class="stat-number">{{ xmlImportProgress.total_stations }}</div>
                    <div class="stat-label">個站點</div>
                  </div>
                </div>
              </div>

              <!-- 衝突檢測結果 -->
              <div v-if="xmlImportProgress.conflicts && xmlImportProgress.conflicts.length > 0" class="conflicts-section">
                <div class="conflicts-header">
                  <div class="conflicts-icon">⚠️</div>
                  <h5>發現衝突</h5>
                </div>
                
                <div class="conflicts-content">
                  <div class="conflicts-list-container">
                    <div v-for="conflict in xmlImportProgress.conflicts" :key="conflict.route_name" class="conflict-item">
                      <div class="conflict-info">
                        <span class="conflict-type">路線衝突</span>
                        <span class="conflict-detail">{{ conflict.message }}</span>
                      </div>
                    </div>
                  </div>
                  
                  <div class="conflict-resolution">
                    <h6>選擇處理方式</h6>
                    <div class="conflict-buttons">
                      <button @click="executeXMLImport(false)" class="conflict-btn skip-btn">
                        <span class="btn-icon">⏭️</span>
                        <span class="btn-text">
                          <strong>跳過衝突路線</strong>
                          <small>保留現有路線，僅匯入新路線</small>
                        </span>
                      </button>
                      <button @click="executeXMLImport(true)" class="conflict-btn overwrite-btn">
                        <span class="btn-icon">🔄</span>
                        <span class="btn-text">
                          <strong>覆蓋現有路線</strong>
                          <small>刪除舊路線，匯入新路線資料</small>
                        </span>
                      </button>
                    </div>
                  </div>
                </div>
              </div>

              <!-- 無衝突狀態 -->
              <div v-else class="no-conflicts-section">
                <div class="success-indicator">
                  <div class="success-icon">✅</div>
                  <div class="success-content">
                    <h5>檢測完成</h5>
                    <p>沒有發現衝突，可以安全匯入所有資料</p>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <!-- 操作按鈕 -->
          <div class="modal-actions confirm-actions">
            <button @click="xmlImportStep = 'preview'" class="btn-secondary action-btn">
              <span class="btn-icon">👈</span>
              返回預覽
            </button>
            
            <button 
              v-if="!xmlImportProgress.conflicts || xmlImportProgress.conflicts.length === 0"
              @click="executeXMLImport(false)" 
              :disabled="isUploadingXML"
              class="btn-primary action-btn start-import-btn"
            >
              <span v-if="isUploadingXML" class="btn-icon spinner">⏳</span>
              <span v-else class="btn-icon">🚀</span>
              {{ isUploadingXML ? '匯入中...' : '開始匯入' }}
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'

// 定義類型
interface Station {
  station_id?: number  // 新增: 站點ID (編輯時存在)
  route_id: number
  route_name: string
  direction: string
  stop_name: string
  latitude: number
  longitude: number
  stop_order: number
  eta_from_start: number
  address: string
  // optional 原始識別欄位，用於安全更新
  original_stop_name?: string
  original_stop_order?: number
  // 新增: 順序調整相關屬性
  replace_existing?: boolean
  auto_reorder?: boolean
}

interface Route {
  route_id: number
  route_name: string
}

// 響應式數據
const stations = ref<Station[]>([])
const availableRoutes = ref<Route[]>([])
const routeList = ref<any[]>([])
const routeSearchQuery = ref('')
const routeSortOrder = ref<'desc' | 'asc'>('desc')
const isLoading = ref(false)
const isSubmitting = ref(false)
const isDeleting = ref(false)
const showModal = ref(false)
const showDeleteModal = ref(false)
const isEditMode = ref(false)

// 新增: 站點順序調整相關狀態
const showOrderAdjustModal = ref(false)
const orderAdjustOptions = ref({
  insertAfter: false,
  autoReorder: true,
  suggestedOrder: 1
})
const conflictingStation = ref<any>(null)

// 搜尋和篩選
const searchQuery = ref('')
const routeFilter = ref('')
const directionFilter = ref('')
const stationSortOrder = ref<'desc' | 'asc'>('desc')
const pageSize = ref<number>(10)
const currentPage = ref(1)
const totalStations = ref(0)

// XML匯入相關狀態
const showXMLImportModal = ref(false)
const isUploadingXML = ref(false)
const xmlFile = ref<File | null>(null)
const xmlParseResult = ref<any>(null)
const xmlImportStep = ref<'upload' | 'preview' | 'confirm'>('upload')
const xmlImportProgress = ref<any>(null)

// 搜尋防抖
let searchTimeout: ReturnType<typeof setTimeout> | null = null
let routeSearchTimeout: ReturnType<typeof setTimeout> | null = null

// 當前編輯的站點
const currentStation = ref<Station>({
  route_id: 0,
  route_name: '',
  direction: '',
  stop_name: '',
  latitude: 0,
  longitude: 0,
  stop_order: 0,
  eta_from_start: 0,
  address: '',
  replace_existing: false,
  auto_reorder: false
})

// 新增路線狀態
const showRouteModal = ref(false)
const isSubmittingRoute = ref(false)
const currentRoute = ref({
  route_id: undefined as number | undefined,
  route_name: '',
  direction: '',
  start_stop: '',
  end_stop: '',
  status: 1
})

// 刪除路線狀態
const showRouteDeleteModal = ref(false)
const isDeletingRoute = ref(false)
const routeToDelete = ref<any>(null)

const deleteRoute = (r: any, ev?: Event) => {
  try { ev && (ev.stopPropagation(), ev.preventDefault()) } catch {}
  routeToDelete.value = r
  showRouteDeleteModal.value = true
}

const cancelRouteDelete = () => {
  showRouteDeleteModal.value = false
  routeToDelete.value = null
}

const confirmRouteDelete = async () => {
  if (!routeToDelete.value) return
  isDeletingRoute.value = true
  try {
    const res = await fetch('/api/routes/delete', {
      method: 'DELETE',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${localStorage.getItem('token') || ''}`
      },
      body: JSON.stringify({ route_id: routeToDelete.value.route_id })
    })
    if (res.ok) {
      await loadRouteList()
      await loadAvailableRoutes()
      showRouteDeleteModal.value = false
      routeToDelete.value = null
      alert('路線已刪除')
    } else {
      let msg = '刪除失敗'
      try { const err = await res.json(); msg = err.detail || err.message || msg } catch(e){}
      alert(msg)
    }
  } catch (e) {
    console.error('刪除路線失敗', e)
    alert('網路錯誤，無法刪除')
  } finally {
    isDeletingRoute.value = false
  }
}

const openEditRoute = (r: any) => {
  currentRoute.value = {
    route_id: r.route_id,
    route_name: r.route_name || '',
    direction: r.direction || '',
    start_stop: r.start_stop || '',
    end_stop: r.end_stop || '',
    status: r.status || 0
  }
  showRouteModal.value = true
}

const loadRouteList = async () => {
  try {
    const res = await fetch('/All_Route')
    let data: any = null
    if (res.ok) {
      try {
        data = await res.json()
      } catch (e) {
        // 解析失敗，可能是 HTML 回應（開發環境 proxy 問題），使用後端 fallback
        data = null
      }
    }

    // 如果沒有拿到有效的 JSON，資料載入失敗
    if (!data) {
      console.warn('無法載入路線資料，請檢查後端服務是否正常運行')
    }

    if (data) {
      // 支援多種回傳形狀：直接陣列、{ records: [] }, { routes: [] }, { data: [] }
      if (Array.isArray(data)) {
        routeList.value = data
      } else if (data && Array.isArray((data as any).records)) {
        routeList.value = (data as any).records
      } else if (data && Array.isArray((data as any).routes)) {
        routeList.value = (data as any).routes
      } else if (data && Array.isArray((data as any).data)) {
        routeList.value = (data as any).data
      } else {
        // 最後嘗試把 object 的 values 轉成陣列
        try {
          const vals = Object.values(data || {})
          routeList.value = vals.flat().filter((v: any) => v && v.route_id)
        } catch (ex) {
          routeList.value = []
        }
      }
      return
    }
    // fallback to older endpoint (try relative first, then backend host)
    if (!routeList.value.length) {
      try {
        let r2 = await fetch('/api/routes')
        let d2: any = null
        if (r2.ok) {
          try { d2 = await r2.json() } catch (e) { d2 = null }
        }
        if (!d2) {
          console.warn('無法載入路線資料，請檢查後端服務是否正常運行')
        }
        if (Array.isArray(d2)) {
          routeList.value = d2
        } else if (d2 && Array.isArray(d2.routes)) {
          routeList.value = d2.routes
        } else if (d2 && Array.isArray(d2.data)) {
          routeList.value = d2.data
        } else {
          routeList.value = []
        }
      } catch (e) {
        // ignore
      }
    }
  } catch (e) {
    console.error('載入路線列表失敗', e)
    routeList.value = []
  }
}

const toggleRouteStatus = async (r: any) => {
  try {
    const newStatus = r.status === 1 ? 0 : 1
    const payload: any = { route_id: r.route_id, status: newStatus }
    const res = await fetch('/api/routes/update', {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${localStorage.getItem('token') || ''}`
      },
      body: JSON.stringify(payload)
    })
    if (res.ok) {
      await loadRouteList()
      await loadAvailableRoutes()
      alert('狀態更新成功')
    } else {
      const err = await res.json()
      alert(err.detail || '更新失敗')
    }
  } catch (e) {
    console.error(e)
    alert('更新失敗')
  }
}

const openCreateRouteModal = () => {
  currentRoute.value = { route_id: undefined, route_name: '', direction: '', start_stop: '', end_stop: '', status: 1 }
  showRouteModal.value = true
}

const closeRouteModal = () => {
  showRouteModal.value = false
  currentRoute.value = { route_id: undefined, route_name: '', direction: '', start_stop: '', end_stop: '', status: 1 }
}

const saveRoute = async () => {
  if (!currentRoute.value.route_name || currentRoute.value.route_name.trim() === '') {
    alert('請輸入路線名稱')
    return
  }
  isSubmittingRoute.value = true
  try {
    let response: Response
    if (currentRoute.value.route_id) {
      response = await fetch('/api/routes/update', {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('token') || ''}`
        },
        body: JSON.stringify(currentRoute.value)
      })
    } else {
      response = await fetch('/api/routes/create', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('token') || ''}`
        },
        body: JSON.stringify(currentRoute.value)
      })
    }

    if (response.ok) {
    const data = await response.json()
    closeRouteModal()
    await loadRouteList()
    await loadAvailableRoutes()
    alert(data.message || '路線處理成功')
    } else {
      let msg = '新增路線失敗'
      try {
        const err = await response.json()
        msg = err.detail || err.message || msg
      } catch (e) {
        // ignore
      }
      alert(msg)
    }
  } catch (e) {
    console.error('saveRoute error', e)
    alert('網路錯誤，無法新增路線')
  } finally {
    isSubmittingRoute.value = false
  }
}

const handleRouteSearch = () => {
  if (routeSearchTimeout) clearTimeout(routeSearchTimeout)
  routeSearchTimeout = setTimeout(() => {
    // no server call here, we use computed filteredRoutes based on routeList
  }, 300)
}

const filteredRoutes = computed(() => {
  const q = routeSearchQuery.value.trim().toLowerCase()
  const list = Array.isArray(routeList.value) ? [...routeList.value] : []
  list.sort((a: any, b: any) => {
    const aId = Number(a?.route_id || 0)
    const bId = Number(b?.route_id || 0)
    return routeSortOrder.value === 'desc' ? bId - aId : aId - bId
  })
  if (!q) return list
  return list.filter((r: any) => (r.route_name || '').toLowerCase().includes(q))
})

// 方法
const loadStations = async () => {
  isLoading.value = true
  try {
    // 建構查詢參數
    const params = new URLSearchParams()
    if (routeFilter.value) {
      params.append('route_id', routeFilter.value)
    }
    if (directionFilter.value) {
      params.append('direction', directionFilter.value)
    }
    if (searchQuery.value) {
      params.append('search', searchQuery.value)
    }
    params.append('page', currentPage.value.toString())
    params.append('page_size', pageSize.value.toString())
    if (stationSortOrder.value) {
      params.append('order', stationSortOrder.value)
    }

    const url = `/api/route-stations${params.toString() ? '?' + params.toString() : ''}`
    
    const response = await fetch(url, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json'
      }
    })

    if (response.ok) {
      const data = await response.json()
      stations.value = data.stations || []
      totalStations.value = data.total || 0
    } else {
      console.error('API 回應錯誤:', response.status)
      stations.value = []
      totalStations.value = 0
    }
  } catch (error) {
    console.error('載入站點失敗:', error)
    stations.value = []
    totalStations.value = 0
  } finally {
    isLoading.value = false
  }
}

const loadAvailableRoutes = async () => {
  try {
    // 優先從 bus_routes_total (/All_Route) 取得路線（與新增路線來源一致）
    let response = await fetch('/All_Route')
    let data: any = null
    if (response.ok) {
      try { data = await response.json() } catch (e) { data = null }
    }
    if (!data) {
      console.warn('無法載入可用路線資料，請檢查後端服務是否正常運行')
      data = null
    }
    if (data) {
      let rows: any[] = []
      if (Array.isArray(data)) rows = data
      else if (data && Array.isArray((data as any).records)) rows = (data as any).records
      else if (data && Array.isArray((data as any).routes)) rows = (data as any).routes
      else if (data && Array.isArray((data as any).data)) rows = (data as any).data

      availableRoutes.value = rows.map((r: any) => ({ route_id: r.route_id, route_name: r.route_name }))
      return
    }

    // 若 /All_Route 不可用，退回到舊的 /api/routes
    response = await fetch('/api/routes')
    if (response.ok) {
      const data = await response.json()
      availableRoutes.value = data.routes || []
    }
  } catch (error) {
    console.error('載入路線失敗:', error)
    // 使用模擬資料
    availableRoutes.value = [
      { route_id: 1, route_name: '市民小巴5(洽公直達線)' },
      { route_id: 2, route_name: '市民小巴6(醫療照護線)' },
      { route_id: 3, route_name: '市民小巴7(市區夜環線)' },
      { route_id: 4, route_name: '市民小巴-行動遊花蓮' }
    ] as Route[]
  }
}

const handleSearch = () => {
  // 實現搜尋邏輯（帶防抖）
  if (searchTimeout) {
    clearTimeout(searchTimeout)
  }
  
  searchTimeout = setTimeout(() => {
    currentPage.value = 1
    loadStations()
  }, 500)
}

// 當 pageSize 改變時重置頁碼並重新載入
const onPageSizeChange = () => {
  currentPage.value = 1
  loadStations()
}

const openCreateModal = () => {
  isEditMode.value = false
  currentStation.value = {
    route_id: 0,
    route_name: '',
    direction: '',
    stop_name: '',
    latitude: 0,
    longitude: 0,
    stop_order: 0,
    eta_from_start: 0,
    address: '',
    replace_existing: false,
    auto_reorder: false
  }
  showModal.value = true
}

const editStation = (station: Station) => {
  isEditMode.value = true
  // 保留原始識別欄位以便安全更新（避免使用者修改後找不到原始記錄）
  currentStation.value = { ...station, original_stop_name: station.stop_name, original_stop_order: station.stop_order }
  showModal.value = true
}

const deleteStation = (station: Station) => {
  currentStation.value = { ...station }
  showDeleteModal.value = true
}

const closeModal = () => {
  showModal.value = false
  currentStation.value = {
    route_id: 0,
    route_name: '',
    direction: '',
    stop_name: '',
    latitude: 0,
    longitude: 0,
    stop_order: 0,
    eta_from_start: 0,
    address: '',
    original_stop_name: undefined,
    original_stop_order: undefined,
    replace_existing: false,
    auto_reorder: false
  }
}

const saveStation = async () => {
  if (isSubmitting.value) return // 防止重複提交
  isSubmitting.value = true
  
  try {
    // 基本欄位檢查
    if (!currentStation.value.route_id || !currentStation.value.direction || 
        !currentStation.value.stop_name || !currentStation.value.stop_order) {
      alert('請填寫所有必填欄位')
      return
    }

    // 前端驗證 (包含衝突檢查)
    const validationResult = await validateStationData()
    if (!validationResult.isValid) {
      if (validationResult.message !== '站點順序衝突，請選擇處理方式') {
        alert(validationResult.message)
      }
      return
    }

    // 執行實際保存
    await performSaveStation()
  } catch (error) {
    console.error('儲存失敗:', error)
    alert('操作失敗，請檢查網路連線')
  } finally {
    isSubmitting.value = false
  }
}

const cancelDelete = () => {
  showDeleteModal.value = false
  currentStation.value = {
    route_id: 0,
    route_name: '',
    direction: '',
    stop_name: '',
    latitude: 0,
    longitude: 0,
    stop_order: 0,
    eta_from_start: 0,
    address: '',
    replace_existing: false,
    auto_reorder: false
  }
}

const confirmDelete = async () => {
  isDeleting.value = true
  try {
    const response = await fetch(`/api/route-stations/delete?route_id=${currentStation.value.route_id}&stop_order=${currentStation.value.stop_order}`, {
      method: 'DELETE',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${localStorage.getItem('token') || ''}`
      }
    })

    if (response.ok) {
      const result = await response.json()
      showDeleteModal.value = false
      loadStations()
      alert(result.message || '站點刪除成功！')
    } else {
      const errorData = await response.json()
      alert(errorData.detail || '刪除失敗，請重試')
    }
  } catch (error) {
    console.error('刪除失敗:', error)
    alert('刪除失敗，請檢查網路連線')
  } finally {
    isDeleting.value = false
  }
}

const goToPage = (page: number) => {
  currentPage.value = page
  loadStations()
}

// 新增: 站點驗證函數
const validateStationData = async () => {
  const { route_id, direction, stop_name, stop_order, latitude, longitude } = currentStation.value

  // 基本欄位檢查
  if (!route_id || !direction || !stop_name || !stop_order || !latitude || !longitude) {
    return { isValid: false, message: '請填寫所有必填欄位' }
  }

  // 座標範圍檢查 (台灣範圍)
  if (latitude < 21.5 || latitude > 25.5 || longitude < 119.5 || longitude > 122.5) {
    return { isValid: false, message: '座標超出台灣範圍，請檢查緯度 (21.5-25.5) 和經度 (119.5-122.5)' }
  }

  // 順序檢查
  if (stop_order < 1) {
    return { isValid: false, message: '站點順序必須大於 0' }
  }

  // 檢查順序衝突 (除了編輯模式下的自己)
  try {
    const conflictCheck = await checkOrderConflict(route_id, direction, stop_order)
    if (conflictCheck.hasConflict) {
      // 編輯模式下，如果衝突的站點就是當前編輯的站點（通過原始名稱和順序判斷），則允許
      if (isEditMode.value && 
          conflictCheck.conflictStation.stop_name === currentStation.value.original_stop_name &&
          conflictCheck.conflictStation.stop_order === currentStation.value.original_stop_order) {
        // 編輯模式下，如果衝突的是自己，則允許
        return { isValid: true, message: '' }
      }
      
      // 顯示衝突處理選項
      conflictingStation.value = conflictCheck.conflictStation
      orderAdjustOptions.value.suggestedOrder = await getSuggestedOrder(route_id, direction)
      showOrderAdjustModal.value = true
      
      return { isValid: false, message: '站點順序衝突，請選擇處理方式' }
    }
  } catch (error) {
    console.warn('順序檢查失敗:', error)
  }

  return { isValid: true, message: '' }
}

// 檢查順序衝突
const checkOrderConflict = async (routeId: number, direction: string, stopOrder: number) => {
  try {
    const token = localStorage.getItem('token')
    if (!token) {
      console.warn('未登入，跳過衝突檢查')
      return { hasConflict: false, conflictStation: null }
    }

    const params = new URLSearchParams({
      route_id: routeId.toString(),
      direction: direction,
      stop_order: stopOrder.toString()
    })
    
    const response = await fetch(`/api/route-stations/check-conflict?${params}`, {
      headers: {
        'Authorization': `Bearer ${token}`
      }
    })
    
    if (response.ok) {
      const data = await response.json()
      return {
        hasConflict: data.hasConflict,
        conflictStation: data.conflictStation
      }
    } else if (response.status === 401) {
      console.warn('認證失敗，跳過衝突檢查')
      return { hasConflict: false, conflictStation: null }
    }
  } catch (error) {
    console.error('檢查順序衝突失敗:', error)
  }
  
  return { hasConflict: false, conflictStation: null }
}

// 獲取建議的順序
const getSuggestedOrder = async (routeId: number, direction: string) => {
  try {
    const token = localStorage.getItem('token')
    if (!token) {
      console.warn('未登入，使用預設建議順序')
      return 1
    }

    const params = new URLSearchParams({
      route_id: routeId.toString(),
      direction: direction
    })
    
    const response = await fetch(`/api/route-stations/suggest-order?${params}`, {
      headers: {
        'Authorization': `Bearer ${token}`
      }
    })
    
    if (response.ok) {
      const data = await response.json()
      return data.suggestedOrder || 1
    } else if (response.status === 401) {
      console.warn('認證失敗，使用預設建議順序')
    }
  } catch (error) {
    console.error('獲取建議順序失敗:', error)
  }
  
  return 1
}

// 處理順序調整
const handleOrderAdjustment = async (option: 'replace' | 'insert' | 'manual') => {
  showOrderAdjustModal.value = false
  
  try {
    if (option === 'replace') {
      // 交換位置
      currentStation.value.replace_existing = true
    } else if (option === 'insert') {
      // 插入並自動調整後續順序
      currentStation.value.auto_reorder = true
    } else if (option === 'manual') {
      // 使用建議的順序
      currentStation.value.stop_order = orderAdjustOptions.value.suggestedOrder
      // 清除調整標記，因為已經改用不衝突的順序
      currentStation.value.replace_existing = false
      currentStation.value.auto_reorder = false
    }
    
    // 直接調用保存邏輯，不再重新驗證
    await performSaveStation()
  } catch (error) {
    console.error('處理順序調整失敗:', error)
    alert('處理失敗，請重試')
  }
}

// 實際執行保存 (跳過驗證)
const performSaveStation = async () => {
  // 在送出前，若使用者只選了 route_id，則從 availableRoutes 填入對應的 route_name
  try {
    if (currentStation.value.route_id && (!currentStation.value.route_name || currentStation.value.route_name.toString().trim() === '')) {
      const found = (availableRoutes.value || []).find((r: any) => Number(r.route_id) === Number(currentStation.value.route_id))
      currentStation.value.route_name = found ? (found.route_name || '') : ''
    }
  } catch (e) {
    console.warn('填入 route_name 時發生錯誤', e)
  }

  const url = isEditMode.value ? '/api/route-stations/update' : '/api/route-stations/create'
  const method = isEditMode.value ? 'PUT' : 'POST'

  const payload = isEditMode.value
    ? JSON.stringify({ ...currentStation.value, original_stop_name: currentStation.value.original_stop_name, original_stop_order: currentStation.value.original_stop_order })
    : JSON.stringify(currentStation.value)

  const response = await fetch(url, {
    method,
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${localStorage.getItem('token') || ''}`
    },
    body: payload
  })

  if (response.ok) {
    const result = await response.json()
    closeModal()
    loadStations()
    alert(result.message || (isEditMode.value ? '站點更新成功！' : '站點新增成功！'))
  } else {
    let errorMessage = '操作失敗，請重試'
    try {
      const errorData = await response.json()
      const detail = errorData.detail || errorData.message || ''
      
      // 處理特定的資料庫錯誤
      if (detail.includes('Duplicate entry') && detail.includes('uk_route_direction_order')) {
        errorMessage = '站點順序已存在，請選擇不同的順序或使用衝突處理功能'
      } else if (detail.includes('Duplicate entry')) {
        errorMessage = '資料重複，請檢查輸入內容'
      } else {
        errorMessage = detail || errorMessage
      }
    } catch (parseError) {
      console.error('解析錯誤回應失敗:', parseError)
    }
    alert(errorMessage)
    throw new Error(errorMessage)
  }
}

// 分頁相關計算
const totalPages = computed(() => Math.ceil(totalStations.value / pageSize.value))

const visiblePages = computed(() => {
  const pages: number[] = []
  const maxPagesToShow = 5
  let start = Math.max(1, currentPage.value - Math.floor(maxPagesToShow / 2))
  let end = Math.min(totalPages.value, start + maxPagesToShow - 1)
  if (end - start < maxPagesToShow - 1) {
    start = Math.max(1, end - maxPagesToShow + 1)
  }
  for (let i = start; i <= end; i++) {
    pages.push(i)
  }
  return pages
})

// ===== XML匯入功能 =====

const openXMLImportModal = () => {
  showXMLImportModal.value = true
  xmlImportStep.value = 'upload'
  xmlFile.value = null
  xmlParseResult.value = null
  xmlImportProgress.value = null
}

const closeXMLImportModal = () => {
  showXMLImportModal.value = false
  xmlImportStep.value = 'upload'
  xmlFile.value = null
  xmlParseResult.value = null
  xmlImportProgress.value = null
}

const handleXMLFileSelect = (event: Event) => {
  const target = event.target as HTMLInputElement
  if (target.files && target.files.length > 0) {
    xmlFile.value = target.files[0]
  }
}

const uploadXMLFile = async () => {
  if (!xmlFile.value) {
    alert('請選擇XML檔案')
    return
  }

  isUploadingXML.value = true
  try {
    const formData = new FormData()
    formData.append('file', xmlFile.value)

    const response = await fetch('/api/xml/upload', {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${localStorage.getItem('token') || ''}`
      },
      body: formData
    })

    if (response.ok) {
      const result = await response.json()
      xmlParseResult.value = result
      xmlImportStep.value = 'preview'
      
      if (result.warnings && result.warnings.length > 0) {
        alert(`解析成功但有警告：\n${result.warnings.slice(0, 5).join('\n')}${result.warnings.length > 5 ? '\n...' : ''}`)
      }
    } else {
      const errorData = await response.json()
      alert(errorData.detail || 'XML檔案解析失敗')
    }
  } catch (error) {
    console.error('上傳XML檔案失敗:', error)
    alert('上傳失敗，請檢查網路連線')
  } finally {
    isUploadingXML.value = false
  }
}

const previewXMLImport = async () => {
  if (!xmlParseResult.value || !xmlParseResult.value.routes) {
    alert('沒有可預覽的資料')
    return
  }

  try {
    const response = await fetch('/api/xml/preview', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${localStorage.getItem('token') || ''}`
      },
      body: JSON.stringify(xmlParseResult.value.routes)
    })

    if (response.ok) {
      const preview = await response.json()
      xmlImportProgress.value = preview
      xmlImportStep.value = 'confirm'
      
      if (preview.conflicts && preview.conflicts.length > 0) {
        alert(`發現 ${preview.conflicts.length} 個衝突，請確認是否繼續匯入`)
      }
    } else {
      const errorData = await response.json()
      alert(errorData.detail || '預覽失敗')
    }
  } catch (error) {
    console.error('預覽失敗:', error)
    alert('預覽失敗，請檢查網路連線')
  }
}

const executeXMLImport = async (overwriteExisting: boolean = false) => {
  if (!xmlParseResult.value || !xmlParseResult.value.routes) {
    alert('沒有可匯入的資料')
    return
  }

  isUploadingXML.value = true
  try {
    const importOptions = {
      overwrite_existing: overwriteExisting,
      auto_resolve_conflicts: true,
      skip_invalid_data: true
    }

    const response = await fetch('/api/xml/import', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${localStorage.getItem('token') || ''}`
      },
      body: JSON.stringify({
        routes_data: xmlParseResult.value.routes,
        options: importOptions
      })
    })

    if (response.ok) {
      const result = await response.json()
      closeXMLImportModal()
      
      // 重新載入資料
      await loadRouteList()
      await loadAvailableRoutes()
      await loadStations()
      
      let message = `匯入成功！\n路線：${result.total_imported_routes} 條\n站點：${result.total_imported_stations} 個`
      if (result.errors && result.errors.length > 0) {
        message += `\n\n警告：\n${result.errors.slice(0, 3).join('\n')}${result.errors.length > 3 ? '\n...' : ''}`
      }
      alert(message)
    } else {
      const errorData = await response.json()
      alert(errorData.detail || '匯入失敗')
    }
  } catch (error) {
    console.error('匯入失敗:', error)
    alert('匯入失敗，請檢查網路連線')
  } finally {
    isUploadingXML.value = false
  }
}

// 生命週期
onMounted(() => {
  loadAvailableRoutes()
  loadRouteList()
  loadStations()
})
</script>

<style scoped>
/* 使用與 AdminManagement.vue 完全相同的樣式 */
.route-management {
  padding: 24px;
  background-color: #f8f9fa;
  min-height: calc(100vh - 60px);
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 32px;
  padding: 24px;
  background: white;
  border-radius: 12px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.header-left h1 {
  color: #2c3e50;
  margin: 0 0 8px 0;
  font-size: 28px;
  font-weight: 600;
}

.header-left p {
  color: #6c757d;
  margin: 0;
  font-size: 14px;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 12px;
}

.btn-primary {
  background: linear-gradient(135deg, #007bff 0%, #0056b3 100%);
  color: white;
  border: none;
  padding: 12px 20px;
  border-radius: 8px;
  cursor: pointer;
  font-weight: 500;
  display: flex;
  align-items: center;
  gap: 8px;
  transition: all 0.2s ease;
  font-size: 14px;
}

.btn-primary:hover {
  background: linear-gradient(135deg, #0056b3 0%, #004085 100%);
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(0, 123, 255, 0.3);
}

.btn-primary:active {
  transform: translateY(0);
}

.filters-section {
  background: white;
  padding: 20px 24px;
  border-radius: 12px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  margin-bottom: 24px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 20px;
}

.search-container {
  flex: 1;
  max-width: 400px;
}

.search-input-wrapper {
  position: relative;
}

.search-icon {
  position: absolute;
  left: 12px;
  top: 50%;
  transform: translateY(-50%);
  color: #6c757d;
  font-size: 16px;
}

.search-input {
  width: 100%;
  padding: 10px 16px 10px 40px;
  border: 2px solid #e9ecef;
  border-radius: 8px;
  font-size: 14px;
  transition: border-color 0.2s ease;
}

.search-input:focus {
  outline: none;
  border-color: #007bff;
  box-shadow: 0 0 0 3px rgba(0, 123, 255, 0.1);
}

.filter-controls {
  display: flex;
  gap: 20px;
  align-items: center;
}

.filter-group {
  display: flex;
  align-items: center;
  gap: 8px;
}

.filter-label {
  color: #495057;
  font-weight: 500;
  font-size: 14px;
  white-space: nowrap;
}

.route-select, .direction-select, .page-size-select {
  padding: 8px 12px;
  border: 2px solid #e9ecef;
  border-radius: 6px;
  font-size: 14px;
  background: white;
  cursor: pointer;
  transition: border-color 0.2s ease;
}

.route-select:focus, .direction-select:focus, .page-size-select:focus {
  outline: none;
  border-color: #007bff;
}

/* 表格容器 - 支援橫向和縱向滾動 */
.table-container {
  background: white;
  border-radius: 16px;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.08);
  border: 1px solid #e5e7eb;
  position: relative;
  margin-bottom: 24px;
  max-height: 600px; /* 限制最大高度，支援縱向滾動 */
  overflow: auto; /* 同時支援上下左右滾動 */
}

.admin-table {
  width: 100%;
  border-collapse: collapse;
  min-width: 1000px; /* 設定最小寬度，確保橫向滾動 */
}

.admin-table th {
  background: #f8f9fa;
  padding: 16px 12px;
  text-align: left;
  font-weight: 600;
  color: #495057;
  border-bottom: 2px solid #e9ecef;
  font-size: 14px;
  position: sticky;
  top: 0; /* 固定表頭 */
  z-index: 1;
}

.admin-table td {
  padding: 16px 12px;
  border-bottom: 1px solid #e9ecef;
  font-size: 14px;
  white-space: nowrap; /* 防止文字換行 */
}

.table-row:hover {
  background: #f8f9fa;
}

.route-cell {
  font-weight: 500;
  color: #2c3e50;
}

.station-cell {
  max-width: 200px;
}

.station-name {
  font-weight: 500;
  color: #2c3e50;
}

.direction-badge {
  display: inline-block;
  padding: 4px 12px;
  border-radius: 20px;
  font-size: 12px;
  font-weight: 500;
  text-align: center;
}

.direction-badge.去程 {
  background: #d4edda;
  color: #155724;
}

.direction-badge.回程 {
  background: #fff3cd;
  color: #856404;
}

.coord-cell {
  font-family: 'Courier New', monospace;
  font-size: 13px;
}

.order-cell {
  text-align: center;
  font-weight: 500;
}

.address-cell {
  max-width: 200px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.eta-cell {
  text-align: center;
}

.actions-column {
  width: 100px;
  text-align: center;
}

.action-buttons {
  display: flex;
  justify-content: center;
  gap: 8px;
}

.btn-edit,
.btn-delete {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 36px;
  height: 36px;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  font-size: 14px;
  transition: all 0.3s ease;
}

.btn-edit {
  background: #dbeafe;
  color: #1e40af;
}

.btn-edit:hover {
  background: #bfdbfe;
  transform: translateY(-1px);
}

.btn-delete {
  background: #fecaca;
  color: #991b1b;
}

.btn-delete:hover:not(:disabled) {
  background: #fca5a5;
  transform: translateY(-1px);
}

/* 載入覆蓋層 */
.loading-overlay {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(255, 255, 255, 0.9);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 16px;
  z-index: 10;
}

.spinner {
  width: 40px;
  height: 40px;
  border: 4px solid #e5e7eb;
  border-top: 4px solid #3b82f6;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

/* 空狀態 */
.empty-state {
  text-align: center;
  padding: 64px 24px;
  color: #6b7280;
}

.empty-icon {
  font-size: 64px;
  margin-bottom: 16px;
  opacity: 0.5;
}

.empty-state h3 {
  font-size: 20px;
  font-weight: 600;
  margin: 0 0 8px 0;
  color: #374151;
}

.empty-state p {
  font-size: 16px;
  margin: 0;
}

/* 分頁樣式 - 完全參照 AdminManagement.vue */
.pagination-container {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 20px 24px;
  background: white;
  border-radius: 12px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  margin-top: 24px;
}

.pagination-info {
  color: #6c757d;
  font-size: 14px;
}

.pagination-controls {
  display: flex;
  align-items: center;
  gap: 12px;
}

.pagination-btn {
  padding: 8px 16px;
  border: 2px solid #dee2e6;
  background: white;
  border-radius: 6px;
  cursor: pointer;
  font-size: 14px;
  transition: all 0.2s ease;
  color: #495057;
}

.pagination-btn:hover:not(:disabled) {
  background: #f8f9fa;
  border-color: #007bff;
  color: #007bff;
}

.pagination-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.page-numbers {
  display: flex;
  gap: 4px;
}

.page-number {
  padding: 8px 12px;
  border: 2px solid #dee2e6;
  background: white;
  border-radius: 6px;
  cursor: pointer;
  font-size: 14px;
  transition: all 0.2s ease;
  color: #495057;
}

.page-number:hover {
  background: #f8f9fa;
  border-color: #007bff;
  color: #007bff;
}

.page-number.active {
  background: #007bff;
  border-color: #007bff;
  color: white;
}

/* Modal 樣式保持不變... */
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.6);
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 1000;
}

.modal-content {
  background: white;
  border-radius: 12px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.15);
  width: 90%;
  max-width: 600px;
  max-height: 90vh;
  overflow-y: auto;
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 20px 24px;
  border-bottom: 1px solid #e9ecef;
}

.modal-header h2 {
  margin: 0;
  color: #2c3e50;
  font-size: 20px;
  font-weight: 600;
}

.close-btn {
  background: none;
  border: none;
  font-size: 24px;
  cursor: pointer;
  color: #6c757d;
  padding: 0;
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 4px;
  transition: background-color 0.2s ease;
}

.close-btn:hover {
  background: #f8f9fa;
  color: #495057;
}

.modal-form {
  padding: 24px;
}

.form-row {
  display: flex;
  gap: 16px;
  margin-bottom: 16px;
}

.form-group {
  flex: 1;
}

.form-group.full-width {
  flex: none;
  width: 100%;
}

.form-label {
  display: block;
  margin-bottom: 6px;
  font-weight: 500;
  color: #374151;
  font-size: 14px;
}

.form-input,
.form-select,
.form-textarea {
  width: 100%;
  padding: 10px 12px;
  border: 2px solid #e5e7eb;
  border-radius: 6px;
  font-size: 14px;
  transition: border-color 0.2s ease;
}

.form-input:focus,
.form-select:focus,
.form-textarea:focus {
  outline: none;
  border-color: #667eea;
}

.form-textarea {
  resize: vertical;
  min-height: 80px;
}

.form-actions {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  margin-top: 24px;
  padding-top: 20px;
  border-top: 1px solid #e9ecef;
}

.btn-secondary {
  padding: 10px 20px;
  border: 2px solid #6c757d;
  background: white;
  color: #6c757d;
  border-radius: 6px;
  cursor: pointer;
  font-size: 14px;
  font-weight: 500;
  transition: all 0.2s ease;
}

.btn-secondary:hover {
  background: #6c757d;
  color: white;
}

.btn-danger {
  padding: 10px 20px;
  border: 2px solid #dc3545;
  background: #dc3545;
  color: white;
  border-radius: 6px;
  cursor: pointer;
  font-size: 14px;
  font-weight: 500;
  transition: all 0.2s ease;
}

.btn-danger:hover {
  background: #c82333;
  border-color: #c82333;
}

.delete-modal {
  max-width: 400px;
}

.modal-body {
  padding: 24px;
  text-align: center;
}

.warning-text {
  color: #dc2626;
  font-weight: 500;
  margin-top: 8px;
}

.modal-actions {
  display: flex;
  gap: 12px;
  justify-content: center;
  padding: 0 24px 24px;
}

/* 響應式設計 */
@media (max-width: 768px) {
  .route-management {
    padding: 10px;
  }

  .page-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 15px;
  }

  .filters-section {
    flex-direction: column;
    align-items: stretch;
  }

  .filter-controls {
    flex-direction: column;
    align-items: stretch;
  }

  .form-row {
    flex-direction: column;
    gap: 12px;
  }

  .form-actions {
    flex-direction: column;
  }

  .pagination-container {
    flex-direction: column;
    gap: 15px;
    text-align: center;
  }

  .admin-table {
    font-size: 12px;
  }

  .admin-table th,
  .admin-table td {
    padding: 8px 6px;
  }
}

.routes-filter-row { display:flex; gap:16px; align-items:center; justify-content:space-between; margin-bottom:12px; flex-wrap:wrap; }
.routes-filter-row .routes-search { flex:1; min-width:220px; }
.routes-filter-row .filter-inline { display:flex; align-items:center; gap:8px; }
.routes-order-select { min-width:140px; }

/* 新增: 順序調整模態框樣式 */
.order-adjust-modal {
  max-width: 500px;
}

.conflict-info {
  background: #fff3cd;
  border: 1px solid #ffeaa7;
  border-radius: 8px;
  padding: 16px;
  margin-bottom: 20px;
}

.conflict-info p {
  margin: 4px 0;
  color: #856404;
}

.adjustment-options h4 {
  margin: 0 0 16px 0;
  color: #2c3e50;
  font-size: 16px;
}

.option-card {
  border: 2px solid #e9ecef;
  border-radius: 8px;
  padding: 16px;
  margin-bottom: 12px;
  cursor: pointer;
  transition: all 0.2s ease;
  background: white;
}

.option-card:hover {
  border-color: #007bff;
  background: #f8f9fa;
  transform: translateY(-1px);
  box-shadow: 0 2px 8px rgba(0, 123, 255, 0.15);
}

.option-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 4px;
}

.option-icon {
  font-size: 20px;
}

.option-card p {
  margin: 0;
  color: #6c757d;
  font-size: 14px;
}

/* 禁用狀態樣式 */
.form-select:disabled,
.form-input:disabled {
  background-color: #f8f9fa;
  color: #6c757d;
  cursor: not-allowed;
  opacity: 0.8;
}

.form-select:disabled,
.form-input:disabled {
  border-color: #dee2e6;
}

/* 禁用狀態的標籤樣式 */
.form-group:has(select:disabled) .form-label,
.form-group:has(input:disabled) .form-label {
  color: #6c757d;
}

/* 為了兼容性，也可以使用這種方式 */
.form-group .form-label.disabled {
  color: #6c757d;
}

/* 編輯模式提示樣式 */
.edit-mode-notice {
  background: linear-gradient(135deg, #e3f2fd 0%, #f3e5f5 100%);
  border: 1px solid #90caf9;
  border-radius: 8px;
  padding: 12px 16px;
  margin-bottom: 20px;
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
  color: #1565c0;
}

.edit-mode-notice .icon {
  font-size: 16px;
}

.edit-mode-notice span {
  font-weight: 500;
}

.option-card strong {
  color: #2c3e50;
  font-size: 15px;
}

/* ===== XML匯入模態框樣式 ===== */
.xml-import-modal {
  max-width: 700px;
  max-height: 90vh;
}

.upload-section h4,
.preview-section h4,
.confirm-section h4 {
  margin: 0 0 16px 0;
  color: #2c3e50;
  font-size: 18px;
  display: flex;
  align-items: center;
  gap: 8px;
}

.upload-description {
  color: #6c757d;
  margin-bottom: 20px;
  font-size: 14px;
}

.file-upload-area {
  margin: 20px 0;
}

.file-input {
  display: none;
}

.file-upload-label {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  border: 2px dashed #d1d5db;
  border-radius: 12px;
  padding: 32px 20px;
  cursor: pointer;
  transition: all 0.3s ease;
  background: #f9fafb;
}

.file-upload-label:hover {
  border-color: #8b5cf6;
  background: #f3f4f6;
}

.upload-icon {
  font-size: 48px;
  margin-bottom: 12px;
  color: #8b5cf6;
}

.upload-text {
  font-size: 16px;
  color: #374151;
  font-weight: 500;
}

.xml-format-info {
  margin-top: 24px;
  padding: 16px;
  background: #f8f9fa;
  border-radius: 8px;
  border-left: 4px solid #8b5cf6;
}

.xml-format-info h5 {
  margin: 0 0 12px 0;
  color: #2c3e50;
  font-size: 14px;
}

.xml-example {
  background: #1f2937;
  color: #e5e7eb;
  padding: 12px;
  border-radius: 6px;
  font-size: 12px;
  line-height: 1.4;
  margin: 0;
  overflow-x: auto;
}

.summary-cards {
  display: flex;
  gap: 16px;
  margin-bottom: 24px;
}

.summary-card {
  flex: 1;
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 16px;
  background: linear-gradient(135deg, #f3f4f6 0%, #e5e7eb 100%);
  border-radius: 12px;
  border: 1px solid #d1d5db;
}

.card-icon {
  font-size: 24px;
}

.card-content {
  display: flex;
  flex-direction: column;
}

.card-number {
  font-size: 24px;
  font-weight: 700;
  color: #1f2937;
  line-height: 1;
}

.card-label {
  font-size: 12px;
  color: #6b7280;
  font-weight: 500;
}

.warnings-section,
.conflicts-section {
  margin: 20px 0;
  padding: 16px;
  background: #fef3c7;
  border: 1px solid #f59e0b;
  border-radius: 8px;
}

.warnings-section h5,
.conflicts-section h5 {
  margin: 0 0 12px 0;
  color: #92400e;
  font-size: 14px;
}

.warnings-list,
.conflicts-list {
  margin: 0;
  padding-left: 20px;
  color: #92400e;
}

.warnings-list li,
.conflicts-list li {
  font-size: 13px;
  margin-bottom: 4px;
}

.routes-preview {
  margin-top: 20px;
}

.routes-preview h5 {
  margin: 0 0 12px 0;
  color: #2c3e50;
  font-size: 14px;
}

.routes-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.route-preview-card {
  padding: 12px;
  background: #f8f9fa;
  border: 1px solid #e9ecef;
  border-radius: 6px;
}

.route-preview-card h6 {
  margin: 0 0 4px 0;
  color: #2c3e50;
  font-size: 14px;
}

.route-preview-card p {
  margin: 0;
  font-size: 12px;
  color: #6c757d;
}

.more-routes {
  padding: 8px 12px;
  text-align: center;
  color: #6c757d;
  font-size: 12px;
  font-style: italic;
}

.summary-info {
  margin-bottom: 20px;
}

.summary-info p {
  margin: 4px 0;
  font-size: 14px;
}

.conflict-options {
  margin-top: 16px;
  display: flex;
  gap: 12px;
  align-items: center;
}

.conflict-options p {
  margin: 0;
  font-size: 14px;
  font-weight: 500;
}

.no-conflicts {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  padding: 24px;
  background: #f0fdf4;
  border: 2px solid #22c55e;
  border-radius: 12px;
  margin: 20px 0;
}

.no-conflicts .success-icon {
  font-size: 32px;
}

.no-conflicts p {
  margin: 0;
  color: #15803d;
  font-weight: 500;
  text-align: center;
}

/* 新增的確認步驟樣式 */
.step-icon {
  font-size: 20px;
  margin-right: 8px;
}

.import-stats-cards {
  display: flex;
  gap: 16px;
  margin-bottom: 24px;
}

.stat-card {
  flex: 1;
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 20px;
  border-radius: 16px;
  border: 1px solid #e5e7eb;
  background: linear-gradient(135deg, #ffffff 0%, #f9fafb 100%);
  transition: all 0.3s ease;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
}

.stat-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.12);
}

.routes-card {
  border-left: 4px solid #3b82f6;
}

.stations-card {
  border-left: 4px solid #10b981;
}

.stat-icon {
  font-size: 32px;
  opacity: 0.8;
}

.stat-content {
  display: flex;
  flex-direction: column;
}

.stat-number {
  font-size: 28px;
  font-weight: 700;
  color: #1f2937;
  line-height: 1;
  margin-bottom: 4px;
}

.stat-label {
  font-size: 13px;
  color: #6b7280;
  font-weight: 500;
}

.conflicts-section {
  margin: 24px 0;
  background: #fef3c7;
  border: 1px solid #f59e0b;
  border-radius: 16px;
  overflow: hidden;
}

.conflicts-header {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 16px 20px;
  background: #f59e0b;
  color: white;
}

.conflicts-icon {
  font-size: 20px;
}

.conflicts-header h5 {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
}

.conflicts-content {
  padding: 20px;
}

.conflicts-list-container {
  margin-bottom: 20px;
}

.conflict-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
  background: #ffffff;
  border: 1px solid #f3f4f6;
  border-radius: 8px;
  margin-bottom: 8px;
}

.conflict-info {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.conflict-type {
  font-size: 12px;
  font-weight: 600;
  color: #d97706;
  text-transform: uppercase;
}

.conflict-detail {
  font-size: 14px;
  color: #92400e;
}

.conflict-resolution h6 {
  margin: 0 0 16px 0;
  font-size: 14px;
  font-weight: 600;
  color: #92400e;
}

.conflict-buttons {
  display: flex;
  gap: 12px;
}

.conflict-btn {
  flex: 1;
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 16px;
  border: 2px solid transparent;
  border-radius: 12px;
  cursor: pointer;
  transition: all 0.3s ease;
  text-align: left;
}

.skip-btn {
  background: #f3f4f6;
  color: #374151;
  border-color: #d1d5db;
}

.skip-btn:hover {
  background: #e5e7eb;
  border-color: #9ca3af;
  transform: translateY(-1px);
}

.overwrite-btn {
  background: #fef2f2;
  color: #dc2626;
  border-color: #fecaca;
}

.overwrite-btn:hover {
  background: #fee2e2;
  border-color: #fca5a5;
  transform: translateY(-1px);
}

.conflict-btn .btn-icon {
  font-size: 20px;
  opacity: 0.8;
}

.conflict-btn .btn-text {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.conflict-btn .btn-text strong {
  font-size: 14px;
  font-weight: 600;
}

.conflict-btn .btn-text small {
  font-size: 12px;
  opacity: 0.7;
}

.no-conflicts-section {
  margin: 24px 0;
}

.success-indicator {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 24px;
  background: #f0fdf4;
  border: 2px solid #22c55e;
  border-radius: 16px;
}

.success-indicator .success-icon {
  font-size: 32px;
}

.success-indicator .success-content h5 {
  margin: 0 0 8px 0;
  color: #15803d;
  font-size: 16px;
  font-weight: 600;
}

.success-indicator .success-content p {
  margin: 0;
  color: #166534;
  font-size: 14px;
}

.confirm-actions {
  margin-top: 32px;
  padding-top: 24px;
  border-top: 1px solid #e5e7eb;
}

.action-btn {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 24px;
  font-size: 14px;
  font-weight: 500;
  border-radius: 8px;
  transition: all 0.3s ease;
}

.action-btn .btn-icon {
  font-size: 16px;
}

.start-import-btn {
  background: linear-gradient(135deg, #10b981 0%, #059669 100%);
  border: none;
  color: white;
}

.start-import-btn:hover:not(:disabled) {
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(16, 185, 129, 0.3);
}

.start-import-btn:disabled {
  opacity: 0.7;
  cursor: not-allowed;
}

.spinner {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

/* 外層容器樣式 */
.container {
  padding: 32px 20px;
  text-align: center;
}

.success-icon {
  font-size: 48px;
  margin-bottom: 12px;
}

.no-conflicts p {
  margin: 0;
  font-size: 16px;
  color: #059669;
  font-weight: 500;
}

/* 按鈕樣式調整 */
.btn-danger {
  background: linear-gradient(135deg, #dc2626 0%, #b91c1c 100%);
  color: white;
  border: none;
  padding: 8px 16px;
  border-radius: 6px;
  cursor: pointer;
  font-size: 14px;
  font-weight: 500;
  transition: all 0.2s ease;
}

.btn-danger:hover:not(:disabled) {
  background: linear-gradient(135deg, #b91c1c 0%, #991b1b 100%);
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(220, 38, 38, 0.3);
}

.btn-danger:disabled {
  opacity: 0.6;
  cursor: not-allowed;
  transform: none;
}

.xml-example {
  text-align: left;
  white-space: pre-wrap;
}
</style>