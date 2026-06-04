import { request } from './config'
import type { MistakeItem } from './mistakes'

export interface KnowledgeTopic {
  topic: string
  subject: string
  count: number
  avg_mastery: number
  latest_mistake_at: string
}

export interface KnowledgeMapResponse {
  subjects: Record<string, KnowledgeTopic[]>
}

export function getKnowledgeMap(): Promise<KnowledgeMapResponse> {
  return request<KnowledgeMapResponse>({ url: '/mistakes/knowledge-map', method: 'GET' })
}

export interface TopicDetailResponse {
  topic: string
  subject: string
  count: number
  avg_mastery: number
  mistakes: MistakeItem[]
}

export function getTopicDetail(subject: string, topic: string): Promise<TopicDetailResponse> {
  return request<TopicDetailResponse>({
    url: `/mistakes/topic/${subject}/${encodeURIComponent(topic)}`,
    method: 'GET',
  })
}

export interface PracticeQuestion {
  question: string
  options: string[]
  correct_index: number
  explanation: string
}

export interface PracticeResponse {
  topic: string
  questions: PracticeQuestion[]
}

export function generatePractice(subject: string, topic: string): Promise<PracticeResponse> {
  return request<PracticeResponse>({
    url: '/mistakes/practice',
    method: 'POST',
    data: { subject, topic },
  })
}
