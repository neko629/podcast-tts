import os
import time
import asyncio
from typing import List, Dict, Optional
import azure.cognitiveservices.speech as speechsdk
from dotenv import load_dotenv
from ..models.schemas import Line, Voice

load_dotenv()

SPEECH_KEY = os.getenv("AZURE_SPEECH_KEY")
SPEECH_REGION = os.getenv("AZURE_SPEECH_REGION", "eastus")

# 预定义的中文语音列表 (经过Azure验证的可用语音)
AVAILABLE_VOICES = [
    # 标准语音
    Voice(id="zh-CN-XiaoxiaoNeural", name="晓晓", gender="Female", locale="zh-CN"),
    Voice(id="zh-CN-XiaoyiNeural", name="晓伊", gender="Female", locale="zh-CN"),
    Voice(id="zh-CN-XiaochenNeural", name="晓晨", gender="Female", locale="zh-CN"),
    Voice(id="zh-CN-XiaohanNeural", name="晓涵", gender="Female", locale="zh-CN"),
    Voice(id="zh-CN-XiaomengNeural", name="晓萌", gender="Female", locale="zh-CN"),
    Voice(id="zh-CN-YunxiNeural", name="云希", gender="Male", locale="zh-CN"),
    Voice(id="zh-CN-YunjianNeural", name="云健", gender="Male", locale="zh-CN"),
    Voice(id="zh-CN-YunfengNeural", name="云枫", gender="Male", locale="zh-CN"),
    Voice(id="zh-CN-YunhaoNeural", name="云皓", gender="Male", locale="zh-CN"),
    Voice(id="zh-CN-YunyeNeural", name="云野", gender="Male", locale="zh-CN"),
    # Dragon HD Flash — 女声
    Voice(id="zh-CN-Xiaoxiao:DragonHDFlashLatestNeural", name="晓晓HD", gender="Female", locale="zh-CN"),
    Voice(id="zh-CN-Xiaoxiao2:DragonHDFlashLatestNeural", name="晓晓HD 多情感", gender="Female", locale="zh-CN"),
    Voice(id="zh-CN-Xiaochen:DragonHDFlashLatestNeural", name="晓晨HD", gender="Female", locale="zh-CN"),
    Voice(id="zh-CN-Xiaoyi:DragonHDFlashLatestNeural", name="晓伊HD", gender="Female", locale="zh-CN"),
    Voice(id="zh-CN-Xiaoyu:DragonHDFlashLatestNeural", name="晓雨HD", gender="Female", locale="zh-CN"),
    Voice(id="zh-CN-Xiaohan:DragonHDFlashLatestNeural", name="晓涵HD", gender="Female", locale="zh-CN"),
    Voice(id="zh-CN-Xiaoshuang:DragonHDFlashLatestNeural", name="晓双HD（童声）", gender="Female", locale="zh-CN"),
    Voice(id="zh-CN-Xiaoyou:DragonHDFlashLatestNeural", name="晓悠HD（童声）", gender="Female", locale="zh-CN"),
    # Dragon HD Flash — 男声
    Voice(id="zh-CN-Yunyi:DragonHDFlashLatestNeural", name="云逸HD", gender="Male", locale="zh-CN"),
    Voice(id="zh-CN-Yunxi:DragonHDFlashLatestNeural", name="云希HD", gender="Male", locale="zh-CN"),
    Voice(id="zh-CN-Yunxiao:DragonHDFlashLatestNeural", name="云霄HD", gender="Male", locale="zh-CN"),
    Voice(id="zh-CN-Yunhan:DragonHDFlashLatestNeural", name="云翰HD", gender="Male", locale="zh-CN"),
    Voice(id="zh-CN-Yunxia:DragonHDFlashLatestNeural", name="云夏HD（童声）", gender="Male", locale="zh-CN"),
    Voice(id="zh-CN-Yunye:DragonHDFlashLatestNeural", name="云野HD", gender="Male", locale="zh-CN"),
    # Dragon HD Latest（非 Flash，更高质量、延迟略高）
    Voice(id="zh-CN-Xiaochen:DragonHDLatestNeural", name="晓晨HD Pro", gender="Female", locale="zh-CN"),
    Voice(id="zh-CN-Yunfan:DragonHDLatestNeural", name="云帆HD Pro", gender="Male", locale="zh-CN"),
]


def get_available_voices() -> List[Voice]:
    """获取可用的语音列表"""
    return AVAILABLE_VOICES


def generate_audio_sync(
    line: Line,
    voice_name: str,
    rate: float,
    output_dir: str
) -> Dict:
    """
    同步生成单条音频（用于后台线程）
    返回生成结果信息
    """
    if not SPEECH_KEY:
        raise ValueError("未配置 Azure Speech Key")

    # 确保输出目录存在
    os.makedirs(output_dir, exist_ok=True)

    # 配置文件名
    file_name = f"{line.index:03d}_{line.speaker}.wav"
    file_path = os.path.join(output_dir, file_name)

    # 删除可能存在的旧文件
    prefix = f"{line.index:03d}_"
    for existing_file in os.listdir(output_dir):
        if existing_file.startswith(prefix) and existing_file.endswith(".wav"):
            try:
                os.remove(os.path.join(output_dir, existing_file))
            except:
                pass

    # 配置Azure语音服务
    speech_config = speechsdk.SpeechConfig(
        subscription=SPEECH_KEY,
        region=SPEECH_REGION
    )

    # 设置超时时间（单位：毫秒）
    # 连接超时：30秒
    speech_config.set_property(
        speechsdk.PropertyId.SpeechServiceConnection_InitialSilenceTimeoutMs, "30000"
    )

    # 设置输出格式为48kHz 16bit单声道PCM
    speech_config.set_speech_synthesis_output_format(
        speechsdk.SpeechSynthesisOutputFormat.Riff48Khz16BitMonoPcm
    )

    speech_config.speech_synthesis_voice_name = voice_name

    # 配置音频输出
    audio_config = speechsdk.audio.AudioOutputConfig(filename=file_path)

    # 创建合成器
    synthesizer = speechsdk.SpeechSynthesizer(
        speech_config=speech_config,
        audio_config=audio_config
    )

    # 构建SSML
    ssml_text = f"""
    <speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" xml:lang="zh-CN">
        <voice name="{voice_name}">
            <prosody rate="{rate}">{line.text}</prosody>
        </voice>
    </speak>
    """

    # 执行合成，最多重试2次（共3次尝试）
    max_retries = 2
    for attempt in range(max_retries + 1):
        # 每次尝试前删除可能存在的部分文件，避免内容堆叠
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
            except:
                pass

        result = synthesizer.speak_ssml_async(ssml_text).get()

        # 检查结果
        if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
            return {
                "index": line.index,
                "filename": file_name,
                "url": f"/output/{file_name}",
                "speaker": line.speaker,
                "text": line.text,
                "success": True
            }
        else:
            error_msg = ""
            if result.reason == speechsdk.ResultReason.Canceled:
                cancellation_details = result.cancellation_details
                error_msg = str(cancellation_details.error_details)

            # 如果还有重试机会，等待后重试
            if attempt < max_retries:
                time.sleep(1)
                continue

            return {
                "index": line.index,
                "filename": None,
                "url": None,
                "speaker": line.speaker,
                "text": line.text,
                "success": False,
                "error": error_msg
            }


async def generate_audio(
    line: Line,
    voice_name: str,
    rate: float,
    output_dir: str
) -> Dict:
    """
    异步生成单条音频
    在线程池中执行同步的Azure SDK调用
    """
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        None,
        generate_audio_sync,
        line,
        voice_name,
        rate,
        output_dir
    )


async def generate_batch(
    lines: List[Line],
    voice_config: Dict[str, str],
    rate: float,
    output_dir: str,
    progress_callback=None
) -> List[Dict]:
    """
    批量生成音频
    """
    results = []

    for line in lines:
        # 获取该角色的声音配置，没有则使用默认
        voice_name = voice_config.get(
            line.speaker,
            "zh-CN-XiaoxiaoNeural"
        )

        try:
            result = await generate_audio(line, voice_name, rate, output_dir)
            results.append(result)

            if progress_callback:
                await progress_callback(result)

            # 稍微延迟避免API限流
            await asyncio.sleep(0.5)

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
                await progress_callback(results[-1])

    return results
