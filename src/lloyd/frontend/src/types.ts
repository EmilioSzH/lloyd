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

export interface InboxItem {
  id: string
  type: 'review' | 'blocked' | 'question' | 'failed' | 'spec_approval'
  project_id: string
  title: string
  created_at: string
  priority: 'high' | 'normal' | 'low'
  context: Record<string, unknown>
  actions: string[]
  resolved: boolean
  resolved_at: string | null
  resolution: string | null
}

export interface BrainstormSession {
  session_id: string
  initial_idea: string
  clarifications: Array<{ question: string; answer: string }>
  spec: string | null
  status: 'in_progress' | 'spec_ready' | 'approved' | 'queued'
  created_at: string
}

export interface LearningEntry {
  id: string
  category: string
  title: string
  description: string
  context: string
  confidence: number
  frequency: number
  last_applied: string | null
  created_at: string
  tags: string[]
}
