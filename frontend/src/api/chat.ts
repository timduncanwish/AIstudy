import { request } from './config'

interface ChatRequest {
  messages: { role: string; content: string }[]
  subject: string
  grade: number
  user_id?: number
  session_id?: string
}

interface ChatResponse {
  reply: string
}

export function chat(data: ChatRequest): Promise<ChatResponse> {
  return request<ChatResponse>({ url: '/chat', method: 'POST', data })
}

export interface ChatHistoryMessage {
  role: string
  content: string
  created_at: string
}

export interface ChatHistoryResponse {
  session_id: string
  subject: string
  grade: number
  messages: ChatHistoryMessage[]
}

export interface ChatSessionSummary {
  session_id: string
  subject: string
  grade: number
  last_message: string
  message_count: number
  created_at: string
}

export interface ChatSessionListResponse {
  sessions: ChatSessionSummary[]
}

export function getChatSessions(userId: number): Promise<ChatSessionListResponse> {
  return request<ChatSessionListResponse>({ url: `/chat/sessions/${userId}`, method: 'GET' })
}

export function getChatHistory(userId: number, sessionId: string): Promise<ChatHistoryResponse> {
  return request<ChatHistoryResponse>({ url: `/chat/history/${userId}/${sessionId}`, method: 'GET' })
}

export function deleteChatHistory(userId: number, sessionId: string): Promise<{ detail: string }> {
  return request<{ detail: string }>({ url: `/chat/history/${userId}/${sessionId}`, method: 'DELETE' })
}
