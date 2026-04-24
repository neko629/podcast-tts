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

    # 同步保存精确的偏移信息，供字幕生成直接读取，避免下游重新计算导致的偏差
    offsets_path = os.path.join(output_dir, f"{script_name}_merged.json")
    try:
        with open(offsets_path, 'w', encoding='utf-8') as f:
            json.dump(
                [{"line_index": idx, "start": s, "end": e} for s, e, idx in segment_offsets],
                f, ensure_ascii=False, indent=2
            )
    except Exception as e:
        logger.warning(f"[merge_audio] 保存偏移文件失败 {offsets_path}: {e}")

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


def _load_merge_offsets(merged_audio_path: str) -> dict:
    """读取合并时保存的精确偏移 JSON，返回 {line_index: start_time}"""
    output_dir = os.path.dirname(merged_audio_path)
    base = os.path.basename(merged_audio_path)
    if base.endswith("_merged.wav"):
        script_name = base[:-len("_merged.wav")]
    else:
        script_name = os.path.splitext(base)[0]
    json_path = os.path.join(output_dir, f"{script_name}_merged.json")
    if not os.path.exists(json_path):
        return {}
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return {int(item["line_index"]): float(item["start"]) for item in data}
    except Exception as e:
        logger.warning(f"[load_merge_offsets] 读取 {json_path} 失败: {e}")
        return {}


def _whisper_char_stream(audio_path: str) -> List[Tuple[str, float, float]]:
    """
    在合并音频上跑一次 Whisper，返回字符级时间流 [(char, start, end), ...]。
    一个 Whisper word 内的多个汉字按词时长等分插值。
    """
    if not WHISPER_AVAILABLE:
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
    except Exception as e:
        logger.error(f"[Whisper] 合并音频识别失败 {audio_path}: {e}")
        return []

    char_stream: List[Tuple[str, float, float]] = []
    for seg in segments:
        if seg.words:
            for w in seg.words:
                word_text = w.word.strip()
                if not word_text:
                    continue
                n = len(word_text)
                duration = max(0.0, w.end - w.start)
                if n == 1 or duration <= 0:
                    char_stream.append((word_text, float(w.start), float(w.end)))
                else:
                    per = duration / n
                    for j, ch in enumerate(word_text):
                        char_stream.append((ch, float(w.start + j * per), float(w.start + (j + 1) * per)))
        else:
            text = seg.text.strip()
            if not text:
                continue
            n = len(text)
            duration = max(0.0, seg.end - seg.start)
            per = duration / n if n > 0 else 0
            for j, ch in enumerate(text):
                char_stream.append((ch, float(seg.start + j * per), float(seg.start + (j + 1) * per)))

    logger.info(f"[Whisper] 合并音频共 {len(char_stream)} 个字符")
    return char_stream


def _align_subsentences(
    text_parts: List[str],
    line_chars: List[Tuple[str, float, float]],
    line_start: float,
    line_end: float,
) -> List[Tuple[float, float, str]]:
    """
    把脚本子句对齐到该 line 内的 Whisper 字符流。
    贪心字符匹配：顺次扫描脚本字符，在 Whisper 字符流中前向窗口内查找匹配字。
    """
    valid = [p for p in text_parts if p.strip()]
    if not valid:
        return []

    def even_distribute() -> List[Tuple[float, float, str]]:
        per = max(0.0, (line_end - line_start)) / max(len(valid), 1)
        return [(line_start + i * per, line_start + (i + 1) * per, p) for i, p in enumerate(valid)]

    if not line_chars:
        return even_distribute()

    # 展开脚本字符（去空格），并记录每个子句的字符长度
    part_lengths: List[int] = []
    script_chars: List[str] = []
    for part in text_parts:
        clean = part.replace(" ", "")
        part_lengths.append(len(clean))
        script_chars.extend(list(clean))

    if not script_chars:
        return []

    WINDOW = 5
    char_times: List[Tuple[float, float]] = []
    last_time = (line_start, line_start)
    whisper_idx = 0
    matched = 0

    for ch in script_chars:
        end_search = min(whisper_idx + WINDOW + 1, len(line_chars))
        found = -1
        for j in range(whisper_idx, end_search):
            if line_chars[j][0] == ch:
                found = j
                break
        if found >= 0:
            t = (line_chars[found][1], line_chars[found][2])
            char_times.append(t)
            last_time = t
            whisper_idx = found + 1
            matched += 1
        else:
            char_times.append(last_time)

    # 匹配率太低时回退到平均分配，避免输出严重错位的时间戳
    if matched < len(script_chars) * 0.4:
        logger.info(f"[align_sub] 匹配率过低 {matched}/{len(script_chars)}, 回退到平均分配")
        return even_distribute()

    result: List[Tuple[float, float, str]] = []
    cum = 0
    prev_end = line_start
    for i, part in enumerate(text_parts):
        n = part_lengths[i]
        if n == 0 or not part.strip():
            cum += n
            continue
        first_t = char_times[cum]
        last_t = char_times[cum + n - 1]
        cum += n

        seg_start = max(prev_end, first_t[0])
        seg_end = max(seg_start + 0.05, last_t[1])
        # 限制在 line 范围内
        seg_start = min(max(seg_start, line_start), line_end)
        seg_end = min(max(seg_end, seg_start + 0.05), line_end)

        result.append((seg_start, seg_end, part))
        prev_end = seg_end

    return result


def _generate_srt_from_merged(
    all_text_parts: List[Tuple[Line, List[str]]],
    merged_audio_path: str,
    ai_provider: str = "deepseek"
) -> str:
    """
    基于合并音频生成字幕。
    策略：在合并音频上整段跑一次 Whisper，得到合并时间轴上的字符级时间戳；
    再用合并时保存的精确 line 偏移把字符流切成 N 段，每行内部用字符贪心匹配
    把脚本子句对齐到 Whisper 字时间戳。
    """
    output_dir = os.path.dirname(merged_audio_path)
    sorted_parts = sorted(all_text_parts, key=lambda x: x[0].index)

    if not sorted_parts:
        return ""

    # 1. 读取 line 偏移：优先从 merge 时保存的 JSON 读取，回退到累加文件时长
    offsets_map = _load_merge_offsets(merged_audio_path)
    if not offsets_map:
        logger.info(f"[generate_srt_from_merged] 未找到偏移 JSON，回退到累加 get_audio_duration")
        cur = 0.0
        offsets_map = {}
        for line, _ in sorted_parts:
            offsets_map[line.index] = cur
            audio_file = f"{line.index:03d}_{line.speaker}.wav"
            audio_path = os.path.join(output_dir, audio_file)
            if os.path.exists(audio_path):
                cur += get_audio_duration(audio_path)

    # 计算合并音频总时长，作为最后一行的结束时间
    try:
        merged_duration = get_audio_duration(merged_audio_path)
    except Exception:
        merged_duration = 0.0

    logger.info(f"[generate_srt_from_merged] 偏移量: {offsets_map}, 合并时长: {merged_duration:.2f}s")

    # 2. 在合并音频上整段跑 Whisper
    char_stream = _whisper_char_stream(merged_audio_path)

    # 3. 逐 line 切片字符流 + 子句对齐
    srt_lines: List[str] = []
    subtitle_index = 1

    for i, (line, text_parts) in enumerate(sorted_parts):
        if not text_parts:
            continue

        line_start = offsets_map.get(line.index, 0.0)
        if i + 1 < len(sorted_parts):
            next_line = sorted_parts[i + 1][0]
            line_end = offsets_map.get(next_line.index, line_start)
        else:
            line_end = merged_duration if merged_duration > line_start else line_start

        # 切出该 line 的 Whisper 字符
        line_chars = [c for c in char_stream if line_start <= c[1] < line_end] if char_stream else []

        aligned = _align_subsentences(text_parts, line_chars, line_start, line_end)

        if not aligned:
            # 整 line 都没有有效子句
            continue

        for seg_start, seg_end, part in aligned:
            srt_lines.append(f"{subtitle_index}")
            srt_lines.append(f"{format_srt_time(seg_start)} --> {format_srt_time(seg_end)}")
            srt_lines.append(part)
            srt_lines.append("")
            subtitle_index += 1

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


def _fill_gaps(srt_content: str, max_gap_fill: float = 0.6) -> str:
    """
    消除相邻字幕之间的小间隙：仅当间隙 <= max_gap_fill 秒时才把上一条的 end
    延伸到下一条的 start。跨越长静音时保留原 end，避免上一条字幕停留过久。
    """
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
            cur_parts = [s.strip() for s in cur_time_line.split("-->")]
            if len(cur_parts) != 2:
                continue
            cur_start, cur_end = cur_parts
            next_start = next_time_line.split("-->")[0].strip()
            try:
                gap = _parse_srt_time(next_start) - _parse_srt_time(cur_end)
            except Exception:
                continue
            if 0 < gap <= max_gap_fill:
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
