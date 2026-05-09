# 前端待完成功能清单

> 基于 Tech-design.md + PRD + 后端 API 实现 vs 当前前端代码的差距分析
> 生成时间：2026-05-09

---

## 已完成项 (no action needed)

| # | 功能 | 文件 | 状态 |
|---|------|------|------|
| ✓ | 左右分栏布局 (420px + flex-1) | `App.vue` | 完成 |
| ✓ | JD textarea + 提交按钮 + 错误提示 | `UploadPanel.vue` | 完成 |
| ✓ | PDF 点击上传 (accept=".pdf") | `UploadPanel.vue` | 完成 |
| ✓ | 总分数值展示 | `ResultBoard.vue` | 完成 |
| ✓ | ECharts 雷达图 (维度可视化) | `RadarChart.vue` | 完成 |
| ✓ | 维度评分卡片 (含 reason) | `ResultBoard.vue` | 完成 |
| ✓ | 缺失技能标签云 | `ResultBoard.vue` | 完成 |
| ✓ | 风险提示列表 | `ResultBoard.vue` | 完成 |
| ✓ | 深度抽取展示 (技能/工作/项目/教育/证书/语言) | `ResultBoard.vue` | 完成 |
| ✓ | 候选人基本信息网格 | `ResultBoard.vue` | 完成 |
| ✓ | AI 分析摘要卡片 | `ResultBoard.vue` | 完成 |
| ✓ | TypeScript 类型对齐后端 Pydantic | `types.ts` | 完成 |
| ✓ | Axios 实例 (60s timeout, 拦截器) | `api.ts` | 完成 |
| ✓ | useAnalyzer 组合式函数 | `useAnalyzer.ts` | 完成 |

---

## P0 — 核心链路缺失 (必须修，影响基础使用)

### 1. 前端文件校验 (客户端侧)

- **现状**：只设了 `accept=".pdf"`，没有 JS 侧校验。后端会拦截并返回 400，但用户已浪费上传时间
- **后端约束**：`MAX_FILE_SIZE=10MB`, `ALLOWED_EXTENSIONS={".pdf"}`, `MIN_JD_LENGTH=10`
- **PRD 要求**：PRD 第 8 节明确列出"文件异常拦截"场景
- **改动**：`UploadPanel.vue` — `onFileChange()` 中增加扩展名和大小校验
  ```ts
  // 伪代码
  if (!file.name.toLowerCase().endsWith('.pdf')) → show error "仅支持PDF格式"
  if (file.size > 10 * 1024 * 1024) → show error "文件超过10MB限制"
  if (jdText.value.trim().length < 10) → 禁用提交 + 提示
  ```

### 2. 错误码分类展示

- **现状**：所有错误统一显示 `e?.message`，用户无法区分是"文件格式问题"还是"服务器故障"
- **后端错误码**：

  | HTTP | Error Class | 含义 |
  |------|------------|------|
  | 400 | FileValidationError | 文件格式/大小/JD过短 |
  | 422 | PdfParseError | PDF 解析失败 |
  | 422 | ScannedPdfError | 扫描件不支持 |
  | 500 | LLMCallError | AI 调用失败 |
  | 500 | OSSUploadError | 文件存储失败 |
  | 500 | CacheError | 缓存异常 |

- **改动**：
  - `api.ts` — 响应拦截器中提取 `response.data.code` 和 `message`，构造有意义错误对象
  - `UploadPanel.vue` — 按错误类型显示不同 UI 样式 (warning/error)

### 3. raw_json 折叠面板展示

- **现状**：`raw_json` 字段在 types.ts 和 schemas.py 中定义，后端会返回，但前端不渲染
- **PRD 要求**："底部折叠面板（Accordion）：展示 AI 抽取的完整 JSON 结构数据，方便开发者/验收者查看底层结果"
- **改动**：`ResultBoard.vue` — 在页面底部新增可折叠区域
  ```vue
  <details class="mt-4 bg-gray-50 rounded-lg p-4">
    <summary class="cursor-pointer text-sm font-medium text-gray-500">
      Raw JSON (AI Extraction)
    </summary>
    <pre class="mt-2 text-xs text-gray-600 overflow-x-auto">{{ JSON.stringify(result.data.raw_json, null, 2) }}</pre>
  </details>
  ```

---

## P1 — 高价值改善 (提升体验，与设计稿对齐)

### 4. 圆形进度条 (Circular Progress)

- **现状**：匹配分数是大号纯数字显示
- **PRD 要求**："顶部卡片：核心看板（候选人姓名 + 圆形进度条展示匹配度分数）"
- **改动**：`ResultBoard.vue` — 替换数字显示为 SVG 环形进度条组件
  ```vue
  <svg viewBox="0 0 100 100" class="w-32 h-32">
    <circle cx="50" cy="50" r="42" fill="none" stroke="#e5e7eb" stroke-width="8" />
    <circle cx="50" cy="50" r="42" fill="none" stroke="#3b82f6" stroke-width="8"
      :stroke-dasharray="2 * Math.PI * 42"
      :stroke-dashoffset="2 * Math.PI * 42 * (1 - score / 100)"
      stroke-linecap="round" transform="rotate(-90 50 50)" />
    <text x="50" y="55" text-anchor="middle" class="text-2xl font-bold" fill="currentColor">
      {{ score }}
    </text>
  </svg>
  ```

### 5. 文件拖拽上传 (Drag & Drop)

- **现状**：只有 `<input type="file">` 点击上传，label 样式模拟了拖拽区外观但没有真正的 DnD
- **PRD**："拖拽式的文件上传组件"
- **改动**：`UploadPanel.vue` — 增加 dragenter/dragover/dragleave/drop 事件处理
  ```ts
  const isDragging = ref(false)
  function onDrop(e: DragEvent) {
    e.preventDefault()
    isDragging.value = false
    const f = e.dataTransfer?.files?.[0]
    if (f) { file.value = f; fileName.value = f.name }
  }
  ```

### 6. shadcn-vue UI 组件接入

- **现状**：`components/ui/` 目录为空，所有 UI 都是手写 HTML + Tailwind
- **Tech-design 明确要求**："UI 组件库: shadcn-vue（代码级引入，高度可定制，AI 生成 UI 成功率极高）"
- **改动**：
  1. 安装 `shadcn-vue` 依赖
  2. 替换以下组件为 shadcn-vue：Button (提交按钮)、Card (结果卡片)、Progress (进度条)、Badge (技能标签)、Accordion (raw_json 折叠)、Textarea (JD 输入)

### 7. 独立上传模式 (`POST /api/v1/upload`)

- **现状**：前端只使用 `/api/v1/analyze` 一个端点
- **后端提供**：`POST /api/v1/upload` — 仅 PDF 上传 + 文本提取，返回 `{filename, text_length, text_preview, raw_text}`
- **PRD P0**："RESTful API: /api/upload (单 PDF 上传及基础文本提取)"
- **改动**：
  - `types.ts` — 新增 `UploadResult` 接口
  - `useAnalyzer.ts` 或新的 `useUploader.ts` — 新增 `upload()` 方法调 `/upload`
  - 可选：`UploadPanel.vue` 增加"仅上传解析"快速模式按钮

### 8. 加载状态增强

- **现状**：只有 `<p class="animate-pulse">Analyzing resume...</p>`
- **PRD P2**："友好的前端加载动画（Skeleton 骨架屏）"
- **改动**：`ResultBoard.vue` —加载时展示 Skeleton 卡片占位
  ```vue
  <div v-if="loading" class="space-y-6 animate-pulse">
    <div class="h-24 bg-gray-200 rounded-xl" />
    <div class="h-48 bg-gray-200 rounded-xl" />
    <div class="h-32 bg-gray-200 rounded-xl" />
  </div>
  ```

### 9. 重置/清空功能

- **现状**：`useAnalyzer` 有 `reset()` 方法但 UI 中未暴露
- **改动**：
  - `UploadPanel.vue` — 结果返回后显示"重新分析"按钮
  - `ResultBoard.vue` — 非空状态下顶部有返回按钮

---

## P2 — 加分项与优化 (锦上添花)

### 10. 响应式布局

- **现状**：固定 420px 左侧栏，移动端完全不可用
- **改动**：`App.vue` — 添加 Tailwind 响应式断点
  ```html
  <aside class="w-full lg:w-[420px] ...">
  <main class="hidden lg:block flex-1 ...">
  ```

### 11. 上传进度指示

- **现状**：无文件上传进度
- **改动**：使用 Axios `onUploadProgress` 回调显示上传百分比

### 12. 多 JD 对比缓存提示

- **现状**：后端有 MD5 缓存，但前端无感知
- **改动**：若后端返回速度极快（<1s 且非首次上传），可显示 "此简历曾被分析过，结果来自缓存"

### 13. 二维码/分享

- **现状**：无
- **PRD 潜在用户**："求职者自测简历匹配度"
- **改动**：结果页尾部增加"分享报告"按钮，生成独立链接或截图

---

## 文件改动汇总

| 文件 | P0 | P1 | P2 | 操作说明 |
|------|:--:|:--:|:--:|----------|
| `UploadPanel.vue` | ✓ | ✓ | ✓ | 文件校验 / 拖拽 / 重置 / JD长度提示 |
| `ResultBoard.vue` | ✓ | ✓ | ✓ | raw_json折叠 / 圆形进度条 / Skeleton / 重置 |
| `api.ts` | ✓ | - | - | 错误拦截器分类处理 |
| `types.ts` | - | ✓ | - | 新增 UploadResult 类型 |
| `RadarChart.vue` | - | - | ✓ | 无维度数据时空状态 |
| `App.vue` | - | - | ✓ | 响应式布局 |
| `useAnalyzer.ts` | - | ✓ | - | 新增 upload 方法 + 进度状态 |
| `components/ui/*` | - | ✓ | - | shadcn-vue 组件初始化 |
| `formatters.ts` | - | - | ✓ | bytesToMB 实际接入使用 |

---

## SESSION_ID

- CODEX_SESSION: N/A (CLI not available)
- GEMINI_SESSION: N/A (CLI not available)
- FALLBACK: Manual analysis by Claude — no session resume available
