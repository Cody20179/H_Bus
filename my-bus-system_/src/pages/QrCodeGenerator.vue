<template>
  <div class="qr-generator">
    <header class="page-header">
      <div class="page-header__titles">
        <h1>QR Code Generator</h1>
        <p>Create route stop QR codes for passengers in one click.</p>
      </div>
    </header>

    <section class="card">
      <form class="form" @submit.prevent="handleSubmit">
        <p class="page-remark">
          This screen is under active testing. Settings may change without notice.
        </p>

        <div class="form-grid">
          <label class="field field--wide">
            <span>Base URL</span>
            <input
              type="url"
              v-model.trim="form.baseUrl"
              placeholder="https://hualenbus.labelnine.app:8700"
              required
            />
          </label>

          <label class="field">
            <span>Route ID</span>
            <input
              type="number"
              min="1"
              v-model.number="form.routeId"
              required
            />
          </label>

          <label class="field">
            <span>Stop count</span>
            <input
              type="number"
              min="1"
              max="200"
              v-model.number="form.stopCount"
              required
            />
          </label>

          <label class="field field--wide">
            <span>File prefix (optional)</span>
            <input
              type="text"
              v-model.trim="form.outputPrefix"
              placeholder="route_1"
              maxlength="64"
            />
          </label>
        </div>

        <div class="form-actions">
          <button class="btn btn-primary" type="submit" :disabled="downloading || !isFormValid">
            {{ downloading ? 'Generating...' : 'Generate QR Codes' }}
          </button>
          <button class="btn btn-secondary" type="button" @click="resetForm" :disabled="downloading">
            Reset
          </button>
        </div>
      </form>

      <transition name="fade">
        <div v-if="feedback.message" class="inline-alert" :class="`inline-alert--${feedback.variant}`">
          {{ feedback.message }}
        </div>
      </transition>

      <div v-if="downloadLink" class="download-box">
        <div class="download-box__info">
          <h3>Download ready</h3>
          <p>{{ downloadName }}</p>
        </div>
        <a class="btn btn-link" :href="downloadLink" :download="downloadName" @click="clearDownloadAfter">
          Download ZIP
        </a>
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import { reactive, ref, computed, onBeforeUnmount } from 'vue'
import { toolsApi, type GenerateQrCodesPayload } from '../services/api'

interface FeedbackState {
  message: string
  variant: 'info' | 'success' | 'error'
}

const DEFAULT_BASE_URL = 'https://hualenbus.labelnine.app:8700'

const form = reactive({
  baseUrl: DEFAULT_BASE_URL,
  routeId: 1,
  stopCount: 8,
  outputPrefix: ''
})

const downloading = ref(false)
const downloadLink = ref<string | null>(null)
const downloadName = ref('')
const feedback = reactive<FeedbackState>({ message: '', variant: 'info' })

const isFormValid = computed(() => {
  const hasUrl = form.baseUrl.trim().length > 0
  const route = Number(form.routeId)
  const stops = Number(form.stopCount)
  return hasUrl && Number.isFinite(route) && route > 0 && Number.isFinite(stops) && stops > 0
})

function setFeedback(message: string, variant: FeedbackState['variant'] = 'info') {
  feedback.message = message
  feedback.variant = variant
  if (message) {
    setTimeout(() => {
      if (feedback.message === message) {
        feedback.message = ''
      }
    }, 4000)
  }
}

function normaliseBaseUrl(url: string) {
  return url.replace(/\/$/, '')
}

function resetForm() {
  form.baseUrl = DEFAULT_BASE_URL
  form.routeId = 1
  form.stopCount = 8
  form.outputPrefix = ''
  clearDownload()
  feedback.message = ''
}

function clearDownload() {
  if (downloadLink.value) {
    URL.revokeObjectURL(downloadLink.value)
    downloadLink.value = null
    downloadName.value = ''
  }
}

function clearDownloadAfter() {
  setTimeout(() => {
    clearDownload()
  }, 2000)
}

async function handleSubmit() {
  if (!isFormValid.value || downloading.value) {
    return
  }

  downloading.value = true
  clearDownload()
  setFeedback('Generating QR codes...', 'info')

  try {
    const payload: GenerateQrCodesPayload = {
      base_url: normaliseBaseUrl(form.baseUrl),
      route_id: Number(form.routeId),
      stop_count: Number(form.stopCount)
    }

    if (form.outputPrefix.trim()) {
      payload.output_prefix = form.outputPrefix.trim()
    }

    const blob = await toolsApi.generateQrCodes(payload)
    const fileName = `${payload.output_prefix ?? `route_${payload.route_id}`}__qr_codes.zip`
    downloadLink.value = URL.createObjectURL(blob)
    downloadName.value = fileName

    triggerDownload(downloadLink.value, downloadName.value)
    setFeedback('QR codes generated successfully.', 'success')
  } catch (error) {
    console.error('Failed to generate QR codes', error)
    setFeedback('Failed to generate QR codes. Please try again.', 'error')
  } finally {
    downloading.value = false
  }
}

function triggerDownload(href: string, filename: string) {
  const link = document.createElement('a')
  link.href = href
  link.download = filename
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
}

onBeforeUnmount(() => {
  clearDownload()
})
</script>

<style scoped>
.page-remark {
  margin: 0 24px 12px;
  padding: 10px 14px;
  border-radius: 12px;
  font-size: 14px;
  background: rgba(250, 204, 21, 0.18);
  color: #854d0e;
}
.qr-generator {
  display: flex;
  flex-direction: column;
  gap: 28px;
  padding: 32px 24px;
  max-width: 760px;
  margin: 0 auto;
}

.page-header {
  background: linear-gradient(135deg, #2563eb 0%, #1d4ed8 100%);
  color: #fff;
  padding: 24px;
  border-radius: 20px;
  box-shadow: 0 20px 40px rgba(37, 99, 235, 0.22);
}

.page-header__titles h1 {
  margin: 0;
  font-size: 24px;
  font-weight: 600;
}

.page-header__titles p {
  margin: 6px 0 0;
  opacity: 0.85;
  font-size: 14px;
}

.card {
  background: #ffffff;
  border-radius: 20px;
  box-shadow: 0 16px 30px rgba(15, 23, 42, 0.12);
  overflow: hidden;
  padding: 28px;
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.form-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 20px;
}

.field {
  display: flex;
  flex-direction: column;
  gap: 8px;
  font-size: 14px;
  color: #1f2937;
}

.field span {
  font-weight: 600;
}

.field input {
  border: 1px solid #cbd5f5;
  border-radius: 12px;
  padding: 10px 12px;
  font-size: 15px;
  transition: border-color 0.2s, box-shadow 0.2s;
}

.field input:focus {
  outline: none;
  border-color: #2563eb;
  box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.15);
}

.field--wide {
  grid-column: span 2;
}

.form-actions {
  display: flex;
  gap: 12px;
  justify-content: flex-end;
}

.btn {
  border: none;
  border-radius: 999px;
  padding: 10px 22px;
  font-weight: 600;
  cursor: pointer;
  transition: transform 0.2s ease, box-shadow 0.2s ease, opacity 0.2s ease;
}

.btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.btn-primary {
  background: #2563eb;
  color: #fff;
  box-shadow: 0 10px 20px rgba(37, 99, 235, 0.3);
}

.btn-primary:hover:not(:disabled) {
  transform: translateY(-1px);
  box-shadow: 0 12px 24px rgba(37, 99, 235, 0.35);
}

.btn-secondary {
  background: #e2e8f0;
  color: #0f172a;
}

.btn-link {
  color: #2563eb;
  font-weight: 600;
  text-decoration: none;
  background: transparent;
  padding: 9px 18px;
  border-radius: 999px;
  border: 1px solid rgba(37, 99, 235, 0.35);
}

.inline-alert {
  padding: 12px 16px;
  border-radius: 12px;
  font-size: 14px;
  font-weight: 500;
}

.inline-alert--info {
  background: rgba(59, 130, 246, 0.1);
  color: #1e3a8a;
}

.inline-alert--success {
  background: rgba(16, 185, 129, 0.12);
  color: #047857;
}

.inline-alert--error {
  background: rgba(248, 113, 113, 0.12);
  color: #b91c1c;
}

.download-box {
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: #f8fafc;
  border-radius: 16px;
  padding: 18px 20px;
  border: 1px solid rgba(226, 232, 240, 0.8);
}

.download-box__info h3 {
  margin: 0 0 6px;
  font-size: 16px;
  color: #0f172a;
}

.download-box__info p {
  margin: 0;
  color: #475569;
  font-size: 14px;
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

@media (max-width: 640px) {
  .qr-generator {
    padding: 20px 16px;
  }

  .card {
    padding: 22px;
  }

  .form-actions {
    flex-direction: column;
    align-items: stretch;
  }

  .field--wide {
    grid-column: span 1;
  }
}
</style>
