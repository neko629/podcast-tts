import os
import time
import datetime
import azure.cognitiveservices.speech as speechsdk
from dotenv import load_dotenv

# 加载 .env 文件中的环境变量
load_dotenv()

# 从环境变量中获取 Azure 密钥
SPEECH_KEY = os.getenv("AZURE_SPEECH_KEY")
# 你的账号归属地为美国东部
SPEECH_REGION = "eastus"


def generate_audio_from_script(script_file):
    if not SPEECH_KEY:
        print("错误: 请在 .env 文件中配置 AZURE_SPEECH_KEY")
        return

    # 创建输出文件夹
    output_dir = "output_audio"
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # 询问用户是否生成全文
    generate_all = input("是否生成全文？(y/n) [默认y]: ").strip().lower()
    start_line = 1
    end_line = float('inf')

    if generate_all == 'n':
        try:
            start_line = int(input("请输入起始句序号 (例如 1): ").strip())
            end_line = int(input("请输入结束句序号 (例如 5): ").strip())
        except ValueError:
            print("输入无效，将默认生成全文。")
            start_line = 1
            end_line = float('inf')

    with open(script_file, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    line_number = 0
    # 初始化总时长变量
    total_duration = datetime.timedelta()

    for line in lines:
        line = line.strip()
        # 跳过空行
        if not line:
            continue

        # 这里的 line_number 对应的是有效的台词句数（对应输出文件名的序号）
        line_number += 1

        # 检查是否在用户指定的范围内
        if line_number < start_line or line_number > end_line:
            continue

        # 支持中英文冒号分割角色和台词
        if ':' in line:
            parts = line.split(':', 1)
        elif '：' in line:
            parts = line.split('：', 1)
        else:
            print(
                f"⚠️ 警告: 第 {line_number} 句格式不正确，跳过 (预期格式 '角色: 台词'): {line}")
            continue

        speaker_name = parts[0].strip()
        text = parts[1].strip()

        # 根据角色名动态获取 .env 中的音色名称
        env_key = f"{speaker_name.upper()}_VOICE"
        voice_name = os.getenv(env_key)

        if not voice_name:
            # 如果没配置，使用默认的晓晓声音
            print(
                f"⚠️ 未找到角色 '{speaker_name}' 的音色配置 ({env_key})，将使用默认音色 zh-CN-XiaoxiaoNeural")
            voice_name = "zh-CN-XiaoxiaoNeural"

        # --- 删除旧文件逻辑 ---
        # 查找并删除该序号对应的旧音频文件（防止修改台词角色名后残留旧文件）
        prefix = f"{line_number:03d}_"
        for existing_file in os.listdir(output_dir):
            if existing_file.startswith(prefix) and existing_file.endswith(".wav"):
                old_file_path = os.path.join(output_dir, existing_file)
                try:
                    os.remove(old_file_path)
                    print(f"🗑️ 已删除旧文件: {existing_file}")
                except Exception as e:
                    print(f"⚠️ 无法删除旧文件 {existing_file}: {e}")

        # 配置 Azure 语音服务
        speech_config = speechsdk.SpeechConfig(subscription=SPEECH_KEY,
                                               region=SPEECH_REGION)

        # 设置超时时间（单位：毫秒）
        # 连接超时：30秒，响应超时：120秒（长文本需要更长时间）
        speech_config.set_property(
            speechsdk.PropertyId.SpeechServiceConnection_InitialSilenceTimeoutMs, "30000"
        )
        speech_config.set_property(
            speechsdk.PropertyId.SpeechServiceConnection_ResponseTimeoutMs, "120000"
        )

        # --- 设置输出音频格式为 48kHz 16bit 单声道 PCM ---
        speech_config.set_speech_synthesis_output_format(
            speechsdk.SpeechSynthesisOutputFormat.Riff48Khz16BitMonoPcm)

        # 注意：在使用 SSML 时，声音名称主要由 SSML 内部的 <voice name="..."> 决定
        speech_config.speech_synthesis_voice_name = voice_name

        # 配置文件输出路径 (格式: 001_角色名.wav)
        file_name = f"{line_number:03d}_{speaker_name}.wav"
        file_path = os.path.join(output_dir, file_name)
        audio_config = speechsdk.audio.AudioOutputConfig(filename=file_path)

        # 创建语音合成器
        synthesizer = speechsdk.SpeechSynthesizer(speech_config=speech_config,
                                                  audio_config=audio_config)
        rate = 0.6
        # 使用 SSML 构建带语速控制的文本，rate="0.7" 代表 0.7 倍速
        ssml_text = f"""
        <speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" xml:lang="zh-CN">
            <voice name="{voice_name}">
                <prosody rate="{rate}">{text}</prosody>
            </voice>
        </speak>
        """

        print(
            f"正在合成第 {line_number} 句 -> 角色: {speaker_name}, 音色: {voice_name}, 语速: {rate}倍, 音质: 48kHz...")

        # 最多重试2次（共3次尝试）
        max_retries = 2
        for attempt in range(max_retries + 1):
            # 每次尝试前删除可能存在的部分文件，避免内容堆叠
            if os.path.exists(file_path):
                try:
                    os.remove(file_path)
                except:
                    pass

            # 执行合成 (注意这里改为了 speak_ssml_async)
            result = synthesizer.speak_ssml_async(ssml_text).get()

            # 处理结果
            if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
                print(f"✅ 成功生成: {file_path}")
                # 累加生成的音频时长
                total_duration += result.audio_duration
                break
            elif result.reason == speechsdk.ResultReason.Canceled:
                cancellation_details = result.cancellation_details
                if attempt < max_retries:
                    print(f"⚠️ 第 {line_number} 句合成失败 (尝试 {attempt + 1}/{max_retries + 1})，正在重试...")
                    time.sleep(1)  # 重试前等待1秒
                    continue
                else:
                    print(f"❌ 合成取消/失败: {cancellation_details.reason}")
                    if cancellation_details.reason == speechsdk.CancellationReason.Error:
                        print(f"错误详情: {cancellation_details.error_details}")
                        print("请检查你的 API 密钥、区域以及网络连接。")

        # 稍微加一点延迟，避免触发 API 速率限制
        time.sleep(0.5)

    # 循环结束后打印总时长
    print(f"\n🎉 指定范围的音频生成完毕！")
    if total_duration.total_seconds() > 0:
        print(f"⏱️ 本次生成的音频总时长: {total_duration}")


if __name__ == "__main__":
    script_path = "script.txt"
    if not os.path.exists(script_path):
        print(f"找不到脚本文件: {script_path}")
    else:
        print("--- 开始生成播客音频 ---")
        generate_audio_from_script(script_path)
        print("--- 生成结束 ---")