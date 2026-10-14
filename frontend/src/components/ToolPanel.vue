<template>
  <div class="tool-panel">
    <!-- 顶部：数据集状态与上传 -->
    <div class="panel-header">
      <span class="panel-title">🧰 数据分析工具箱</span>
      <div class="dataset-bar">
        <span v-if="dataset.loaded" class="dataset-info">
          已加载 <b>{{ dataset.rows }}</b> 行 × <b>{{ dataset.column_count }}</b> 列
        </span>
        <span v-else class="dataset-info muted">尚未上传数据集</span>
        <label class="upload-btn">
          {{ uploading ? '上传中…' : '上传数据 (CSV/XLSX)' }}
          <input type="file" accept=".csv,.xlsx,.xls" hidden :disabled="uploading" @change="onFilePicked" />
        </label>
      </div>
    </div>

    <div class="panel-body">
      <!-- 左：工具列表 -->
      <div class="tool-list">
        <input v-model="keyword" class="search-input" type="text" placeholder="搜索工具…" />

        <div v-for="stage in filteredStages" :key="stage.stage_id" class="stage">
          <div class="stage-name">{{ stage.stage_name }}</div>
          <div v-for="sub in stage.sub_categories" :key="sub.sub_category_id" class="sub-category">
            <div class="sub-name">{{ sub.sub_category_name }}</div>
            <div
              v-for="tool in sub.tools"
              :key="tool.name"
              class="tool-item"
              :class="{ active: selectedTool && selectedTool.name === tool.name }"
              @click="selectTool(tool)"
            >
              <span class="tool-name">{{ tool.display_name || tool.name }}</span>
              <span class="tool-code">{{ tool.name }}</span>
            </div>
          </div>
        </div>

        <div v-if="!filteredStages.length" class="empty-hint">没有匹配的工具</div>
      </div>

      <!-- 右：参数与结果 -->
      <div class="tool-detail">
        <template v-if="selectedTool">
          <div class="detail-title">{{ selectedTool.display_name }}</div>
          <div class="detail-desc">{{ selectedTool.description }}</div>
          <div class="detail-code">函数名：{{ selectedTool.name }}</div>

          <div class="param-form">
            <div v-if="!selectedTool.parameters.length" class="no-param">该工具无需参数</div>

            <div v-for="p in selectedTool.parameters" :key="p.name" class="param-row">
              <label class="param-label">
                {{ p.label || p.name }}
                <span v-if="p.required" class="required">*</span>
              </label>

              <!-- 数值 -->
              <input
                v-if="p.type === 'number'"
                v-model.number="paramValues[p.name]"
                type="number"
                class="param-input"
              />

              <!-- 下拉单选 -->
              <select v-else-if="p.type === 'select'" v-model="paramValues[p.name]" class="param-input">
                <option v-for="opt in selectOptions(p)" :key="opt.value" :value="opt.value">
                  {{ opt.label }}
                </option>
              </select>

              <!-- 多选列 -->
              <div v-else-if="p.type === 'multi_select'" class="multi-select">
                <label v-for="col in dataset.columns" :key="col" class="checkbox-item">
                  <input type="checkbox" :value="col" v-model="paramValues[p.name]" />
                  <span>{{ col }}</span>
                </label>
                <div v-if="!dataset.columns.length" class="hint">请先上传数据集以获取列名</div>
              </div>

              <!-- 列名映射（JSON） -->
              <textarea
                v-else-if="p.type === 'mapping'"
                v-model="paramValues[p.name]"
                class="param-input mono"
                rows="3"
                placeholder='{"旧列名": "新列名"}'
              ></textarea>

              <!-- 文本 -->
              <input v-else v-model="paramValues[p.name]" type="text" class="param-input" />

              <div v-if="p.description" class="param-hint">{{ p.description }}</div>
            </div>
          </div>

          <div class="actions">
            <button class="run-btn" :disabled="running" @click="executeTool">
              {{ running ? '执行中…' : '执行' }}
            </button>
            <button class="reset-btn" :disabled="running" @click="resetParams">重置参数</button>
          </div>
        </template>

        <div v-else class="empty-hint">从左侧选择一个工具开始</div>

        <!-- 错误 -->
        <div v-if="errorMsg" class="result-box error">{{ errorMsg }}</div>

        <!-- 结果 -->
        <div v-if="result" class="result-box">
          <div class="result-title">执行结果</div>

          <template v-for="(item, key) in flatResults" :key="key">
            <div class="result-block">
              <div class="result-key">{{ key || 'result' }}</div>

              <img v-if="item.kind === 'image'" :src="item.src" class="result-image" alt="分析图表" />

              <div v-else-if="item.kind === 'file'" class="result-file">
                已生成文件：<a :href="item.src" target="_blank" rel="noopener">{{ item.name }}</a>
                <button
                  v-if="isTabular(item.name)"
                  class="adopt-btn"
                  :disabled="adopting === item.name"
                  @click="adoptResult(item.name)"
                >
                  {{ adopting === item.name ? '处理中…' : '设为此会话数据集' }}
                </button>
                <div class="hint">
                  {{ isTabular(item.name)
                    ? '点「设为此会话数据集」即可把它作为下一步分析的输入，无需手动下载再上传。'
                    : '该结果保存在服务器 out_file 目录。' }}
                </div>
              </div>

              <table v-else-if="item.kind === 'table'" class="result-table">
                <thead>
                  <tr><th v-for="h in item.headers" :key="h">{{ h }}</th></tr>
                </thead>
                <tbody>
                  <tr v-for="(row, i) in item.rows" :key="i">
                    <td v-for="h in item.headers" :key="h">{{ row[h] }}</td>
                  </tr>
                </tbody>
              </table>

              <pre v-else class="result-json">{{ item.text }}</pre>
            </div>
          </template>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { apiFetch } from '../utils/api'

const emit = defineEmits(['notify'])

const stages = ref([])
const keyword = ref('')
const dataset = ref({ loaded: false, rows: 0, column_count: 0, columns: [], numeric_columns: [] })
const uploading = ref(false)
const selectedTool = ref(null)
const paramValues = reactive({})
const running = ref(false)
const result = ref(null)
const errorMsg = ref('')
const adopting = ref('')

/** 是否为表格类产物（可设回数据集） */
function isTabular(name) {
  return /\.(csv|xlsx|xls)$/i.test(name || '')
}

const filteredStages = computed(() => {
  const kw = keyword.value.trim().toLowerCase()
  if (!kw) return stages.value

  return stages.value
    .map((stage) => ({
      ...stage,
      sub_categories: stage.sub_categories
        .map((sub) => ({
          ...sub,
          tools: sub.tools.filter((t) =>
            [t.name, t.display_name, t.description]
              .filter(Boolean)
              .some((v) => String(v).toLowerCase().includes(kw))
          )
        }))
        .filter((sub) => sub.tools.length)
    }))
    .filter((stage) => stage.sub_categories.length)
})

function selectOptions(param) {
  if (param.options && param.options.length) return param.options

  // 未显式声明选项时，用数据集的列名作为候选（如 column / x_column / y_column）
  const useColumns = param.name && /column|target|y_true|y_pred/i.test(param.name)
  const cols = useColumns ? dataset.value.columns : []
  return cols.map((c) => ({ label: c, value: c }))
}

function notify(text) {
  emit('notify', text)
}

async function loadTools() {
  try {
    const res = await apiFetch('/api/tools')
    const data = await res.json()
    if (data.status === 'success') {
      stages.value = data.data
    } else {
      errorMsg.value = `工具列表加载失败：${data.message || '未知错误'}`
    }
  } catch (e) {
    errorMsg.value = `工具列表加载失败：${e.message}`
  }
}

async function loadDataset() {
  try {
    const res = await apiFetch('/api/data/info')
    const data = await res.json()
    if (data.status === 'success') {
      dataset.value = data.data
    }
  } catch (e) {
    console.warn('获取数据集信息失败:', e)
  }
}

async function onFilePicked(event) {
  const file = event.target.files && event.target.files[0]
  event.target.value = ''
  if (!file) return

  uploading.value = true
  errorMsg.value = ''
  try {
    const form = new FormData()
    form.append('file', file)
    const res = await apiFetch('/api/upload', { method: 'POST', body: form })
    const data = await res.json()
    if (data.status === 'success') {
      await loadDataset()
      notify(`>>> 数据集已上传：${file.name}（${dataset.value.rows} 行）`)
    } else {
      errorMsg.value = data.message || '上传失败'
    }
  } catch (e) {
    errorMsg.value = `上传失败：${e.message}`
  } finally {
    uploading.value = false
  }
}

function defaultFor(param) {
  if (param.type === 'multi_select') return Array.isArray(param.default) ? [...param.default] : []
  if (param.type === 'mapping') {
    return typeof param.default === 'object' && param.default
      ? JSON.stringify(param.default)
      : '{}'
  }
  return param.default !== undefined ? param.default : ''
}

function selectTool(tool) {
  selectedTool.value = tool
  result.value = null
  errorMsg.value = ''
  resetParams()
}

function resetParams() {
  Object.keys(paramValues).forEach((k) => delete paramValues[k])
  if (!selectedTool.value) return
  for (const p of selectedTool.value.parameters || []) {
    paramValues[p.name] = defaultFor(p)
  }
}

async function executeTool() {
  if (!selectedTool.value) return

  running.value = true
  errorMsg.value = ''
  result.value = null

  try {
    // 参数按 methodConfig 约定提交（后端同时兼容顶层写法）
    const payload = { methodConfig: {} }
    for (const p of selectedTool.value.parameters || []) {
      let value = paramValues[p.name]

      if (p.type === 'mapping') {
        try {
          value = value && String(value).trim() ? JSON.parse(value) : {}
        } catch {
          throw new Error(`参数「${p.label || p.name}」不是合法 JSON`)
        }
      }
      if (p.type === 'multi_select' && (!value || !value.length)) {
        if (p.required) throw new Error(`参数「${p.label || p.name}」为必填项`)
        continue
      }
      if (p.required && (value === '' || value === null || value === undefined)) {
        throw new Error(`参数「${p.label || p.name}」为必填项`)
      }
      payload.methodConfig[p.name] = value
    }

    const res = await apiFetch(`/api/tools/${selectedTool.value.name}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    })
    const data = await res.json()

    if (data.status === 'success') {
      result.value = data.result
      notify(`>>> 工具 ${selectedTool.value.name} 执行成功`)
      await loadDataset()   // 部分工具会改动数据集，刷新列信息
    } else {
      errorMsg.value = data.message || '执行失败'
      notify(`>>> 工具 ${selectedTool.value.name} 执行失败：${data.message || ''}`)
    }
  } catch (e) {
    errorMsg.value = e.message
  } finally {
    running.value = false
  }
}

/** 把分析产物设为当前会话数据集，以便串联下一步分析 */
async function adoptResult(filename) {
  adopting.value = filename
  errorMsg.value = ''
  try {
    const res = await apiFetch('/api/data/adopt', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ filename })
    })
    const data = await res.json()

    if (data.status === 'success') {
      dataset.value = { ...dataset.value, ...data.data }
      await loadDataset()
      notify(`>>> 已将 ${filename} 设为当前数据集（${data.data.rows} 行 × ${data.data.column_count} 列）`)
    } else {
      errorMsg.value = data.message || '设为数据集失败'
    }
  } catch (e) {
    errorMsg.value = `设为数据集失败：${e.message}`
  } finally {
    adopting.value = ''
  }
}

/** 把工具返回的嵌套结果摊平为可渲染的块 */
const flatResults = computed(() => {
  const out = {}
  const walk = (value, path) => {
    if (value === null || value === undefined) return

    if (Array.isArray(value)) {
      const looksLikeRecords =
        value.length && value.every((v) => v && typeof v === 'object' && !Array.isArray(v))
      if (looksLikeRecords) {
        const headers = Array.from(new Set(value.flatMap((r) => Object.keys(r))))
        out[path] = { kind: 'table', headers, rows: value }
      } else {
        out[path] = { kind: 'json', text: JSON.stringify(value, null, 2) }
      }
      return
    }

    if (typeof value === 'object') {
      if (value._type === 'image' && value.path) {
        out[path] = { kind: 'image', src: value.path }
        return
      }
      if (value._type === 'file' && value.path) {
        out[path] = {
          kind: 'file',
          src: value.path === 'updated' ? '#' : value.path,
          name: value.filename || value.path
        }
        return
      }
      if (value._type === 'series') {
        out[path] = { kind: 'json', text: JSON.stringify(value.data, null, 2) }
        return
      }
      for (const [k, v] of Object.entries(value)) {
        walk(v, path ? `${path}.${k}` : k)
      }
      return
    }

    out[path] = { kind: 'json', text: String(value) }
  }

  walk(result.value, '')
  return out
})

onMounted(async () => {
  await loadTools()
  await loadDataset()
})
</script>

<style scoped>
.tool-panel {
  display: flex;
  flex-direction: column;
  height: 100%;
  background-color: #1e1e1e;
  color: #cccccc;
  font-size: 13px;
}

.panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 8px 12px;
  background-color: #252526;
  border-bottom: 1px solid #3c3c3c;
  flex-shrink: 0;
}

.panel-title { font-weight: 600; }

.dataset-bar { display: flex; align-items: center; gap: 10px; }
.dataset-info { font-size: 12px; color: #9cdcfe; }
.dataset-info.muted { color: #888; }

.upload-btn {
  padding: 4px 10px;
  background-color: #007acc;
  color: #fff;
  border-radius: 3px;
  cursor: pointer;
  font-size: 12px;
}
.upload-btn:hover { background-color: #006bb3; }

.panel-body {
  display: flex;
  flex: 1;
  min-height: 0;
}

.tool-list {
  width: 260px;
  flex-shrink: 0;
  overflow-y: auto;
  border-right: 1px solid #3c3c3c;
  padding: 8px;
}

.search-input {
  width: 100%;
  box-sizing: border-box;
  padding: 5px 8px;
  margin-bottom: 8px;
  background-color: #3c3c3c;
  border: 1px solid #454545;
  border-radius: 3px;
  color: #ddd;
  font-size: 12px;
}
.search-input:focus { outline: none; border-color: #007acc; }

.stage-name {
  margin: 10px 0 4px;
  font-size: 11px;
  letter-spacing: 0.5px;
  color: #6a9955;
  text-transform: uppercase;
}

.sub-name { margin: 6px 0 2px; font-size: 12px; color: #ababab; }

.tool-item {
  display: flex;
  flex-direction: column;
  padding: 5px 8px;
  border-radius: 3px;
  cursor: pointer;
}
.tool-item:hover { background-color: #2a2d2e; }
.tool-item.active { background-color: #094771; }

.tool-name { color: #dcdcaa; }
.tool-code { font-size: 10px; color: #666; }

.tool-detail {
  flex: 1;
  min-width: 0;
  overflow-y: auto;
  padding: 12px 16px;
}

.detail-title { font-size: 15px; font-weight: 600; color: #fff; }
.detail-desc { margin: 6px 0; color: #9d9d9d; line-height: 1.6; }
.detail-code { font-size: 11px; color: #666; margin-bottom: 12px; }

.param-form { margin: 12px 0; }
.no-param { color: #777; font-size: 12px; }

.param-row { margin-bottom: 12px; }
.param-label { display: block; margin-bottom: 4px; font-size: 12px; color: #ce9178; }
.required { color: #f48771; }

.param-input {
  width: 100%;
  max-width: 420px;
  box-sizing: border-box;
  padding: 5px 8px;
  background-color: #3c3c3c;
  border: 1px solid #454545;
  border-radius: 3px;
  color: #ddd;
  font-size: 12px;
}
.param-input:focus { outline: none; border-color: #007acc; }
.param-input.mono { font-family: Consolas, Monaco, monospace; }

.param-hint { margin-top: 3px; font-size: 11px; color: #666; }

.multi-select {
  display: flex;
  flex-wrap: wrap;
  gap: 4px 12px;
  max-height: 160px;
  overflow-y: auto;
  padding: 6px 8px;
  background-color: #252526;
  border: 1px solid #454545;
  border-radius: 3px;
}
.checkbox-item { display: flex; align-items: center; gap: 4px; font-size: 12px; cursor: pointer; }

.actions { display: flex; gap: 8px; margin: 16px 0; }

.run-btn, .reset-btn {
  padding: 6px 18px;
  border: none;
  border-radius: 3px;
  cursor: pointer;
  font-size: 13px;
}
.run-btn { background-color: #007acc; color: #fff; }
.run-btn:hover:not(:disabled) { background-color: #006bb3; }
.reset-btn { background-color: #3c3c3c; color: #ccc; }
.reset-btn:hover:not(:disabled) { background-color: #4a4a4a; }
.run-btn:disabled, .reset-btn:disabled { opacity: 0.5; cursor: not-allowed; }

.result-box {
  margin-top: 16px;
  padding: 12px;
  background-color: #252526;
  border: 1px solid #3c3c3c;
  border-radius: 4px;
}
.result-box.error { border-color: #a1260d; color: #f48771; background-color: #2d1a18; }

.result-title { font-weight: 600; margin-bottom: 10px; color: #fff; }
.result-block { margin-bottom: 14px; }
.result-key { font-size: 11px; color: #569cd6; margin-bottom: 4px; }

.result-image { max-width: 100%; border-radius: 4px; background: #fff; }
.result-file a { color: #4ec9b0; }

.adopt-btn {
  margin-left: 10px;
  padding: 3px 10px;
  background-color: #0e639c;
  color: #fff;
  border: none;
  border-radius: 3px;
  cursor: pointer;
  font-size: 12px;
}
.adopt-btn:hover:not(:disabled) { background-color: #1177bb; }
.adopt-btn:disabled { opacity: 0.5; cursor: not-allowed; }

.result-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 12px;
  max-height: 320px;
  display: block;
  overflow: auto;
}
.result-table th, .result-table td {
  border: 1px solid #3c3c3c;
  padding: 4px 8px;
  text-align: left;
  white-space: nowrap;
}
.result-table th { background-color: #2d2d2d; color: #dcdcaa; position: sticky; top: 0; }

.result-json {
  margin: 0;
  padding: 8px;
  background-color: #1e1e1e;
  border-radius: 3px;
  font-size: 12px;
  max-height: 320px;
  overflow: auto;
  white-space: pre-wrap;
  word-break: break-word;
}

.empty-hint { padding: 20px; color: #777; font-size: 12px; }
.hint { margin-top: 4px; font-size: 11px; color: #777; }
</style>
