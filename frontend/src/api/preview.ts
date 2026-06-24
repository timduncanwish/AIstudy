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

function encodeParams(params: Record<string, string | number>) {
  return Object.entries(params)
    .map(([key, value]) => `${encodeURIComponent(key)}=${encodeURIComponent(String(value))}`)
    .join('&')
}
