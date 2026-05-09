# 📋 实施计划：异步分析重构

## 任务类型
- [x] 全栈 (后端 + 前端并行改造)

## 技术方案

采用 **两阶段演进**：
- **第一阶段（当前）**：用 `asyncio.create_task` 实现轻量异步，适合单机部署 MVP
- **第二阶段（后续）**：引入 Redis Queue + 独立 Worker，适合生产多实例部署

核心思路：将 `/api/v1/analyze` 拆分为两阶段

```
Phase 1 (同步 <2s):  PDF提取 → Regex基本信息 → 规则匹配 → 立即返回 + task_id
Phase 2 (异步后台):  LLM深度提取 → LLM Rubric评分 → 写入缓存 → 前端轮询获取
```

**新增 API 端点**：
- `GET /api/v1/analyze/tasks/{task_id}` — 查询异步任务状态和结果

**修改 API 端点**：
- `POST /api/v1/analyze` — 返回值从完整 `AnalysisResponse` 改为含 `task_id` 的部分结果

### 新 API 合约设计

**POST /api/v1/analyze 新返回（Phase 1 完成时）**：
```json
{
  "code": 200,
  "message": "基本信息提取完成，深度分析已启动",
  "data": {
    "task_id": "uuid-string",
    "status": "running",
    "candidate_info": { "name": "", "phone": "", ... },
    "rule_match": {
      "overall_score": 72,
      "dimensions": [...],
      "risk_tips": [...]
    }
  }
}
```

**GET /api/v1/analyze/tasks/{task_id} 处理中**：
```json
{
  "code": 200,
  "data": {
    "task_id": "uuid-string",
    "status": "running",
    "phase": "llm_scoring",
    "result": null
  }
}
```

**GET /api/v1/analyze/tasks/{task_id} 完成**：
```json
{
  "code": 200,
  "data": {
    "task_id": "uuid-string",
    "status": "succeeded",
    "result": {
      "candidate_info": {...},
      "overall_score": 86,
      "summary": "...",
      "dimensions": [...],
      "missing_skills": [...],
      "risk_tips": [...],
      "deep_extraction": {...},
      "raw_json": {...}
    }
  }
}
```

## 实施步骤

### Step 1：后端 Schema 层 → 新增异步相关模型

**文件**：`backend/models/schemas.py`
**操作**：追加新 Pydantic 模型

```python
# 任务状态枚举
class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    EXPIRED = "expired"

# Phase 1 快速响应
class QuickAnalysisData(BaseModel):
    task_id: str
    status: str = "running"
    candidate_info: CandidateInfo
    rule_match: dict  # { overall_score, dimensions, risk_tips }

# 任务状态查询响应
class TaskResultData(BaseModel):
    task_id: str
    status: str  # pending/running/succeeded/failed/expired
    phase: str = ""  # llm_extraction / llm_scoring
    result: AnalysisData | None = None
    error: str | None = None
```

### Step 2：后端缓存层 → 扩展支持任务状态

**文件**：`backend/services/cache_service.py`
**操作**：追加任务状态缓存方法

```python
TASK_TTL = 900  # 15min，异步任务结果

async def set_task_state(task_id: str, state: dict, ttl: int = TASK_TTL) -> None:
    """存储异步任务状态到 Redis + Memory"""
    key = f"task:{task_id}"

async def get_task_state(task_id: str) -> dict | None:
    """从 Redis/Memory 获取任务状态"""

async def set_final_result(file_md5: str, jd_text: str, result: dict) -> None:
    """最终完整结果写入 resume:{md5}:{jd_md5}:final"""

async def get_final_result(file_md5: str, jd_text: str) -> dict | None:
    """检查是否已有完成的结果（幂等复用）"""
```

### Step 3：后端核心重构 → analyze.py 拆分为两阶段

**文件**：`backend/api/v1/analyze.py`
**操作**：重构 `analyze_resume` + 新增后台任务 + 新增轮询端点

**伪代码**：

```python
import uuid
from models.schemas import QuickAnalysisData, TaskResultData

@router.post("/analyze")
async def analyze_resume(file, jd_text):
    # ── Phase 1: 快速同步返回 ──
    # 1. 校验文件 + JD（不变）
    file_bytes = await file.read()
    validate_file(file, file_bytes)
    jd_text = jd_text.strip()

    # 2. 计算 MD5 + 检查是否已有完整缓存
    file_md5 = pdf_service.compute_md5_bytes(file_bytes)
    cached = await cache_service.get_final_result(file_md5, jd_text)
    if cached:
        return AnalysisResponse(code=200, message="解析成功（缓存）", data=cached)

    # 3. 检查是否有正在执行的任务（幂等）
    existing_task = await cache_service.get_task_index(file_md5, jd_text)
    if existing_task:
        task_state = await cache_service.get_task_state(existing_task)
        if task_state and task_state["status"] in ("pending", "running"):
            # 返回已有 task_id, 避免重复创建任务
            return _build_quick_response(existing_task, ...)

    # 4. PDF 提取 + 清洗 + 扫描检测（不变）
    raw_text = await pdf_service.extract_text(tmp_path)
    cleaned_text = pdf_service.clean_text(raw_text)
    if pdf_service.is_scanned_pdf(cleaned_text):
        raise ScannedPdfError(...)

    # 5. Regex 快速提取基本信息（不调用 LLM）
    basic_info = _regex_extract(cleaned_text)  # 已有函数
    candidate_info = CandidateInfo(
        name=basic_info.get("name", ""),
        phone=basic_info.get("phone", ""),
        email=basic_info.get("email", ""),
        address=basic_info.get("address", ""),
    )

    # 6. 规则匹配（纯 CPU，无 LLM）
    rule_match = match_service.calculate_rule_match(cleaned_text, jd_text)

    # 7. 生成 task_id，写入任务状态
    task_id = str(uuid.uuid4())
    await cache_service.set_task_state(task_id, {
        "status": "pending",
        "phase": "",
        "cleaned_text": cleaned_text,
        "jd_text": jd_text,
        "file_md5": file_md5,
    })
    await cache_service.set_task_index(file_md5, jd_text, task_id)

    # 8. 启动后台异步任务
    asyncio.create_task(_run_deep_analysis(task_id, cleaned_text, jd_text, file_md5))

    # 9. 立即返回 Phase 1 结果
    return {
        "code": 200,
        "message": "基本信息提取完成，深度分析已启动",
        "data": {
            "task_id": task_id,
            "status": "running",
            "candidate_info": candidate_info.model_dump(),
            "rule_match": rule_match,
        }
    }


async def _run_deep_analysis(task_id, cleaned_text, jd_text, file_md5):
    """后台异步执行 LLM 深度分析"""
    try:
        # 更新状态 → running
        await cache_service.set_task_state(task_id, {"status": "running", "phase": "llm_extraction"})

        # LLM 深度提取
        deep_extraction = None
        extraction = {}
        try:
            deep_result = await llm_service.extract_resume_deep(cleaned_text)
            extraction = deep_result
            deep_extraction = DeepExtraction(...)  # 同现有逻辑
        except LLMCallError:
            # 降级到 regex
            extraction = _regex_extract(cleaned_text)

        # 更新状态
        await cache_service.set_task_state(task_id, {"status": "running", "phase": "llm_scoring"})

        # LLM Rubric 评分
        overall_score = 0
        summary = ""
        dimensions = []
        missing_skills = []
        try:
            rubric = await llm_service.score_resume_vs_jd(cleaned_text, jd_text)
            dimensions = [DimensionScore(**d) for d in rubric.get("dimensions", [])]
            overall_score = rubric.get("overall_score", 0)
            summary = rubric.get("summary", "")
            missing_skills = rubric.get("missing_skills", [])
        except LLMCallError:
            # 降级到规则评分
            rule_match = match_service.calculate_rule_match(cleaned_text, jd_text)
            dimensions = [DimensionScore(**d) for d in rule_match["dimensions"]]
            overall_score = rule_match["overall_score"]

        # 组装最终结果
        result_data = AnalysisData(
            candidate_info=CandidateInfo(...),
            overall_score=overall_score,
            summary=summary,
            dimensions=dimensions,
            missing_skills=missing_skills,
            risk_tips=rule_match.get("risks", []),
            deep_extraction=deep_extraction,
            raw_json=extraction,
        )

        # 存入最终结果缓存
        await cache_service.set_final_result(file_md5, jd_text, result_data.model_dump())

        # 更新任务状态 → succeeded
        await cache_service.set_task_state(task_id, {
            "status": "succeeded",
            "phase": "completed",
            "result": result_data.model_dump(),
        })

    except Exception as e:
        # 失败回退到规则匹配结果
        await cache_service.set_task_state(task_id, {
            "status": "failed",
            "phase": "error",
            "error": str(e),
            "result": {...},  # fallback to rule match only
        })


# ── 新端点：轮询任务状态 ──

@router.get("/analyze/tasks/{task_id}")
async def get_task_status(task_id: str):
    state = await cache_service.get_task_state(task_id)
    if not state:
        return {"code": 404, "message": "任务不存在或已过期", "data": None}

    return {
        "code": 200,
        "data": {
            "task_id": task_id,
            "status": state["status"],
            "phase": state.get("phase", ""),
            "result": state.get("result"),
            "error": state.get("error"),
        }
    }
```

### Step 4：前端类型层 → 新增异步相关类型

**文件**：`frontend/src/features/analyzer/types.ts`
**操作**：追加类型定义

```typescript
// Phase 1 快速响应
export interface QuickAnalysisData {
  task_id: string
  status: 'running' | 'succeeded' | 'failed' | 'expired'
  candidate_info: CandidateInfo
  rule_match: RuleMatch
}

export interface RuleMatch {
  overall_score: number
  dimensions: DimensionScore[]
  risk_tips: string[]
}

// 任务轮询响应
export interface TaskStatusData {
  task_id: string
  status: 'running' | 'succeeded' | 'failed' | 'expired'
  phase: string
  result: AnalysisData | null
  error: string | null
}
```

### Step 5：前端状态管理 → useAnalyzer 改造

**文件**：`frontend/src/features/analyzer/composables/useAnalyzer.ts`
**操作**：新增异步状态 + 轮询逻辑

```typescript
// 新增状态
const asyncStatus = ref<'idle' | 'loading' | 'polling' | 'done' | 'failed'>('idle')
const partialResult = ref<QuickAnalysisData | null>(null)  // Phase 1 结果
const taskId = ref<string | null>(null)
let pollTimer: ReturnType<typeof setInterval> | null = null

// 轮询配置
const POLL_CONFIG = {
  initialDelay: 500,      // 首次轮询延迟
  fastInterval: 1000,     // 快速轮询间隔 (前10s)
  mediumInterval: 2000,   // 中速轮询间隔 (10-30s)
  slowInterval: 5000,     // 慢速轮询间隔 (30-90s)
  maxDuration: 90000,     // 最长轮询时间
}

async function analyze(file: File, jdText: string) {
  loading.value = true
  asyncStatus.value = 'loading'
  error.value = null
  result.value = null
  partialResult.value = null

  const formData = new FormData()
  formData.append('file', file)
  formData.append('jd_text', jdText)

  try {
    // Phase 1: 提交并获得快速结果
    const { data } = await api.post<AnalysisResult & QuickAnalysisData>('/analyze', formData, ...)

    if (data.data?.task_id && data.data?.status === 'running') {
      // 异步模式：先展示部分结果
      partialResult.value = data.data
      taskId.value = data.data.task_id
      loading.value = false
      asyncStatus.value = 'polling'
      startPolling(data.data.task_id)
    } else {
      // 缓存命中或同步完成：直接展示
      result.value = data
      loading.value = false
      asyncStatus.value = 'done'
    }
  } catch (e) {
    loading.value = false
    asyncStatus.value = 'failed'
    error.value = ...
  }
}

async function pollTask(id: string) {
  try {
    const { data } = await api.get<TaskStatusData>(`/analyze/tasks/${id}`)
    if (data.data.status === 'succeeded') {
      stopPolling()
      asyncStatus.value = 'done'
      result.value = { code: 200, message: '解析成功', data: data.data.result }
    } else if (data.data.status === 'failed' || data.data.status === 'expired') {
      stopPolling()
      asyncStatus.value = 'failed'
      error.value = data.data.error || '深度分析失败'
      // 但仍保留 partialResult（Phase 1 结果仍可用）
    }
    // running 状态继续轮询
  } catch (e) {
    // 轮询出错不停止，但降低频率
  }
}

function startPolling(id: string) {
  const startTime = Date.now()
  let interval = POLL_CONFIG.fastInterval

  setTimeout(() => {
    pollTask(id)
    pollTimer = setInterval(() => {
      const elapsed = Date.now() - startTime
      if (elapsed > POLL_CONFIG.maxDuration) {
        stopPolling()
        asyncStatus.value = 'failed'
        error.value = '深度分析超时，请重新提交'
        return
      }
      if (elapsed > 30000) interval = POLL_CONFIG.slowInterval
      else if (elapsed > 10000) interval = POLL_CONFIG.mediumInterval
      // Adjust timer if interval changed...

      pollTask(id)
    }, interval)
  }, POLL_CONFIG.initialDelay)
}

function stopPolling() {
  if (pollTimer) {
    clearInterval(pollTimer)
    pollTimer = null
  }
}

function reset() {
  stopPolling()
  // 原有 reset 逻辑...
}

// 在组件 onUnmounted 时停止轮询
function cleanup() {
  stopPolling()
}
```

### Step 6：前端 UI 层 → ResultBoard 渐进式展示

**文件**：`frontend/src/features/analyzer/components/ResultBoard.vue`
**操作**：新增 `partialResult` 状态的处理

```vue
<script setup lang="ts">
const { result, loading, partialResult, asyncStatus } = useAnalyzer()
</script>

<template>
  <!-- 异步进行中：展示部分结果 + 加载指示 -->
  <div v-if="asyncStatus === 'polling' && partialResult" class="space-y-6">
    <!-- 基本信息（Phase 1 结果，立即可见）-->
    <CandidateInfoCard :info="partialResult.candidate_info" />

    <!-- 规则评分（Phase 1 结果，立即可见）-->
    <RuleMatchCard :match="partialResult.rule_match" />

    <!-- 深度分析进行中指示器 -->
    <div class="bg-white rounded-xl p-6 shadow-sm border border-blue-200">
      <div class="flex items-center gap-3">
        <div class="animate-spin w-5 h-5 border-2 border-blue-500 border-t-transparent rounded-full" />
        <div>
          <h3 class="text-sm font-medium text-blue-700">AI 深度分析进行中...</h3>
          <p class="text-xs text-blue-400 mt-1">正在调用大模型进行语义分析与评分</p>
        </div>
      </div>
      <!-- 进度条 -->
      <div class="mt-4 w-full bg-blue-100 rounded-full h-1.5 overflow-hidden">
        <div class="bg-blue-500 h-full rounded-full animate-progress-indeterminate" style="width: 60%" />
      </div>
    </div>
  </div>

  <!-- 完整结果（Phase 2 完成）-->
  <div v-if="asyncStatus === 'done' && result && result.data" class="space-y-6">
    <!-- 原有完整结果展示 -->
    ...
  </div>

  <!-- 异步失败但仍有部分结果 -->
  <div v-if="asyncStatus === 'failed' && partialResult" class="space-y-6">
    <CandidateInfoCard :info="partialResult.candidate_info" />
    <RuleMatchCard :match="partialResult.rule_match" />
    <div class="p-3 bg-yellow-50 text-yellow-700 rounded-lg text-sm border border-yellow-200">
      AI 深度分析未能完成，当前展示规则匹配结果
    </div>
  </div>
</template>
```

### Step 7：后端 main.py → 注册新轮询端点（自动）

新路由 `GET /api/v1/analyze/tasks/{task_id}` 已在 `analyze_router` 中定义，无需修改 `main.py`。

### Step 8：后端测试适配

**文件**：`backend/test_pipeline.py`、`backend/test_api.py`
**操作**：新增异步流程测试用例

```python
# test_api.py 新增
def test_analyze_returns_task_id(client):
    """POST /analyze 应返回 task_id 和部分结果"""
    ...

def test_task_status_polling(client):
    """GET /analyze/tasks/{task_id} 应返回任务状态"""
    ...

def test_task_not_found(client):
    """GET /analyze/tasks/nonexistent 应返回 404"""
    ...

def test_repeated_submit_reuses_task(client):
    """相同 file+JD 重复提交应复用已有 task"""
    ...
```

## 关键文件清单

| 文件 | 操作 | 说明 |
|------|------|------|
| `backend/models/schemas.py:L80-87` | 追加 | 新增 TaskStatus、QuickAnalysisData、TaskResultData |
| `backend/services/cache_service.py:L25-78` | 追加 | 新增 set_task_state/get_task_state/set_final_result/get_final_result/set_task_index/get_task_index |
| `backend/api/v1/analyze.py:L82-246` | 重构 | 拆分为 analyze_resume(Phase1) + _run_deep_analysis(Phase2) + get_task_status |
| `frontend/src/features/analyzer/types.ts:L55-80` | 追加 | 新增 QuickAnalysisData、RuleMatch、TaskStatusData |
| `frontend/src/features/analyzer/composables/useAnalyzer.ts` | 重构 | 新增 asyncStatus/partialResult/taskId + pollTask/startPolling/stopPolling |
| `frontend/src/features/analyzer/components/ResultBoard.vue:L42-317` | 改造 | 新增 polling 状态 + 部分结果展示 |
| `backend/test_api.py` | 追加 | 新增异步流程测试 |

## 风险与缓解

| 风险 | 缓解措施 |
|------|----------|
| Phase 1 超过 2s（PDF 大文件） | 限制页数/大小；PDF 提取放入线程池 |
| 后台任务丢失（进程重启） | 第一阶段接受此风险；第二阶段引入 Redis Queue |
| 重复提交导致重复 LLM 调用 | 用 file_md5+jd_hash 做幂等索引，已有 running 任务复用 task_id |
| LLM 失败后用户无结果 | Phase 2 失败保留 Phase 1 fallback 结果 |
| Redis 故障导致轮询失效 | Memory cache 作为单机降级 |
| Phase 1 规则评分与 Phase 2 AI 评分差异大 | 前端文案区分"规则初评"和"AI 深度评分" |
| 任务堆积（高并发） | Worker 并发限制 + 队列长度保护 + LLM 超时 |

## SESSION_ID（供 /ccg:execute 使用）

- CODEX_SESSION: `019e0ab5-fd4e-73f3-bf44-9dd664497e7d`
- GEMINI_SESSION: 不可用（缺少 GEMINI_API_KEY）
