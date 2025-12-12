import { createFileRoute } from '@tanstack/react-router'
import { VoiceChanger } from '@/features/voice-changer'

export const Route = createFileRoute('/_authenticated/voice-changer/')({
  component: VoiceChanger,
})
