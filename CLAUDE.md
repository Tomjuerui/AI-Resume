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
- `python test_pipeline.py` — Run the 12-test integration suite (PDF extraction, schema validation, rule matching, etc.)

No linter or formatter is configured in either frontend or backend.

## Architecture

### Backend — Three-Layer (FastAPI)

Entry at `backend/main.py`: creates FastAPI app, registers CORS (origins from `.env`), mounts `/api/v1` router, defines global exception handlers mapping custom exceptions → `{ code, message, data: null }`.

**API Layer** (`api/v1/analyze.py`): single endpoint `POST /api/v1/analyze` (multipart: PDF file + JD text). Pipeline: validate → extract text → clean → check scanned → LLM extract → rule match → LLM score → respond. Has regex fallback for contact info extraction when LLM is unavailable.

**Services** (`services/`):
- `pdf_service.py` — PDF text extraction (pdfplumber → PyMuPDF fallback), text cleaning, scanned-PDF detection, MD5 computation for caching
- `llm_service.py` — OpenAI-compatible client factory supporting multiple providers (OpenAI/DeepSeek/Qianwen). Three prompts: basic extraction (P0 fields), deep extraction (full profile), rubric scoring (from System Prompt.md). Falls back through deep → basic → regex on extraction, rubric → rule → empty on scoring
- `match_service.py` — Rule-based keyword matching with 70+ tech keyword set. Scores skills (40%), experience (30%), education (15%), soft skills (15%). Always runs as baseline, no LLM dependency
- `cache_service.py` — Redis get/set by MD5, 1-hour TTL
- `oss_service.py` — Alibaba Cloud OSS upload (optional, gated by config)

**Core** (`core/`): `config.py` (Pydantic BaseSettings from `.env` with multi-provider LLM config), `exceptions.py` (6 custom exception classes), `redis.py` (lazy async connection pool)

**Models** (`models/schemas.py`): Pydantic v2 models — `AnalyzeRequest`, `CandidateInfo`, `SkillItem`, `WorkExperience`, `ProjectItem`, `DeepExtraction`, `DimensionScore`, `AnalysisData`, `AnalysisResponse`, `ErrorResponse`

### Frontend — Vertical Slicing (Vue 3 + TypeScript)

Entry at `frontend/src/main.ts`. Root `App.vue` is a full-screen flex layout: left sidebar (420px, `UploadPanel`) + right area (`ResultBoard`).

**Feature module** (`features/analyzer/`):
- `types.ts` — TypeScript interfaces mirroring backend Pydantic schemas exactly
- `composables/useAnalyzer.ts` — All reactive state lives here (loading, result, error). Single `analyze(file, jdText)` method creates FormData and POSTs to `/api/v1/analyze`
- `components/UploadPanel.vue` — JD textarea + PDF drop zone + submit button + error display
- `components/ResultBoard.vue` — Empty/loading/success states, overall score, radar chart, dimension cards, missing skills, risk tips, deep profile (skills, work, projects, education, certs, languages), candidate info grid
- `components/RadarChart.vue` — ECharts radar visualization, watches dimension changes, handles resize

**Global services**: `services/api.ts` (Axios instance, baseURL `/api/v1`, 60s timeout), `utils/formatters.ts` (bytesToMB, formatScore, formatDate)

Vite config proxies `/api` to `http://localhost:8000` in dev. No frontend routing (single-page app; `vue-router` is installed but unused). No state management library — all state in the `useAnalyzer` composable.

## Key Design Patterns

- **Two-stage scoring**: rule-based (always, free) + LLM semantic (when available)
- **Graceful degradation**: LLM failures cascade downward at every step
- **Multi-provider LLM**: `.env` `llm_provider` supports `openai`, `deepseek`, `qianwen` via OpenAI-compatible API
- **API contract**: dual-defined in `backend/models/schemas.py` (Pydantic) and `frontend/src/features/analyzer/types.ts` (TypeScript) — keep them in sync
- **Caching**: Redis keyed by file MD5 to avoid re-analyzing identical resumes

## Environment Variables (backend/.env)

Key settings read by `core/config.py`: `llm_provider`, `llm_api_key`, `llm_model`, `llm_base_url`, `redis_dsn`, `cors_origins`, `oss_endpoint`/`oss_bucket`/`oss_access_key_id`/`oss_access_key_secret`. Legacy keys `openai_api_key`/`openai_base_url` are supported for backward compatibility.
