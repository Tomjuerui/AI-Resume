# AI-Resume 运行手册

## 环境要求

| 依赖 | 版本要求 | 说明 |
|------|----------|------|
| Python | ≥ 3.10 | 建议 3.12 |
| Node.js | ≥ 18 | 建议 20 LTS |
| Redis | ≥ 5.0 | 缓存层，可降级为内存 LRU |

---

## 一、后端配置与启动

### 1. 安装依赖

```bash
cd backend
pip install -r requirements.txt
```

### 2. 配置 `.env`

复制 `.env.example` 并修改：

```bash
cp .env.example .env
```

**必填项：**

```env
# ── LLM Provider（三选一）──
LLM_PROVIDER=deepseek          # openai | deepseek | qianwen
LLM_API_KEY=sk-你的API密钥      # 必填
LLM_MODEL=                     # 留空使用 provider 默认，或手动指定
LLM_BASE_URL=                  # 留空使用 provider 默认 base_url
```

**可选项（建议配置，缺失时自动降级）：**

```env
# ── Redis（未配置时自动降级为内存 LRU 缓存）──
REDIS_DSN=redis://localhost:6379/0
REDIS_PASSWORD=

# ── OSS（未配置则跳过 PDF 归档上传）──
OSS_ENDPOINT=oss-cn-hangzhou.aliyuncs.com
OSS_BUCKET=your-bucket-name
OSS_ACCESS_KEY_ID=your-access-key-id
OSS_ACCESS_KEY_SECRET=your-access-key-secret

# ── App ──
CORS_ORIGINS=http://localhost:5173   # 前端地址，逗号分隔多个
MAX_UPLOAD_SIZE_MB=10
```

#### 各 Provider 默认值

| Provider | Base URL | 默认模型 |
|----------|----------|----------|
| `openai` | `https://api.openai.com/v1` | `gpt-4o` |
| `deepseek` | `https://api.deepseek.com/v1` | `deepseek-chat` |
| `qianwen` | `https://dashscope.aliyuncs.com/compatible-mode/v1` | `qwen-plus` |

> 兼容旧版 key：如果之前用的是 `OPENAI_API_KEY` / `OPENAI_BASE_URL`，当前版本仍可识别，但建议迁移到新 key。

### 3. 启动

```bash
cd backend
python main.py
```

服务启动在 **http://localhost:8000**，带热重载。

验证：

```bash
curl http://localhost:8000/
# → {"status":"ok","service":"AI-Resume Analyzer"}
```

### 4. 运行测试

```bash
cd backend
python test_pipeline.py    # 12 个集成测试
python test_api.py         # API 端点测试
```

---

## 二、前端配置与启动

### 1. 安装依赖

```bash
cd frontend
npm install
```

### 2. 启动开发服务器

```bash
npm run dev
```

开发服务器启动在 **http://localhost:5173**，Vite 自动将 `/api` 请求代理到后端 8000 端口。

### 3. 生产构建

```bash
npm run build    # TypeScript 类型检查 + Vite 打包
npm run preview  # 预览生产构建
```

---

## 三、完整联调流程

1. **确保 Redis 已启动**（如未安装 Redis，后端自动降级为内存 LRU 缓存，不影响使用）
2. **启动后端**：`cd backend && python main.py`
3. **启动前端**：`cd frontend && npm run dev`
4. **打开浏览器**：http://localhost:5173
5. **使用步骤**：
   - 左侧文本框中粘贴岗位描述（JD）
   - 拖拽或点击上传 PDF 简历
   - 点击 "Analyze Resume"
   - 右侧面板展示：综合得分、雷达图、维度详情、缺失技能、风险提示、深度信息提取

---

## 四、降级策略

| 组件 | 可用时 | 不可用时 |
|------|--------|----------|
| LLM API | 深度提取 + 语义评分 | 规则匹配兜底 + regex 提取 |
| Redis | 持久化缓存 | 内存 LRU 缓存（进程内） |
| OSS | PDF 归档上传 | 跳过上传，不影响分析 |
| PyMuPDF | PDF 解析回退 | pdfplumber 优先 |

---

## 五、常见问题

**Q: 启动后端报 `ModuleNotFoundError`**
A: 运行 `pip install -r requirements.txt` 安装所有依赖。

**Q: 分析结果中AI总结为空**
A: LLM API Key 未配置或不可用，系统已自动降级为规则评分。检查 `LLM_API_KEY` 是否正确，模型是否可访问。

**Q: 前端页面可以打开，但点击分析后报"网络连接失败"**
A: 后端未启动或端口被占用。确认 `python main.py` 正在运行，端口 8000 未被占用。

**Q: 上传 PDF 后提示"不支持扫描件"**
A: 简历 PDF 是图片扫描版，没有嵌入文本层。请使用文本型 PDF（如 Word 直接导出的 PDF）。

**Q: Redis 连接失败**
A: 不影响正常使用，系统自动降级为内存 LRU 缓存。如需启用 Redis，检查 `REDIS_DSN` 配置和 Redis 服务状态。
