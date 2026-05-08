# 全栈技术架构设计文档 

**项目:** AI-Resume-Analyzer (智能简历分析系统) **架构模式:** 前后端分离 / 领域驱动切片 (Vertical Slicing) / 契约驱动 (API-First)

## 1. 确定的技术选型 (Tech Stack)

### 1.1 后端 (Backend) - 关注高并发、异步与强类型

- **语言:** Python 3.10+ (完美契合 AI 生态)
- **Web 框架:** **FastAPI** (基于 ASGI，原生支持异步，基于 Pydantic 的强类型校验，自动生成 Swagger，**Vibe Coding 后端首选**)
- **PDF 解析:** `pdfplumber` (文本提取精准) + `PyMuPDF` (备选，速度极快)
- **AI 交互:** `openai` 官方 SDK (利用 `response_format={ "type": "json_object" }` 强制结构化输出)
- **缓存:** Redis (阿里云 KVStore，用于缓存相同 PDF 的解析结果，基于文件 MD5)
- **部署环境:** 阿里云函数计算 (FC) Serverless

### 1.2 前端 (Frontend) - 关注极速开发与组件化

- **构建工具:** Vite
- **核心框架:** **Vue 3** (Composition API `<script setup>`)
- **语言:** TypeScript (必须强类型，与后端 Pydantic 契约对齐)
- **CSS 框架:** Tailwind CSS (极速样式开发)
- **UI 组件库:** `shadcn-vue` (代码级引入，高度可定制，AI 生成 UI 成功率极高)
- **可视化:** `ECharts` (绘制多维度匹配雷达图)
- **网络请求:** `Axios`

------

## 2. 全栈目录结构设计 (Monorepo 风格)

为了方便 Vibe Coding 和单人全栈维护，建议采用一个代码仓库，顶层分为 `frontend/` 和 `backend/`。结构设计严格遵循“高内聚、低耦合”原则。

### 2.1 后端目录树 (`/backend`)

采用经典的三层架构（路由层 -> 服务层 -> 数据模型层），特别适合 FastAPI。

Plaintext

```
backend/
├── main.py                  # FastAPI 应用入口，CORS 配置，路由注册
├── requirements.txt         # 核心依赖清单
├── .env                     # 环境变量 (API Keys, Redis DSN)
├── api/                     # Controller 层 (只处理 HTTP 请求与响应)
│   ├── dependencies.py      # 依赖注入 (如鉴权、获取 Redis 连接)
│   └── v1/
│       └── analyze.py       # 核心业务路由: POST /api/v1/analyze
├── core/                    # 全局配置与基础组件
│   ├── config.py            # 读取 .env 配置的 Pydantic BaseSettings
│   ├── exceptions.py        # 全局自定义异常 (如 PdfParseError)
│   └── redis.py             # Redis 连接池初始化
├── models/                  # 契约层：出入参结构与数据校验
│   └── schemas.py           # 定义 Pydantic BaseModel (JDRequest, AnalysisResponse)
└── services/                # Service 层 (核心业务逻辑，AI 提点重点)
    ├── pdf_service.py       # 处理文件读取、文本清理与降噪
    ├── llm_service.py       # 封装大模型 Prompt，执行 JSON 信息抽取
    ├── match_service.py     # 计算匹配度得分与雷达图维度
    └── cache_service.py     # 封装计算文件 MD5 与 Redis 存取逻辑
```

### 2.2 前端目录树 (`/frontend`)

采用垂直业务切片（Vertical Slicing）模式，将简历分析相关的所有代码（UI、逻辑、类型）内聚在一个文件夹中。

Plaintext

```
frontend/
├── index.html               # 页面入口
├── vite.config.ts           # Vite 配置 (配置后端 API 代理)
├── src/
│   ├── main.ts              # Vue 实例初始化，引入 Tailwind
│   ├── App.vue              # 根组件 (在此搭建左右分栏 Split View 骨架)
│   ├── components/          # 全局共享/基础 UI 组件
│   │   └── ui/              # shadcn-vue 生成的基础组件 (Button, Card, Progress)
│   ├── features/            # 业务模块 (核心！)
│   │   └── analyzer/        # 简历分析域
│   │       ├── components/  # 仅此域使用的业务组件
│   │       │   ├── UploadPanel.vue  # 左侧：上传区与 JD 输入区
│   │       │   ├── ResultBoard.vue  # 右侧：主结果展示看板
│   │       │   └── RadarChart.vue   # 右侧：ECharts 雷达图组件
│   │       ├── composables/ 
│   │       │   └── useAnalyzer.ts   # 核心交互逻辑与状态管理 (调用 API)
│   │       └── types.ts     # TypeScript 接口 (严格对应后端 schemas.py)
│   ├── services/            # 全局服务
│   │   └── api.ts           # Axios 实例封装 (统一拦截器、BaseURL)
│   └── utils/               # 工具函数
│       └── formatters.ts    # 如：字节转 MB，日期格式化等
```

------

## 3. 核心契约 (The Contract)

在让 AI 编写具体业务逻辑前，必须**首先**让前后端在这个核心接口上达成共识。

### `POST /api/v1/analyze`

- **请求体 (`multipart/form-data`)**:
  - `file`: PDF 文件二进制流。
  - `jd_text`: 字符串，岗位描述文本。
- **响应体 (`application/json`)**: (对应后端 `schemas.AnalysisResponse` 与 前端 `types.AnalysisResult`)

JSON

```
{
  "code": 200,
  "message": "解析成功",
  "data": {
    "candidate_info": {
      "name": "张三",
      "phone": "13800138000",
      "email": "zhangsan@example.com"
    },
    "overall_score": 85,
    "dimensions": [
      {
        "name": "技能匹配度",
        "score": 90,
        "reason": "熟练掌握 Java/Spring，与 JD 要求的微服务架构高度契合。"
      },
      {
        "name": "经验相关性",
        "score": 80,
        "reason": "有 12306 高并发项目经验，但缺少前端开发经验。"
      }
    ],
    "raw_json": {
       // 大模型返回的包含教育背景、工作经历等信息的全量原始 JSON
    }
  }
}
```