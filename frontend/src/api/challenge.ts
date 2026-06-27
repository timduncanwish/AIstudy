import { request } from './config'

export interface ChallengeOption {
  text: string
  index: number
}

export interface ChallengeQuestion {
  word: string
  target_word: string
  pinyin: string
  level: number
  level_name: string
  question_text: string
  hint: string
  options: ChallengeOption[]
  correct_answer: string
}

export interface SubmitAnswerResponse {
  correct: boolean
  correct_answer: string
  new_level: number
  points_earned: number
  streak: number
  badge_earned: string | null
  encouragement: string
}

export interface DailyTaskResponse {
  task_date: string
  subject: string
  total: number
  completed: number
  remaining: number
  words: string[]
}

export interface BadgeDetail {
  id: string
  name: string
  desc: string
}

export interface UserStatsResponse {
  total_points: number
  streak_days: number
  words_mastered: number
  badges: BadgeDetail[]
}

export function getDailyTask(subject: string, grade: number): Promise<DailyTaskResponse> {
  return request<DailyTaskResponse>({
    url: `/challenge/daily?subject=${subject}&grade=${grade}`,
    method: 'GET',
  })
}

export function getChallengeQuestion(subject: string, grade: number): Promise<ChallengeQuestion | null> {
  return request<ChallengeQuestion | null>({
    url: `/challenge/question?subject=${subject}&grade=${grade}`,
    method: 'GET',
  })
}

export function submitChallengeAnswer(data: {
  word: string
  subject: string
  grade: number
  level: number
  answer: string
  streak: number
}): Promise<SubmitAnswerResponse> {
  return request<SubmitAnswerResponse>({
    url: '/challenge/submit',
    method: 'POST',
    data,
  })
}

export function getUserStats(): Promise<UserStatsResponse> {
  return request<UserStatsResponse>({ url: '/challenge/stats', method: 'GET' })
}
