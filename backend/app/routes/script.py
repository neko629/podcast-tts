from fastapi import APIRouter, UploadFile, File, HTTPException
from ..models.schemas import ScriptParseResponse
from ..services.parser import parse_script, extract_characters

router = APIRouter(prefix="/api/script", tags=["script"])


@router.post("/parse", response_model=ScriptParseResponse)
async def parse_uploaded_script(file: UploadFile = File(...)):
    """
    上传并解析剧本文件
    """
    # 检查文件类型
    if not file.filename.endswith('.txt'):
        raise HTTPException(status_code=400, detail="只支持 .txt 文件")

    try:
        # 读取文件内容
        content = await file.read()
        text = content.decode('utf-8')

        # 解析剧本
        lines = parse_script(text)

        if not lines:
            raise HTTPException(status_code=400, detail="无法解析剧本内容，请检查格式")

        # 提取角色
        characters = extract_characters(lines)

        return ScriptParseResponse(
            characters=characters,
            lines=lines
        )

    except UnicodeDecodeError:
        raise HTTPException(status_code=400, detail="文件编码错误，请使用UTF-8编码")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"解析失败: {str(e)}")
