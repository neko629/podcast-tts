import os
import logging
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import List

logger = logging.getLogger("subtitle_routes")

from ..models.schemas import Line
from ..services.subtitle import generate_srt, preview_subtitle
from ..services.ai_segment import split_sentences_with_ai

router = APIRouter(prefix="/api/subtitle", tags=["subtitle"])

OUTPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "output")


class SubtitleGenerateRequest(BaseModel):
    lines: List[Line]
    max_length: int = 40
    use_ai: bool = False


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


class SubtitleResponse(BaseModel):
    filename: str
    url: str
    content: str


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
        # 如果启用 AI 断句，先调用 AI 对每行文本进行断句
        ai_sentences_map = {}
        if request.use_ai:
            logger.info(f"[generate_subtitle] use_ai=True, 开始AI断句, 共 {len(request.lines)} 行")
            for line in request.lines:
                try:
                    sentences = await split_sentences_with_ai(line.text, request.max_length)
                    ai_sentences_map[line.index] = sentences
                    logger.info(f"[generate_subtitle] AI断句成功 line.index={line.index}: {sentences}")
                except Exception as e:
                    logger.error(f"AI断句失败 [{line.speaker}]: {e}")
                    raise HTTPException(status_code=502, detail=f"AI断句失败: {str(e)}")
        else:
            logger.info(f"[generate_subtitle] use_ai=False, 跳过AI断句")

        content, filename = generate_srt(
            request.lines,
            OUTPUT_DIR,
            request.max_length,
            ai_sentences_map if request.use_ai else None
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
        # 如果启用 AI 断句，先调用 AI 对每行文本进行断句
        ai_sentences_map = {}
        if request.use_ai:
            for line in request.lines:
                try:
                    sentences = await split_sentences_with_ai(line.text, request.max_length)
                    ai_sentences_map[line.index] = sentences
                except Exception as e:
                    logger.error(f"AI断句失败 [{line.speaker}]: {e}")
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
