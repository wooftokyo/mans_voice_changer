import { useState, useCallback, useRef, useEffect } from 'react'
import { useSearch } from '@tanstack/react-router'
import {
  Upload, Play, Pause, Download, Trash2, Plus, AudioWaveform,
  SkipBack, SkipForward, Volume2, ZoomIn, ZoomOut, RefreshCw,
  ChevronDown, ChevronUp, Clock, Loader2, MousePointer2, Move
} from 'lucide-react'
import { toast } from 'sonner'
import WaveSurfer from 'wavesurfer.js'
import RegionsPlugin from 'wavesurfer.js/dist/plugins/regions.js'
import TimelinePlugin from 'wavesurfer.js/dist/plugins/timeline.js'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Label } from '@/components/ui/label'
import { RadioGroup, RadioGroupItem } from '@/components/ui/radio-group'
import { Slider } from '@/components/ui/slider'
import { Badge } from '@/components/ui/badge'
import { Progress } from '@/components/ui/progress'
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip'
import { Header } from '@/components/layout/header'
import { Main } from '@/components/layout/main'
import { uploadForEditor, applyManualPitch, getAudioUrl, getVideoUrl, getDownloadUrl, getStatus, pollStatus, type Region, type ProcessedSegment, type StatusResponse } from '@/lib/api'

interface RegionData {
  id: string
  start: number
  end: number
  direction: 'down' | 'up'
  shift: number
}

export function WaveformEditor() {
  const search = useSearch({ strict: false })

  const waveformRef = useRef<HTMLDivElement>(null)
  const timelineRef = useRef<HTMLDivElement>(null)
  const videoRef = useRef<HTMLVideoElement>(null)
  const wavesurferRef = useRef<WaveSurfer | null>(null)
  const regionsRef = useRef<RegionsPlugin | null>(null)

  const [taskId, setTaskId] = useState<string | null>((search as { taskId?: string }).taskId || null)
  const [isPlaying, setIsPlaying] = useState(false)
  const [isLoading, setIsLoading] = useState(false)
  const [isProcessing, setIsProcessing] = useState(false)
  const [processingProgress, setProcessingProgress] = useState(0)
  const [processingStep, setProcessingStep] = useState('')
  const [isDragging, setIsDragging] = useState(false)
  const [currentTime, setCurrentTime] = useState(0)
  const [duration, setDuration] = useState(0)
  const [zoom, setZoom] = useState(50)
  const [volume, setVolume] = useState(100)

  // Edit mode: 'select' for region selection, 'navigate' for scrolling/moving
  const [editMode, setEditMode] = useState<'select' | 'navigate'>('select')

  // Selection state
  const [selection, setSelection] = useState<{ start: number; end: number } | null>(null)
  const [direction, setDirection] = useState<'down' | 'up'>('down')
  const [shift, setShift] = useState(3)

  // Regions list
  const [regions, setRegions] = useState<RegionData[]>([])

  // Processed segments from auto-processing (for display only)
  const [processedSegments, setProcessedSegments] = useState<ProcessedSegment[]>([])

  // Store edit mode in a ref for use in event handlers (needed before initialization)
  const editModeRef = useRef(editMode)

  // Initialize WaveSurfer
  useEffect(() => {
    if (!waveformRef.current || !timelineRef.current) return

    const ws = WaveSurfer.create({
      container: waveformRef.current,
      waveColor: '#64748b',
      progressColor: '#3b82f6',
      cursorColor: '#ef4444',
      cursorWidth: 2,
      height: 180, // Increased height
      barWidth: 2,
      barGap: 1,
      barRadius: 2,
      normalize: true,
      backend: 'WebAudio',
    })

    const regionsPlugin = ws.registerPlugin(RegionsPlugin.create())
    ws.registerPlugin(
      TimelinePlugin.create({
        container: timelineRef.current,
        primaryLabelInterval: 5,
        secondaryLabelInterval: 1,
        style: {
          fontSize: '11px',
          color: '#94a3b8',
        },
      })
    )

    // Enable region creation by dragging
    regionsPlugin.enableDragSelection({
      color: 'rgba(234, 179, 8, 0.4)',
    })

    regionsPlugin.on('region-created', (region) => {
      // Ignore region creation in navigate mode
      if (editModeRef.current === 'navigate') {
        region.remove()
        return
      }
      // Clear previous selection region (yellow)
      regionsPlugin.getRegions().forEach((r) => {
        if (r.id !== region.id && r.color?.includes('234, 179, 8')) {
          r.remove()
        }
      })
      setSelection({ start: region.start, end: region.end })
    })

    regionsPlugin.on('region-updated', (region) => {
      if (region.color?.includes('234, 179, 8')) {
        setSelection({ start: region.start, end: region.end })
      }
    })

    ws.on('play', () => {
      setIsPlaying(true)
      if (videoRef.current) {
        videoRef.current.play()
      }
    })
    ws.on('pause', () => {
      setIsPlaying(false)
      if (videoRef.current) {
        videoRef.current.pause()
      }
    })
    ws.on('timeupdate', (time) => {
      setCurrentTime(time)
      // Sync video with audio
      if (videoRef.current && Math.abs(videoRef.current.currentTime - time) > 0.3) {
        videoRef.current.currentTime = time
      }
    })
    ws.on('seeking', (time) => {
      if (videoRef.current) {
        videoRef.current.currentTime = time
      }
    })
    ws.on('ready', () => {
      setDuration(ws.getDuration())
      setIsLoading(false)
    })

    wavesurferRef.current = ws
    regionsRef.current = regionsPlugin

    // Load audio if taskId is provided
    if (taskId) {
      setIsLoading(true)
      ws.load(getAudioUrl(taskId))

      // Fetch processed segments from backend
      getStatus(taskId).then((status) => {
        if (status.processed_segments && status.processed_segments.length > 0) {
          setProcessedSegments(status.processed_segments)
        }
      }).catch(() => {
        // Ignore errors - processed segments are optional
      })
    }

    return () => {
      ws.destroy()
    }
  }, [])

  // Load audio when taskId changes (not on initial load)
  const loadTask = useCallback((newTaskId: string) => {
    if (!wavesurferRef.current) return

    setIsLoading(true)
    wavesurferRef.current.load(getAudioUrl(newTaskId))

    // Clear existing manual regions only (keep processed segments separate)
    regionsRef.current?.clearRegions()
    setRegions([])
    setSelection(null)
    setProcessedSegments([])

    // Fetch processed segments from backend
    getStatus(newTaskId).then((status) => {
      if (status.processed_segments && status.processed_segments.length > 0) {
        setProcessedSegments(status.processed_segments)
      }
    }).catch(() => {
      // Ignore errors - processed segments are optional
    })
  }, [])

  // Update URL when taskId changes
  useEffect(() => {
    if (taskId) {
      window.history.replaceState({}, '', `/editor?taskId=${taskId}`)
    }
  }, [taskId])

  // Display processed segments when waveform is ready and segments are loaded
  useEffect(() => {
    if (processedSegments.length > 0 && regionsRef.current && wavesurferRef.current && duration > 0) {
      // Add processed segments as blue regions (read-only, for display)
      processedSegments.forEach((seg, index) => {
        regionsRef.current?.addRegion({
          id: `processed-${index}`,
          start: seg.start,
          end: seg.end,
          color: 'rgba(59, 130, 246, 0.3)', // Blue color for auto-processed
          drag: false,
          resize: false,
        })
      })
    }
  }, [processedSegments, duration])

  // Update edit mode ref when it changes
  useEffect(() => {
    editModeRef.current = editMode
  }, [editMode])

  // Handle scroll for zoom/pan based on edit mode
  useEffect(() => {
    const container = waveformRef.current
    if (!container || !wavesurferRef.current) return

    const handleWheel = (e: WheelEvent) => {
      e.preventDefault()
      const ws = wavesurferRef.current
      if (!ws) return

      const currentEditMode = editModeRef.current
      const isHorizontal = Math.abs(e.deltaX) > Math.abs(e.deltaY) * 0.5

      if (isHorizontal && e.deltaX !== 0) {
        // Horizontal swipe handling based on mode
        if (currentEditMode === 'navigate') {
          // Navigate mode: scroll through the audio
          const duration = ws.getDuration()
          // Lower sensitivity = slower/more precise movement
          const sensitivity = 0.00005
          const delta = e.deltaX * duration * sensitivity

          // Move playhead in navigate mode
          const currentTime = ws.getCurrentTime()
          const newTime = Math.max(0, Math.min(duration, currentTime + delta))
          ws.setTime(newTime)
        }
        // In select mode, don't handle horizontal scroll - let drag selection work
      } else if (Math.abs(e.deltaY) > 0) {
        // Zoom with vertical scroll
        const currentZoom = ws.options.minPxPerSec || 50
        const zoomDelta = e.deltaY > 0 ? -10 : 10
        const newZoom = Math.max(10, Math.min(500, currentZoom + zoomDelta))
        ws.zoom(newZoom)
        setZoom(newZoom)
      }
    }

    container.addEventListener('wheel', handleWheel, { passive: false })
    return () => container.removeEventListener('wheel', handleWheel)
  }, [])

  // Keyboard shortcuts
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Ignore if typing in an input
      if (e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement) return

      if (e.code === 'Space') {
        e.preventDefault()
        wavesurferRef.current?.playPause()
      } else if (e.code === 'Delete' || e.code === 'Backspace') {
        if (selection) {
          setSelection(null)
          regionsRef.current?.getRegions().forEach((r) => {
            if (r.color?.includes('234, 179, 8')) {
              r.remove()
            }
          })
        }
      } else if (e.code === 'ArrowLeft') {
        e.preventDefault()
        const ws = wavesurferRef.current
        if (ws) {
          ws.setTime(Math.max(0, ws.getCurrentTime() - 5))
        }
      } else if (e.code === 'ArrowRight') {
        e.preventDefault()
        const ws = wavesurferRef.current
        if (ws) {
          ws.setTime(Math.min(ws.getDuration(), ws.getCurrentTime() + 5))
        }
      } else if (e.code === 'KeyM') {
        // Toggle edit mode
        setEditMode(prev => prev === 'select' ? 'navigate' : 'select')
      }
    }

    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [selection])

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(true)
  }, [])

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(false)
  }, [])

  const handleDrop = useCallback(async (e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(false)
    const file = e.dataTransfer.files[0]
    if (file && (file.type.startsWith('video/') || file.type.startsWith('audio/'))) {
      await handleUpload(file)
    } else {
      toast.error('動画または音声ファイルをドロップしてください')
    }
  }, [])

  const handleFileChange = useCallback(async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (file) {
      await handleUpload(file)
    }
  }, [])

  const handleUpload = async (file: File) => {
    setIsLoading(true)
    try {
      const response = await uploadForEditor(file)
      setTaskId(response.task_id)
      loadTask(response.task_id)
      toast.success('ファイルをアップロードしました')
    } catch (error) {
      toast.error('アップロードに失敗しました')
      setIsLoading(false)
    }
  }

  const handleAddRegion = () => {
    if (!selection) {
      toast.error('先に区間を選択してください（波形をドラッグ）')
      return
    }

    const regionId = crypto.randomUUID()
    const color = direction === 'down' ? 'rgba(239, 68, 68, 0.4)' : 'rgba(34, 197, 94, 0.4)'

    // Add visual region
    regionsRef.current?.addRegion({
      id: regionId,
      start: selection.start,
      end: selection.end,
      color,
      drag: false,
      resize: false,
    })

    // Add to list
    setRegions((prev) => [
      ...prev,
      {
        id: regionId,
        start: selection.start,
        end: selection.end,
        direction,
        shift,
      },
    ])

    // Clear selection
    setSelection(null)
    regionsRef.current?.getRegions().forEach((r) => {
      if (r.color?.includes('234, 179, 8')) {
        r.remove()
      }
    })

    toast.success('区間を追加しました')
  }

  const handleRemoveRegion = (id: string) => {
    regionsRef.current?.getRegions().forEach((r) => {
      if (r.id === id) {
        r.remove()
      }
    })
    setRegions((prev) => prev.filter((r) => r.id !== id))
  }

  const handleClearAllRegions = () => {
    regions.forEach((r) => {
      regionsRef.current?.getRegions().forEach((wr) => {
        if (wr.id === r.id) {
          wr.remove()
        }
      })
    })
    setRegions([])
    toast.success('全ての区間を削除しました')
  }

  const handleProcess = async () => {
    if (!taskId || regions.length === 0) {
      toast.error('処理する区間がありません')
      return
    }

    setIsProcessing(true)
    setProcessingProgress(0)
    setProcessingStep('処理を開始中...')

    try {
      // Convert direction + shift to pitch for backend
      const regionData: Region[] = regions.map((r) => ({
        start: r.start,
        end: r.end,
        direction: r.direction,
        shift: r.shift,
        pitch: r.direction === 'down' ? -Math.abs(r.shift) : Math.abs(r.shift),
      }))

      const response = await applyManualPitch({
        task_id: taskId,
        regions: regionData,
      })

      // Poll for completion
      await pollStatus(response.task_id, (status: StatusResponse) => {
        setProcessingProgress(status.progress)
        setProcessingStep(status.step || status.message || '処理中...')
      })

      toast.success('処理が完了しました！')

      // Load the new audio after processing is complete
      setTaskId(response.task_id)
      loadTask(response.task_id)

    } catch (error) {
      toast.error('処理に失敗しました: ' + (error instanceof Error ? error.message : '不明なエラー'))
    } finally {
      setIsProcessing(false)
      setProcessingProgress(0)
      setProcessingStep('')
    }
  }

  const handleDownload = (type: 'video' | 'audio') => {
    if (taskId) {
      window.open(getDownloadUrl(taskId, type), '_blank')
    }
  }

  const handleZoom = (delta: number) => {
    const ws = wavesurferRef.current
    if (!ws) return
    const newZoom = Math.max(10, Math.min(500, zoom + delta))
    ws.zoom(newZoom)
    setZoom(newZoom)
  }

  const handleVolumeChange = (value: number[]) => {
    const ws = wavesurferRef.current
    if (!ws) return
    ws.setVolume(value[0] / 100)
    setVolume(value[0])
  }

  const handleSeek = (delta: number) => {
    const ws = wavesurferRef.current
    if (!ws) return
    const newTime = Math.max(0, Math.min(ws.getDuration(), ws.getCurrentTime() + delta))
    ws.setTime(newTime)
  }

  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60)
    const secs = Math.floor(seconds % 60)
    const ms = Math.floor((seconds % 1) * 100)
    return `${mins}:${secs.toString().padStart(2, '0')}.${ms.toString().padStart(2, '0')}`
  }

  const formatDuration = (seconds: number) => {
    const mins = Math.floor(seconds / 60)
    const secs = Math.floor(seconds % 60)
    return `${mins}:${secs.toString().padStart(2, '0')}`
  }

  return (
    <>
      <Header />
      <Main>
        <div className="mb-4">
          <h1 className="text-2xl font-bold tracking-tight">波形エディタ</h1>
          <p className="text-muted-foreground">
            手動で区間を選択してピッチを変更 · Space: 再生/停止 · ← →: 5秒移動 · M: モード切替
          </p>
        </div>

        {/* Processing Overlay */}
        {isProcessing && (
          <Card className="mb-4 border-blue-500/50 bg-blue-500/5">
            <CardContent className="pt-6">
              <div className="flex items-center gap-4">
                <Loader2 className="h-6 w-6 animate-spin text-blue-500" />
                <div className="flex-1">
                  <div className="flex items-center justify-between mb-2">
                    <span className="font-medium">{processingStep}</span>
                    <span className="text-sm text-muted-foreground">{processingProgress}%</span>
                  </div>
                  <Progress value={processingProgress} className="h-2" />
                </div>
              </div>
            </CardContent>
          </Card>
        )}

        <div className="grid gap-4 lg:grid-cols-4">
          {/* Main Editor Area */}
          <div className="lg:col-span-3 space-y-4">
            {/* Upload Area (when no audio loaded) */}
            {!taskId && (
              <Card className="border-dashed">
                <CardContent className="pt-6">
                  <div
                    className={`relative border-2 border-dashed rounded-xl p-12 text-center cursor-pointer transition-all ${
                      isDragging
                        ? 'border-primary bg-primary/10 scale-[1.02]'
                        : 'border-muted-foreground/25 hover:border-primary/50 hover:bg-muted/50'
                    }`}
                    onDragOver={handleDragOver}
                    onDragLeave={handleDragLeave}
                    onDrop={handleDrop}
                    onClick={() => document.getElementById('editor-file-input')?.click()}
                  >
                    <input
                      id="editor-file-input"
                      type="file"
                      accept="video/*,audio/*"
                      className="hidden"
                      onChange={handleFileChange}
                    />
                    <Upload className="mx-auto h-16 w-16 text-muted-foreground mb-4" />
                    <p className="text-lg font-medium mb-2">
                      ファイルをドロップ
                    </p>
                    <p className="text-sm text-muted-foreground">
                      または クリックして選択 · 動画/音声ファイル対応
                    </p>
                  </div>
                </CardContent>
              </Card>
            )}

            {/* Video + Waveform */}
            {taskId && (
              <Card>
                <CardContent className="p-0">
                  {/* Video Display */}
                  <div className="relative bg-black rounded-t-lg overflow-hidden">
                    <video
                      ref={videoRef}
                      src={getVideoUrl(taskId)}
                      className="w-full max-h-[350px] object-contain"
                      muted
                      playsInline
                    />
                    {/* Video overlay controls */}
                    <div className="absolute bottom-0 left-0 right-0 bg-gradient-to-t from-black/80 to-transparent p-4">
                      <div className="flex items-center gap-2 text-white text-sm">
                        <Clock className="h-4 w-4" />
                        <span className="font-mono">{formatTime(currentTime)}</span>
                        <span className="text-white/50">/</span>
                        <span className="font-mono text-white/70">{formatDuration(duration)}</span>
                      </div>
                    </div>
                  </div>

                  {/* Waveform Section */}
                  <div className="p-4 space-y-3 bg-muted/20">
                    {/* Color Legend & Mode Indicator */}
                    <div className="flex items-center justify-between flex-wrap gap-2">
                      <div className="flex items-center gap-4 text-xs flex-wrap">
                        <div className="flex items-center gap-1.5">
                          <div className="w-3 h-3 rounded bg-yellow-500/40 border border-yellow-500/60" />
                          <span className="text-muted-foreground">選択中</span>
                        </div>
                        {processedSegments.length > 0 && (
                          <div className="flex items-center gap-1.5">
                            <div className="w-3 h-3 rounded bg-blue-500/30 border border-blue-500/50" />
                            <span className="text-muted-foreground">自動処理済 ({processedSegments.length})</span>
                          </div>
                        )}
                        <div className="flex items-center gap-1.5">
                          <div className="w-3 h-3 rounded bg-red-500/40 border border-red-500/60" />
                          <span className="text-muted-foreground">下げる</span>
                        </div>
                        <div className="flex items-center gap-1.5">
                          <div className="w-3 h-3 rounded bg-green-500/40 border border-green-500/60" />
                          <span className="text-muted-foreground">上げる</span>
                        </div>
                      </div>
                      {/* Current Mode Indicator */}
                      <Badge
                        variant="outline"
                        className={`text-xs ${
                          editMode === 'select'
                            ? 'bg-yellow-500/10 border-yellow-500/50 text-yellow-700'
                            : 'bg-blue-500/10 border-blue-500/50 text-blue-700'
                        }`}
                      >
                        {editMode === 'select' ? (
                          <>
                            <MousePointer2 className="h-3 w-3 mr-1" />
                            選択モード
                          </>
                        ) : (
                          <>
                            <Move className="h-3 w-3 mr-1" />
                            移動モード
                          </>
                        )}
                      </Badge>
                    </div>

                    {/* Timeline */}
                    <div ref={timelineRef} className="h-5" />

                    {/* Waveform */}
                    <div
                      ref={waveformRef}
                      className={`rounded-lg bg-background/50 border ${isLoading ? 'opacity-50' : ''}`}
                    />

                    {/* Playback Controls */}
                    <div className="flex items-center gap-2 pt-2 flex-wrap">
                      <TooltipProvider delayDuration={300}>
                        {/* Edit Mode Toggle */}
                        <div className="flex items-center gap-1 bg-muted rounded-lg p-1">
                          <Tooltip>
                            <TooltipTrigger asChild>
                              <Button
                                size="icon"
                                variant={editMode === 'select' ? 'secondary' : 'ghost'}
                                className={`h-8 w-8 ${editMode === 'select' ? 'bg-yellow-500/20 hover:bg-yellow-500/30' : ''}`}
                                onClick={() => setEditMode('select')}
                              >
                                <MousePointer2 className="h-4 w-4" />
                              </Button>
                            </TooltipTrigger>
                            <TooltipContent>選択モード（区間をドラッグで選択）(M)</TooltipContent>
                          </Tooltip>

                          <Tooltip>
                            <TooltipTrigger asChild>
                              <Button
                                size="icon"
                                variant={editMode === 'navigate' ? 'secondary' : 'ghost'}
                                className={`h-8 w-8 ${editMode === 'navigate' ? 'bg-blue-500/20 hover:bg-blue-500/30' : ''}`}
                                onClick={() => setEditMode('navigate')}
                              >
                                <Move className="h-4 w-4" />
                              </Button>
                            </TooltipTrigger>
                            <TooltipContent>移動モード（スワイプで移動）(M)</TooltipContent>
                          </Tooltip>
                        </div>

                        <div className="h-6 w-px bg-border" />

                        {/* Play Controls */}
                        <div className="flex items-center gap-1 bg-muted rounded-lg p-1">
                          <Tooltip>
                            <TooltipTrigger asChild>
                              <Button
                                size="icon"
                                variant="ghost"
                                className="h-8 w-8"
                                onClick={() => handleSeek(-5)}
                                disabled={isLoading}
                              >
                                <SkipBack className="h-4 w-4" />
                              </Button>
                            </TooltipTrigger>
                            <TooltipContent>5秒戻る (←)</TooltipContent>
                          </Tooltip>

                          <Tooltip>
                            <TooltipTrigger asChild>
                              <Button
                                size="icon"
                                variant="ghost"
                                className="h-8 w-8"
                                onClick={() => wavesurferRef.current?.playPause()}
                                disabled={isLoading}
                              >
                                {isPlaying ? <Pause className="h-4 w-4" /> : <Play className="h-4 w-4" />}
                              </Button>
                            </TooltipTrigger>
                            <TooltipContent>再生/停止 (Space)</TooltipContent>
                          </Tooltip>

                          <Tooltip>
                            <TooltipTrigger asChild>
                              <Button
                                size="icon"
                                variant="ghost"
                                className="h-8 w-8"
                                onClick={() => handleSeek(5)}
                                disabled={isLoading}
                              >
                                <SkipForward className="h-4 w-4" />
                              </Button>
                            </TooltipTrigger>
                            <TooltipContent>5秒進む (→)</TooltipContent>
                          </Tooltip>
                        </div>

                        {/* Volume */}
                        <div className="flex items-center gap-2 bg-muted rounded-lg px-2 py-1">
                          <Volume2 className="h-4 w-4 text-muted-foreground" />
                          <Slider
                            value={[volume]}
                            onValueChange={handleVolumeChange}
                            max={100}
                            step={1}
                            className="w-20"
                          />
                        </div>

                        {/* Zoom Controls */}
                        <div className="flex items-center gap-1 bg-muted rounded-lg p-1">
                          <Tooltip>
                            <TooltipTrigger asChild>
                              <Button
                                size="icon"
                                variant="ghost"
                                className="h-8 w-8"
                                onClick={() => handleZoom(-20)}
                              >
                                <ZoomOut className="h-4 w-4" />
                              </Button>
                            </TooltipTrigger>
                            <TooltipContent>縮小</TooltipContent>
                          </Tooltip>
                          <span className="text-xs w-10 text-center text-muted-foreground">{zoom}%</span>
                          <Tooltip>
                            <TooltipTrigger asChild>
                              <Button
                                size="icon"
                                variant="ghost"
                                className="h-8 w-8"
                                onClick={() => handleZoom(20)}
                              >
                                <ZoomIn className="h-4 w-4" />
                              </Button>
                            </TooltipTrigger>
                            <TooltipContent>拡大</TooltipContent>
                          </Tooltip>
                        </div>

                        <div className="flex-1" />

                        {/* Download Buttons */}
                        <div className="flex items-center gap-1">
                          <Tooltip>
                            <TooltipTrigger asChild>
                              <Button
                                variant="outline"
                                size="sm"
                                onClick={() => handleDownload('video')}
                                disabled={!taskId}
                              >
                                <Download className="mr-1.5 h-3.5 w-3.5" />
                                MP4
                              </Button>
                            </TooltipTrigger>
                            <TooltipContent>動画をダウンロード</TooltipContent>
                          </Tooltip>
                          <Tooltip>
                            <TooltipTrigger asChild>
                              <Button
                                variant="outline"
                                size="sm"
                                onClick={() => handleDownload('audio')}
                                disabled={!taskId}
                              >
                                <Download className="mr-1.5 h-3.5 w-3.5" />
                                WAV
                              </Button>
                            </TooltipTrigger>
                            <TooltipContent>音声をダウンロード</TooltipContent>
                          </Tooltip>
                        </div>
                      </TooltipProvider>
                    </div>
                  </div>
                </CardContent>
              </Card>
            )}

            {/* Region Controls */}
            {taskId && (
              <Card>
                <CardHeader className="pb-3">
                  <CardTitle className="text-base">ピッチ編集</CardTitle>
                  <CardDescription>
                    波形をドラッグして区間を選択 → 設定を調整 → リストに追加 → まとめて処理
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="grid gap-4 sm:grid-cols-2">
                    {/* Direction */}
                    <div className="space-y-3">
                      <Label className="text-sm font-medium">ピッチ方向</Label>
                      <RadioGroup
                        value={direction}
                        onValueChange={(v) => setDirection(v as 'down' | 'up')}
                        className="grid grid-cols-2 gap-2"
                      >
                        <Label
                          htmlFor="down"
                          className={`flex items-center justify-center gap-2 p-3 rounded-lg border-2 cursor-pointer transition-all ${
                            direction === 'down'
                              ? 'border-red-500 bg-red-500/10 text-red-600'
                              : 'border-muted hover:border-red-500/50'
                          }`}
                        >
                          <RadioGroupItem value="down" id="down" className="sr-only" />
                          <ChevronDown className="h-4 w-4" />
                          <span>下げる</span>
                        </Label>
                        <Label
                          htmlFor="up"
                          className={`flex items-center justify-center gap-2 p-3 rounded-lg border-2 cursor-pointer transition-all ${
                            direction === 'up'
                              ? 'border-green-500 bg-green-500/10 text-green-600'
                              : 'border-muted hover:border-green-500/50'
                          }`}
                        >
                          <RadioGroupItem value="up" id="up" className="sr-only" />
                          <ChevronUp className="h-4 w-4" />
                          <span>上げる</span>
                        </Label>
                      </RadioGroup>
                    </div>

                    {/* Shift Amount */}
                    <div className="space-y-3">
                      <div className="flex items-center justify-between">
                        <Label className="text-sm font-medium">シフト量</Label>
                        <Badge variant="secondary" className="font-mono">
                          {direction === 'down' ? '-' : '+'}{shift} 半音
                        </Badge>
                      </div>
                      <Slider
                        value={[shift]}
                        onValueChange={([v]) => setShift(v)}
                        min={1}
                        max={12}
                        step={0.5}
                        className="py-2"
                      />
                      <div className="flex justify-between text-xs text-muted-foreground">
                        <span>1</span>
                        <span>6</span>
                        <span>12</span>
                      </div>
                    </div>
                  </div>

                  {/* Selection Info */}
                  {selection ? (
                    <div className="flex items-center gap-3 p-3 bg-yellow-500/10 rounded-lg border border-yellow-500/30">
                      <div className="flex-1">
                        <div className="text-sm font-medium">
                          選択区間: {formatTime(selection.start)} 〜 {formatTime(selection.end)}
                        </div>
                        <div className="text-xs text-muted-foreground">
                          長さ: {(selection.end - selection.start).toFixed(2)}秒
                        </div>
                      </div>
                      <Button onClick={handleAddRegion}>
                        <Plus className="mr-2 h-4 w-4" />
                        追加
                      </Button>
                    </div>
                  ) : (
                    <div className="text-sm text-muted-foreground text-center py-3 border border-dashed rounded-lg">
                      波形をドラッグして区間を選択してください
                    </div>
                  )}
                </CardContent>
              </Card>
            )}
          </div>

          {/* Sidebar */}
          <div className="space-y-4">
            {/* Region List */}
            {taskId && (
              <Card>
                <CardHeader className="pb-3">
                  <div className="flex items-center justify-between">
                    <CardTitle className="text-base">編集リスト</CardTitle>
                    {regions.length > 0 && (
                      <Button
                        variant="ghost"
                        size="sm"
                        className="h-7 text-xs"
                        onClick={handleClearAllRegions}
                      >
                        <Trash2 className="mr-1 h-3 w-3" />
                        全削除
                      </Button>
                    )}
                  </div>
                  <CardDescription>
                    {regions.length === 0
                      ? '区間を追加してください'
                      : `${regions.length} 件の区間`
                    }
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-2">
                  {regions.length === 0 ? (
                    <div className="text-center py-8 text-muted-foreground">
                      <AudioWaveform className="h-8 w-8 mx-auto mb-2 opacity-50" />
                      <p className="text-sm">まだ区間がありません</p>
                    </div>
                  ) : (
                    <>
                      <div className="space-y-2 max-h-[300px] overflow-y-auto pr-1">
                        {regions.map((region) => (
                          <div
                            key={region.id}
                            className={`flex items-center gap-2 p-2.5 rounded-lg text-sm transition-colors ${
                              region.direction === 'down'
                                ? 'bg-red-500/10 border border-red-500/30 hover:bg-red-500/20'
                                : 'bg-green-500/10 border border-green-500/30 hover:bg-green-500/20'
                            }`}
                          >
                            <div className="flex-1 min-w-0">
                              <div className="font-mono text-xs">
                                {formatTime(region.start)} → {formatTime(region.end)}
                              </div>
                              <div className="flex items-center gap-2 mt-1">
                                <Badge
                                  variant="outline"
                                  className={`text-xs ${
                                    region.direction === 'down'
                                      ? 'border-red-500/50 text-red-600'
                                      : 'border-green-500/50 text-green-600'
                                  }`}
                                >
                                  {region.direction === 'down' ? '↓' : '↑'} {region.shift}半音
                                </Badge>
                              </div>
                            </div>
                            <Button
                              size="icon"
                              variant="ghost"
                              className="h-7 w-7 shrink-0"
                              onClick={() => handleRemoveRegion(region.id)}
                            >
                              <Trash2 className="h-3.5 w-3.5" />
                            </Button>
                          </div>
                        ))}
                      </div>

                      <Button
                        className="w-full mt-3"
                        size="lg"
                        onClick={handleProcess}
                        disabled={isLoading || isProcessing || regions.length === 0}
                      >
                        {isProcessing ? (
                          <>
                            <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                            処理中...
                          </>
                        ) : (
                          <>
                            <RefreshCw className="mr-2 h-4 w-4" />
                            まとめて処理 ({regions.length}件)
                          </>
                        )}
                      </Button>
                    </>
                  )}
                </CardContent>
              </Card>
            )}

            {/* Auto-Processed Segments */}
            {taskId && processedSegments.length > 0 && (
              <Card>
                <CardHeader className="pb-3">
                  <CardTitle className="flex items-center gap-2 text-base">
                    <div className="w-2.5 h-2.5 rounded bg-blue-500" />
                    自動処理済み
                  </CardTitle>
                  <CardDescription>{processedSegments.length} 区間</CardDescription>
                </CardHeader>
                <CardContent className="max-h-[200px] overflow-y-auto">
                  <div className="space-y-1">
                    {processedSegments.slice(0, 15).map((seg, index) => (
                      <div
                        key={index}
                        className="flex items-center justify-between p-2 rounded bg-blue-500/10 border border-blue-500/20 text-xs"
                      >
                        <span className="font-mono">
                          {formatTime(seg.start)} → {formatTime(seg.end)}
                        </span>
                        <Badge variant="outline" className="text-blue-600 border-blue-500/50 text-xs">
                          {seg.pitch}半音
                        </Badge>
                      </div>
                    ))}
                    {processedSegments.length > 15 && (
                      <div className="text-center text-xs text-muted-foreground py-2">
                        他 {processedSegments.length - 15} 区間...
                      </div>
                    )}
                  </div>
                </CardContent>
              </Card>
            )}
          </div>
        </div>
      </Main>
    </>
  )
}
