export type TaskStatus = 'todo' | 'in_progress' | 'completed'
export type SummaryStatus = 'pending' | 'success' | 'failed'

export interface Language {
  id: number
  name: string
}

export interface Task {
  id: number
  language: string
  title: string
  description: string
  status: TaskStatus
  summary_status: SummaryStatus
  summary_error?: string | null
  completed_at?: string | null
  created_at: string
  updated_at: string
}

export interface TaskCreatePayload {
  language: string
  title: string
  description: string
}
