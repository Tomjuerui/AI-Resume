/** Corresponds to backend models/schemas.py */

export interface CandidateInfo {
  name: string
  phone: string
  email: string
  address: string
}

export interface DimensionScore {
  name: string
  score: number
  reason: string
}

export interface AnalysisData {
  candidate_info: CandidateInfo
  overall_score: number
  dimensions: DimensionScore[]
  raw_json: Record<string, unknown>
}

export interface AnalysisResult {
  code: number
  message: string
  data: AnalysisData | null
}
