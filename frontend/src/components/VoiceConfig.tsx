import React, { useState, useEffect, useRef } from 'react';
import { Mic, Play, Pause, RefreshCw, Volume2 } from 'lucide-react';
import type { Voice } from '@/types';
import { audioApi } from '@/services/api';

interface VoiceConfigProps {
  characters: string[];
  voiceConfig: Record<string, string>;
  availableVoices: Voice[];
  onVoiceChange: (character: string, voiceId: string) => void;
}

interface VoiceItemProps {
  character: string;
  selectedVoiceId: string;
  availableVoices: Voice[];
  onVoiceChange: (voiceId: string) => void;
}

const VoiceItem: React.FC<VoiceItemProps> = ({
  character,
  selectedVoiceId,
  availableVoices,
  onVoiceChange,
}) => {
  const [isPlaying, setIsPlaying] = useState(false);
  const [isGeneratingPreview, setIsGeneratingPreview] = useState(false);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [previewExists, setPreviewExists] = useState(false);
  const audioRef = useRef<HTMLAudioElement>(null);

  // 获取选中的语音信息
  const selectedVoice = availableVoices.find(v => v.id === selectedVoiceId);

  // 检查试听音频状态
  useEffect(() => {
    if (selectedVoiceId) {
      checkPreviewStatus();
    }
  }, [selectedVoiceId]);

  const checkPreviewStatus = async () => {
    try {
      const status = await audioApi.checkPreviewStatus(selectedVoiceId);
      setPreviewExists(status.exists);
      if (status.exists && status.url) {
        setPreviewUrl(status.url);
      } else {
        setPreviewUrl(null);
      }
    } catch (error) {
      console.error('检查试听状态失败:', error);
      setPreviewExists(false);
      setPreviewUrl(null);
    }
  };

  const handlePlayPreview = () => {
    if (audioRef.current) {
      if (isPlaying) {
        audioRef.current.pause();
        setIsPlaying(false);
      } else {
        audioRef.current.play().catch(() => {
          // 播放失败，可能需要重新生成
          setIsPlaying(false);
        });
        setIsPlaying(true);
      }
    }
  };

  const handleGeneratePreview = async () => {
    if (!selectedVoiceId || isGeneratingPreview) return;

    setIsGeneratingPreview(true);
    try {
      const result = await audioApi.generatePreview(selectedVoiceId);
      if (result.success) {
        setPreviewUrl(result.url);
        setPreviewExists(true);
        // 等待文件生成完成
        setTimeout(() => {
          checkPreviewStatus();
        }, 1000);
      }
    } catch (error) {
      console.error('生成试听音频失败:', error);
      alert('生成试听音频失败，请检查网络连接');
    } finally {
      setIsGeneratingPreview(false);
    }
  };

  const handleAudioEnded = () => {
    setIsPlaying(false);
  };

  const handleAudioPlay = () => {
    setIsPlaying(true);
  };

  const handleAudioPause = () => {
    setIsPlaying(false);
  };

  return (
    <div className="border rounded-lg p-4 bg-white hover:shadow-md transition-shadow">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <Mic className="h-4 w-4 text-blue-500" />
          <span className="font-medium text-gray-900">{character}</span>
        </div>
        {selectedVoice && (
          <span className="text-xs px-2 py-1 rounded-full bg-blue-100 text-blue-600">
            {selectedVoice.name}
          </span>
        )}
      </div>

      <select
        value={selectedVoiceId || ''}
        onChange={(e) => onVoiceChange(e.target.value)}
        className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 mb-3"
      >
        <option value="">选择声音...</option>
        {availableVoices.map((voice) => (
          <option key={voice.id} value={voice.id}>
            {voice.name} ({voice.gender === 'Female' ? '女' : '男'})
          </option>
        ))}
      </select>

      {!selectedVoiceId && (
        <p className="text-xs text-orange-500 mb-3">
          未选择，将使用默认声音
        </p>
      )}

      {/* 试听功能 */}
      {selectedVoiceId && (
        <div className="mt-3 pt-3 border-t border-gray-100">
          <div className="flex items-center justify-between mb-2">
            <div className="flex items-center gap-2">
              <Volume2 className="h-4 w-4 text-gray-500" />
              <span className="text-xs font-medium text-gray-700">试听</span>
            </div>
            <div className="flex items-center gap-2">
              {/* 重新生成按钮 */}
              <button
                onClick={handleGeneratePreview}
                disabled={isGeneratingPreview}
                title="重新生成试听"
                className={`p-1.5 rounded-full transition-colors ${
                  isGeneratingPreview
                    ? 'bg-gray-100 text-gray-400 cursor-not-allowed'
                    : 'bg-orange-50 text-orange-600 hover:bg-orange-100'
                }`}
              >
                <RefreshCw className={`h-3 w-3 ${isGeneratingPreview ? 'animate-spin' : ''}`} />
              </button>

              {/* 播放按钮 */}
              <button
                onClick={handlePlayPreview}
                disabled={!previewExists || isGeneratingPreview}
                title={previewExists ? "播放试听" : "请先生成试听"}
                className={`p-1.5 rounded-full transition-colors ${
                  previewExists && !isGeneratingPreview
                    ? 'bg-blue-50 text-blue-600 hover:bg-blue-100'
                    : 'bg-gray-50 text-gray-300 cursor-not-allowed'
                }`}
              >
                {isPlaying ? (
                  <Pause className="h-3 w-3" />
                ) : (
                  <Play className="h-3 w-3" />
                )}
              </button>
            </div>
          </div>

          <div className="text-xs text-gray-500 space-y-1">
            <p>内容：大家好，欢迎来到今天的《大白话中文》！</p>
            <p>语速：0.8倍</p>
            {!previewExists && !isGeneratingPreview && (
              <p className="text-orange-500">试听音频不存在，点击刷新按钮生成</p>
            )}
            {isGeneratingPreview && (
              <p className="text-blue-500">正在生成试听音频...</p>
            )}
          </div>

          {/* 隐藏的音频元素 */}
          {previewUrl && (
            <audio
              ref={audioRef}
              src={previewUrl}
              onEnded={handleAudioEnded}
              onPlay={handleAudioPlay}
              onPause={handleAudioPause}
              className="hidden"
            />
          )}
        </div>
      )}
    </div>
  );
};

export const VoiceConfig: React.FC<VoiceConfigProps> = ({
  characters,
  voiceConfig,
  availableVoices,
  onVoiceChange,
}) => {
  if (characters.length === 0) {
    return (
      <div className="text-center py-8 text-gray-500 border rounded-lg">
        请先上传剧本文件
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
      {characters.map((character) => (
        <VoiceItem
          key={character}
          character={character}
          selectedVoiceId={voiceConfig[character] || ''}
          availableVoices={availableVoices}
          onVoiceChange={(voiceId) => onVoiceChange(character, voiceId)}
        />
      ))}
    </div>
  );
};
