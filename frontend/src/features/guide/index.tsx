import {
  Upload,
  AudioWaveform,
  MousePointer2,
  Move,
  Keyboard,
  CheckCircle,
  Settings,
} from 'lucide-react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Header } from '@/components/layout/header'
import { Main } from '@/components/layout/main'

export function Guide() {
  return (
    <>
      <Header />
      <Main>
        <div className="mb-6">
          <h1 className="text-2xl font-bold tracking-tight">使い方ガイド</h1>
          <p className="text-muted-foreground">
            男性ボイスチェンジャーの使い方を説明します
          </p>
        </div>

        <div className="space-y-6 max-w-4xl">
          {/* Overview */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <CheckCircle className="h-5 w-5 text-green-500" />
                このツールでできること
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <p>
                動画や音声ファイル内の<strong>男性の声だけ</strong>を自動検出し、ピッチを下げて変換します。
                女性の声はそのまま残ります。
              </p>
              <div className="flex flex-wrap gap-2">
                <Badge variant="secondary">AI声質判定（CNN）</Badge>
                <Badge variant="secondary">精度95-98%</Badge>
                <Badge variant="secondary">手動編集も可能</Badge>
              </div>
            </CardContent>
          </Card>

          {/* Basic Usage */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Upload className="h-5 w-5 text-blue-500" />
                基本的な使い方
              </CardTitle>
              <CardDescription>自動処理で簡単に変換</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-3">
                <div className="flex gap-3">
                  <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-blue-500 text-white text-sm font-bold">
                    1
                  </div>
                  <div>
                    <p className="font-medium">ファイルをアップロード</p>
                    <p className="text-sm text-muted-foreground">
                      「アップロード＆処理」ページで動画または音声ファイルをドラッグ＆ドロップ
                    </p>
                  </div>
                </div>

                <div className="flex gap-3">
                  <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-blue-500 text-white text-sm font-bold">
                    2
                  </div>
                  <div>
                    <p className="font-medium">処理モードを選択</p>
                    <p className="text-sm text-muted-foreground">
                      <strong>AI声質判定（推奨）</strong>: CNNで男性/女性を高精度判定<br />
                      <strong>簡易ピッチ検出</strong>: 周波数ベースで高速処理
                    </p>
                  </div>
                </div>

                <div className="flex gap-3">
                  <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-blue-500 text-white text-sm font-bold">
                    3
                  </div>
                  <div>
                    <p className="font-medium">ピッチシフト量を調整</p>
                    <p className="text-sm text-muted-foreground">
                      -3〜-5半音がおすすめ。マイナスで低く、プラスで高くなります
                    </p>
                  </div>
                </div>

                <div className="flex gap-3">
                  <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-blue-500 text-white text-sm font-bold">
                    4
                  </div>
                  <div>
                    <p className="font-medium">処理開始 → ダウンロード</p>
                    <p className="text-sm text-muted-foreground">
                      処理完了後、MP4（動画）またはWAV（音声のみ）をダウンロード
                    </p>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Editor Usage */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <AudioWaveform className="h-5 w-5 text-purple-500" />
                波形エディタの使い方
              </CardTitle>
              <CardDescription>手動で細かく調整したい場合</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <p className="text-sm text-muted-foreground">
                自動処理では対応できない部分や、追加で調整したい場合に使用します。
              </p>

              <div className="grid gap-4 sm:grid-cols-2">
                <div className="space-y-2">
                  <div className="flex items-center gap-2">
                    <MousePointer2 className="h-4 w-4 text-yellow-500" />
                    <span className="font-medium">選択モード</span>
                  </div>
                  <p className="text-sm text-muted-foreground">
                    波形をドラッグして区間を選択し、ピッチを上げる/下げる設定を追加
                  </p>
                </div>

                <div className="space-y-2">
                  <div className="flex items-center gap-2">
                    <Move className="h-4 w-4 text-blue-500" />
                    <span className="font-medium">移動モード</span>
                  </div>
                  <p className="text-sm text-muted-foreground">
                    横スワイプで波形を移動。長い音声ファイルの閲覧に便利
                  </p>
                </div>
              </div>

              <div className="rounded-lg border p-3 bg-muted/30">
                <p className="font-medium mb-2">エディタの色の意味</p>
                <div className="flex flex-wrap gap-3 text-sm">
                  <div className="flex items-center gap-1.5">
                    <div className="w-3 h-3 rounded bg-yellow-500/40 border border-yellow-500/60" />
                    <span>選択中の区間</span>
                  </div>
                  <div className="flex items-center gap-1.5">
                    <div className="w-3 h-3 rounded bg-blue-500/30 border border-blue-500/50" />
                    <span>自動処理済み</span>
                  </div>
                  <div className="flex items-center gap-1.5">
                    <div className="w-3 h-3 rounded bg-red-500/40 border border-red-500/60" />
                    <span>ピッチを下げる</span>
                  </div>
                  <div className="flex items-center gap-1.5">
                    <div className="w-3 h-3 rounded bg-green-500/40 border border-green-500/60" />
                    <span>ピッチを上げる</span>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Keyboard Shortcuts */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Keyboard className="h-5 w-5 text-orange-500" />
                キーボードショートカット
              </CardTitle>
              <CardDescription>波形エディタで使用可能</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="grid gap-2 sm:grid-cols-2">
                <div className="flex items-center justify-between p-2 rounded bg-muted/50">
                  <span className="text-sm">再生/停止</span>
                  <Badge variant="outline" className="font-mono">Space</Badge>
                </div>
                <div className="flex items-center justify-between p-2 rounded bg-muted/50">
                  <span className="text-sm">5秒戻る</span>
                  <Badge variant="outline" className="font-mono">←</Badge>
                </div>
                <div className="flex items-center justify-between p-2 rounded bg-muted/50">
                  <span className="text-sm">5秒進む</span>
                  <Badge variant="outline" className="font-mono">→</Badge>
                </div>
                <div className="flex items-center justify-between p-2 rounded bg-muted/50">
                  <span className="text-sm">モード切り替え</span>
                  <Badge variant="outline" className="font-mono">M</Badge>
                </div>
                <div className="flex items-center justify-between p-2 rounded bg-muted/50">
                  <span className="text-sm">選択を削除</span>
                  <Badge variant="outline" className="font-mono">Delete</Badge>
                </div>
                <div className="flex items-center justify-between p-2 rounded bg-muted/50">
                  <span className="text-sm">ズーム</span>
                  <Badge variant="outline" className="font-mono">縦スクロール</Badge>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Tips */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Settings className="h-5 w-5 text-gray-500" />
                Tips
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <div className="space-y-2">
                <p className="font-medium">ダブルチェックを有効にする</p>
                <p className="text-sm text-muted-foreground">
                  AI声質判定モードで「ダブルチェック」をオンにすると、追加の検証で精度が向上します。
                  処理時間は長くなりますが、より正確な結果が得られます。
                </p>
              </div>

              <div className="space-y-2">
                <p className="font-medium">処理後にエディタで確認</p>
                <p className="text-sm text-muted-foreground">
                  自動処理の結果が完璧でない場合は、波形エディタで追加の調整ができます。
                  処理完了後に「エディタ」ボタンをクリックしてください。
                </p>
              </div>

              <div className="space-y-2">
                <p className="font-medium">長い動画の場合</p>
                <p className="text-sm text-muted-foreground">
                  30分以上の動画は処理に時間がかかります。
                  ブラウザを閉じずにお待ちください。
                </p>
              </div>
            </CardContent>
          </Card>
        </div>
      </Main>
    </>
  )
}
