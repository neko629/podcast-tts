import os
import uuid
from fastapi import APIRouter, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse, StreamingResponse
from typing import Dict, List
import asyncio

from ..models.schemas import GenerateRequest, TaskStatus, AudioFile
from ..services.tts import generate_batch
from ..services.parser import parse_script

router = APIRouter(prefix="/api/audio", tags=["audio"])

# 内存中的任务状态存储
tasks: Dict[str, TaskStatus] = {}
results_store: Dict[str, List[dict]] = {}
# 任务取消标志
task_cancel_flags: Dict[str, bool] = {}

OUTPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "output")


@router.post("/generate")
async def generate_audio_api(
    request: GenerateRequest,
    background_tasks: BackgroundTasks
):
    """
    提交音频生成任务
    接收完整的台词列表而不是依赖服务器状态
    """

    # 创建任务
    task_id = str(uuid.uuid4())

    # 过滤需要生成的台词
    lines_to_generate = request.lines
    if request.line_indices:
        lines_to_generate = [
            line for line in request.lines
            if line.index in request.line_indices
        ]

    if not lines_to_generate:
        raise HTTPException(status_code=400, detail="没有需要生成的台词")

    # 初始化任务状态
    tasks[task_id] = TaskStatus(
        task_id=task_id,
        status="processing",
        progress=0,
        total=len(lines_to_generate),
        completed=0,
        message="开始生成..."
    )
    results_store[task_id] = []
    task_cancel_flags[task_id] = False

    # 启动后台任务
    background_tasks.add_task(
        process_generation,
        task_id,
        lines_to_generate,
        request.voice_config,
        request.rate
    )

    return {"task_id": task_id}


async def process_generation(
    task_id: str,
    lines,
    voice_config: Dict[str, str],
    rate: float
):
    """
    后台处理音频生成
    """
    async def progress_callback(result):
        # 检查是否已取消
        if task_cancel_flags.get(task_id, False):
            return False  # 返回False表示停止生成

        tasks[task_id].completed += 1
        tasks[task_id].progress = int(
            (tasks[task_id].completed / tasks[task_id].total) * 100
        )
        results_store[task_id].append(result)

        if result.get("success"):
            tasks[task_id].message = f"已生成 {result['speaker']} 的第 {result['index']} 句"
        else:
            tasks[task_id].message = f"生成失败: {result.get('error', '未知错误')}"
        return True  # 继续生成

    try:
        await generate_batch_with_cancel(
            task_id,
            lines,
            voice_config,
            rate,
            OUTPUT_DIR,
            progress_callback
        )
        if not task_cancel_flags.get(task_id, False):
            tasks[task_id].status = "completed"
            tasks[task_id].message = "生成完成"
    except asyncio.CancelledError:
        tasks[task_id].status = "cancelled"
        tasks[task_id].message = "用户已取消"
    except Exception as e:
        tasks[task_id].status = "failed"
        tasks[task_id].message = str(e)


async def generate_batch_with_cancel(
    task_id: str,
    lines: List,
    voice_config: Dict[str, str],
    rate: float,
    output_dir: str,
    progress_callback=None
) -> List[Dict]:
    """
    批量生成音频，支持取消
    """
    from ..services.tts import generate_audio
    results = []

    for line in lines:
        # 检查是否已取消
        if task_cancel_flags.get(task_id, False):
            raise asyncio.CancelledError("用户已取消")

        # 获取该角色的声音配置，没有则使用默认
        voice_name = voice_config.get(
            line.speaker,
            "zh-CN-XiaoxiaoNeural"
        )

        try:
            result = await generate_audio(line, voice_name, rate, output_dir)
            results.append(result)

            if progress_callback:
                should_continue = await progress_callback(result)
                if not should_continue:
                    break

            # 稍微延迟避免API限流
            await asyncio.sleep(0.5)

        except asyncio.CancelledError:
            raise
        except Exception as e:
            results.append({
                "index": line.index,
                "filename": None,
                "url": None,
                "speaker": line.speaker,
                "text": line.text,
                "success": False,
                "error": str(e)
            })
            if progress_callback:
                should_continue = await progress_callback(results[-1])
                if not should_continue:
                    break

    return results


@router.get("/status/{task_id}", response_model=TaskStatus)
async def get_task_status(task_id: str):
    """
    获取任务状态
    """
    if task_id not in tasks:
        raise HTTPException(status_code=404, detail="任务不存在")
    return tasks[task_id]


@router.post("/stop/{task_id}")
async def stop_task(task_id: str):
    """
    停止正在进行的任务
    """
    if task_id not in tasks:
        raise HTTPException(status_code=404, detail="任务不存在")

    if tasks[task_id].status != "processing":
        return {"message": "任务已完成或已失败", "status": tasks[task_id].status}

    # 设置取消标志
    task_cancel_flags[task_id] = True
    tasks[task_id].status = "cancelled"
    tasks[task_id].message = "用户已取消"

    return {"message": "正在停止任务", "task_id": task_id}


@router.get("/results/{task_id}")
async def get_task_results(task_id: str):
    """
    获取任务结果
    """
    if task_id not in results_store:
        raise HTTPException(status_code=404, detail="任务不存在")

    return {
        "task_id": task_id,
        "status": tasks[task_id].status,
        "files": results_store[task_id]
    }


@router.post("/regenerate/{index}")
async def regenerate_single(
    index: int,
    request: GenerateRequest,
    background_tasks: BackgroundTasks
):
    """
    重新生成单条音频
    会删除原有文件并生成新的
    """
    task_id = str(uuid.uuid4())

    # 找到对应索引的台词
    line_to_regenerate = None
    for line in request.lines:
        if line.index == index:
            line_to_regenerate = line
            break

    if not line_to_regenerate:
        raise HTTPException(status_code=404, detail=f"找不到第 {index} 句台词")

    # 删除旧文件
    prefix = f"{index:03d}_"
    deleted_files = []
    if os.path.exists(OUTPUT_DIR):
        for filename in os.listdir(OUTPUT_DIR):
            if filename.startswith(prefix) and filename.endswith(".wav"):
                try:
                    os.remove(os.path.join(OUTPUT_DIR, filename))
                    deleted_files.append(filename)
                except Exception as e:
                    print(f"删除旧文件失败: {filename}, {e}")

    # 获取声音配置
    voice_name = request.voice_config.get(
        line_to_regenerate.speaker,
        "zh-CN-XiaoxiaoNeural"
    )

    # 初始化任务状态
    tasks[task_id] = TaskStatus(
        task_id=task_id,
        status="processing",
        progress=0,
        total=1,
        completed=0,
        message=f"正在重新生成第 {index} 句..."
    )
    results_store[task_id] = []

    # 启动后台任务
    background_tasks.add_task(
        process_single_generation,
        task_id,
        line_to_regenerate,
        voice_name,
        request.rate
    )

    return {
        "task_id": task_id,
        "deleted_files": deleted_files,
        "message": f"已开始重新生成第 {index} 句"
    }


async def process_single_generation(
    task_id: str,
    lines,
    voice_name: str,
    rate: float
):
    """
    后台处理单条音频重新生成
    """
    try:
        from ..services.tts import generate_audio
        # lines 是一个列表，取第一个
        line = lines[0] if isinstance(lines, list) else lines
        result = await generate_audio(line, voice_name, rate, OUTPUT_DIR)
        results_store[task_id].append(result)
        tasks[task_id].completed = 1
        tasks[task_id].progress = 100
        tasks[task_id].status = "completed" if result.get("success") else "failed"
        tasks[task_id].message = f"重新生成完成" if result.get("success") else f"生成失败: {result.get('error', '未知错误')}"
    except Exception as e:
        tasks[task_id].status = "failed"
        tasks[task_id].message = str(e)


@router.get("/download/{filename}")
async def download_audio(filename: str):
    """
    下载生成的音频文件
    """
    file_path = os.path.join(OUTPUT_DIR, filename)

    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="文件不存在")

    return FileResponse(
        file_path,
        media_type="audio/wav",
        filename=filename
    )


@router.get("/list")
async def list_generated_files():
    """
    列出所有已生成的音频文件
    """
    if not os.path.exists(OUTPUT_DIR):
        return {"files": []}

    files = []
    for filename in sorted(os.listdir(OUTPUT_DIR)):
        if filename.endswith(".wav"):
            file_path = os.path.join(OUTPUT_DIR, filename)
            stat = os.stat(file_path)
            files.append({
                "filename": filename,
                "url": f"/output/{filename}",
                "size": stat.st_size,
                "created": stat.st_mtime
            })

    return {"files": files}
