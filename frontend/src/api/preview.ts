import { request } from './config'

export interface TextbookOption {
  subject: string
  grade: number
  semester: string
  version: string
  label: string
  source_name: string
  source_url: string
  status: string
}

export interface PreviewUnit {
  unit: number
  title: string
  total_items: number
  completed_items: number
  source_status: string
}

export interface PreviewItem {
  item_key: string
  item_type: string
  category_label: string
  word: string
  pronunciation: string
  meaning: string
  hint: string
  sample_sentences: string[]
  practice_prompt: string
  completed: boolean
}

export interface PreviewUnitDetail {
  subject: string
  grade: number
  semester: string
  textbook_version: string
  unit: number
  title: string
  source_name: string
  source_url: string
  source_status: string
  guidance: string
  items: PreviewItem[]
}

export function getTextbooks(): Promise<{ items: TextbookOption[] }> {
  return request<{ items: TextbookOption[] }>({ url: '/preview/textbooks', method: 'GET' })
}

export function getPreviewUnits(params: {
  subject: string
  grade: number
  semester: string
  textbook_version: string
}): Promise<{ subject: string; grade: number; semester: string; textbook_version: string; units: PreviewUnit[] }> {
  const q = encodeParams(params)
  return request<{ subject: string; grade: number; semester: string; textbook_version: string; units: PreviewUnit[] }>({
    url: `/preview/units?${q}`,
    method: 'GET',
  })
}

export function getPreviewUnitDetail(params: {
  subject: string
  grade: number
  semester: string
  textbook_version: string
  unit: number
}): Promise<PreviewUnitDetail> {
  const { unit, ...rest } = params
  return request<PreviewUnitDetail>({ url: `/preview/units/${unit}?${encodeParams(rest)}`, method: 'GET' })
}

export function completePreviewItem(data: {
  subject: string
  grade: number
  semester: string
  textbook_version: string
  unit: number
  item_key: string
  item_type: string
}): Promise<{ item_key: string; completed: boolean; completed_at: string }> {
  return request<{ item_key: string; completed: boolean; completed_at: string }>({
    url: '/preview/complete',
    method: 'POST',
    data,
  })
}

export interface ChallengeOption {
  text: string
  is_correct: boolean
  index: number
}

export interface ChallengeQuestion {
  word: string
  pinyin: string
  type: string
  question_text: string
  options: ChallengeOption[]
  correct_answer: string
}

export function getUnitChallenge(params: {
  subject: string
  grade: number
  semester: string
  unit_no: number
}): Promise<{ subject: string; grade: number; semester: string; unit: number; questions: ChallengeQuestion[] }> {
  const q = encodeParams(params)
  return request<{ subject: string; grade: number; semester: string; unit: number; questions: ChallengeQuestion[] }>({
    url: `/preview/unit-challenge?${q}`,
    method: 'GET',
  })
}

export interface ChallengeResult {
  points_earned: number
  correct_count: number
  total: number
  total_points: number
  streak_days: number
  words_mastered: number
  new_badges: { id: string; name: string; desc: string }[]
}

export function submitChallengeResult(data: {
  subject: string
  grade: number
  results: { word: string; correct: boolean }[]
}): Promise<ChallengeResult> {
  return request<ChallengeResult>({ url: '/preview/challenge-result', method: 'POST', data })
}

export interface StudiedUnit {
  subject: string
  grade: number
  semester: string
  unit: number
  title: string
  completed_items: number
  total_items: number
  percent: number
}

export interface ParentSummary {
  period_days: number
  weekly_completed: number
  subject_breakdown: Record<string, number>
  studied_units: StudiedUnit[]
  review_suggestions: string[]
}

export function getParentSummary(params: { days?: number; grade: number }): Promise<ParentSummary> {
  const q = encodeParams({ days: params.days ?? 7, grade: params.grade })
  return request<ParentSummary>({ url: `/preview/parent-summary?${q}`, method: 'GET' })
}

export function explainPreviewItem(data: {
  subject: string
  grade: number
  word: string
  item_type: string
  category_label?: string
  unit_title?: string
  meaning?: string
}): Promise<{ word: string; explanation: string }> {
  return request<{ word: string; explanation: string }>({
    url: '/preview/explain',
    method: 'POST',
    data,
  })
}

function encodeParams(params: Record<string, string | number>) {
  return Object.entries(params)
    .map(([key, value]) => `${encodeURIComponent(key)}=${encodeURIComponent(String(value))}`)
    .join('&')
}
