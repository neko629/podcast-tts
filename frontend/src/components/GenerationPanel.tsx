import React from 'react';
import { Play, Square, RefreshCw } from 'lucide-react';
import type { TaskStatus } from '@/types';

interface GenerationPanelProps {
  rate: number;
  onRateChange: (rate: number) => void;
  isGenerating: boolean;
  onGenerate: () => void;
  onStop?: () => void;
  taskStatus: TaskStatus | null;
  hasSelectedLines: boolean;
}

export const GenerationPanel: React.FC<GenerationPanelProps> = ({
  rate,
  onRateChange,
  isGenerating,
  onGenerate,
  onStop,
  taskStatus,
  hasSelectedLines,
}) => {
  const isCancelled = taskStatus?.status === 'cancelled';

  return (
    <div className="border rounded-lg p-4 bg-gray-50">
      <h3 className="text-sm font-medium text-gray-900 mb-4">生成选项</h3>

      {/* 语速调节 */}
      <div className="mb-4">
        <div className="flex items-center justify-between mb-2">
          <label className="text-sm text-gray-700">语速</label>
          <span className="text-sm font-mono text-blue-600">{rate.toFixed(1)}x</span>
        </div>
        <input
          type="range"
          min="0.3"
          max="1.0"
          step="0.1"
          value={rate}
          onChange={(e) => onRateChange(parseFloat(e.target.value))}
          className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-blue-600"
        />
        <div className="flex justify-between text-xs text-gray-500 mt-1">
          <span>慢</span>
          <span>快</span>
        </div>
      </div>

      {/* 生成/停止按钮 */}
      {isGenerating ? (
        <button
          onClick={onStop}
          className="w-full flex items-center justify-center gap-2 py-3 px-4 rounded-lg font-medium bg-red-600 text-white hover:bg-red-700 transition-colors"
        >
          <Square className="h-5 w-5 fill-current" />
          停止生成
        </button>
      ) : (
        <button
          onClick={onGenerate}
          disabled={!hasSelectedLines}
          className={`w-full flex items-center justify-center gap-2 py-3 px-4 rounded-lg font-medium transition-colors ${
            !hasSelectedLines
              ? 'bg-gray-300 text-gray-500 cursor-not-allowed'
              : 'bg-blue-600 text-white hover:bg-blue-700'
          }`}
        >
          <Play className="h-5 w-5" />
          开始生成音频
        </button>
      )}

      {/* 进度显示 */}
      {taskStatus && (
        <div className={`mt-4 p-3 bg-white rounded border ${isCancelled ? 'border-orange-300 bg-orange-50' : ''}`}>
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm font-medium text-gray-700">
              {taskStatus.status === 'completed'
                ? '✅ 生成完成'
                : taskStatus.status === 'failed'
                ? '❌ 生成失败'
                : taskStatus.status === 'cancelled'
                ? '⚠️ 已取消'
                : '🔄 生成中...'}
            </span>
            <span className="text-xs text-gray-500">
              {taskStatus.completed}/{taskStatus.total}
            </span>
          </div>

          {/* 进度条 */}
          <div className="w-full bg-gray-200 rounded-full h-2.5 mb-2">
            <div
              className={`h-2.5 rounded-full transition-all duration-300 ${
                isCancelled ? 'bg-orange-500' : 'bg-blue-600'
              }`}
              style={{ width: `${taskStatus.progress}%` }}
            />
          </div>

          {taskStatus.message && (
            <p className={`text-xs ${isCancelled ? 'text-orange-600' : 'text-gray-500'}`}>
              {taskStatus.message}
            </p>
          )}
        </div>
      )}
    </div>
  );
};
