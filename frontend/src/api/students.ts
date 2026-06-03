import { request } from './config'

export interface StudentInfo {
  id: number
  name: string
  grade: number
  avatar_tag: string
  is_active: boolean
  created_at: string
}

export function getStudents(): Promise<StudentInfo[]> {
  return request<StudentInfo[]>({ url: '/students', method: 'GET' })
}

export function addStudent(data: { name: string; grade: number; avatar_tag: string }): Promise<StudentInfo> {
  return request<StudentInfo>({ url: '/students', method: 'POST', data })
}

export function updateStudent(id: number, data: Partial<StudentInfo>): Promise<StudentInfo> {
  return request<StudentInfo>({ url: `/students/${id}`, method: 'PUT', data })
}

export function deleteStudent(id: number): Promise<{ ok: boolean }> {
  return request<{ ok: boolean }>({ url: `/students/${id}`, method: 'DELETE' })
}

export function activateStudent(id: number): Promise<StudentInfo> {
  return request<StudentInfo>({ url: `/students/${id}/activate`, method: 'POST' })
}
