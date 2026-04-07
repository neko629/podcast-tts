import os
import logging
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import List

logger = logging.getLogger("subtitle_routes")

from ..models.schemas import Line
from ..services.subtitle import generate_srt, preview_subtitle
from ..services.ai_segment import split_sentences_with_ai, batch_split_all_in_one_call, generate_pinyin_subtitles, generate_english_subtitles, generate_pinyin_subtitles_with_chunking, generate_english_subtitles_with_chunking

router = APIRouter(prefix="/api/subtitle", tags=["subtitle"])

OUTPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "output")


class SubtitleGenerateRequest(BaseModel):
    lines: List[Line]
    max_length: int = 40
    use_ai: bool = False
    ai_provider: str = "deepseek"
    script_name: str = "subtitle"


class AISplitRequest(BaseModel):
    text: str
    max_length: int = 40


class AISplitResponse(BaseModel):
    sentences: List[str]


class SubtitlePreviewRequest(BaseModel):
    lines: List[Line]
    max_length: int = 40
    max_preview_lines: int = 5
    use_ai: bool = False
    ai_provider: str = "deepseek"


class SubtitleResponse(BaseModel):
    filename: str
    url: str
    content: str


class PinyinSubtitleRequest(BaseModel):
    content: str
    ai_provider: str = "deepseek"
    base_name: str = "subtitle"


class PinyinSubtitleResponse(BaseModel):
    content: str
    filename: str


class EnglishSubtitleRequest(BaseModel):
    content: str
    ai_provider: str = "deepseek"
    base_name: str = "subtitle"


class EnglishSubtitleResponse(BaseModel):
    content: str
    filename: str


class SubtitlePreviewResponse(BaseModel):
    preview: List[str]
    total_subtitles: int


@router.post("/generate", response_model=SubtitleResponse)
async def generate_subtitle(request: SubtitleGenerateRequest):
    """
    生成SRT字幕文件
    """
    if not request.lines:
        raise HTTPException(status_code=400, detail="没有需要生成字幕的台词")

    try:
        # 如果启用 AI 断句，一次性将所有文本发送给 AI 进行断句
        ai_sentences_map = {}
        if request.use_ai:
            logger.info(f"[generate_subtitle] use_ai=True, 开始AI断句, 共 {len(request.lines)} 行（一次性请求）")
            try:
                lines_dict = [{"index": ln.index, "speaker": ln.speaker, "text": ln.text} for ln in request.lines]
                ai_sentences_map = await batch_split_all_in_one_call(lines_dict, request.max_length, request.ai_provider)
                logger.info(f"[generate_subtitle] AI断句完成: {ai_sentences_map}")
            except Exception as e:
                logger.error(f"AI断句失败: {e}")
                raise HTTPException(status_code=502, detail=f"AI断句失败: {str(e)}")
        else:
            logger.info(f"[generate_subtitle] use_ai=False, 跳过AI断句")

        content, filename = generate_srt(
            request.lines,
            OUTPUT_DIR,
            request.max_length,
            ai_sentences_map if request.use_ai else None,
            ai_provider=request.ai_provider,
            script_name=request.script_name
        )

        return SubtitleResponse(
            filename=filename,
            url=f"/subtitle/{filename}",
            content=content
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"生成字幕失败: {str(e)}")


@router.post("/preview", response_model=SubtitlePreviewResponse)
async def preview_subtitle_api(request: SubtitlePreviewRequest):
    """
    预览字幕分割效果
    """
    if not request.lines:
        raise HTTPException(status_code=400, detail="没有需要预览的台词")

    try:
        # 如果启用 AI 断句，一次性将所有文本发送给 AI 进行断句
        ai_sentences_map = {}
        if request.use_ai:
            logger.info(f"[preview_subtitle] use_ai=True, 开始AI断句, 共 {len(request.lines)} 行（一次性请求）")
            try:
                lines_dict = [{"index": ln.index, "speaker": ln.speaker, "text": ln.text} for ln in request.lines]
                ai_sentences_map = await batch_split_all_in_one_call(lines_dict, request.max_length, request.ai_provider)
            except Exception as e:
                logger.error(f"AI断句失败: {e}")
                raise HTTPException(status_code=502, detail=f"AI断句失败: {str(e)}")

        preview = preview_subtitle(
            request.lines,
            request.max_length,
            request.max_preview_lines,
            ai_sentences_map if request.use_ai else None
        )

        # 计算总字幕条数
        from ..services.subtitle import split_text_by_length
        total = 0
        for line in request.lines:
            parts = split_text_by_length(line.text, request.max_length,
                                        ai_sentences_map.get(line.index) if request.use_ai else None)
            total += len(parts)

        return SubtitlePreviewResponse(
            preview=preview,
            total_subtitles=total
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"预览失败: {str(e)}")


@router.post("/ai-split", response_model=AISplitResponse)
async def ai_split_subtitle(request: AISplitRequest):
    """
    使用 AI 智能断句
    """
    if not request.text.strip():
        return AISplitResponse(sentences=[])

    try:
        sentences = await split_sentences_with_ai(request.text, request.max_length)
        return AISplitResponse(sentences=sentences)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI断句失败: {str(e)}")


@router.get("/download/{filename}")
async def download_subtitle(filename: str):
    """
    下载字幕文件
    """
    file_path = os.path.join(OUTPUT_DIR, filename)

    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="字幕文件不存在")

    return FileResponse(
        file_path,
        media_type="application/x-subrip",
        filename=filename
    )


@router.post("/pinyin", response_model=PinyinSubtitleResponse)
async def generate_pinyin_subtitle(request: PinyinSubtitleRequest):
    """
    将中文 SRT 字幕转换为拼音字幕
    """
    if not request.content.strip():
        raise HTTPException(status_code=400, detail="字幕内容不能为空")

    try:
        logger.info(f"[generate_pinyin_subtitle] 开始生成拼音字幕，长度: {len(request.content)}")

        # 根据内容长度选择处理方式
        if len(request.content) > 20000:  # 超过2万字符使用分块处理
            pinyin_content = await generate_pinyin_subtitles_with_chunking(
                request.content,
                provider=request.ai_provider
            )
            logger.info(f"[generate_pinyin_subtitle] 使用分块处理完成")
        else:
            pinyin_content = await generate_pinyin_subtitles(
                request.content,
                provider=request.ai_provider
            )

        # 生成文件名：基础名 + py.srt
        base_name = request.base_name if request.base_name else "subtitle"
        base_filename = f"{base_name}py.srt"
        file_path = os.path.join(OUTPUT_DIR, base_filename)

        # 写入文件
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(pinyin_content)

        return PinyinSubtitleResponse(
            content=pinyin_content,
            filename=base_filename
        )
    except Exception as e:
        logger.error(f"拼音字幕生成失败: {e}")
        raise HTTPException(status_code=500, detail=f"拼音字幕生成失败: {str(e)}")


@router.post("/english", response_model=EnglishSubtitleResponse)
async def generate_english_subtitle(request: EnglishSubtitleRequest):
    """
    将中文 SRT 字幕转换为英文字幕
    """
    if not request.content.strip():
        raise HTTPException(status_code=400, detail="字幕内容不能为空")

    try:
        logger.info(f"[generate_english_subtitle] 开始生成英文字幕，长度: {len(request.content)}")

        # 根据内容长度选择处理方式
        if len(request.content) > 20000:  # 超过2万字符使用分块处理
            english_content = await generate_english_subtitles_with_chunking(
                request.content,
                provider=request.ai_provider
            )
            logger.info(f"[generate_english_subtitle] 使用分块处理完成")
        else:
            english_content = await generate_english_subtitles(
                request.content,
                provider=request.ai_provider
            )

        # 生成文件名：基础名 + en.srt
        base_name = request.base_name if request.base_name else "subtitle"
        base_filename = f"{base_name}en.srt"
        file_path = os.path.join(OUTPUT_DIR, base_filename)

        # 写入文件
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(english_content)

        return EnglishSubtitleResponse(
            content=english_content,
            filename=base_filename
        )
    except Exception as e:
        logger.error(f"英文字幕生成失败: {e}")
        raise HTTPException(status_code=500, detail=f"英文字幕生成失败: {str(e)}")


class TextProcessRequest(BaseModel):
    text: str
    max_length: int = 40
    ai_provider: str = "deepseek"


class TextProcessResponse(BaseModel):
    processed_text: str
    sentences: List[str]


def _remove_speaker_names(text: str) -> str:
    """
    移除对话文本中的角色名和冒号。
    格式："角色名: 台词" 或 "角色名：台词"
    只移除行首的角色名和冒号，不处理其他位置的冒号。
    """
    lines = text.split('\n')
    cleaned_lines = []

    for line in lines:
        # 检查行是否包含冒号（中文或英文）
        colon_index = line.find(':')
        chinese_colon_index = line.find('：')

        # 使用第一个找到的冒号
        colon_pos = -1
        if colon_index != -1 and chinese_colon_index != -1:
            colon_pos = min(colon_index, chinese_colon_index)
        elif colon_index != -1:
            colon_pos = colon_index
        elif chinese_colon_index != -1:
            colon_pos = chinese_colon_index

        # 如果找到冒号且冒号位置合理（不是行尾），移除角色名部分
        if colon_pos > 0 and colon_pos < len(line) - 1:
            # 移除角色名和冒号，保留台词部分
            dialogue = line[colon_pos + 1:].strip()
            cleaned_lines.append(dialogue)
        else:
            # 没有角色名格式，保留原行
            cleaned_lines.append(line.strip())

    return '\n'.join(cleaned_lines)


@router.post("/process-text", response_model=TextProcessResponse)
async def process_text(request: TextProcessRequest):
    """
    使用AI对对话文本进行智能断句处理（字幕生成前置处理）
    不包含时间戳，只进行AI断句
    """
    if not request.text.strip():
        raise HTTPException(status_code=400, detail="文本内容不能为空")

    try:
        logger.info(f"[process_text] 开始AI文本处理，原始长度={len(request.text)}，max_length={request.max_length}")

        # 预处理：移除角色名和冒号
        preprocessed_text = _remove_speaker_names(request.text)
        logger.info(f"[process_text] 预处理后长度={len(preprocessed_text)}")

        if preprocessed_text != request.text:
            logger.info(f"[process_text] 已移除角色名和冒号")

        # 使用现有的AI分割函数
        sentences = await split_sentences_with_ai(
            preprocessed_text,
            max_length=request.max_length,
            provider=request.ai_provider
        )

        # 将句子连接成处理后的文本（每行一句）
        processed_text = "\n".join(sentences)

        logger.info(f"[process_text] AI处理完成，生成{len(sentences)}个句子")

        return TextProcessResponse(
            processed_text=processed_text,
            sentences=sentences
        )
    except Exception as e:
        logger.error(f"文本处理失败: {e}")
        raise HTTPException(status_code=500, detail=f"文本处理失败: {str(e)}")
