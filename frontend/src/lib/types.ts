export interface User {
  id: number
  email: string
  role: string
  is_active: boolean
}

export interface PageSummary {
  id: number
  fb_page_id: string
  name: string
  system_prompt: string
  closing_message: string
  llm_model: string
  is_active: boolean
  has_access_token: boolean
  my_role: string
  knowledge_count: number
  created_at: string
}

export interface KnowledgeItem {
  id: number
  page_id: number
  title: string
  content: string
  source: string
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface ConversationSummary {
  id: number
  psid: string
  started_at: string
  last_message_at: string
  message_count: number
  last_message_preview: string
}

export interface Message {
  id: number
  direction: 'in' | 'out'
  text: string
  attachments: unknown[]
  created_at: string
}

export interface ConversationDetail {
  id: number
  psid: string
  started_at: string
  last_message_at: string
  messages: Message[]
}

export interface Suggestion {
  id: number
  page_id: number
  question: string
  answer: string
  occurrences: number
  status: 'pending' | 'approved' | 'rejected'
  created_at: string
  reviewed_at: string | null
  knowledge_item_id: number | null
}

export interface Member {
  user_id: number
  email: string
  role: string
}

export interface TokenResponse {
  access_token: string
  token_type: string
  user: User
}
