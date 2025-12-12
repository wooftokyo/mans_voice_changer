import { useState, useEffect } from 'react'
import {
  Upload,
  AudioWaveform,
  Trash2,
  Download,
  Clock,
  CheckCircle,
  XCircle,
  Activity,
  HardDrive,
  Mic,
  TrendingUp
} from 'lucide-react'
import { toast } from 'sonner'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Progress } from '@/components/ui/progress'
import { Badge } from '@/components/ui/badge'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Header } from '@/components/layout/header'
import { Main } from '@/components/layout/main'
import { useProjectHistory, type Project } from '@/features/voice-changer/use-project-history'
import { getDownloadUrl } from '@/lib/api'

interface DashboardStats {
  totalProcessed: number
  successCount: number
  failedCount: number
  totalDuration: number
  avgProcessingTime: number
  aiModeCount: number
  simpleModeCount: number
}

export function Dashboard() {
  const { projects, deleteProject, clearProjects } = useProjectHistory()
  const [stats, setStats] = useState<DashboardStats>({
    totalProcessed: 0,
    successCount: 0,
    failedCount: 0,
    totalDuration: 0,
    avgProcessingTime: 0,
    aiModeCount: 0,
    simpleModeCount: 0,
  })

  // Calculate statistics from project history
  useEffect(() => {
    const successCount = projects.filter(p => p.status === 'completed').length
    const failedCount = projects.filter(p => p.status === 'error').length
    const aiModeCount = projects.filter(p => p.mode === 'ai').length
    const simpleModeCount = projects.filter(p => p.mode === 'simple').length

    setStats({
      totalProcessed: projects.length,
      successCount,
      failedCount,
      totalDuration: 0, // Would need to track this in project data
      avgProcessingTime: 0,
      aiModeCount,
      simpleModeCount,
    })
  }, [projects])

  const handleNavigate = (path: string) => {
    window.location.href = path
  }

  const handleDownload = (project: Project, type: 'video' | 'audio') => {
    window.open(getDownloadUrl(project.taskId, type), '_blank')
  }

  const handleOpenEditor = (project: Project) => {
    window.location.href = `/editor?taskId=${project.taskId}`
  }

  const successRate = stats.totalProcessed > 0
    ? Math.round((stats.successCount / stats.totalProcessed) * 100)
    : 0

  const formatDate = (dateString: string) => {
    const date = new Date(dateString)
    return date.toLocaleDateString('ja-JP', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    })
  }

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'completed':
        return <Badge variant="default" className="bg-green-500">完了</Badge>
      case 'error':
        return <Badge variant="destructive">エラー</Badge>
      case 'processing':
        return <Badge variant="secondary">処理中</Badge>
      default:
        return <Badge variant="outline">{status}</Badge>
    }
  }

  const getModeBadge = (mode: string) => {
    switch (mode) {
      case 'ai':
        return <Badge variant="outline" className="border-blue-500 text-blue-500">AI声質</Badge>
      case 'simple':
        return <Badge variant="outline" className="border-orange-500 text-orange-500">簡易</Badge>
      default:
        return <Badge variant="outline">{mode}</Badge>
    }
  }

  return (
    <>
      <Header />
      <Main>
        <div className="mb-6">
          <h1 className="text-2xl font-bold tracking-tight">ダッシュボード</h1>
          <p className="text-muted-foreground">
            男性ボイスチェンジャーの概要と履歴
          </p>
        </div>

        {/* Statistics Cards */}
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4 mb-6">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">総処理数</CardTitle>
              <Activity className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{stats.totalProcessed}</div>
              <p className="text-xs text-muted-foreground">
                ファイル処理済み
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">成功率</CardTitle>
              <TrendingUp className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{successRate}%</div>
              <Progress value={successRate} className="mt-2" />
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">AI声質モード</CardTitle>
              <Mic className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{stats.aiModeCount}</div>
              <p className="text-xs text-muted-foreground">
                高精度処理
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">簡易モード</CardTitle>
              <Clock className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{stats.simpleModeCount}</div>
              <p className="text-xs text-muted-foreground">
                高速処理
              </p>
            </CardContent>
          </Card>
        </div>

        <div className="grid gap-6 lg:grid-cols-3">
          {/* Quick Actions */}
          <Card className="lg:col-span-1">
            <CardHeader>
              <CardTitle>クイックアクション</CardTitle>
              <CardDescription>よく使う機能へのショートカット</CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              <Button
                className="w-full justify-start"
                onClick={() => handleNavigate('/voice-changer')}
              >
                <Upload className="mr-2 h-4 w-4" />
                新規ファイルをアップロード
              </Button>
              <Button
                variant="outline"
                className="w-full justify-start"
                onClick={() => handleNavigate('/editor')}
              >
                <AudioWaveform className="mr-2 h-4 w-4" />
                波形エディタを開く
              </Button>
            </CardContent>
          </Card>

          {/* Status Summary */}
          <Card className="lg:col-span-2">
            <CardHeader>
              <CardTitle>処理サマリー</CardTitle>
              <CardDescription>処理結果の内訳</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                <div className="flex items-center">
                  <CheckCircle className="h-5 w-5 text-green-500 mr-3" />
                  <div className="flex-1">
                    <div className="flex items-center justify-between">
                      <span className="text-sm font-medium">成功</span>
                      <span className="text-sm text-muted-foreground">{stats.successCount}件</span>
                    </div>
                    <Progress
                      value={stats.totalProcessed > 0 ? (stats.successCount / stats.totalProcessed) * 100 : 0}
                      className="mt-1 h-2"
                    />
                  </div>
                </div>
                <div className="flex items-center">
                  <XCircle className="h-5 w-5 text-red-500 mr-3" />
                  <div className="flex-1">
                    <div className="flex items-center justify-between">
                      <span className="text-sm font-medium">失敗</span>
                      <span className="text-sm text-muted-foreground">{stats.failedCount}件</span>
                    </div>
                    <Progress
                      value={stats.totalProcessed > 0 ? (stats.failedCount / stats.totalProcessed) * 100 : 0}
                      className="mt-1 h-2 [&>div]:bg-red-500"
                    />
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Project History */}
        <Card className="mt-6">
          <CardHeader className="flex flex-row items-center justify-between">
            <div>
              <CardTitle>プロジェクト履歴</CardTitle>
              <CardDescription>最近の処理履歴（最大20件、ローカル保存）</CardDescription>
            </div>
            {projects.length > 0 && (
              <Button
                variant="outline"
                size="sm"
                onClick={() => {
                  if (confirm('履歴をすべて削除しますか？')) {
                    clearProjects()
                    toast.success('履歴を削除しました')
                  }
                }}
              >
                <Trash2 className="mr-2 h-4 w-4" />
                履歴をクリア
              </Button>
            )}
          </CardHeader>
          <CardContent>
            {projects.length === 0 ? (
              <div className="text-center py-12">
                <HardDrive className="mx-auto h-12 w-12 text-muted-foreground mb-4" />
                <p className="text-muted-foreground mb-4">
                  処理履歴がありません
                </p>
                <Button onClick={() => handleNavigate('/voice-changer')}>
                  <Upload className="mr-2 h-4 w-4" />
                  最初のファイルをアップロード
                </Button>
              </div>
            ) : (
              <ScrollArea className="h-[400px]">
                <div className="space-y-3">
                  {projects.map((project) => (
                    <div
                      key={project.id}
                      className="flex items-center justify-between p-4 rounded-lg border bg-card hover:bg-accent/50 transition-colors"
                    >
                      <div className="flex items-center gap-4 flex-1 min-w-0">
                        <div className="flex-shrink-0">
                          <Mic className="h-8 w-8 text-muted-foreground" />
                        </div>
                        <div className="flex-1 min-w-0">
                          <p className="font-medium truncate">{project.filename}</p>
                          <div className="flex items-center gap-2 mt-1 flex-wrap">
                            {getStatusBadge(project.status)}
                            {getModeBadge(project.mode)}
                            <span className="text-xs text-muted-foreground">
                              ピッチ: {project.pitchShift > 0 ? '+' : ''}{project.pitchShift}半音
                            </span>
                          </div>
                          <p className="text-xs text-muted-foreground mt-1">
                            {formatDate(project.createdAt)}
                          </p>
                        </div>
                      </div>
                      <div className="flex items-center gap-2 flex-shrink-0 ml-4">
                        {project.status === 'completed' && (
                          <>
                            <Button
                              size="sm"
                              variant="outline"
                              onClick={() => handleDownload(project, 'video')}
                              title="MP4ダウンロード"
                            >
                              <Download className="h-4 w-4" />
                            </Button>
                            <Button
                              size="sm"
                              variant="outline"
                              onClick={() => handleOpenEditor(project)}
                              title="エディタで開く"
                            >
                              <AudioWaveform className="h-4 w-4" />
                            </Button>
                          </>
                        )}
                        <Button
                          size="sm"
                          variant="ghost"
                          onClick={() => {
                            deleteProject(project.id)
                            toast.success('削除しました')
                          }}
                          title="削除"
                        >
                          <Trash2 className="h-4 w-4" />
                        </Button>
                      </div>
                    </div>
                  ))}
                </div>
              </ScrollArea>
            )}
          </CardContent>
        </Card>

        {/* Tips */}
        <Card className="mt-6">
          <CardHeader>
            <CardTitle>使い方のヒント</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
              <div className="p-4 rounded-lg bg-muted/50">
                <h4 className="font-medium mb-2">AI声質判定モード</h4>
                <p className="text-sm text-muted-foreground">
                  CNNで声質を分析し、高精度（95-98%）で男性の声を検出します。処理に時間がかかりますが、精度が高いです。
                </p>
              </div>
              <div className="p-4 rounded-lg bg-muted/50">
                <h4 className="font-medium mb-2">簡易モード</h4>
                <p className="text-sm text-muted-foreground">
                  ピッチ（Hz）のみで判定します。高速（数秒〜数十秒）ですが、高い声の男性を誤判定する場合があります。
                </p>
              </div>
              <div className="p-4 rounded-lg bg-muted/50">
                <h4 className="font-medium mb-2">波形エディタ</h4>
                <p className="text-sm text-muted-foreground">
                  自動処理後に手動で微調整が可能です。区間を選択してピッチを上げ下げできます。
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
      </Main>
    </>
  )
}
