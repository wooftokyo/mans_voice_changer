import {
  Upload,
  AudioWaveform,
  Palette,
  Mic,
  LayoutDashboard,
  HelpCircle,
} from 'lucide-react'
import { type SidebarData } from '../types'

export const sidebarData: SidebarData = {
  user: {
    name: 'User',
    email: '',
    avatar: '',
  },
  teams: [
    {
      name: 'ボイスチェンジャー',
      logo: Mic,
      plan: '男性の声をピッチダウン',
    },
  ],
  navGroups: [
    {
      title: 'メイン',
      items: [
        {
          title: 'ダッシュボード',
          url: '/',
          icon: LayoutDashboard,
        },
        {
          title: 'アップロード＆処理',
          url: '/voice-changer',
          icon: Upload,
        },
        {
          title: '波形エディタ',
          url: '/editor',
          icon: AudioWaveform,
        },
      ],
    },
    {
      title: 'ヘルプ',
      items: [
        {
          title: '使い方',
          url: '/guide',
          icon: HelpCircle,
        },
      ],
    },
    {
      title: '設定',
      items: [
        {
          title: '外観',
          url: '/settings/appearance',
          icon: Palette,
        },
      ],
    },
  ],
}
