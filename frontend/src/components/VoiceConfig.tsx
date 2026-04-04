import React from 'react';
import { Mic } from 'lucide-react';
import type { Voice } from '@/types';

interface VoiceConfigProps {
  characters: string[];
  voiceConfig: Record<string, string>;
  availableVoices: Voice[];
  onVoiceChange: (character: string, voiceId: string) => void;
}

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
        <div
          key={character}
          className="border rounded-lg p-4 bg-white hover:shadow-md transition-shadow"
        >
          <div className="flex items-center gap-2 mb-3">
            <Mic className="h-4 w-4 text-blue-500" />
            <span className="font-medium text-gray-900">{character}</span>
          </div>
          <select
            value={voiceConfig[character] || ''}
            onChange={(e) => onVoiceChange(character, e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="">选择声音...</option>
            {availableVoices.map((voice) => (
              <option key={voice.id} value={voice.id}>
                {voice.name} ({voice.gender === 'Female' ? '女' : '男'})
              </option>
            ))}
          </select>
          {!voiceConfig[character] && (
            <p className="mt-2 text-xs text-orange-500">
              未选择，将使用默认声音
            </p>
          )}
        </div>
      ))}
    </div>
  );
};
