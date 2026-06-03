import { getUserId } from '@/utils/user'

const BASE_URL = 'http://localhost:8000'

export interface QuestionResult {
  question_number: number
  question_text: string
  student_answer: string
  correct_answer: string
  is_correct: boolean
  explanation: string
  topic: string
}

export interface HomeworkUploadResponse {
  homework_id: number
  status: string
  questions: QuestionResult[]
  summary: string
  score: number | null
  encouragement: string
  mistake_count: number
}

export function uploadHomework(options: {
  filePath: string
  subject: string
  grade: number
}): Promise<HomeworkUploadResponse> {
  const userId = getUserId()
  return new Promise((resolve, reject) => {
    uni.uploadFile({
      url: BASE_URL + '/homework/upload',
      filePath: options.filePath,
      name: 'file',
      formData: {
        subject: options.subject,
        grade: String(options.grade),
      },
      header: {
        'X-User-Id': userId,
      },
      success: (res) => {
        if (res.statusCode >= 200 && res.statusCode < 300) {
          resolve(JSON.parse(res.data) as HomeworkUploadResponse)
        } else {
          reject(res)
        }
      },
      fail: reject,
    })
  })
}
