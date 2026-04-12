import React, { useRef, useState, useEffect, useCallback, forwardRef, useImperativeHandle } from 'react';
import { Play, Pause, Download, RefreshCw, CheckCircle, XCircle, Square, Pencil } from 'lucide-react';
import type { AudioFile, Line, TaskStatus } from '@/types';
import { audioApi } from '@/services/api';
import { ConfirmDialog } from './ConfirmDialog';

interface AudioPlayerProps {
  files: AudioFile[];
  lines: Line[];
  voiceConfig: Record<string, string>;
  rate: number;
  onRegenerateComplete?: (taskId: string) => void;
  onTextUpdate?: (index: number, newText: string) => void;
}

const POLL_INTERVAL = 1000;

// 单个音频项组件
interface AudioItemProps {
  file: AudioFile;
  lines: Line[];
  voiceConfig: Record<string, string>;
  rate: number;
  onRegenerateComplete?: (taskId: string) => void;
  onTextUpdate?: (index: number, newText: string) => void;
  isPlaying: boolean;
  onPlay: () => void;
  onPause: () => void;
  onEnded: () => void;
}

const AudioItem = forwardRef<HTMLAudioElement, AudioItemProps>(
  ({ file, lines, voiceConfig, rate, onRegenerateComplete, onTextUpdate, isPlaying, onPlay, onPause, onEnded }, ref) => {
    const audioRef = useRef<HTMLAudioElement>(null);
    const [isDownloading, setIsDownloading] = useState(false);
    const [showConfirm, setShowConfirm] = useState(false);

    // 编辑状态
    const [isEditing, setIsEditing] = useState(false);
    const [editedText, setEditedText] = useState('');

    // 重新生成状态
    const [isRegenerating, setIsRegenerating] = useState(false);
    const [regenerateProgress, setRegenerateProgress] = useState(0);
    const [regenerateMessage, setRegenerateMessage] = useState('');
    const [regenerateTaskId, setRegenerateTaskId] = useState<string | null>(null);

    // 暴露 audioRef 给父组件
    useImperativeHandle(ref, () => audioRef.current!);

    // 当 isPlaying 状态改变时，控制音频播放
    useEffect(() => {
      if (audioRef.current) {
        if (isPlaying) {
          audioRef.current.play().catch(() => {
            // 播放失败，可能需要用户交互
          });
        } else {
          audioRef.current.pause();
        }
      }
    }, [isPlaying]);

    const togglePlay = () => {
      if (isPlaying) {
        onPause();
      } else {
        onPlay();
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

    const handleRegenerate = async (newText?: string) => {
      setShowConfirm(false);
      setIsEditing(false);
      setIsRegenerating(true);
      setRegenerateProgress(0);
      setRegenerateMessage('开始重新生成...');

      // 构造修改后的 lines
      const modifiedLines = newText
        ? lines.map(line => line.index === file.index ? { ...line, text: newText } : line)
        : lines;

      try {
        const response = await audioApi.regenerate(file.index, {
          lines: modifiedLines,
          voice_config: voiceConfig,
          line_indices: [file.index],
          rate,
        });

        setRegenerateTaskId(response.task_id);

        // 更新父组件的文字状态
        if (newText && onTextUpdate) {
          onTextUpdate(file.index, newText);
        }
      } catch (error) {
        console.error('Regenerate failed:', error);
        setRegenerateMessage('启动失败');
        setIsRegenerating(false);
      }
    };

    // 打开编辑对话框
    const handleOpenEdit = () => {
      setEditedText(file.text);
      setIsEditing(true);
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

            // 通知父组件重新生成完成，传递 taskId 以便获取结果
            if (onRegenerateComplete) {
              onRegenerateComplete(regenerateTaskId);
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

          {/* 编辑按钮 */}
          <button
            onClick={handleOpenEdit}
            disabled={isRegenerating}
            title="编辑文字"
            className={`p-2 rounded-full transition-colors ${
              isRegenerating
                ? 'bg-blue-50 text-blue-300 cursor-not-allowed'
                : 'bg-blue-50 text-blue-600 hover:bg-blue-100'
            }`}
          >
            <Pencil className="h-4 w-4" />
          </button>

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
              onEnded={onEnded}
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
          onConfirm={() => handleRegenerate()}
          onCancel={() => setShowConfirm(false)}
        />

        {/* 编辑对话框 */}
        {isEditing && (
          <div className="fixed inset-0 z-50 flex items-center justify-center">
            <div
              className="absolute inset-0 bg-black/50 backdrop-blur-sm"
              onClick={() => setIsEditing(false)}
            />
            <div className="relative bg-white rounded-lg shadow-xl max-w-md w-full mx-4 p-6 animate-in fade-in zoom-in duration-200">
              <h3 className="text-lg font-semibold text-gray-900 mb-4">编辑文字内容</h3>

              {/* 角色名 */}
              <div className="mb-3">
                <label className="block text-xs text-gray-500 mb-1">角色</label>
                <div className="text-sm font-medium text-gray-700">{file.speaker}</div>
              </div>

              {/* 文本编辑框 */}
              <div className="mb-4">
                <label className="block text-xs text-gray-500 mb-1">台词内容</label>
                <textarea
                  value={editedText}
                  onChange={(e) => setEditedText(e.target.value)}
                  rows={3}
                  className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-none"
                  placeholder="输入台词内容"
                />
              </div>

              {/* 按钮组 */}
              <div className="flex gap-3 justify-end">
                <button
                  onClick={() => setIsEditing(false)}
                  className="px-4 py-2 text-sm font-medium text-gray-700 bg-gray-100 hover:bg-gray-200 rounded-lg transition-colors"
                >
                  取消
                </button>
                <button
                  onClick={() => handleRegenerate(editedText)}
                  disabled={!editedText.trim()}
                  className={`px-4 py-2 text-sm font-medium text-white rounded-lg transition-colors ${
                    editedText.trim()
                      ? 'bg-blue-600 hover:bg-blue-700'
                      : 'bg-blue-300 cursor-not-allowed'
                  }`}
                >
                  保存并重新生成
                </button>
              </div>
            </div>
          </div>
        )}
      </>
    );
  }
);

AudioItem.displayName = 'AudioItem';

export const AudioPlayer: React.FC<AudioPlayerProps> = ({
  files,
  lines,
  voiceConfig,
  rate,
  onRegenerateComplete,
  onTextUpdate,
}) => {
  // 自动连续播放开关
  const [autoPlayNext, setAutoPlayNext] = useState(false);
  // 当前正在播放的文件索引
  const [playingIndex, setPlayingIndex] = useState<number | null>(null);

  // 获取成功生成的文件索引列表（用于连续播放）
  const successFiles = files.filter(f => f.success);
  const successIndices = successFiles.map(f => f.index);

  // 播放指定索引的音频
  const handlePlay = useCallback((index: number) => {
    setPlayingIndex(index);
  }, []);

  // 暂停
  const handlePause = useCallback(() => {
    setPlayingIndex(null);
  }, []);

  // 音频播放结束
  const handleEnded = useCallback((currentIndex: number) => {
    if (autoPlayNext) {
      // 找到下一个成功的文件
      const currentPos = successIndices.indexOf(currentIndex);
      if (currentPos !== -1 && currentPos < successIndices.length - 1) {
        // 播放下一个
        const nextIndex = successIndices[currentPos + 1];
        setPlayingIndex(nextIndex);
      } else {
        // 已经是最后一个，停止播放
        setPlayingIndex(null);
      }
    } else {
      setPlayingIndex(null);
    }
  }, [autoPlayNext, successIndices]);

  // 停止播放
  const handleStop = useCallback(() => {
    setPlayingIndex(null);
  }, []);

  if (files.length === 0) {
    return null;
  }

  const successCount = files.filter((f) => f.success).length;

  return (
    <div className="border rounded-lg p-4">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-3">
          <h3 className="text-sm font-medium text-gray-900">生成结果</h3>
          {/* 自动连续播放开关 */}
          <label className="flex items-center gap-1.5 cursor-pointer">
            <input
              type="checkbox"
              checked={autoPlayNext}
              onChange={(e) => setAutoPlayNext(e.target.checked)}
              className="h-4 w-4 text-blue-600 rounded border-gray-300 focus:ring-blue-500"
            />
            <span className="text-xs text-gray-600">连续播放</span>
          </label>
          {/* 停止按钮 - 只在播放时显示 */}
          {playingIndex !== null && (
            <button
              onClick={handleStop}
              className="flex items-center gap-1 px-2 py-1 text-xs bg-red-100 text-red-600 rounded hover:bg-red-200 transition-colors"
            >
              <Square className="h-3 w-3" />
              <span>停止</span>
            </button>
          )}
        </div>
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
            onTextUpdate={onTextUpdate}
            isPlaying={playingIndex === file.index}
            onPlay={() => handlePlay(file.index)}
            onPause={handlePause}
            onEnded={() => handleEnded(file.index)}
          />
        ))}
      </div>
    </div>
  );
};
