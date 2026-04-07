import os
import json
import wave
import logging
import random
import string
from typing import List, Tuple, Optional
from dotenv import load_dotenv
from ..models.schemas import Line
from .ai_segment import get_llm

# 加载环境变量
load_dotenv()

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
        # 从环境变量获取 Hugging Face token
        hf_token = os.getenv("HF_TOKEN")
        model_kwargs = {
            "model_size_or_path": "large",
            "device": "cuda",
            "compute_type": "float16",
        }
        if hf_token:
            model_kwargs["token"] = hf_token
            logging.getLogger("subtitle_service").info(f"[Whisper] 使用 HF_TOKEN 下载模型")

        _whisper_model = WhisperModel(**model_kwargs)
    return _whisper_model


def merge_audio_files(
    lines: List[Line],
    output_dir: str,
    script_name: str = "merged"
) -> Tuple[Optional[str], List[Tuple[float, float, int]]]:
    """
    将多个单条 WAV 按 index 顺序合并为一个完整的 WAV 文件。

    返回:
        (merged_file_path, segment_offsets)
        segment_offsets: [(start_time, end_time, line_index), ...]
        每个元素记录该行音频在合并文件中的起止时间
    """
    sorted_lines = sorted(lines, key=lambda l: l.index)
    audio_files = []
    for line in sorted_lines:
        audio_file = f"{line.index:03d}_{line.speaker}.wav"
        audio_path = os.path.join(output_dir, audio_file)
        if os.path.exists(audio_path):
            audio_files.append((audio_path, line.index))

    if not audio_files:
        logger.warning("[merge_audio] 没有找到任何音频文件")
        return None, []

    # 读取第一个文件获取参数
    with wave.open(audio_files[0][0], 'rb') as first:
        params = first.getparams()
        n_channels = params.nchannels
        sampwidth = params.sampwidth
        framerate = params.framerate

    # 合并所有音频数据
    all_frames = b""
    segment_offsets = []

    for audio_path, line_index in audio_files:
        start_time = len(all_frames) / (n_channels * sampwidth * framerate)
        try:
            with wave.open(audio_path, 'rb') as wf:
                frames = wf.readframes(wf.getnframes())
                all_frames += frames
        except Exception as e:
            logger.error(f"[merge_audio] 读取 {audio_path} 失败: {e}")
            continue
        end_time = len(all_frames) / (n_channels * sampwidth * framerate)
        segment_offsets.append((start_time, end_time, line_index))

    # 写入合并文件
    merged_filename = f"{script_name}_merged.wav"
    merged_path = os.path.join(output_dir, merged_filename)

    with wave.open(merged_path, 'wb') as out:
        out.setnchannels(n_channels)
        out.setsampwidth(sampwidth)
        out.setframerate(framerate)
        out.writeframes(all_frames)

    duration = len(all_frames) / (n_channels * sampwidth * framerate)
    logger.info(f"[merge_audio] 合并完成: {merged_path}, 总时长: {duration:.2f}s, {len(segment_offsets)} 段")

    return merged_path, segment_offsets


def align_sentences_with_whisper(
    audio_path: str,
    sentences: List[str],
    provider: str = "deepseek"
) -> List[Tuple[float, float, str]]:
    """
    用 Whisper 识别词级时间戳，然后用算法把字幕句子对齐到时间轴上。
    不依赖 AI 对齐，纯算法匹配更稳定。
    """
    if not WHISPER_AVAILABLE or not sentences:
        return []

    try:
        model = _get_whisper_model()
        segments_iter, _ = model.transcribe(
            audio_path,
            language="zh",
            beam_size=5,
            vad_filter=False,
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

    if not word_segs:
        return []

    logger.info(f"[Whisper] 共 {len(word_segs)} 个词, 总时长: {word_segs[0]['start']:.3f} - {word_segs[-1]['end']:.3f}")

    # 只有一句直接返回整段时间
    if len(sentences) == 1:
        return [(word_segs[0]["start"], word_segs[-1]["end"], sentences[0])]

    # 纯算法对齐：按字符数比例分配 Whisper 词
    # 计算每句的字符数（去空格），按比例将词分配给各句
    char_counts = [len(s.replace(" ", "")) for s in sentences]
    total_chars = sum(char_counts)

    if total_chars == 0:
        return []

    result = []
    word_idx = 0
    total_words = len(word_segs)

    for i, sent in enumerate(sentences):
        # 按字符比例计算这句应该分配多少个词
        if i == len(sentences) - 1:
            # 最后一句拿走剩余所有词
            n_words = total_words - word_idx
        else:
            ratio = char_counts[i] / total_chars
            n_words = max(1, round(total_words * ratio))
            # 确保不会超出剩余词数（至少给后面每句留1个词）
            remaining_sentences = len(sentences) - i - 1
            max_take = total_words - word_idx - remaining_sentences
            n_words = min(n_words, max(1, max_take))

        if word_idx >= total_words:
            # 词已用完，用最后一个词的时间
            last_end = word_segs[-1]["end"]
            result.append((last_end, last_end, sent))
            continue

        seg_start = word_segs[word_idx]["start"]
        seg_end_idx = min(word_idx + n_words - 1, total_words - 1)
        seg_end = word_segs[seg_end_idx]["end"]

        result.append((seg_start, seg_end, sent))
        word_idx = seg_end_idx + 1

    logger.info(f"[算法对齐] 结果: {[(round(s,3), round(e,3), t) for s,e,t in result]}")
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
    # 如果有 AI 断句结果，使用但需要二次检查长度
    if ai_sentences:
        result = []
        for s in ai_sentences:
            s = s.strip()
            if not s:
                continue
            if len(s) <= max_length:
                result.append(s)
            else:
                # AI 断句结果超长，按 max_length 强制拆分
                result.extend(_force_split(s, max_length))
        return result

    # 没有 AI 结果时，按 max_length 分割文本
    text = text.strip()
    if not text:
        return []

    return _force_split(text, max_length)


def _force_split(text: str, max_length: int) -> List[str]:
    """按 max_length 强制拆分文本，尽量在空格处断开"""
    if len(text) <= max_length:
        return [text]

    parts = []
    while len(text) > max_length:
        # 在 max_length 范围内找最后一个空格
        cut = text.rfind(' ', 0, max_length)
        if cut <= 0:
            # 没有空格，直接硬切
            cut = max_length
        parts.append(text[:cut].strip())
        text = text[cut:].strip()
    if text:
        parts.append(text)
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

    如果存在合并音频（{script_name}_merged.wav），则用合并音频跑一次 Whisper 对齐，
    避免分段音频拼接导致的时间漂移。

    返回: (srt_content, filename)
    """
    logger.info(f"[generate_srt] 调用: max_length={max_length}, ai_sentences_map={ai_sentences_map}")

    # 收集所有断句结果
    all_text_parts = []
    for line in lines:
        ai_sentences = ai_sentences_map.get(line.index) if ai_sentences_map else None
        text_parts = split_text_by_length(line.text, max_length, ai_sentences)
        all_text_parts.append((line, text_parts))

    # 检查是否存在合并音频
    merged_audio_path = os.path.join(output_dir, f"{script_name}_merged.wav")
    if not os.path.exists(merged_audio_path):
        # 尝试查找任何 _merged.wav 文件
        for f in os.listdir(output_dir):
            if f.endswith("_merged.wav"):
                merged_audio_path = os.path.join(output_dir, f)
                break

    if os.path.exists(merged_audio_path) and WHISPER_AVAILABLE:
        logger.info(f"[generate_srt] 使用合并音频: {merged_audio_path}")
        srt_content = _generate_srt_from_merged(all_text_parts, merged_audio_path, ai_provider)
    else:
        logger.info(f"[generate_srt] 使用分段音频")
        srt_content = _generate_srt_from_segments(all_text_parts, output_dir, ai_provider)

    # 最终处理：消除相邻字幕之间的间隙
    srt_content = _fill_gaps(srt_content)

    # 生成文件名: 脚本名 + 4位随机数
    random_suffix = ''.join(random.choices(string.digits, k=4))
    base_name = script_name if script_name else "subtitle"
    filename = f"{base_name}{random_suffix}.srt"
    file_path = os.path.join(output_dir, filename)

    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(srt_content)

    return srt_content, filename


def _generate_srt_from_merged(
    all_text_parts: List[Tuple[Line, List[str]]],
    merged_audio_path: str,
    ai_provider: str = "deepseek"
) -> str:
    """
    基于合并音频生成字幕。
    策略：逐段用 Whisper 识别单个音频文件（短音频识别更准确），
    然后用合并时记录的精确偏移量将时间戳映射到合并音频的时间轴上。
    """
    output_dir = os.path.dirname(merged_audio_path)

    # 先计算每个单独音频文件在合并文件中的真实偏移量
    segment_offsets = {}  # line_index -> start_offset
    sorted_parts = sorted(all_text_parts, key=lambda x: x[0].index)

    # 读取合并音频的参数来计算偏移
    try:
        with wave.open(merged_audio_path, 'rb') as mf:
            n_channels = mf.getnchannels()
            sampwidth = mf.getsampwidth()
            framerate = mf.getframerate()
    except Exception as e:
        logger.error(f"[generate_srt_from_merged] 无法读取合并音频参数: {e}")
        return ""

    # 按顺序累加每个单独文件的时长来计算精确偏移
    current_offset = 0.0
    for line, text_parts in sorted_parts:
        audio_file = f"{line.index:03d}_{line.speaker}.wav"
        audio_path = os.path.join(output_dir, audio_file)
        segment_offsets[line.index] = current_offset
        if os.path.exists(audio_path):
            current_offset += get_audio_duration(audio_path)

    logger.info(f"[generate_srt_from_merged] 偏移量: {segment_offsets}")

    # 逐段 Whisper 识别 + 偏移
    srt_lines = []
    subtitle_index = 1

    for line, text_parts in sorted_parts:
        if not text_parts:
            continue

        audio_file = f"{line.index:03d}_{line.speaker}.wav"
        audio_path = os.path.join(output_dir, audio_file)
        offset = segment_offsets.get(line.index, 0.0)

        if os.path.exists(audio_path):
            aligned = align_sentences_with_whisper(audio_path, text_parts, provider=ai_provider)
            if aligned:
                for seg_start, seg_end, part in aligned:
                    if not part.strip():
                        continue
                    # 加上合并偏移量
                    abs_start = offset + seg_start
                    abs_end = offset + seg_end
                    srt_lines.append(f"{subtitle_index}")
                    srt_lines.append(f"{format_srt_time(abs_start)} --> {format_srt_time(abs_end)}")
                    srt_lines.append(part)
                    srt_lines.append("")
                    subtitle_index += 1
                continue

        # 回退：按该段音频时长平均分配
        if os.path.exists(audio_path):
            total_duration = get_audio_duration(audio_path)
        else:
            total_duration = 3.0

        sentence_count = len([p for p in text_parts if p.strip()])
        if sentence_count == 0:
            continue
        duration = total_duration / sentence_count
        t = offset

        for part in text_parts:
            if not part.strip():
                continue
            srt_lines.append(f"{subtitle_index}")
            srt_lines.append(f"{format_srt_time(t)} --> {format_srt_time(t + duration)}")
            srt_lines.append(part)
            srt_lines.append("")
            subtitle_index += 1
            t += duration

    return "\n".join(srt_lines)


def _generate_srt_from_segments(
    all_text_parts: List[Tuple[Line, List[str]]],
    output_dir: str,
    ai_provider: str = "deepseek"
) -> str:
    """
    基于分段音频逐个用 Whisper 对齐（原有逻辑）。
    """
    srt_lines = []
    subtitle_index = 1
    current_time = 0.0

    for line, text_parts in all_text_parts:
        audio_file = f"{line.index:03d}_{line.speaker}.wav"
        audio_path = os.path.join(output_dir, audio_file)

        # 优先用 Whisper 精确对齐时间轴
        if text_parts and os.path.exists(audio_path):
            aligned = align_sentences_with_whisper(audio_path, text_parts, provider=ai_provider)
            if aligned:
                last_seg_end = 0.0
                for seg_start, seg_end, part in aligned:
                    if not part.strip():
                        continue
                    srt_lines.append(f"{subtitle_index}")
                    srt_lines.append(f"{format_srt_time(current_time + seg_start)} --> {format_srt_time(current_time + seg_end)}")
                    srt_lines.append(part)
                    srt_lines.append("")
                    subtitle_index += 1
                    last_seg_end = seg_end
                current_time += last_seg_end
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

            srt_lines.append(f"{subtitle_index}")
            srt_lines.append(f"{format_srt_time(current_time)} --> {format_srt_time(current_time + duration)}")
            srt_lines.append(part)
            srt_lines.append("")

            subtitle_index += 1
            current_time += duration

    return "\n".join(srt_lines)


def _fill_gaps(srt_content: str) -> str:
    """消除相邻字幕之间的间隙：把上一条的 end 延伸到下一条的 start"""
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

    for i in range(len(entries) - 1):
        cur_time_line = entries[i][1]
        next_time_line = entries[i + 1][1]
        if "-->" in cur_time_line and "-->" in next_time_line:
            cur_start = cur_time_line.split("-->")[0].strip()
            next_start = next_time_line.split("-->")[0].strip()
            entries[i][1] = f"{cur_start} --> {next_start}"

    result = "\n\n".join("\n".join(e) for e in entries)
    if not result.endswith("\n"):
        result += "\n"
    return result


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
