export interface Story {
  id: string
  title: string
  description: string
  acceptanceCriteria: string[]
  priority: number
  passes: boolean
  attempts: number
  notes: string
  dependencies: string[]
}

export interface StatusResponse {
  project_name: string
  description: string
  status: string
  total_stories: number
  completed_stories: number
  stories: Story[]
}

export interface ProgressResponse {
  content: string
  lines: string[]
}

export interface WebSocketMessage {
  type: string
  message?: string
  phase?: string
  iteration?: number
  status?: string
  stories?: Story[]
}
