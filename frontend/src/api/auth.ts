import { request } from './config'

interface LoginResponse {
  token: string
  is_new_user: boolean
  nickname: string
}

export function wxLogin(code: string, nickname?: string, avatar?: string): Promise<LoginResponse> {
  return request<LoginResponse>({
    url: '/auth/login',
    method: 'POST',
    data: { code, nickname: nickname || '家长', avatar: avatar || '' },
  })
}
