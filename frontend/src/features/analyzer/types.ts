/** Corresponds to backend models/schemas.py */

export interface CandidateInfo {
  name: string
  phone: string
  email: string
  address: string
  years_of_experience: string
  highest_degree: string
  school: string
  major: string
}

export interface SkillItem {
  name: string
  level: string
}

export interface WorkExperience {
  company: string
  role: string
  duration: string
  highlights: string[]
}

export interface ProjectItem {
  name: string
  role: string
  description: string
  tech_stack: string[]
}

export interface DeepExtraction {
  name: string
  phone: string
  email: string
  address: string
  years_of_experience: string
  highest_degree: string
  school: string
  major: string
  skills: SkillItem[]
  work_experience: WorkExperience[]
  projects: ProjectItem[]
  certificates: string[]
  languages: string[]
}

export interface DimensionScore {
  name: string
  score: number
  reason: string
}

export interface AnalysisData {
  candidate_info: CandidateInfo
  overall_score: number
  summary: string
  dimensions: DimensionScore[]
  missing_skills: string[]
  risk_tips: string[]
  deep_extraction: DeepExtraction | null
  raw_json: Record<string, unknown>
}

export interface AnalysisResult {
  code: number
  message: string
  data: AnalysisData | null
}

/** Phase 1 quick analysis response */
export interface QuickAnalysisData {
  task_id: string
  status: string
  candidate_info: CandidateInfo
  overall_score: number
  summary: string
  dimensions: DimensionScore[]
  missing_skills: string[]
  risk_tips: string[]
  raw_json: Record<string, unknown>
}

/** GET /api/v1/analyze/tasks/{task_id} response */
export interface TaskStatusData {
  task_id: string
  status: 'pending' | 'running' | 'succeeded' | 'failed' | 'expired'
  phase: string
  progress: number
  result: AnalysisData | null
  fallback_result: AnalysisData | null
  error: string | null
}

export interface TaskStatusResult {
  code: number
  message: string
  data: TaskStatusData | null
}

/** POST /api/v1/upload response */
export interface UploadResult {
  code: number
  message: string
  filename: string
  text_length: number
  text_preview: string
  raw_text: string
}
