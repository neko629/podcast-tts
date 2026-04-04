from pydantic import BaseModel
from typing import List, Dict, Optional
from enum import Enum


class Line(BaseModel):
    """台词数据模型"""
    index: int
    speaker: str
    text: str


class Voice(BaseModel):
    """语音选项模型"""
    id: str
    name: str
    gender: str
    locale: str


class GenerateRequest(BaseModel):
    """音频生成请求模型"""
    lines: List[Line]  # 完整的台词列表
    voice_config: Dict[str, str]
    line_indices: List[int] = []  # 为空则生成全部
    rate: float = 0.6


class GenerateResponse(BaseModel):
    """音频生成响应模型"""
    task_id: str
    files: List[Dict]


class TaskStatus(BaseModel):
    """任务状态模型"""
    task_id: str
    status: str  # processing, completed, failed, cancelled
    progress: int
    total: int
    completed: int
    message: Optional[str] = None


class AudioFile(BaseModel):
    """音频文件信息模型"""
    index: int
    filename: str
    url: str
    speaker: str
    text: str


class ScriptParseResponse(BaseModel):
    """剧本解析响应模型"""
    characters: List[str]
    lines: List[Line]
