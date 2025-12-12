import { useState, useCallback } from 'react'
import { Upload, Download, AudioWaveform } from 'lucide-react'
import { toast } from 'sonner'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Progress } from '@/components/ui/progress'
import { Label } from '@/components/ui/label'
import { RadioGroup, RadioGroupItem } from '@/components/ui/radio-group'
import { Slider } from '@/components/ui/slider'
import { Switch } from '@/components/ui/switch'
import { Header } from '@/components/layout/header'
import { Main } from '@/components/layout/main'
import { ScrollArea } from '@/components/ui/scroll-area'
import { uploadFile, pollStatus, getDownloadUrl, type StatusResponse, type LogEntry } from '@/lib/api'
import { useProjectHistory } from './use-project-history'

type ProcessingState = 'idle' | 'uploading' | 'processing' | 'completed' | 'error'

export function VoiceChanger() {
  const [file, setFile] = useState<File | null>(null)
  const [mode, setMode] = useState<'ai' | 'simple'>('ai')
  const [pitchShift, setPitchShift] = useState(-3)
  const [doubleCheck, setDoubleCheck] = useState(true)
  const [state, setState] = useState<ProcessingState>('idle')
  const [progress, setProgress] = useState(0)
  const [message, setMessage] = useState('')
  const [logs, setLogs] = useState<LogEntry[]>([])
  const [taskId, setTaskId] = useState<string | null>(null)
  const [isDragging, setIsDragging] = useState(false)

  const { addProject } = useProjectHistory()

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(true)
  }, [])

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(false)
  }, [])

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(false)
    const droppedFile = e.dataTransfer.files[0]
    if (droppedFile && (droppedFile.type.startsWith('video/') || droppedFile.type.startsWith('audio/'))) {
      setFile(droppedFile)
    } else {
      toast.error('動画または音声ファイルをドロップしてください')
    }
  }, [])

  const handleFileChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFile = e.target.files?.[0]
    if (selectedFile) {
      setFile(selectedFile)
    }
  }, [])

  const handleProcess = async () => {
    if (!file) return

    setState('uploading')
    setProgress(0)
    setMessage('ファイルをアップロード中...')
    setLogs([])

    try {
      const response = await uploadFile(file, {
        mode,
        pitchShift,
        doubleCheck,
        onProgress: (p) => {
          setProgress(p)
          setMessage(`アップロード中: ${p}%`)
        },
      })

      setTaskId(response.task_id)
      setState('processing')
      setMessage('処理中...')

      await pollStatus(response.task_id, (s: StatusResponse) => {
        setProgress(s.progress)
        setMessage(s.step || s.message || '処理中...')
        if (s.logs) {
          setLogs(s.logs)
        }
      })

      setState('completed')
      setMessage('処理が完了しました！')

      // Add to project history
      addProject({
        filename: file.name,
        taskId: response.task_id,
        mode,
        pitchShift,
        status: 'completed',
      })

      toast.success('処理が完了しました！')
    } catch (error) {
      setState('error')
      setMessage(error instanceof Error ? error.message : 'エラーが発生しました')
      toast.error('処理に失敗しました')
    }
  }

  const handleDownload = (type: 'video' | 'audio') => {
    if (taskId) {
      window.open(getDownloadUrl(taskId, type), '_blank')
    }
  }

  const handleOpenEditor = () => {
    if (taskId) {
      window.location.href = `/editor?taskId=${taskId}`
    } else {
      window.location.href = '/editor'
    }
  }

  return (
    <>
      <Header />
      <Main>
        <div className="mb-6">
          <h1 className="text-2xl font-bold tracking-tight">男性ボイスチェンジャー</h1>
          <p className="text-muted-foreground">
            AI検出で男性の声だけをピッチダウン
          </p>
        </div>

        <div className="space-y-6 max-w-4xl">
          {/* Upload & Settings */}
          <div className="space-y-6">
            {/* File Upload */}
            <Card>
              <CardHeader>
                <CardTitle>ファイルアップロード</CardTitle>
                <CardDescription>
                  動画または音声ファイルをドラッグ＆ドロップ、またはクリックして選択
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div
                  className={`relative border-2 border-dashed rounded-lg p-8 text-center cursor-pointer transition-colors ${
                    isDragging
                      ? 'border-primary bg-primary/5'
                      : file
                      ? 'border-green-500 bg-green-500/5'
                      : 'border-muted-foreground/25 hover:border-primary/50'
                  }`}
                  onDragOver={handleDragOver}
                  onDragLeave={handleDragLeave}
                  onDrop={handleDrop}
                  onClick={() => document.getElementById('file-input')?.click()}
                >
                  <input
                    id="file-input"
                    type="file"
                    accept="video/*,audio/*"
                    className="hidden"
                    onChange={handleFileChange}
                  />
                  <Upload className="mx-auto h-12 w-12 text-muted-foreground mb-4" />
                  {file ? (
                    <p className="text-sm font-medium">{file.name}</p>
                  ) : (
                    <p className="text-sm text-muted-foreground">
                      ここに動画または音声ファイルをドロップ
                    </p>
                  )}
                </div>
              </CardContent>
            </Card>

            {/* Processing Options */}
            <Card>
              <CardHeader>
                <CardTitle>処理オプション</CardTitle>
              </CardHeader>
              <CardContent className="space-y-6">
                <div className="space-y-3">
                  <Label>検出モード</Label>
                  <RadioGroup value={mode} onValueChange={(v) => setMode(v as 'ai' | 'simple')}>
                    <div className="flex items-center space-x-2">
                      <RadioGroupItem value="ai" id="ai" />
                      <Label htmlFor="ai" className="cursor-pointer">
                        AI声質判定（推奨、精度95-98%）
                      </Label>
                    </div>
                    <div className="flex items-center space-x-2">
                      <RadioGroupItem value="simple" id="simple" />
                      <Label htmlFor="simple" className="cursor-pointer">
                        簡易ピッチ検出（高速、精度70-80%）
                      </Label>
                    </div>
                  </RadioGroup>
                </div>

                <div className="space-y-3">
                  <div className="flex items-center justify-between">
                    <Label>ピッチシフト（半音）</Label>
                    <span className="text-sm font-medium">{pitchShift}</span>
                  </div>
                  <Slider
                    value={[pitchShift]}
                    onValueChange={([v]) => setPitchShift(v)}
                    min={-12}
                    max={12}
                    step={0.5}
                  />
                  <p className="text-xs text-muted-foreground">
                    マイナス = 低く、プラス = 高く
                  </p>
                </div>

                {mode === 'ai' && (
                  <div className="flex items-center justify-between">
                    <div className="space-y-0.5">
                      <Label>ダブルチェック</Label>
                      <p className="text-xs text-muted-foreground">
                        追加検証で精度向上
                      </p>
                    </div>
                    <Switch checked={doubleCheck} onCheckedChange={setDoubleCheck} />
                  </div>
                )}

                <Button
                  className="w-full"
                  size="lg"
                  disabled={!file || state === 'uploading' || state === 'processing'}
                  onClick={handleProcess}
                >
                  {state === 'uploading' || state === 'processing' ? '処理中...' : '処理開始'}
                </Button>
              </CardContent>
            </Card>

            {/* Progress */}
            {(state === 'uploading' || state === 'processing' || state === 'completed') && (
              <Card>
                <CardHeader>
                  <CardTitle>進捗</CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="space-y-2">
                    <div className="flex items-center justify-between text-sm">
                      <span>{message}</span>
                      <span className="font-medium">{progress}%</span>
                    </div>
                    <Progress value={progress} />
                  </div>

                  {/* Logs */}
                  {logs.length > 0 && (
                    <ScrollArea className="h-40 rounded-md border bg-muted/30 p-3">
                      <div className="space-y-1 text-xs font-mono">
                        {logs.map((log, i) => (
                          <div
                            key={i}
                            className={`${
                              log.type === 'error'
                                ? 'text-red-500'
                                : log.type === 'warning'
                                ? 'text-yellow-500'
                                : 'text-muted-foreground'
                            }`}
                          >
                            {log.message}
                          </div>
                        ))}
                      </div>
                    </ScrollArea>
                  )}

                  {state === 'completed' && (
                    <div className="flex gap-2">
                      <Button onClick={() => handleDownload('video')} className="flex-1">
                        <Download className="mr-2 h-4 w-4" />
                        MP4ダウンロード
                      </Button>
                      <Button onClick={() => handleDownload('audio')} variant="outline" className="flex-1">
                        <Download className="mr-2 h-4 w-4" />
                        WAVダウンロード
                      </Button>
                      <Button onClick={() => handleOpenEditor()} variant="secondary">
                        <AudioWaveform className="mr-2 h-4 w-4" />
                        エディタ
                      </Button>
                    </div>
                  )}
                </CardContent>
              </Card>
            )}
          </div>
        </div>
      </Main>
    </>
  )
}
