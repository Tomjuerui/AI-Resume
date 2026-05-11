# AI Resume Analyzer

一个基于AI的智能简历分析系统，帮助HR和招聘人员快速评估候选人与职位的匹配度。

## 在线体验

🌐 **在线演示地址**: [https://juerui.top/](https://juerui.top/)

## 功能特性

### 🎯 核心功能
- **职位描述解析**: 支持输入详细的职位要求（JD）
- **简历上传**: 支持PDF格式简历上传（支持中文简历）
- **AI智能分析**: 基于大语言模型的深度简历分析
- **匹配评分**: 自动计算候选人与职位的匹配度

### 📊 分析维度
| 维度 | 说明 |
|------|------|
| 技能匹配度 | 评估候选人技能与JD核心技能的匹配程度 |
| 项目经验相关性 | 分析项目经验与目标岗位的契合度 |
| 背景与加分项 | 综合评估学历、证书、竞赛等背景信息 |

### 📈 输出报告
- **AI分析总结**: 自然语言总结候选人优势与不足
- **总体匹配分数**: 可视化展示匹配评分（0-100分）
- **雷达图分析**: 三维度可视化对比
- **缺失技能提示**: 明确指出欠缺的关键技能
- **风险警报**: 标注潜在风险点
- **深度简历提取**: 结构化展示候选人技能、项目、教育背景

## 技术栈

### 前端
- **框架**: Vue 3 + TypeScript
- **构建工具**: Vite
- **样式**: TailwindCSS 3
- **图表**: 自定义雷达图组件

### 后端
- **框架**: FastAPI
- **语言**: Python 3.10+
- **缓存**: Redis
- **文件存储**: OSS (阿里云对象存储)
- **LLM集成**: 支持主流大语言模型

## 项目结构

```
AI-Resume/
├── backend/                    # 后端服务
│   ├── api/                    # REST API 路由
│   │   └── v1/                 # API版本控制
│   │       ├── analyze.py      # 分析接口
│   │       └── upload.py       # 上传接口
│   ├── core/                   # 核心配置与工具
│   ├── models/                 # 数据模型
│   └── services/               # 业务服务层
│       ├── llm_service.py      # LLM服务
│       ├── match_service.py    # 匹配服务
│       └── pdf_service.py      # PDF解析服务
├── frontend/                   # 前端应用
│   └── src/
│       ├── features/
│       │   └── analyzer/       # 分析器功能模块
│       │       ├── components/ # Vue组件
│       │       └── composables/# 组合式函数
│       ├── services/           # API服务
│       └── utils/              # 工具函数
└── README.md                   # 项目说明文档
```

## 快速开始

### 环境要求
- Python 3.10+
- Node.js 18+
- Redis 7+

### 后端启动

```bash
cd backend
pip install -r requirements.txt
cp .env.example .env
# 配置 .env 文件中的 API 密钥和 Redis 连接
uvicorn main:app --reload
```

### 前端启动

```bash
cd frontend
npm install
npm run dev
```

### 访问应用
- 前端: http://localhost:5173
- 后端API: http://localhost:8000

## API接口

### 上传简历
```
POST /api/v1/upload
Content-Type: multipart/form-data

参数:
- file: PDF文件
```

### 分析简历
```
POST /api/v1/analyze
Content-Type: application/json

{
  "job_description": "职位描述文本",
  "resume_id": "上传返回的文件ID"
}
```

### 响应示例
```json
{
  "overall_score": 79,
  "match_rating": "Good Match",
  "summary": "候选人技术扎实...",
  "dimension_scores": {
    "skill_match": 85,
    "project_relevance": 75,
    "background": 70
  },
  "missing_skills": ["React", "Vue深入实践"],
  "risk_alerts": ["缺失技能: react, 人工智能, go"]
}
```

## 使用流程

1. **输入职位描述**: 在文本框中粘贴JD内容
2. **上传简历**: 点击上传区域选择PDF文件
3. **开始分析**: 点击"Analyze Resume"按钮
4. **查看报告**: 系统将展示完整的分析结果

## 安全特性

- ✅ PII敏感信息自动脱敏
- ✅ 文件上传安全校验
- ✅ 数据传输加密
- ✅ 缓存数据定时清理

## 许可证

MIT License

## 贡献

欢迎提交Issue和Pull Request！

---

*Made with ❤️ by AI Resume Team*