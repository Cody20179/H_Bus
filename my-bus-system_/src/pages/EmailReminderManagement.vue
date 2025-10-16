<template>
  <div class="email-reminder">
    <header class="page-header">
      <div class="page-header__titles">
        <h1>Email Reminder Scheduler</h1>
        <p>Configure the daily reservation reminder email window.</p>
      </div>
      <button
        class="btn btn-run"
        @click="runNow"
        :disabled="running || loading"
      >
        {{ running ? 'Running...' : 'Run Now' }}
      </button>
    </header>

    <section class="card">
        <div class="testing-banner">
          This screen is under active testing. Settings may change without notice.
        </div>
      <div class="card-header">
        <div>
          <h2>Schedule Settings</h2>
          <p>Daily reminders will use these values the next time the job runs.</p>
        </div>
        <span class="status-chip" :class="form.enabled ? 'status-chip--on' : 'status-chip--off'">
          {{ form.enabled ? 'Enabled' : 'Disabled' }}
        </span>
      </div>

      <div class="card-body">
        <div class="form-grid">
          <label class="field">
            <span>Hour</span>
            <input
              type="number"
              min="0"
              max="23"
              v-model.number="form.hour"
            />
          </label>
          <label class="field">
            <span>Minute</span>
            <input
              type="number"
              min="0"
              max="59"
              v-model.number="form.minute"
            />
          </label>
          <label class="field">
            <span>Timezone (IANA)</span>
            <input
              type="text"
              v-model="form.timezone"
              placeholder="Asia/Taipei"
            />
          </label>
        </div>
      </div>

      <div class="card-footer">
        <button
          class="btn btn-secondary"
          type="button"
          @click="toggleEnabled"
          :disabled="saving"
        >
          {{ form.enabled ? 'Disable schedule' : 'Enable schedule' }}
        </button>
        <button
          class="btn btn-primary"
          type="button"
          @click="saveConfig"
          :disabled="saving"
        >
          {{ saving ? 'Saving...' : 'Save changes' }}
        </button>
      </div>

      <div class="meta-list">
        <div class="meta-item">
          <span class="meta-label">Next run</span>
          <span class="meta-value">{{ displayTime(config?.next_run_at) }}</span>
        </div>
        <div class="meta-item">
          <span class="meta-label">Last run</span>
          <span class="meta-value">{{ displayTime(config?.last_run_summary?.started_at || config?.last_run_at) }}</span>
        </div>
        <div class="meta-item" v-if="config?.last_run_summary">
          <span class="meta-label">Last result</span>
          <span class="meta-value">
            {{ formatStatus(config.last_run_summary.status) }}
            (success {{ config.last_run_summary.success_emails }} / failed {{ config.last_run_summary.failed_emails }})
          </span>
        </div>
        <div class="meta-item meta-item--error" v-if="config?.last_error">
          <span class="meta-label">Last error</span>
          <span class="meta-value">{{ config.last_error }}</span>
        </div>
        <div class="meta-item meta-item--info" v-if="runResult">
          <span class="meta-label">Manual run</span>
          <span class="meta-value">
            {{ formatStatus(runResult.status) }}
            <template v-if="runResult.message">- {{ runResult.message }}</template>
            <template v-if="runResult.error">- {{ runResult.error }}</template>
          </span>
        </div>
      </div>

      <transition name="fade">
        <div v-if="notice" class="inline-alert" :class="`inline-alert--${noticeType}`">
          {{ notice }}
        </div>
      </transition>
    </section>
  </div>
</template>

<script setup lang="ts">
import { reactive, ref, onMounted } from 'vue'
import {
  emailReminderApi,
  type EmailReminderConfig,
  type EmailReminderRunResult
} from '../services/api'

type Maybe<T> = T | null | undefined

const loading = ref(true)
const saving = ref(false)
const running = ref(false)

const config = ref<EmailReminderConfig | null>(null)
const runResult = ref<EmailReminderRunResult | null>(null)

const form = reactive({
  enabled: false,
  hour: 8,
  minute: 0,
  timezone: 'Asia/Taipei'
})

const notice = ref('')
const noticeType = ref<'info' | 'success' | 'error'>('info')

function setNotice(message: string, type: 'info' | 'success' | 'error' = 'info') {
  notice.value = message
  noticeType.value = type
  if (message) {
    setTimeout(() => {
      if (notice.value === message) {
        notice.value = ''
      }
    }, 4000)
  }
}

function syncFormFromConfig(value: EmailReminderConfig | null) {
  if (!value) return
  form.enabled = value.enabled
  form.hour = value.hour ?? 8
  form.minute = value.minute ?? 0
  form.timezone = value.timezone || 'Asia/Taipei'
}

function sanitizeForm() {
  form.hour = Math.min(23, Math.max(0, Math.floor(Number(form.hour) || 0)))
  form.minute = Math.min(59, Math.max(0, Math.floor(Number(form.minute) || 0)))
  if (!form.timezone.trim()) {
    form.timezone = 'Asia/Taipei'
  }
}

function displayTime(value: Maybe<string>) {
  if (!value) return '--'
  try {
    const dt = new Date(value)
    if (Number.isNaN(dt.getTime())) return value
    return dt.toLocaleString('en-GB', { hour12: false })
  } catch (error) {
    return value
  }
}

function formatStatus(status?: string) {
  if (!status) return '--'
  const mapping: Record<string, string> = {
    success: 'Success',
    failed: 'Failed',
    partial: 'Partial',
    empty: 'No data',
    running: 'Running',
    busy: 'Running'
  }
  return mapping[status] ?? status
}

async function loadConfig() {
  loading.value = true
  try {
    const data = await emailReminderApi.getConfig()
    config.value = data
    syncFormFromConfig(data)
  } catch (error) {
    console.error('Failed to load email reminder configuration', error)
    setNotice('Failed to load configuration.', 'error')
  } finally {
    loading.value = false
  }
}

async function saveConfig() {
  sanitizeForm()
  saving.value = true
  try {
    const payload = {
      enabled: form.enabled,
      hour: form.hour,
      minute: form.minute,
      timezone: form.timezone
    }
    const data = await emailReminderApi.updateConfig(payload)
    config.value = data
    syncFormFromConfig(data)
    setNotice('Configuration updated successfully.', 'success')
  } catch (error) {
    console.error('Failed to save email reminder configuration', error)
    setNotice('Failed to save configuration.', 'error')
  } finally {
    saving.value = false
  }
}

async function toggleEnabled() {
  form.enabled = !form.enabled
  await saveConfig()
}

async function runNow() {
  running.value = true
  try {
    const response = await emailReminderApi.runNow()
    runResult.value = response.result
    config.value = response.config
    syncFormFromConfig(response.config)
    setNotice('Reminder job triggered.', 'success')
  } catch (error: any) {
    if (error?.response?.status === 409) {
      setNotice('Reminder job is already running.', 'info')
    } else {
      console.error('Failed to trigger reminder job', error)
      setNotice('Unable to start reminder job.', 'error')
    }
  } finally {
    running.value = false
  }
}

onMounted(async () => {
  await loadConfig()
})
</script>

<style scoped>
.email-reminder {
  display: flex;
  flex-direction: column;
  gap: 28px;
  padding: 32px 24px;
  max-width: 900px;
  width: 100%;
  margin: 0 auto;
  box-sizing: border-box;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  background: linear-gradient(135deg, #1f2937 0%, #0f172a 100%);
  color: #fff;
  padding: 28px 32px;
  border-radius: 24px;
  box-shadow: 0 20px 40px rgba(15, 23, 42, 0.25);
  width: 100%;
  box-sizing: border-box;
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

.btn-run {
  background: rgba(255, 255, 255, 0.12);
  color: #fff;
  border: 1px solid rgba(255, 255, 255, 0.25);
  border-radius: 999px;
  padding: 10px 22px;
  font-weight: 600;
  cursor: pointer;
  transition: background 0.2s ease, opacity 0.2s ease;
}

.btn-run:hover:not(:disabled) {
  background: rgba(255, 255, 255, 0.18);
}

.card {
  background: #ffffff;
  border-radius: 24px;
  box-shadow: 0 16px 40px rgba(15, 23, 42, 0.12);
  overflow: hidden;
  display: flex;
  flex-direction: column;
  width: 100%;
  box-sizing: border-box;
}

.testing-banner {
  width: 100%;
  margin: 0 32px 18px;
  padding: 14px 18px;
  border-radius: 12px;
  background: rgba(239, 68, 68, 0.12);
  border: 1px solid rgba(239, 68, 68, 0.35);
  color: #991b1b;
  font-weight: 600;
  line-height: 1.4;
  box-sizing: border-box;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 26px 32px 16px;
  border-bottom: 1px solid rgba(148, 163, 184, 0.18);
}

.card-header h2 {
  margin: 0;
  font-size: 20px;
  color: #0f172a;
}

.card-header p {
  margin: 6px 0 0;
  color: #64748b;
  font-size: 14px;
}

.card-body {
  padding: 0 32px 28px;
}

.form-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(160px, 1fr));
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

.card-footer {
  padding: 20px 32px;
  display: flex;
  gap: 14px;
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
  cursor: not-allowed;
  opacity: 0.6;
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

.status-chip {
  padding: 6px 14px;
  border-radius: 999px;
  font-size: 13px;
  font-weight: 600;
}

.status-chip--on {
  background: rgba(22, 163, 74, 0.1);
  color: #15803d;
}

.status-chip--off {
  background: rgba(220, 38, 38, 0.1);
  color: #b91c1c;
}

.meta-list {
  padding: 0 32px 32px;
  display: grid;
  grid-template-columns: repeat(2, minmax(220px, 1fr));
  gap: 20px;
}

.meta-item {
  background: #f8fafc;
  border-radius: 16px;
  padding: 16px 18px;
  display: flex;
  flex-direction: column;
  gap: 6px;
  border: 1px solid rgba(226, 232, 240, 0.7);
}

.meta-item--error {
  border-color: rgba(239, 68, 68, 0.45);
  background: rgba(254, 226, 226, 0.7);
}

.meta-item--info {
  border-color: rgba(59, 130, 246, 0.25);
  background: rgba(219, 234, 254, 0.6);
}

.meta-label {
  font-size: 12px;
  font-weight: 600;
  color: #475569;
  text-transform: uppercase;
  letter-spacing: 0.08em;
}

.meta-value {
  font-size: 15px;
  color: #1f2937;
}

.inline-alert {
  margin: 0 32px 28px;
  padding: 16px 18px;
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
  background: rgba(248, 113, 113, 0.16);
  color: #b91c1c;
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

@media (max-width: 768px) {
  .email-reminder {
    padding: 20px 16px;
  }

  .page-header {
    padding: 24px;
    flex-direction: column;
    align-items: flex-start;
    gap: 16px;
  }

  .card-header,
  .card-body,
  .card-footer,
  .meta-list {
    padding-left: 24px;
    padding-right: 24px;
  }

  .form-grid {
    grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
  }

  .meta-list {
    grid-template-columns: 1fr;
  }

  .card-footer {
    flex-direction: column;
    align-items: stretch;
  }
}
</style>

