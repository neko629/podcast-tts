from fastapi import APIRouter
from typing import List
from ..models.schemas import Voice
from ..services.tts import get_available_voices

router = APIRouter(prefix="/api/voices", tags=["voices"])


@router.get("", response_model=List[Voice])
async def list_voices():
    """
    获取所有可用的语音列表
    """
    return get_available_voices()
