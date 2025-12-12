import { createFileRoute } from '@tanstack/react-router'
import { WaveformEditor } from '@/features/editor'

interface EditorSearchParams {
  taskId?: string
}

export const Route = createFileRoute('/_authenticated/editor/')({
  validateSearch: (search: Record<string, unknown>): EditorSearchParams => {
    return {
      taskId: typeof search.taskId === 'string' ? search.taskId : undefined,
    }
  },
  component: WaveformEditor,
})
