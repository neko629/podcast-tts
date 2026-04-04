// 台词
export interface Line {
  index: number;
  speaker: string;
  text: string;
}

// 语音选项
export interface Voice {
  id: string;
  name: string;
  gender: string;
  locale: string;
}

// 生成请求
export interface GenerateRequest {
  lines: Line[];  // 完整的台词列表
  voice_config: Record<string, string>;
  line_indices: number[];
  rate: number;
}

// 重新生成响应
export interface RegenerateResponse {
  task_id: string;
  deleted_files: string[];
  message: string;
}

// 任务状态
export interface TaskStatus {
  task_id: string;
  status: 'processing' | 'completed' | 'failed' | 'cancelled';
  progress: number;
  total: number;
  completed: number;
  message?: string;
}

// 音频文件
export interface AudioFile {
  index: number;
  filename: string;
  url: string;
  speaker: string;
  text: string;
  success: boolean;
  error?: string;
}

// 剧本解析响应
export interface ScriptParseResponse {
  characters: string[];
  lines: Line[];
}
