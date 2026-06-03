import { request } from './config'

export interface DailyReport {
  date: string
  chat_count: number
  homework_count: number
  words_learned: number
  mistakes_count: number
  review_count: number
  subject_dist: Record<string, number>
  weak_topics: { topic: string; count: number }[]
  total_interactions: number
}

export interface WeeklyDayData {
  date: string
  count: number
}

export interface WeeklyReport {
  week_start: string
  week_end: string
  total_interactions: number
  words_learned: number
  words_mastered: number
  mistakes_reviewed: number
  daily_trend: WeeklyDayData[]
  subject_dist: Record<string, number>
  weak_topics: { topic: string; count: number }[]
  vs_last_week: { interactions: number; words: number }
}

export function getDailyReport(date?: string): Promise<DailyReport> {
  const qs = date ? `?date=${date}` : ''
  return request<DailyReport>({ url: `/reports/daily${qs}`, method: 'GET' })
}

export function getWeeklyReport(weekStart?: string): Promise<WeeklyReport> {
  const qs = weekStart ? `?week_start=${weekStart}` : ''
  return request<WeeklyReport>({ url: `/reports/weekly${qs}`, method: 'GET' })
}
