import { request } from './config'

export interface PracticeQuestion {
  question: string
  options: string[]
  correct_index: number
  explanation: string
}

export interface DailyPracticeResponse {
  id: number
  subject: string
  topic: string
  questions: PracticeQuestion[]
  score: number | null
  total: number
  created_at: string
}

export function generateDailyPractice(subject: string = 'chinese'): Promise<DailyPracticeResponse> {
  return request<DailyPracticeResponse>({
    url: '/practice/generate',
    method: 'POST',
    data: { subject },
  })
}

export function submitPractice(id: number, answers: number[]): Promise<DailyPracticeResponse> {
  return request<DailyPracticeResponse>({
    url: `/practice/${id}/submit`,
    method: 'POST',
    data: { answers },
  })
}

export interface PracticeHistoryItem {
  id: number
  subject: string
  topic: string
  score: number | null
  total: number
  created_at: string
}

export interface PracticeHistoryResponse {
  items: PracticeHistoryItem[]
  streak: number
}

export function getPracticeHistory(): Promise<PracticeHistoryResponse> {
  return request<PracticeHistoryResponse>({ url: '/practice/history', method: 'GET' })
}
