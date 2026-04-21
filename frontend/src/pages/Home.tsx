import React, { useState, useEffect, useCallback } from 'react';
import { Mic, FileText, Settings, Music } from 'lucide-react';
import { FileUpload } from '@/components/FileUpload';
import { ScriptViewer } from '@/components/ScriptViewer';
import { VoiceConfig } from '@/components/VoiceConfig';
import { GenerationPanel } from '@/components/GenerationPanel';
import { AudioPlayer } from '@/components/AudioPlayer';
import { SubtitleGenerator } from '@/components/SubtitleGenerator';
import { SubtitleToolbar } from '@/components/SubtitleToolbar';
import { scriptApi, voiceApi, audioApi } from '@/services/api';
import type { Line, Voice, TaskStatus, AudioFile } from '@/types';

const POLL_INTERVAL = 1000; // 轮询间隔1秒

export const Home: React.FC = () => {
  // 文件上传状态
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [isUploading, setIsUploading] = useState(false);

  // 剧本数据
  const [lines, setLines] = useState<Line[]>([]);
  const [characters, setCharacters] = useState<string[]>([]);
  const [selectedIndices, setSelectedIndices] = useState<number[]>([]);

  // 语音配置
  const [availableVoices, setAvailableVoices] = useState<Voice[]>([]);
  const [voiceConfig, setVoiceConfig] = useState<Record<string, string>>({});

  // 生成选项
  const [rate, setRate] = useState(0.6);
  const [isGenerating, setIsGenerating] = useState(false);
  const [taskStatus, setTaskStatus] = useState<TaskStatus | null>(null);
  const [taskId, setTaskId] = useState<string | null>(null);
  const [generatedFiles, setGeneratedFiles] = useState<AudioFile[]>([]);

  // 批量重新生成失败项
  const [isRegeneratingFailed, setIsRegeneratingFailed] = useState(false);
  const [failedTaskId, setFailedTaskId] = useState<string | null>(null);
  const [failedTaskStatus, setFailedTaskStatus] = useState<TaskStatus | null>(null);

  // 加载可用语音
  useEffect(() => {
    const loadVoices = async () => {
      try {
        const voices = await voiceApi.getVoices();
        setAvailableVoices(voices);
      } catch (error) {
        console.error('Failed to load voices:', error);
      }
    };
    loadVoices();
  }, []);

  // 处理文件上传
  const handleFileSelect = useCallback(async (file: File) => {
    setSelectedFile(file);
    setIsUploading(true);

    try {
      const result = await scriptApi.uploadScript(file);
      setLines(result.lines);
      setCharacters(result.characters);
      setSelectedIndices(result.lines.map((l) => l.index));

      // 初始化语音配置（尝试为不同性别分配不同声音）
      const initialConfig: Record<string, string> = {};
      result.characters.forEach((char, idx) => {
        // 简单启发式：第一个角色用女声，第二个用男声
        if (idx === 0) {
          initialConfig[char] = 'zh-CN-XiaoxiaoNeural';
        } else if (idx === 1) {
          initialConfig[char] = 'zh-CN-YunxiNeural';
        }
      });
      setVoiceConfig(initialConfig);
    } catch (error) {
      console.error('Failed to upload script:', error);
      alert('上传失败，请检查文件格式');
    } finally {
      setIsUploading(false);
    }
  }, []);

  // 清除文件
  const handleClearFile = useCallback(() => {
    setSelectedFile(null);
    setLines([]);
    setCharacters([]);
    setSelectedIndices([]);
    setVoiceConfig({});
    setGeneratedFiles([]);
    setTaskStatus(null);
    setTaskId(null);
  }, []);

  // 切换行选择
  const toggleSelection = useCallback((index: number) => {
    setSelectedIndices((prev) =>
      prev.includes(index)
        ? prev.filter((i) => i !== index)
        : [...prev, index]
    );
  }, []);

  // 全选
  const selectAll = useCallback(() => {
    setSelectedIndices(lines.map((l) => l.index));
  }, [lines]);

  // 清空选择
  const clearSelection = useCallback(() => {
    setSelectedIndices([]);
  }, []);

  // 修改语音配置
  const handleVoiceChange = useCallback((character: string, voiceId: string) => {
    setVoiceConfig((prev) => ({
      ...prev,
      [character]: voiceId,
    }));
  }, []);

  // 开始生成
  const handleGenerate = useCallback(async () => {
    if (selectedIndices.length === 0) return;

    setIsGenerating(true);
    setGeneratedFiles([]);

    try {
      const { task_id } = await audioApi.generate({
        lines,
        voice_config: voiceConfig,
        line_indices: selectedIndices,
        rate,
      });

      setTaskId(task_id);
    } catch (error) {
      console.error('Failed to start generation:', error);
      alert('生成任务启动失败');
      setIsGenerating(false);
    }
  }, [selectedIndices, voiceConfig, rate, lines]);

  // 停止生成
  const handleStop = useCallback(async () => {
    if (!taskId) return;

    try {
      await audioApi.stopTask(taskId);
      // 更新本地状态显示已取消
      setTaskStatus((prev) =>
        prev
          ? { ...prev, status: 'cancelled', message: '正在停止...' }
          : null
      );
    } catch (error) {
      console.error('Failed to stop generation:', error);
    }
  }, [taskId]);

  // 重新生成完成回调
  const handleRegenerateComplete = useCallback(async (regenerateTaskId: string) => {
    try {
      const result = await audioApi.getTaskResults(regenerateTaskId);
      if (result.files && result.files.length > 0) {
        const newFile = result.files[0];
        // 更新对应文件的状态
        setGeneratedFiles((prev) =>
          prev.map((f) => (f.index === newFile.index ? newFile : f))
        );
      }
    } catch (error) {
      console.error('Failed to get regenerate results:', error);
    }
  }, []);

  // 文字更新回调（编辑文字后同步更新剧本）
  const handleTextUpdate = useCallback((index: number, newText: string) => {
    setLines((prev) =>
      prev.map((line) =>
        line.index === index ? { ...line, text: newText } : line
      )
    );
  }, []);

  // 一键重新生成失败项
  const handleRegenerateFailed = useCallback(async (failedIndices: number[]) => {
    if (failedIndices.length === 0) return;

    setIsRegeneratingFailed(true);

    try {
      const { task_id } = await audioApi.generate({
        lines,
        voice_config: voiceConfig,
        line_indices: failedIndices,
        rate,
      });

      setFailedTaskId(task_id);
    } catch (error) {
      console.error('Failed to start regeneration:', error);
      alert('重新生成失败项启动失败');
      setIsRegeneratingFailed(false);
    }
  }, [lines, voiceConfig, rate]);

  // 轮询任务状态
  useEffect(() => {
    if (!taskId || !isGenerating) return;

    const pollStatus = async () => {
      try {
        const status = await audioApi.getTaskStatus(taskId);
        setTaskStatus(status);

        if (status.status === 'completed' || status.status === 'failed' || status.status === 'cancelled') {
          setIsGenerating(false);

          // 获取结果
          const result = await audioApi.getTaskResults(taskId);
          setGeneratedFiles(result.files);
        }
      } catch (error) {
        console.error('Failed to get task status:', error);
      }
    };

    pollStatus();
    const interval = setInterval(pollStatus, POLL_INTERVAL);

    return () => clearInterval(interval);
  }, [taskId, isGenerating]);

  // 轮询失败项重新生成任务状态
  useEffect(() => {
    if (!failedTaskId || !isRegeneratingFailed) return;

    const pollStatus = async () => {
      try {
        const status = await audioApi.getTaskStatus(failedTaskId);
        setFailedTaskStatus(status);

        if (status.status === 'completed' || status.status === 'failed' || status.status === 'cancelled') {
          setIsRegeneratingFailed(false);

          // 获取结果并更新对应的文件
          const result = await audioApi.getTaskResults(failedTaskId);
          if (result.files && result.files.length > 0) {
            setGeneratedFiles((prev) => {
              const updatedFiles = [...prev];
              result.files.forEach((newFile) => {
                const index = updatedFiles.findIndex((f) => f.index === newFile.index);
                if (index !== -1) {
                  updatedFiles[index] = newFile;
                }
              });
              return updatedFiles;
            });
          }

          setFailedTaskId(null);
          setFailedTaskStatus(null);
        }
      } catch (error) {
        console.error('Failed to get task status:', error);
      }
    };

    pollStatus();
    const interval = setInterval(pollStatus, POLL_INTERVAL);

    return () => clearInterval(interval);
  }, [failedTaskId, isRegeneratingFailed]);

  return (
    <div className="min-h-screen bg-gray-50">
      {/* 头部 */}
      <header className="bg-white shadow-sm border-b">
        <div className="max-w-7xl mx-auto px-4 py-4">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-blue-600 rounded-lg">
              <Mic className="h-6 w-6 text-white" />
            </div>
            <div>
              <h1 className="text-xl font-bold text-gray-900">播客TTS生成器</h1>
              <p className="text-sm text-gray-500">将剧本转换为高质量语音</p>
            </div>
          </div>
        </div>
      </header>

      {/* 字幕工具栏 */}
      <SubtitleToolbar />

      {/* 主内容 */}
      <main className="max-w-7xl mx-auto px-4 py-6">
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* 左侧：上传和剧本 */}
          <div className="space-y-6">
            {/* 上传区域 */}
            <section className="bg-white rounded-lg shadow p-6">
              <div className="flex items-center gap-2 mb-4">
                <FileText className="h-5 w-5 text-blue-600" />
                <h2 className="text-lg font-medium text-gray-900">1. 上传剧本</h2>
              </div>
              <FileUpload
                onFileSelect={handleFileSelect}
                selectedFile={selectedFile}
                onClear={handleClearFile}
              />
              {isUploading && (
                <p className="mt-2 text-sm text-blue-600">正在解析...</p>
              )}
            </section>

            {/* 剧本显示 */}
            {lines.length > 0 && (
              <section className="bg-white rounded-lg shadow p-6">
                <div className="flex items-center gap-2 mb-4">
                  <FileText className="h-5 w-5 text-blue-600" />
                  <h2 className="text-lg font-medium text-gray-900">
                    2. 剧本内容
                  </h2>
                </div>
                <ScriptViewer
                  lines={lines}
                  selectedIndices={selectedIndices}
                  onToggleSelection={toggleSelection}
                  onSelectAll={selectAll}
                  onClearSelection={clearSelection}
                />
              </section>
            )}
          </div>

          {/* 右侧：配置和生成 */}
          <div className="space-y-6">
            {/* 语音配置 */}
            {characters.length > 0 && (
              <section className="bg-white rounded-lg shadow p-6">
                <div className="flex items-center gap-2 mb-4">
                  <Settings className="h-5 w-5 text-blue-600" />
                  <h2 className="text-lg font-medium text-gray-900">
                    3. 角色声音配置
                  </h2>
                </div>
                <VoiceConfig
                  characters={characters}
                  voiceConfig={voiceConfig}
                  availableVoices={availableVoices}
                  onVoiceChange={handleVoiceChange}
                />
              </section>
            )}

            {/* 生成选项 */}
            {characters.length > 0 && (
              <section className="bg-white rounded-lg shadow p-6">
                <div className="flex items-center gap-2 mb-4">
                  <Music className="h-5 w-5 text-blue-600" />
                  <h2 className="text-lg font-medium text-gray-900">
                    4. 生成音频
                  </h2>
                </div>
                <GenerationPanel
                  rate={rate}
                  onRateChange={setRate}
                  isGenerating={isGenerating}
                  onGenerate={handleGenerate}
                  onStop={handleStop}
                  taskStatus={taskStatus}
                  hasSelectedLines={selectedIndices.length > 0}
                />
              </section>
            )}

            {/* 生成结果 */}
            {generatedFiles.length > 0 && (
              <section className="bg-white rounded-lg shadow p-6">
                <div className="flex items-center justify-between mb-4">
                  <h2 className="text-lg font-medium text-gray-900">生成的音频</h2>
                  <SubtitleGenerator
                    lines={lines}
                    generatedFiles={generatedFiles}
                    scriptName={selectedFile?.name.replace('.txt', '')}
                  />
                </div>
                <AudioPlayer
                  files={generatedFiles}
                  lines={lines}
                  voiceConfig={voiceConfig}
                  rate={rate}
                  onRegenerateComplete={handleRegenerateComplete}
                  onTextUpdate={handleTextUpdate}
                  onRegenerateFailed={handleRegenerateFailed}
                  isRegeneratingFailed={isRegeneratingFailed}
                  failedTaskStatus={failedTaskStatus}
                />
              </section>
            )}
          </div>
        </div>
      </main>
    </div>
  );
};
