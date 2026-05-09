# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

AI-Resume — an AI-powered resume analyzer that compares uploaded PDF resumes against job descriptions using LLM semantic scoring + rule-based keyword matching. Monorepo with `frontend/` (Vue 3 + Vite + Tailwind) and `backend/` (FastAPI + Python). Remote: `https://github.com/Tomjuerui/AI-Resume.git`

## Commands

### Frontend (`frontend/`)
- `npm run dev` — Start Vite dev server (port 5173, proxies `/api` → `localhost:8000`)
- `npm run build` — Type-check with `vue-tsc` then production build to `dist/`
- `npm run preview` — Preview production build locally

### Backend (`backend/`)
- `pip install -r requirements.txt` — Install Python dependencies
- `python main.py` — Start FastAPI server (port 8000 with hot reload)
- `python test_pipeline.py` — Run the 12-test integration suite (PDF extraction, schema validation, rule matching, LLM config, etc.)
- `python test_api.py` — Run the 11-test HTTP endpoint suite (using FastAPI TestClient, validates full request/response contract)

No linter or formatter is configured in either frontend or backend.

## Architecture

### Backend — Three-Layer (FastAPI)

Entry at `backend/main.py`: creates FastAPI app, registers CORS (origins from `.env`), mounts two routers (`analyze` + `upload`), defines global exception handlers for all custom exceptions → `{ code, message, data: null }`.

**Endpoints:**
- `POST /api/v1/analyze` — Main endpoint (multipart: PDF file + JD text). Full pipeline: validate → extract text → clean → check scanned → LLM deep extract → rule match → LLM rubric score → cache → respond
- `POST /api/v1/upload` — Lightweight standalone PDF upload & text extraction only (no matching)
- `GET /` — Health check

**API Layer** (`api/`):
- `api/v1/analyze.py` — Core analyze endpoint with validation, caching, and the full extraction→matching→scoring pipeline. Has `_regex_extract()` fallback for contact info when LLM is unavailable
- `api/v1/upload.py` — Standalone upload endpoint returning extracted text + preview
- `api/dependencies.py` — FastAPI dependency injection (async Redis connection pool)

**Services** (`services/`):
- `pdf_service.py` — PDF text extraction (pdfplumber → PyMuPDF fallback), text cleaning (control chars, whitespace collapse), scanned-PDF detection (whitespace-only → scanned), MD5 computation
- `llm_service.py` — OpenAI-compatible client factory supporting multiple providers (OpenAI/DeepSeek/Qianwen). Three prompts: basic extraction (P0: name/phone/email/address), deep extraction (P1: full profile with skills/works/projects/certs/languages), rubric scoring (3-dimension rubric from System Prompt). Falls back through deep → basic → regex on extraction, rubric → rule → empty on scoring. Cleans JSON responses (Markdown fences, think tags, surrounding text) with retry
- `match_service.py` — Rule-based keyword matching with 70+ tech keyword set. Three rubric-aligned dimensions: skills (50%), experience (35%), bonus/background (15%). Always runs as baseline, no LLM dependency
- `cache_service.py` — Composite cache key: `resume:{file_md5}:{jd_md5}`. Dual-write: Redis first (1-hour TTL), then in-memory LRU as backup. Also has legacy by-path wrappers
- `memory_cache.py` — In-memory LRU cache with TTL (max 128 entries, 1-hour TTL). Fallback when Redis is unavailable
- `oss_service.py` — Alibaba Cloud OSS upload (optional, gated by `oss_configured`)

**Core** (`core/`):
- `config.py` — Pydantic BaseSettings from `.env` with multi-provider LLM config (`openai`/`deepseek`/`qianwen`), Redis DSN, OSS credentials, CORS origins. `effective_api_key` and `effective_base_url` computed properties with legacy fallback
- `exceptions.py` — 6 custom exception classes: `FileValidationError`, `PdfParseError`, `ScannedPdfError`, `LLMCallError`, `OSSUploadError`, `CacheError`
- `redis.py` — Lazy async Redis connection pool
- `pii_mask.py` — PII masking for log desensitization: `mask_name()`, `mask_phone()`, `mask_email()`, `mask_pii_dict()`

**Models** (`models/schemas.py`): Pydantic v2 models — `AnalyzeRequest`, `CandidateInfo`, `SkillItem`, `WorkExperience`, `ProjectItem`, `DeepExtraction`, `DimensionScore`, `AnalysisData` (includes `summary`, `missing_skills`, `risk_tips`, `deep_extraction`, `raw_json`), `AnalysisResponse`, `ErrorResponse`

**Deployment** (`fc_handler.py`): Alibaba Cloud Function Compute handler — ASGI-to-WSGI bridge wrapping the FastAPI app for Serverless deployment

### Frontend — Vertical Slicing (Vue 3 + TypeScript)

Entry at `frontend/src/main.ts`. Root `App.vue` is a full-screen flex layout: left sidebar (420px, `UploadPanel`) + right area (`ResultBoard`).

**Feature module** (`features/analyzer/`):
- `types.ts` — TypeScript interfaces mirroring backend Pydantic schemas exactly (includes `DeepExtraction`, `UploadResult`)
- `composables/useAnalyzer.ts` — All reactive state lives here (loading, result, error). Single `analyze(file, jdText)` method creates FormData and POSTs to `/api/v1/analyze`
- `components/UploadPanel.vue` — JD textarea + PDF drop zone + submit button + error display
- `components/ResultBoard.vue` — Empty/loading/success states, overall score, radar chart, dimension cards, missing skills, risk tips, deep profile (skills, work, projects, education, certs, languages), candidate info grid
- `components/RadarChart.vue` — ECharts radar visualization, watches dimension changes, handles resize

**Global services**: `services/api.ts` (Axios instance, baseURL `/api/v1`, 120s timeout, typed error classification into `file`/`scanned`/`parse`/`server`/`network`/`unknown` categories), `utils/formatters.ts` (bytesToMB, formatScore, formatDate)

Vite config proxies `/api` to `http://localhost:8000` in dev. No frontend routing (single-page app; `vue-router` is installed but unused). No state management library — all state in the `useAnalyzer` composable.

## Key Design Patterns

- **Two-stage scoring**: rule-based keyword matching (always, free) + LLM rubric semantic scoring (3 dimensions: skills 50%, experience 35%, bonus 15%)
- **Graceful degradation**: LLM failures cascade downward at every step (deep → basic → regex extraction; rubric → rule scoring)
- **Multi-provider LLM**: `.env` `llm_provider` supports `openai`, `deepseek`, `qianwen` via OpenAI-compatible API. Provider defaults auto-filled
- **API contract**: dual-defined in `backend/models/schemas.py` (Pydantic) and `frontend/src/features/analyzer/types.ts` (TypeScript) — keep them in sync
- **Caching**: Composite key by file MD5 + JD MD5, dual-write to Redis + in-memory LRU fallback
- **PII masking**: All candidate PII (name, phone, email) is masked in logs via `core/pii_mask.py`

## Environment Variables (backend/.env)

Key settings read by `core/config.py`: `llm_provider`, `llm_api_key`, `llm_model`, `llm_base_url`, `redis_dsn`, `redis_password`, `cors_origins`, `app_env`, `max_upload_size_mb`, `oss_endpoint`/`oss_bucket`/`oss_access_key_id`/`oss_access_key_secret`. Legacy keys `openai_api_key`/`openai_base_url` are supported for backward compatibility.
