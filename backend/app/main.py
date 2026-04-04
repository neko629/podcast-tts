import os
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .routes import voice, audio
from .models.schemas import ScriptParseResponse
from .services.parser import parse_script, extract_characters
from . import state

app = FastAPI(
    title="播客TTS生成器",
    description="将剧本转换为语音的Web服务",
    version="1.0.0"
)

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],  # Vite默认端口
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 确保输出目录存在
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "output")
os.makedirs(OUTPUT_DIR, exist_ok=True)

# 挂载静态文件服务（用于访问生成的音频）
app.mount("/output", StaticFiles(directory=OUTPUT_DIR), name="output")


@app.post("/api/script/parse", response_model=ScriptParseResponse)
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

        # 保存到全局变量
        state.last_uploaded_script = lines

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


# 注册其他路由
app.include_router(voice.router)
app.include_router(audio.router)


@app.get("/")
async def root():
    return {
        "message": "播客TTS生成器API",
        "docs": "/docs"
    }


@app.get("/api/health")
async def health_check():
    return {"status": "ok"}
