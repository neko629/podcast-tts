import React, { useState, useCallback } from 'react';
import { Upload, FileText, X, Languages, Globe, AlertCircle, Sparkles } from 'lucide-react';
import * as Slider from '@radix-ui/react-slider';
import { subtitleApi } from '@/services/api';

interface SubtitleToolbarProps {
  // 可选的额外样式类
  className?: string;
}

export const SubtitleToolbar: React.FC<SubtitleToolbarProps> = ({ className }) => {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [fileType, setFileType] = useState<'srt' | 'txt' | null>(null);
  const [fileContent, setFileContent] = useState<string>('');
  const [aiProvider, setAiProvider] = useState('deepseek');
  const [selectedLength, setSelectedLength] = useState(15);
  const [isGeneratingPinyin, setIsGeneratingPinyin] = useState(false);
  const [isGeneratingEnglish, setIsGeneratingEnglish] = useState(false);
  const [isProcessingText, setIsProcessingText] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [baseName, setBaseName] = useState<string>('');

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      const file = e.dataTransfer.files[0];
      if (file && (file.name.endsWith('.srt') || file.name.endsWith('.txt'))) {
        handleFileSelect(file);
      } else {
        setError('请上传 .srt 字幕文件或 .txt 文本文件');
      }
    },
    []
  );

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
  };

  const handleFileInput = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      handleFileSelect(file);
    }
  };

  const handleFileSelect = async (file: File) => {
    setError(null);
    setSelectedFile(file);

    // 判断文件类型
    if (file.name.endsWith('.srt')) {
      setFileType('srt');
    } else if (file.name.endsWith('.txt')) {
      setFileType('txt');
    }

    // 读取文件内容
    try {
      const content = await file.text();
      setFileContent(content);

      // 从文件名提取基础名称（去掉文件扩展名）
      const base = file.name.replace(/\.(srt|txt)$/, '');
      setBaseName(base);
    } catch (err) {
      setError('读取文件失败');
      console.error('读取文件失败:', err);
    }
  };

  const handleClear = () => {
    setSelectedFile(null);
    setFileType(null);
    setFileContent('');
    setBaseName('');
    setError(null);
  };

  const handleGeneratePinyin = async () => {
    if (!fileContent) return;

    setIsGeneratingPinyin(true);
    setError(null);

    try {
      const result = await subtitleApi.generatePinyin({
        content: fileContent,
        ai_provider: aiProvider,
        base_name: baseName,
      });

      // 下载拼音字幕文件
      const blob = new Blob([result.content], { type: 'application/x-subrip' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = result.filename;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch (error: any) {
      const msg = error?.response?.data?.detail ?? error?.message ?? '生成拼音字幕失败';
      console.error('生成拼音字幕失败:', error);
      setError(msg);
    } finally {
      setIsGeneratingPinyin(false);
    }
  };

  const handleGenerateEnglish = async () => {
    if (!fileContent) return;

    setIsGeneratingEnglish(true);
    setError(null);

    try {
      const result = await subtitleApi.generateEnglish({
        content: fileContent,
        ai_provider: aiProvider,
        base_name: baseName,
      });

      // 下载英文字幕文件
      const blob = new Blob([result.content], { type: 'application/x-subrip' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = result.filename;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch (error: any) {
      const msg = error?.response?.data?.detail ?? error?.message ?? '生成英文字幕失败';
      console.error('生成英文字幕失败:', error);
      setError(msg);
    } finally {
      setIsGeneratingEnglish(false);
    }
  };

  const handleProcessText = async () => {
    if (!fileContent || fileType !== 'txt') return;

    setIsProcessingText(true);
    setError(null);

    try {
      const result = await subtitleApi.processText({
        text: fileContent,
        max_length: selectedLength, // 使用滑块选择的长度
        ai_provider: aiProvider,
      });

      // 下载处理后的文本文件
      const blob = new Blob([result.processed_text], { type: 'text/plain;charset=utf-8' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${baseName}_processed.txt`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);

    } catch (error: any) {
      const msg = error?.response?.data?.detail ?? error?.message ?? '文本处理失败';
      console.error('文本处理失败:', error);
      setError(msg);
    } finally {
      setIsProcessingText(false);
    }
  };

  return (
    <div className={`bg-white border-b border-gray-200 py-3 ${className || ''}`}>
      <div className="max-w-7xl mx-auto px-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <div className="text-sm font-medium text-gray-700">
              字幕工具
            </div>

            {/* 文件上传区域 */}
            <div className="flex items-center gap-3">
              {!selectedFile ? (
                <div
                  onDrop={handleDrop}
                  onDragOver={handleDragOver}
                  className="border border-dashed border-gray-300 rounded-md p-2 text-center hover:border-blue-500 transition-colors cursor-pointer"
                >
                  <input
                    type="file"
                    accept=".srt,.txt"
                    onChange={handleFileInput}
                    className="hidden"
                    id="file-input"
                  />
                  <label htmlFor="file-input" className="cursor-pointer flex items-center gap-2">
                    <Upload className="h-4 w-4 text-gray-500" />
                    <span className="text-sm text-gray-600">上传字幕 (.srt) 或文本 (.txt)</span>
                  </label>
                </div>
              ) : (
                <div className="flex items-center gap-2 bg-blue-50 border border-blue-200 rounded-md px-3 py-1.5">
                  <FileText className="h-4 w-4 text-blue-500" />
                  <div className="flex items-center gap-2">
                    <div>
                      <p className="text-sm font-medium text-gray-900">
                        {selectedFile.name}
                      </p>
                    </div>
                    <span className="text-xs px-1.5 py-0.5 bg-blue-100 text-blue-700 rounded">
                      {fileType === 'srt' ? 'SRT字幕' : 'TXT文本'}
                    </span>
                  </div>
                  <button
                    onClick={handleClear}
                    className="p-0.5 hover:bg-blue-100 rounded transition-colors"
                  >
                    <X className="h-3 w-3 text-gray-500" />
                  </button>
                </div>
              )}
            </div>

            {/* AI提供商选择 */}
            {selectedFile && (
              <div className="flex items-center gap-2">
                <label className="text-sm text-gray-600">AI引擎：</label>
                <div className="flex gap-1">
                  <button
                    onClick={() => setAiProvider('deepseek')}
                    className={`px-2 py-1 text-xs rounded ${
                      aiProvider === 'deepseek'
                        ? 'bg-blue-100 text-blue-700 border border-blue-300'
                        : 'bg-gray-100 text-gray-700 border border-gray-300 hover:bg-gray-200'
                    }`}
                  >
                    DeepSeek
                  </button>
                  <button
                    onClick={() => setAiProvider('minimax')}
                    className={`px-2 py-1 text-xs rounded ${
                      aiProvider === 'minimax'
                        ? 'bg-blue-100 text-blue-700 border border-blue-300'
                        : 'bg-gray-100 text-gray-700 border border-gray-300 hover:bg-gray-200'
                    }`}
                  >
                    MiniMax
                  </button>
                </div>
              </div>
            )}

            {/* 长度滑块（仅对txt文件显示） */}
            {selectedFile && fileType === 'txt' && (
              <div className="flex items-center gap-2 w-48">
                <label className="text-sm text-gray-600 whitespace-nowrap">长度：{selectedLength}字</label>
                <Slider.Root
                  className="relative flex items-center select-none touch-none w-full h-5"
                  value={[selectedLength]}
                  onValueChange={([value]) => setSelectedLength(value)}
                  min={10}
                  max={40}
                  step={1}
                >
                  <Slider.Track className="bg-gray-200 relative grow rounded-full h-2">
                    <Slider.Range className="absolute bg-blue-500 rounded-full h-full" />
                  </Slider.Track>
                  <Slider.Thumb
                    className="block w-5 h-5 bg-white shadow-lg border-2 border-blue-500 rounded-full hover:bg-blue-50 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2"
                    aria-label="Length"
                  />
                </Slider.Root>
              </div>
            )}
          </div>

          {/* 生成按钮 */}
          {selectedFile && fileType === 'srt' && (
            <div className="flex items-center gap-2">
              <button
                onClick={handleGeneratePinyin}
                disabled={isGeneratingPinyin}
                className="flex items-center gap-2 px-3 py-1.5 text-sm font-medium text-blue-600 bg-blue-50 hover:bg-blue-100 border border-blue-300 rounded-md transition-colors disabled:opacity-50"
              >
                <Languages className="h-4 w-4" />
                {isGeneratingPinyin ? '生成中...' : '生成拼音字幕'}
              </button>
              <button
                onClick={handleGenerateEnglish}
                disabled={isGeneratingEnglish}
                className="flex items-center gap-2 px-3 py-1.5 text-sm font-medium text-indigo-600 bg-indigo-50 hover:bg-indigo-100 border border-indigo-300 rounded-md transition-colors disabled:opacity-50"
              >
                <Globe className="h-4 w-4" />
                {isGeneratingEnglish ? '生成中...' : '生成英文字幕'}
              </button>
            </div>
          )}

          {selectedFile && fileType === 'txt' && (
            <div className="flex items-center gap-2">
              <button
                onClick={handleProcessText}
                disabled={isProcessingText}
                className="flex items-center gap-2 px-3 py-1.5 text-sm font-medium text-emerald-600 bg-emerald-50 hover:bg-emerald-100 border border-emerald-300 rounded-md transition-colors disabled:opacity-50"
              >
                <Sparkles className="h-4 w-4" />
                {isProcessingText ? '处理中...' : 'AI智能断句'}
              </button>
            </div>
          )}
        </div>

        {/* 错误提示 */}
        {error && (
          <div className="mt-2 flex items-start gap-2 rounded-md bg-red-50 p-2 text-sm text-red-700">
            <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
            <span>{error}</span>
          </div>
        )}
      </div>
    </div>
  );
};