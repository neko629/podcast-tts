import axios from 'axios';
import type { ScriptParseResponse, Voice, TaskStatus, AudioFile, GenerateRequest, RegenerateResponse, Line } from '@/types';

const api = axios.create({
  baseURL: '/api',
});

export const scriptApi = {
  // 上传并解析剧本
  uploadScript: async (file: File): Promise<ScriptParseResponse> => {
    const formData = new FormData();
    formData.append('file', file);
    const { data } = await api.post('/script/parse', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return data;
  },
};

export const voiceApi = {
  // 获取可用语音列表
  getVoices: async (): Promise<Voice[]> => {
    const { data } = await api.get('/voices');
    return data;
  },
};

export const subtitleApi = {
  // 预览字幕分割效果
  preview: async (data: {
    lines: Line[];
    max_length: number;
    max_preview_lines?: number;
    use_ai?: boolean;
  }): Promise<{ preview: string[]; total_subtitles: number }> => {
    const { data: result } = await api.post('/subtitle/preview', data);
    return result;
  },

  // 生成字幕文件
  generate: async (data: {
    lines: Line[];
    max_length: number;
    use_ai?: boolean;
  }): Promise<{ filename: string; url: string; content: string }> => {
    const { data: result } = await api.post('/subtitle/generate', data);
    return result;
  },
};

export const audioApi = {
  // 提交生成任务
  generate: async (request: GenerateRequest): Promise<{ task_id: string }> => {
    const { data } = await api.post('/audio/generate', request);
    return data;
  },

  // 获取任务状态
  getTaskStatus: async (taskId: string): Promise<TaskStatus> => {
    const { data } = await api.get(`/audio/status/${taskId}`);
    return data;
  },

  // 获取任务结果
  getTaskResults: async (taskId: string): Promise<{ task_id: string; status: string; files: AudioFile[] }> => {
    const { data } = await api.get(`/audio/results/${taskId}`);
    return data;
  },

  // 获取生成文件列表
  listFiles: async (): Promise<{ files: { filename: string; url: string; size: number; created: number }[] }> => {
    const { data } = await api.get('/audio/list');
    return data;
  },

  // 下载文件
  downloadFile: async (filename: string): Promise<Blob> => {
    const { data } = await api.get(`/audio/download/${filename}`, {
      responseType: 'blob',
    });
    return data;
  },

  // 重新生成单条音频
  regenerate: async (index: number, request: GenerateRequest): Promise<RegenerateResponse> => {
    const { data } = await api.post(`/audio/regenerate/${index}`, request);
    return data;
  },

  // 停止任务
  stopTask: async (taskId: string): Promise<{ message: string; status?: string }> => {
    const { data } = await api.post(`/audio/stop/${taskId}`);
    return data;
  },
};
