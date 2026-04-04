import React from 'react';
import type { Line } from '@/types';

interface ScriptViewerProps {
  lines: Line[];
  selectedIndices: number[];
  onToggleSelection: (index: number) => void;
  onSelectAll: () => void;
  onClearSelection: () => void;
}

export const ScriptViewer: React.FC<ScriptViewerProps> = ({
  lines,
  selectedIndices,
  onToggleSelection,
  onSelectAll,
  onClearSelection,
}) => {
  if (lines.length === 0) {
    return (
      <div className="text-center py-8 text-gray-500">
        暂无剧本内容
      </div>
    );
  }

  return (
    <div className="border rounded-lg overflow-hidden">
      <div className="bg-gray-50 px-4 py-2 border-b flex items-center justify-between">
        <span className="text-sm font-medium text-gray-700">
          共 {lines.length} 句台词
        </span>
        <div className="flex gap-2">
          <button
            onClick={onSelectAll}
            className="text-xs px-2 py-1 bg-blue-100 text-blue-700 rounded hover:bg-blue-200 transition-colors"
          >
            全选
          </button>
          <button
            onClick={onClearSelection}
            className="text-xs px-2 py-1 bg-gray-100 text-gray-700 rounded hover:bg-gray-200 transition-colors"
          >
            清空
          </button>
        </div>
      </div>
      <div className="max-h-96 overflow-y-auto">
        {lines.map((line) => (
          <div
            key={line.index}
            onClick={() => onToggleSelection(line.index)}
            className={`px-4 py-3 border-b last:border-b-0 cursor-pointer transition-colors ${
              selectedIndices.includes(line.index)
                ? 'bg-blue-50 border-blue-200'
                : 'hover:bg-gray-50'
            }`}
          >
            <div className="flex items-start gap-3">
              <input
                type="checkbox"
                checked={selectedIndices.includes(line.index)}
                onChange={() => {}}
                className="mt-1 h-4 w-4 text-blue-600 rounded border-gray-300"
              />
              <div className="flex-1">
                <div className="flex items-center gap-2 mb-1">
                  <span className="text-xs text-gray-400 font-mono">
                    {String(line.index).padStart(3, '0')}
                  </span>
                  <span className="text-sm font-medium text-blue-600">
                    {line.speaker}
                  </span>
                </div>
                <p className="text-sm text-gray-800">{line.text}</p>
              </div>
            </div>
          </div>
        ))}
      </div>
      {selectedIndices.length > 0 && (
        <div className="bg-blue-50 px-4 py-2 border-t">
          <span className="text-xs text-blue-700">
            已选择 {selectedIndices.length} 句台词
          </span>
        </div>
      )}
    </div>
  );
};
