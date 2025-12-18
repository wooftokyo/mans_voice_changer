import axios from 'axios'

// In development (Vite), use the proxy. In production (served by Flask), use direct paths.
const api = axios.create({
  baseURL: '',
})

// Types
export interface UploadResponse {
  task_id: string
  status: string
  message: string
}

export interface LogEntry {
  message: string
  type?: 'info' | 'error' | 'warning'
  timestamp?: string
}

export interface ProcessedSegment {
  start: number
  end: number
  pitch: number
}

export interface StatusResponse {
  status: 'processing' | 'complete' | 'completed' | 'error' | 'analyzing'
  progress: number
  message?: string
  step?: string
  output_file?: string
  output_audio?: string
  logs?: LogEntry[]
  processed_segments?: ProcessedSegment[]
}

export interface Region {
  start: number
  end: number
  direction: 'down' | 'up'
  shift: number
  pitch?: number
}

export interface ApplyPitchRequest {
  task_id: string
  regions: Region[]
}

export interface ApplyPitchResponse {
  status: string
  message: string
  task_id: string
  output_file?: string
  output_audio?: string
}

// API Functions
export async function uploadFile(
  file: File,
  options: {
    mode?: 'ai' | 'simple' | 'precision'
    pitchShift?: number
    doubleCheck?: boolean
    onProgress?: (progress: number) => void
  } = {}
): Promise<UploadResponse> {
  const formData = new FormData()
  formData.append('file', file)
  // Backend expects: 'timbre' (AI voice quality), 'simple' (Hz only), 'precision' (speaker separation + CNN)
  const modeMap: Record<string, string> = {
    ai: 'timbre',
    simple: 'simple',
    precision: 'precision'
  }
  const backendMode = modeMap[options.mode || 'ai'] || 'timbre'
  formData.append('mode', backendMode)
  formData.append('pitch', String(options.pitchShift || -3))
  formData.append('double_check', options.doubleCheck ? '1' : '0')

  const response = await api.post<UploadResponse>('/upload', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
    onUploadProgress: (progressEvent) => {
      if (progressEvent.total && options.onProgress) {
        const progress = Math.round((progressEvent.loaded / progressEvent.total) * 100)
        options.onProgress(progress)
      }
    },
  })
  return response.data
}

export async function uploadForEditor(
  file: File,
  onProgress?: (progress: number) => void
): Promise<UploadResponse> {
  const formData = new FormData()
  formData.append('file', file)

  const response = await api.post<UploadResponse>('/upload_for_editor', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
    onUploadProgress: (progressEvent) => {
      if (progressEvent.total && onProgress) {
        const progress = Math.round((progressEvent.loaded / progressEvent.total) * 100)
        onProgress(progress)
      }
    },
  })
  return response.data
}

export async function getStatus(taskId: string): Promise<StatusResponse> {
  const response = await api.get<StatusResponse>(`/status/${taskId}`)
  return response.data
}

export async function applyManualPitch(
  request: ApplyPitchRequest
): Promise<ApplyPitchResponse> {
  const response = await api.post<ApplyPitchResponse>('/apply_manual_pitch', request)
  return response.data
}

export function getDownloadUrl(taskId: string, type: 'video' | 'audio' = 'video'): string {
  return `/download/${taskId}?type=${type}`
}

export function getAudioUrl(taskId: string): string {
  return `/audio/${taskId}`
}

export function getVideoUrl(taskId: string): string {
  return `/video/${taskId}`
}

// Polling helper
export async function pollStatus(
  taskId: string,
  onProgress: (status: StatusResponse) => void,
  intervalMs = 1000
): Promise<StatusResponse> {
  return new Promise((resolve, reject) => {
    const poll = async () => {
      try {
        const status = await getStatus(taskId)
        onProgress(status)

        if (status.status === 'completed' || status.status === 'complete') {
          resolve(status)
        } else if (status.status === 'error') {
          reject(new Error(status.message || status.step || 'エラーが発生しました'))
        } else {
          setTimeout(poll, intervalMs)
        }
      } catch (error) {
        reject(error)
      }
    }
    poll()
  })
}

export default api
