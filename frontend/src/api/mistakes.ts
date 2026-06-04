import { request } from './config'

export interface MistakeItem {
  id: number
  subject: string
  question_text: string
  correct_answer: string
  student_answer: string
  explanation: string
  topic: string
  mastery: number
  review_count: number
  next_review: string
  created_at: string
}

interface MistakeListResponse {
  items: MistakeItem[]
  total: number
  page: number
}

interface MistakeListParams {
  subject?: string
  review_due?: boolean
  topic?: string
  page?: number
  size?: number
}

export function getMistakes(params: MistakeListParams = {}): Promise<MistakeListResponse> {
  const query: string[] = []
  if (params.subject) query.push(`subject=${params.subject}`)
  if (params.review_due) query.push(`review_due=true`)
  if (params.topic) query.push(`topic=${encodeURIComponent(params.topic)}`)
  if (params.page) query.push(`page=${params.page}`)
  if (params.size) query.push(`size=${params.size}`)
  const qs = query.length > 0 ? '?' + query.join('&') : ''
  return request<MistakeListResponse>({ url: `/mistakes${qs}`, method: 'GET' })
}

export function getMistakeDetail(id: number): Promise<MistakeItem> {
  return request<MistakeItem>({ url: `/mistakes/${id}`, method: 'GET' })
}

export function reviewMistake(id: number, correct: boolean): Promise<MistakeItem> {
  return request<MistakeItem>({
    url: `/mistakes/${id}/review`,
    method: 'POST',
    data: { correct },
  })
}

export interface TopicStat {
  topic: string
  count: number
  avg_mastery: number
}

export interface MistakeStatsResponse {
  total_mistakes: number
  mastered_count: number
  reviewing_count: number
  new_count: number
  topics: TopicStat[]
  subject_dist: Record<string, number>
}

export function getMistakeStats(): Promise<MistakeStatsResponse> {
  return request<MistakeStatsResponse>({ url: '/mistakes/stats', method: 'GET' })
}
