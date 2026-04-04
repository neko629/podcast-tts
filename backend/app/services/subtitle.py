import os
import wave
import logging
from typing import List, Tuple
from ..models.schemas import Line

# 创建subtitle_service的logger
_subtitle_logger = logging.getLogger("subtitle_service")
if not _subtitle_logger.handlers:
    _log_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "logs")
    os.makedirs(_log_dir, exist_ok=True)
    _log_file = os.path.join(_log_dir, "subtitle_service.log")
    _file_handler = logging.FileHandler(_log_file, encoding='utf-8')
    _file_handler.setLevel(logging.INFO)
    _formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
    _file_handler.setFormatter(_formatter)
    _subtitle_logger.addHandler(_file_handler)
    _subtitle_logger.setLevel(logging.INFO)

logger = _subtitle_logger


def get_audio_duration(file_path: str) -> float:
    """
    获取音频文件的时长（秒）
    """
    try:
        with wave.open(file_path, 'rb') as wav_file:
            frames = wav_file.getnframes()
            rate = wav_file.getframerate()
            duration = frames / float(rate)
            return duration
    except Exception:
        return 3.0  # 默认3秒


def split_text_by_length(text: str, max_length: int, ai_sentences: List[str] = None) -> List[str]:
    """
    按长度分割文本，优先使用 AI 断句结果

    Args:
        text: 原始文本
        max_length: 每句最大字符数
        ai_sentences: AI 断句结果，如果有则优先使用
    """
    # 如果有 AI 断句结果，直接使用
    if ai_sentences:
        return [s.strip() for s in ai_sentences if s.strip()]

    # 没有 AI 结果时，按 max_length 分割文本
    text = text.strip()
    if not text:
        return []

    parts = []
    current = ""
    for char in text:
        if len(current) >= max_length:
            parts.append(current)
            current = char
        else:
            current += char
    if current:
        parts.append(current)

    return parts


def generate_srt(
    lines: List[Line],
    output_dir: str,
    max_length: int = 14,
    ai_sentences_map: dict = None
) -> Tuple[str, str]:
    """
    生成SRT字幕文件

    返回: (srt_content, filename)
    """
    logger.info(f"[generate_srt] 调用: max_length={max_length}, ai_sentences_map={ai_sentences_map}")

    srt_lines = []
    subtitle_index = 1
    current_time = 0.0

    for line in lines:
        # 分割文本
        ai_sentences = ai_sentences_map.get(line.index) if ai_sentences_map else None
        logger.info(f"[generate_srt] line.index={line.index}, ai_sentences={ai_sentences}")
        text_parts = split_text_by_length(line.text, max_length, ai_sentences)
        logger.info(f"[generate_srt] text_parts={text_parts}")

        for part in text_parts:
            if not part.strip():
                continue

            # 获取对应音频文件的时长
            audio_file = f"{line.index:03d}_{line.speaker}.wav"
            audio_path = os.path.join(output_dir, audio_file)

            if os.path.exists(audio_path):
                duration = get_audio_duration(audio_path)
            else:
                duration = 3.0  # 默认3秒

            # 计算时间码
            start_time = format_srt_time(current_time)
            end_time = format_srt_time(current_time + duration)

            # 添加SRT条目
            srt_lines.append(f"{subtitle_index}")
            srt_lines.append(f"{start_time} --> {end_time}")
            srt_lines.append(part)
            srt_lines.append("")

            subtitle_index += 1
            current_time += duration

    srt_content = "\n".join(srt_lines)

    # 生成文件名
    filename = f"subtitle_{lines[0].index if lines else 0:03d}_{lines[-1].index if lines else 0:03d}.srt"
    file_path = os.path.join(output_dir, filename)

    # 写入文件
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(srt_content)

    return srt_content, filename


def format_srt_time(seconds: float) -> str:
    """
    将秒数转换为SRT时间格式 HH:MM:SS,mmm
    """
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int((seconds % 1) * 1000)

    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


def preview_subtitle(lines: List[Line], max_length: int = 14, max_lines: int = 5, ai_sentences_map: dict = None) -> List[str]:
    """
    生成字幕预览（只返回前几行的分割结果）
    """
    preview = []
    for line in lines[:max_lines]:
        ai_sentences = ai_sentences_map.get(line.index) if ai_sentences_map else None
        parts = split_text_by_length(line.text, max_length, ai_sentences)
        preview.extend(parts)
    return preview
