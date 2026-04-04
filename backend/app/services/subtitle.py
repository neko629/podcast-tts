import os
import json
import wave
import logging
import random
import string
from typing import List, Tuple, Optional
from ..models.schemas import Line
from .ai_segment import get_llm

try:
    from faster_whisper import WhisperModel
    WHISPER_AVAILABLE = True
except ImportError:
    WHISPER_AVAILABLE = False
    logging.getLogger("subtitle_service").warning("faster-whisper not installed, subtitle alignment will use average distribution")


# Whisper 模型全局缓存，避免重复加载
_whisper_model: Optional[WhisperModel] = None


def _get_whisper_model():
    """获取或初始化 Whisper 模型（全局单例）"""
    global _whisper_model
    if _whisper_model is None:
        _whisper_model = WhisperModel("base", device="cpu", compute_type="int8")
    return _whisper_model


def align_sentences_with_whisper(
    audio_path: str,
    sentences: List[str],
    provider: str = "deepseek"
) -> List[Tuple[float, float, str]]:
    """
    用 Whisper 识别词级时间戳，再交给 AI 把正确文本对齐到时间轴上。
    """
    if not WHISPER_AVAILABLE or not sentences:
        return []

    try:
        model = _get_whisper_model()
        segments_iter, _ = model.transcribe(
            audio_path,
            language="zh",
            beam_size=5,
            vad_filter=True,
            word_timestamps=True,
        )
        segments = list(segments_iter)
        logger.info(f"[Whisper] 音频 {audio_path} 识别出 {len(segments)} 个段")
    except Exception as e:
        logger.error(f"[Whisper] 识别失败 {audio_path}: {e}")
        return []

    if not segments:
        return []

    # 收集词级时间戳
    word_segs = []
    for seg in segments:
        if seg.words:
            for w in seg.words:
                word_segs.append({"word": w.word.strip(), "start": round(w.start, 3), "end": round(w.end, 3)})
        else:
            word_segs.append({"word": seg.text.strip(), "start": round(seg.start, 3), "end": round(seg.end, 3)})

    # 只有一句直接返回整段时间
    if len(sentences) == 1:
        return [(word_segs[0]["start"], word_segs[-1]["end"], sentences[0])]

    # 把 Whisper 时间戳 + AI 断句发给 AI 做对齐
    whisper_json = json.dumps(word_segs, ensure_ascii=False)
    sentences_json = json.dumps(sentences, ensure_ascii=False)

    prompt = f"""你是字幕时间轴对齐专家。

下面是语音识别给出的词级时间戳（可能有同音字错误，但时间是准确的）：
{whisper_json}

下面是正确的字幕分行结果（文字正确，但没有时间戳）：
{sentences_json}

任务：根据词级时间戳的时间分布，为每句正确字幕分配合理的 start 和 end 时间（单位：秒）。
规则：
1. 按照识别词的顺序，把字幕句子依次对应到时间轴上
2. 相邻句子的时间不能重叠，end <= 下一句的 start
3. 第一句 start 不早于识别词第一个词的 start，最后一句 end 不晚于识别词最后一个词的 end
4. 每句时长按该句字符数（去空格）在总字数中的比例从总时长中分配

只返回 JSON 数组，格式：
[{{"start": 0.0, "end": 1.5, "text": "字幕内容"}}, ...]
不要任何解释。"""

    try:
        llm = get_llm(provider=provider)
        from langchain_core.messages import HumanMessage
        response = llm.invoke([HumanMessage(content=prompt)])
        raw = response.content.strip()
        # 去掉可能的 markdown 代码块
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        aligned = json.loads(raw)
        result = [(item["start"], item["end"], item["text"]) for item in aligned]
        # 消除字幕间隙：上一句 end = 下一句 start
        for i in range(len(result) - 1):
            result[i] = (result[i][0], result[i + 1][0], result[i][2])
        logger.info(f"[AI对齐] 结果: {result}")
        return result
    except Exception as e:
        logger.error(f"[AI对齐] 失败，回退到字符比例分配: {e}")
        # 回退：按字符数比例均分
        audio_start = word_segs[0]["start"]
        audio_end = word_segs[-1]["end"]
        total_chars = sum(len(s.replace(" ", "")) for s in sentences)
        if total_chars == 0:
            return []
        result = []
        t = audio_start
        total_duration = audio_end - audio_start
        for sent in sentences:
            chars = len(sent.replace(" ", ""))
            dur = total_duration * chars / total_chars
            result.append((t, t + dur, sent))
            t += dur
        # 消除字幕间隙：上一句 end = 下一句 start
        for i in range(len(result) - 1):
            result[i] = (result[i][0], result[i + 1][0], result[i][2])
        return result

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
    ai_sentences_map: dict = None,
    ai_provider: str = "deepseek",
    script_name: str = "subtitle"
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

        # 音频文件路径
        audio_file = f"{line.index:03d}_{line.speaker}.wav"
        audio_path = os.path.join(output_dir, audio_file)

        # 优先用 Whisper 精确对齐时间轴
        if text_parts and os.path.exists(audio_path):
            aligned = align_sentences_with_whisper(audio_path, text_parts, provider=ai_provider)
            if aligned:
                for seg_start, seg_end, part in aligned:
                    if not part.strip():
                        continue
                    srt_lines.append(f"{subtitle_index}")
                    srt_lines.append(f"{format_srt_time(current_time + seg_start)} --> {format_srt_time(current_time + seg_end)}")
                    srt_lines.append(part)
                    srt_lines.append("")
                    subtitle_index += 1
                # 用音频文件真实时长推进基准时间（而不是用字幕end），确保行间无缝
                current_time += get_audio_duration(audio_path)
                continue

        # 回退：按平均分配
        for part in text_parts:
            if not part.strip():
                continue

            if os.path.exists(audio_path):
                total_duration = get_audio_duration(audio_path)
            else:
                total_duration = 3.0

            sentence_count = len(text_parts)
            duration = total_duration / sentence_count

            start_time = format_srt_time(current_time)
            end_time = format_srt_time(current_time + duration)

            srt_lines.append(f"{subtitle_index}")
            srt_lines.append(f"{start_time} --> {end_time}")
            srt_lines.append(part)
            srt_lines.append("")

            subtitle_index += 1
            current_time += duration

    srt_content = "\n".join(srt_lines)

    # 最终处理：消除相邻字幕之间的间隙
    # 把上一条的 end 延伸到下一条的 start
    entries = []
    block = []
    for raw_line in srt_content.split("\n"):
        if raw_line.strip() == "" and block:
            entries.append(block)
            block = []
        else:
            block.append(raw_line)
    if block:
        entries.append(block)

    # 每个 entry: [index_line, time_line, text_line, ...]
    for i in range(len(entries) - 1):
        cur_time_line = entries[i][1]
        next_time_line = entries[i + 1][1]
        if "-->" in cur_time_line and "-->" in next_time_line:
            cur_start = cur_time_line.split("-->")[0].strip()
            next_start = next_time_line.split("-->")[0].strip()
            # 把当前条的 end 改为下一条的 start
            entries[i][1] = f"{cur_start} --> {next_start}"

    srt_content = "\n\n".join("\n".join(e) for e in entries)
    if not srt_content.endswith("\n"):
        srt_content += "\n"

    # 生成文件名: 脚本名 + 4位随机数
    random_suffix = ''.join(random.choices(string.digits, k=4))
    base_name = script_name if script_name else "subtitle"
    filename = f"{base_name}{random_suffix}.srt"
    file_path = os.path.join(output_dir, filename)

    # 写入文件
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(srt_content)

    return srt_content, filename


def _parse_srt_time(time_str: str) -> float:
    """将 SRT 时间格式 HH:MM:SS,mmm 转换为秒数"""
    time_str = time_str.strip()
    h, m, rest = time_str.split(":")
    s, ms = rest.split(",")
    return int(h) * 3600 + int(m) * 60 + int(s) + int(ms) / 1000


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
