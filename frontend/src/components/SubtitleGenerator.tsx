import React, { useState } from 'react';
import { FileText, Download, X, AlertCircle, Languages, Globe } from 'lucide-react';
import * as Slider from '@radix-ui/react-slider';
import type { Line } from '@/types';
import { subtitleApi } from '@/services/api';

interface SubtitleGeneratorProps {
  lines: Line[];
  generatedFiles: { index: number; speaker: string }[];
  scriptName?: string;
}

export const SubtitleGenerator: React.FC<SubtitleGeneratorProps> = ({
  lines,
  generatedFiles,
  scriptName,
}) => {
  const [isOpen, setIsOpen] = useState(false);
  const [selectedLength, setSelectedLength] = useState(14);
  const [aiProvider, setAiProvider] = useState('deepseek');
  const [preview, setPreview] = useState<string[]>([]);
  const [totalSubtitles, setTotalSubtitles] = useState(0);
  const [isLoading, setIsLoading] = useState(false);
  const [isGenerating, setIsGenerating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [hasPreviewed, setHasPreviewed] = useState(false);
  const [generatedContent, setGeneratedContent] = useState<string | null>(null);
  const [baseFileName, setBaseFileName] = useState<string>('');
  const [isGeneratingPinyin, setIsGeneratingPinyin] = useState(false);
  const [isGeneratingEnglish, setIsGeneratingEnglish] = useState(false);

  // 获取需要生成字幕的台词（只取已生成音频的）
  const linesToSubtitle = lines.filter((line) =>
    generatedFiles.some((f) => f.index === line.index)
  );

  const handleOpen = async () => {
    setIsOpen(true);
    setError(null);
    setPreview([]);
    setHasPreviewed(false);
    setGeneratedContent(null);
    setBaseFileName('');
  };

  const handlePreview = async () => {
    setIsLoading(true);
    setError(null);

    try {
      const result = await subtitleApi.preview({
        lines: linesToSubtitle,
        max_length: selectedLength,
        max_preview_lines: 5,
        use_ai: true,
        ai_provider: aiProvider,
      });
      setPreview(result.preview);
      setTotalSubtitles(result.total_subtitles);
      setHasPreviewed(true);
    } catch (error: any) {
      const msg = error?.response?.data?.detail ?? error?.message ?? '预览失败';
      console.error('预览失败:', error);
      setError(msg);
    } finally {
      setIsLoading(false);
    }
  };

  const handleLengthChange = (newLength: number) => {
    setSelectedLength(newLength);
    setHasPreviewed(false);
    setPreview([]);
  };

  const handleGenerate = async () => {
    setIsGenerating(true);
    setError(null);

    try {
      const result = await subtitleApi.generate({
        lines: linesToSubtitle,
        max_length: selectedLength,
        use_ai: true,
        ai_provider: aiProvider,
        script_name: scriptName,
      });

      // 保存内容并下载
      setGeneratedContent(result.content);
      // 保存基础文件名（去掉 .srt 后缀）
      const baseName = result.filename.replace('.srt', '');
      setBaseFileName(baseName);

      // 下载文件
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
      const msg = error?.response?.data?.detail ?? error?.message ?? '生成字幕失败';
      console.error('生成字幕失败:', error);
      setError(msg);
    } finally {
      setIsGenerating(false);
    }
  };

  const handleGeneratePinyin = async () => {
    if (!generatedContent) return;

    setIsGeneratingPinyin(true);
    setError(null);

    try {
      const result = await subtitleApi.generatePinyin({
        content: generatedContent,
        ai_provider: aiProvider,
        base_name: baseFileName,
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
    if (!generatedContent) return;

    setIsGeneratingEnglish(true);
    setError(null);

    try {
      const result = await subtitleApi.generateEnglish({
        content: generatedContent,
        ai_provider: aiProvider,
        base_name: baseFileName,
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

  if (linesToSubtitle.length === 0) {
    return null;
  }

  return (
    <>
      <button
        onClick={handleOpen}
        className="flex items-center gap-2 px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors"
      >
        <FileText className="h-4 w-4" />
        生成字幕
      </button>

      {isOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center">
          {/* 遮罩层 */}
          <div
            className="absolute inset-0 bg-black/50 backdrop-blur-sm"
            onClick={() => { setIsOpen(false); setGeneratedContent(null); }}
          />

          {/* 对话框 */}
          <div className="relative bg-white rounded-lg shadow-xl max-w-lg w-full mx-4 p-6 animate-in fade-in zoom-in duration-200">
            {/* 关闭按钮 */}
            <button
              onClick={() => { setIsOpen(false); setGeneratedContent(null); }}
              className="absolute top-4 right-4 p-1 hover:bg-gray-100 rounded-full transition-colors"
            >
              <X className="h-5 w-5 text-gray-400" />
            </button>

            {/* 标题 */}
            <div className="flex items-center gap-3 mb-6">
              <div className="p-2 bg-green-100 rounded-lg">
                <FileText className="h-6 w-6 text-green-600" />
              </div>
              <div>
                <h3 className="text-lg font-semibold text-gray-900">生成字幕文件</h3>
                <p className="text-sm text-gray-500">
                  将生成 {linesToSubtitle.length} 条台词的 SRT 字幕
                </p>
              </div>
            </div>

            {/* 长度选择 */}
            <div className="mb-6">
              <div className="flex items-center justify-between mb-2">
                <label className="text-sm font-medium text-gray-700">
                  每行字幕长度
                </label>
                <span className="text-sm font-medium text-blue-600">
                  {selectedLength} 字/行
                </span>
              </div>
              <Slider.Root
                className="relative flex items-center select-none touch-none w-full h-5"
                value={[selectedLength]}
                onValueChange={([value]) => handleLengthChange(value)}
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
              <div className="flex justify-between mt-1 text-xs text-gray-400">
                <span>10</span>
                <span>40</span>
              </div>
            </div>

            {/* AI 提供商选择 */}
            <div className="mb-6">
              <div className="flex items-center justify-between mb-2">
                <label className="text-sm font-medium text-gray-700">
                  AI 断句引擎
                </label>
              </div>
              <div className="flex gap-3">
                <button
                  onClick={() => setAiProvider('deepseek')}
                  className={`flex-1 px-4 py-2 text-sm font-medium rounded-lg border transition-colors ${
                    aiProvider === 'deepseek'
                      ? 'bg-blue-50 border-blue-500 text-blue-700'
                      : 'bg-white border-gray-300 text-gray-700 hover:bg-gray-50'
                  }`}
                >
                  DeepSeek
                </button>
                <button
                  onClick={() => setAiProvider('minimax')}
                  className={`flex-1 px-4 py-2 text-sm font-medium rounded-lg border transition-colors ${
                    aiProvider === 'minimax'
                      ? 'bg-blue-50 border-blue-500 text-blue-700'
                      : 'bg-white border-gray-300 text-gray-700 hover:bg-gray-50'
                  }`}
                >
                  MiniMax
                </button>
              </div>
            </div>

            {/* 错误提示 */}
            {error && (
              <div className="mb-4 flex items-start gap-2 rounded-lg bg-red-50 p-3 text-sm text-red-700">
                <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
                <span>{error}</span>
              </div>
            )}

            {/* 预览 */}
            <div className="mb-6">
              <div className="flex items-center justify-between mb-2">
                <label className="text-sm font-medium text-gray-700">
                  预览（前几行）
                </label>
                <div className="flex items-center gap-2">
                  {hasPreviewed && (
                    <span className="text-sm text-gray-500">
                      共 {totalSubtitles} 条字幕
                    </span>
                  )}
                  <button
                    onClick={handlePreview}
                    disabled={isLoading}
                    className="px-3 py-1 text-xs font-medium text-blue-600 border border-blue-300 rounded-md hover:bg-blue-50 transition-colors disabled:opacity-50"
                  >
                    {isLoading ? '加载中...' : hasPreviewed ? '重新预览' : 'AI 预览'}
                  </button>
                </div>
              </div>
              <div className="bg-gray-50 rounded-lg p-4 max-h-48 overflow-y-auto">
                {isLoading ? (
                  <p className="text-sm text-gray-500">加载中...</p>
                ) : hasPreviewed && preview.length > 0 ? (
                  <div className="space-y-2">
                    {preview.map((line, idx) => (
                      <div key={idx} className="text-sm text-gray-700">
                        {idx + 1}. {line}
                      </div>
                    ))}
                    {totalSubtitles > preview.length && (
                      <p className="text-sm text-gray-400 pt-2">
                        ... 还有 {totalSubtitles - preview.length} 条字幕
                      </p>
                    )}
                  </div>
                ) : (
                  <p className="text-sm text-gray-400">点击「AI 预览」查看断句效果</p>
                )}
              </div>
            </div>

            {/* 按钮 */}
            <div className="flex gap-3 justify-end">
              <button
                onClick={() => { setIsOpen(false); setGeneratedContent(null); }}
                className="px-4 py-2 text-sm font-medium text-gray-700 bg-gray-100 hover:bg-gray-200 rounded-lg transition-colors"
              >
                取消
              </button>
              {generatedContent && (
                <>
                  <button
                    onClick={handleGeneratePinyin}
                    disabled={isGeneratingPinyin}
                    className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-blue-600 bg-blue-50 hover:bg-blue-100 border border-blue-300 rounded-lg transition-colors disabled:opacity-50"
                  >
                    <Languages className="h-4 w-4" />
                    {isGeneratingPinyin ? '生成中...' : '生成拼音字幕'}
                  </button>
                  <button
                    onClick={handleGenerateEnglish}
                    disabled={isGeneratingEnglish}
                    className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-indigo-600 bg-indigo-50 hover:bg-indigo-100 border border-indigo-300 rounded-lg transition-colors disabled:opacity-50"
                  >
                    <Globe className="h-4 w-4" />
                    {isGeneratingEnglish ? '生成中...' : '生成英文字幕'}
                  </button>
                </>
              )}
              <button
                onClick={handleGenerate}
                disabled={isGenerating}
                className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-white bg-green-600 hover:bg-green-700 rounded-lg transition-colors disabled:opacity-50"
              >
                <Download className="h-4 w-4" />
                {isGenerating ? '生成中...' : '生成并下载'}
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
};
