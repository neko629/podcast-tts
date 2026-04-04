import React, { useRef, useState, useEffect } from 'react';
import { Play, Pause, Download, RefreshCw, CheckCircle, XCircle } from 'lucide-react';
import type { AudioFile, Line, TaskStatus } from '@/types';
import { audioApi } from '@/services/api';
import { ConfirmDialog } from './ConfirmDialog';

interface AudioPlayerProps {
  files: AudioFile[];
  lines: Line[];
  voiceConfig: Record<string, string>;
  rate: number;
  onRegenerateComplete?: () => void;
}

const POLL_INTERVAL = 1000;

const AudioItem: React.FC<{
  file: AudioFile;
  lines: Line[];
  voiceConfig: Record<string, string>;
  rate: number;
  onRegenerateComplete?: () => void;
}> = ({ file, lines, voiceConfig, rate, onRegenerateComplete }) => {
  const audioRef = useRef<HTMLAudioElement>(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [isDownloading, setIsDownloading] = useState(false);
  const [showConfirm, setShowConfirm] = useState(false);

  // 重新生成状态
  const [isRegenerating, setIsRegenerating] = useState(false);
  const [regenerateProgress, setRegenerateProgress] = useState(0);
  const [regenerateMessage, setRegenerateMessage] = useState('');
  const [regenerateTaskId, setRegenerateTaskId] = useState<string | null>(null);

  const togglePlay = () => {
    if (audioRef.current) {
      if (isPlaying) {
        audioRef.current.pause();
      } else {
        audioRef.current.play();
      }
      setIsPlaying(!isPlaying);
    }
  };

  const handleDownload = async () => {
    if (!file.filename || isDownloading) return;

    setIsDownloading(true);
    try {
      const blob = await audioApi.downloadFile(file.filename);
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = file.filename;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (error) {
      console.error('Download failed:', error);
    } finally {
      setIsDownloading(false);
    }
  };

  const handleRegenerate = async () => {
    setShowConfirm(false);
    setIsRegenerating(true);
    setRegenerateProgress(0);
    setRegenerateMessage('开始重新生成...');

    try {
      const response = await audioApi.regenerate(file.index, {
        lines,
        voice_config: voiceConfig,
        line_indices: [file.index],
        rate,
      });

      setRegenerateTaskId(response.task_id);
    } catch (error) {
      console.error('Regenerate failed:', error);
      setRegenerateMessage('启动失败');
      setIsRegenerating(false);
    }
  };

  // 轮询重新生成任务状态
  useEffect(() => {
    if (!regenerateTaskId || !isRegenerating) return;

    const pollStatus = async () => {
      try {
        const status: TaskStatus = await audioApi.getTaskStatus(regenerateTaskId);
        setRegenerateProgress(status.progress);
        setRegenerateMessage(status.message || '');

        if (status.status === 'completed' || status.status === 'failed') {
          setIsRegenerating(false);
          setRegenerateTaskId(null);

          // 通知父组件重新生成完成
          if (onRegenerateComplete) {
            onRegenerateComplete();
          }
        }
      } catch (error) {
        console.error('Failed to get task status:', error);
      }
    };

    pollStatus();
    const interval = setInterval(pollStatus, POLL_INTERVAL);

    return () => clearInterval(interval);
  }, [regenerateTaskId, isRegenerating, onRegenerateComplete]);

  return (
    <>
      <div className="flex items-center gap-2 p-3 bg-white border rounded-lg">
        {/* 播放按钮 */}
        <button
          onClick={togglePlay}
          disabled={!file.success || isRegenerating}
          className={`p-2 rounded-full ${
            file.success && !isRegenerating
              ? 'bg-blue-100 text-blue-600 hover:bg-blue-200'
              : 'bg-gray-100 text-gray-400 cursor-not-allowed'
          }`}
        >
          {isPlaying ? (
            <Pause className="h-4 w-4" />
          ) : (
            <Play className="h-4 w-4" />
          )}
        </button>

        {/* 信息 */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <span className="text-xs text-gray-400 font-mono">
              {String(file.index).padStart(3, '0')}
            </span>
            <span className="text-sm font-medium text-gray-900 truncate">
              {file.speaker}
            </span>
            {file.success ? (
              <CheckCircle className="h-4 w-4 text-green-500" />
            ) : (
              <XCircle className="h-4 w-4 text-red-500" />
            )}
          </div>
          <p className="text-xs text-gray-500 truncate">{file.text}</p>

          {/* 重新生成进度条 */}
          {isRegenerating && (
            <div className="mt-2">
              <div className="flex items-center gap-2">
                <div className="flex-1 h-1.5 bg-gray-200 rounded-full overflow-hidden">
                  <div
                    className="h-full bg-orange-500 transition-all duration-300"
                    style={{ width: `${regenerateProgress}%` }}
                  />
                </div>
                <span className="text-xs text-orange-600 font-medium">
                  {regenerateProgress}%
                </span>
              </div>
              {regenerateMessage && (
                <p className="text-xs text-gray-500 mt-1">{regenerateMessage}</p>
              )}
            </div>
          )}

          {!file.success && file.error && !isRegenerating && (
            <p className="text-xs text-red-500">{file.error}</p>
          )}
        </div>

        {/* 重新生成按钮 */}
        <button
          onClick={() => setShowConfirm(true)}
          disabled={isRegenerating}
          title="重新生成"
          className={`p-2 rounded-full transition-colors ${
            isRegenerating
              ? 'bg-orange-50 text-orange-300 cursor-not-allowed'
              : 'bg-orange-50 text-orange-600 hover:bg-orange-100'
          }`}
        >
          <RefreshCw className={`h-4 w-4 ${isRegenerating ? 'animate-spin' : ''}`} />
        </button>

        {/* 下载按钮 */}
        <button
          onClick={handleDownload}
          disabled={!file.success || isDownloading || isRegenerating}
          title="下载"
          className={`p-2 rounded-full ${
            file.success && !isDownloading && !isRegenerating
              ? 'bg-gray-100 text-gray-600 hover:bg-gray-200'
              : 'bg-gray-50 text-gray-300 cursor-not-allowed'
          }`}
        >
          <Download className="h-4 w-4" />
        </button>

        {/* 隐藏音频元素 */}
        {file.url && (
          <audio
            ref={audioRef}
            src={file.url}
            onEnded={() => setIsPlaying(false)}
            className="hidden"
          />
        )}
      </div>

      {/* 确认对话框 */}
      <ConfirmDialog
        isOpen={showConfirm}
        title="确认重新生成"
        message={`确定要重新生成第 ${file.index} 句 "${file.speaker}" 的音频吗？\n\n这会删除原有的音频文件并重新生成同名文件。`}
        confirmText="重新生成"
        cancelText="取消"
        onConfirm={handleRegenerate}
        onCancel={() => setShowConfirm(false)}
      />
    </>
  );
};

export const AudioPlayer: React.FC<AudioPlayerProps> = ({
  files,
  lines,
  voiceConfig,
  rate,
  onRegenerateComplete,
}) => {
  if (files.length === 0) {
    return null;
  }

  const successCount = files.filter((f) => f.success).length;

  return (
    <div className="border rounded-lg p-4">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-sm font-medium text-gray-900">生成结果</h3>
        <span className="text-xs text-gray-500">
          成功 {successCount}/{files.length}
        </span>
      </div>

      <div className="space-y-2 max-h-80 overflow-y-auto">
        {files.map((file) => (
          <AudioItem
            key={file.index}
            file={file}
            lines={lines}
            voiceConfig={voiceConfig}
            rate={rate}
            onRegenerateComplete={onRegenerateComplete}
          />
        ))}
      </div>
    </div>
  );
};
