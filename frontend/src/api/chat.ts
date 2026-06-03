import { request } from './config'

interface ChatRequest {
  messages: { role: string; content: string }[]
  subject: string
  grade: number
}

interface ChatResponse {
  reply: string
}

export function chat(data: ChatRequest): Promise<ChatResponse> {
  return request<ChatResponse>({ url: '/chat', method: 'POST', data })
}
