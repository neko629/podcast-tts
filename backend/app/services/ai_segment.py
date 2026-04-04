"""
MiniMax AI 服务 - 使用 LangChain 进行智能断句
"""
import os
import json
import logging
from datetime import datetime
from typing import List
from dotenv import load_dotenv

load_dotenv()

from langchain_openai import ChatOpenAI
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import JsonOutputParser

MINIMAX_API_KEY = os.getenv("MINIMAX_API_KEY", "")
MINIMAX_BASE_URL = "https://api.minimaxi.com/v1"
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
DEEPSEEK_BASE_URL = "https://api.deepseek.com"

# 创建专门的logger
logger = logging.getLogger("ai_segment")

# 配置日志（仅当logger没有处理器时）
if not logger.handlers:
    log_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "logs")
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, "ai_segment.log")

    # 文件处理器
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setLevel(logging.INFO)
    file_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                                      datefmt='%Y-%m-%d %H:%M:%S')
    file_handler.setFormatter(file_formatter)

    # 控制台处理器
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))

    # 添加到logger
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    logger.setLevel(logging.INFO)

    # 记录初始化信息，同时测试文件和控制台输出
    logger.info(f"AI Segment logger initialized - 日志文件: {log_file}")
    logger.info(f"Logger handlers: {logger.handlers}")


def get_llm(provider: str = "deepseek"):
    """获取 LLM 实例，支持 deepseek 和 minimax"""
    if provider == "deepseek":
        if not DEEPSEEK_API_KEY:
            raise ValueError("未配置 DEEPSEEK_API_KEY 环境变量")
        return ChatOpenAI(
            model="deepseek-chat",
            api_key=DEEPSEEK_API_KEY,
            base_url=DEEPSEEK_BASE_URL,
            temperature=0.3,
            max_tokens=180000,
        )
    elif provider == "minimax":
        if not MINIMAX_API_KEY:
            raise ValueError("未配置 MINIMAX_API_KEY 环境变量")
        return ChatOpenAI(
            model="MiniMax-M2.7",
            api_key=MINIMAX_API_KEY,
            base_url=MINIMAX_BASE_URL,
            temperature=0.3,
            max_tokens=180000,
            extra_body={"reasoning_split": True}
        )
    else:
        raise ValueError(f"不支持的 AI 提供商: {provider}")


async def split_sentences_with_ai(text: str, max_length: int = 40, provider: str = "deepseek") -> List[str]:
    """
    使用 MiniMax AI 对文本进行智能断句

    Args:
        text: 原始文本
        max_length: 每句最大字符数

    Returns:
        断句后的文本列表
    """
    logger.info(f"split_sentences_with_ai 调用: text_length={len(text)}, max_length={max_length}")

    if not MINIMAX_API_KEY:
        logger.error("未配置 MINIMAX_API_KEY 环境变量")
        raise ValueError("未配置 MINIMAX_API_KEY 环境变量")

    if not text or not text.strip():
        logger.warning("split_sentences_with_ai: 输入文本为空")
        return []

    prompt = PromptTemplate.from_template(
        """你是一个专业的播客字幕编辑。请将以下中文文本智能地分割成简短的字幕句子。

要求：
1. 长度限制： 每行字幕不超过 {max_length} 个字符（包含所有字符：汉字、英文字母、空格、标点等）。如果超过，必须在语义合理处断行，绝不能因为原句没有标点就不断行。
2. 合并优先： 在长度允许的前提下，尽量将相邻的短语合并成一行，避免产生过短的字幕（少于4个字的行应尽量与相邻行合并）。
3. 标点清理： 删除原文中所有的句号、逗号、感叹号、顿号。仅保留问号（？）。
4. 空格代标点： 删除标点后，所有原标点位置（包括句号、逗号、感叹号、顿号）一律替换为一个半角空格，用空格模拟说话停顿感。多个短句合并成一行时，句与句之间同样用空格连接，不能直接拼接。
5. 书名号保护： 书名号《》及其内部内容视为整体，禁止从中途断开。
6. 强制断行： 即使原句没有任何标点，如果一行超过 {max_length} 个字符，也必须在主谓之间、因果转折等语义完整处强制断行。
7. 输出格式： 仅返回一个 JSON 字符串数组，每项为一行字幕。

示例（max_length=10）：
输入：哈哈看来你今天早上起来很不容易
输出：["哈哈 看来", "你今天早上", "起来很不容易"]

示例（max_length=15）：
输入：大家好，我是小悦！欢迎来到今天的《大白话中文》！
输出：["大家好 我是小悦", "欢迎来到今天的《大白话中文》"]

示例（max_length=15）：
输入：Leo，早上好！你看上去很累，昨晚没睡好吗？
输出：["Leo 早上好", "你看上去很累 昨晚没睡好吗？"]

待处理文本：
{text}

请直接返回JSON数组，不要有任何解释："""
    )

    parser = JsonOutputParser()

    chain = prompt | get_llm(provider=provider) | parser

    result = await chain.ainvoke({
        "text": text,
        "max_length": max_length
    })

    logger.info(f"[AI断句] 输入: {text}")
    logger.info(f"[AI断句] 输出: {result}")

    if isinstance(result, list):
        return [s.strip() for s in result if s.strip()]

    raise Exception(f"无法解析 AI 返回的结果: {result}")


async def batch_split_sentences_with_ai(
    lines: List[dict],
    max_length: int = 40,
    provider: str = "deepseek"
) -> List[List[str]]:
    """
    批量使用 AI 对多段文本进行智能断句

    Args:
        lines: [{"speaker": "角色名", "text": "文本"}, ...]
        max_length: 每句最大字符数
        provider: AI 提供商 (deepseek 或 minimax)

    Returns:
        外层列表每个元素对应一行文本的断句结果
    """
    results = []

    for line in lines:
        speaker = line.get("speaker", "")
        text = line.get("text", "")

        if not text.strip():
            results.append([])
            continue

        try:
            sentences = await split_sentences_with_ai(text, max_length, provider)
            results.append(sentences)
        except Exception as e:
            logger.error(f"AI断句失败 [{speaker}]: {e}")
            results.append([])

    return results


async def generate_english_subtitles(
    srt_content: str,
    provider: str = "deepseek"
) -> str:
    """
    将中文 SRT 字幕转换为英文字幕

    Args:
        srt_content: 原始中文 SRT 字幕内容
        provider: AI 提供商 (deepseek 或 minimax)

    Returns:
        英文字幕 SRT 内容（保持相同时间轴）
    """
    logger.info(f"generate_english_subtitles 调用: provider={provider}")

    prompt = f"""你是专业的中英翻译专家。请将以下中文 SRT 字幕内容翻译为英文。

要求：
1. 保留所有时间戳和序号完全不变
2. 将中文字符翻译为简洁自然的英文（适合字幕阅读）
3. 保留所有标点符号（逗号、句号、感叹号、问号等）
4. 保留原有的换行格式
5. 每行长度控制在合理范围内，便于阅读
6. 专有名词"大白话中文"固定翻译为"Simply Natural Chinese"
7. **重要：英文字幕条目数量必须与中文字幕完全一致，每行中文对应一行英文，不能合并或拆分，确保时间轴上每一秒都有内容**

示例：
输入：
1
00:00:01,000 --> 00:00:03,500
你好 Leo，今天天气不错！

2
00:00:03,500 --> 00:00:06,000
是啊，我们出去散步吗？

输出：
1
00:00:01,000 --> 00:00:03,500
Hi Leo, the weather is nice today!

2
00:00:03,500 --> 00:00:06,000
Yeah, shall we go for a walk?

待翻译内容：
{srt_content}

请直接返回翻译后的 SRT 内容，不要有任何解释或代码块标记。"""

    try:
        llm = get_llm(provider=provider)
        from langchain_core.messages import HumanMessage
        response = llm.invoke([HumanMessage(content=prompt)])
        english_srt = response.content.strip()

        # 移除可能的 markdown 代码块
        if english_srt.startswith("```"):
            english_srt = english_srt.split("```")[1]
            if english_srt.startswith("srt"):
                english_srt = english_srt[3:].strip()

        logger.info(f"[英文翻译] 成功生成英文字幕，长度: {len(english_srt)}")
        return english_srt

    except Exception as e:
        logger.error(f"[英文翻译] 失败: {e}")
        raise Exception(f"英文翻译失败: {str(e)}")


async def generate_pinyin_subtitles(
    srt_content: str,
    provider: str = "deepseek"
) -> str:
    """
    将中文 SRT 字幕转换为拼音字幕

    Args:
        srt_content: 原始中文 SRT 字幕内容
        provider: AI 提供商 (deepseek 或 minimax)

    Returns:
        拼音字幕 SRT 内容（保持相同时间轴）
    """
    logger.info(f"generate_pinyin_subtitles 调用: provider={provider}")

    prompt = f"""你是拼音转换专家。请将以下中文 SRT 字幕内容转换为拼音字幕。

要求：
1. 保留所有时间戳和序号完全不变
2. 将中文字符转换为拼音（带声调符号直接标在字母上，如：zhōng wén）
3. 移除所有标点符号（包括逗号、句号、感叹号、顿号、问号等）
4. 保留所有英文单词原样不变
5. 保留原有的换行格式

声调符号规则：
- 第一声（阴平）：ā ē ī ō ū ǖ
- 第二声（阳平）：á é í ó ú ǘ
- 第三声（上声）：ǎ ě ǐ ǒ ǔ ǚ
- 第四声（去声）：à è ì ò ù ǜ
- 轻声：a e i o u ü

示例：
输入：
1
00:00:01,000 --> 00:00:03,500
你好 Leo，今天天气不错！

2
00:00:03,500 --> 00:00:06,000
是啊 我们出去散步吗？

输出：
1
00:00:01,000 --> 00:00:03,500
nǐ hǎo Leo jīn tiān tiān qì bù cuò

2
00:00:03,500 --> 00:00:06,000
shì a wǒ men chū qù sàn bù ma

待转换内容：
{srt_content}

请直接返回转换后的 SRT 内容，不要有任何解释或代码块标记。"""

    try:
        llm = get_llm(provider=provider)
        from langchain_core.messages import HumanMessage
        response = llm.invoke([HumanMessage(content=prompt)])
        pinyin_srt = response.content.strip()

        # 移除可能的 markdown 代码块
        if pinyin_srt.startswith("```"):
            pinyin_srt = pinyin_srt.split("```")[1]
            if pinyin_srt.startswith("srt"):
                pinyin_srt = pinyin_srt[3:].strip()

        logger.info(f"[拼音转换] 成功生成拼音字幕，长度: {len(pinyin_srt)}")
        return pinyin_srt

    except Exception as e:
        logger.error(f"[拼音转换] 失败: {e}")
        raise Exception(f"拼音转换失败: {str(e)}")


async def batch_split_all_in_one_call(
    lines: List[dict],
    max_length: int = 40,
    provider: str = "deepseek"
) -> dict:
    """
    将所有文本合并为一段，一次性发送给 AI 进行断句，
    返回结果按原始行的 index 映射。

    Args:
        lines: [{"index": 1, "speaker": "角色名", "text": "文本"}, ...]
        max_length: 每句最大字符数

    Returns:
        dict: {index: [句子列表], ...}
    """
    logger.info(f"batch_split_all_in_one_call 调用: 共 {len(lines)} 行")

    if not MINIMAX_API_KEY:
        logger.error("未配置 MINIMAX_API_KEY 环境变量")
        raise ValueError("未配置 MINIMAX_API_KEY 环境变量")

    # 过滤空文本，并将中文引号替换为全角括号防止JSON解析失败
    def clean_text(text: str) -> str:
        text = text.replace('"', '「').replace('"', '」')
        return text

    non_empty = [ln for ln in lines if ln.get("text", "").strip()]
    if not non_empty:
        return {ln["index"]: [] for ln in lines}

    # 将所有文本用换行拼接，一次性发给 AI
    combined = "\n".join(f"[{ln['index']}]{ln['speaker']}: {clean_text(ln['text'])}" for ln in non_empty)

    prompt = PromptTemplate.from_template(
        """你是一个专业的播客字幕编辑。请将以下中文文本智能地分割成简短的字幕句子。

要求：
1. 长度限制： 每行字幕不超过 {max_length} 个字符（包含所有字符：汉字、英文字母、空格、标点等）。如果超过，必须在语义合理处断行，绝不能因为原句没有标点就不断行。
2. 合并优先： 在长度允许的前提下，尽量将相邻的短语合并成一行，避免产生过短的字幕（少于4个字的行应尽量与相邻行合并）。
3. 标点清理： 删除原文中所有的句号、逗号、感叹号、顿号。仅保留问号（？）。
4. 空格代标点： 删除标点后，所有原标点位置（包括句号、逗号、感叹号、顿号）一律替换为一个半角空格，用空格模拟说话停顿感。多个短句合并成一行时，句与句之间同样用空格连接，不能直接拼接。
5. 书名号保护： 书名号《》及其内部内容视为整体，禁止从中途断开。
6. 强制断行： 即使原句没有任何标点，如果一行超过 {max_length} 个字符，也必须在主谓之间、因果转折等语义完整处强制断行。
7. 输出格式： 仅返回一个 JSON 字符串数组，每项为一行字幕。
8. 行号标记： 返回时用 [序号] 标注每句属于哪一行文本（序号为输入中每行开头的数字标记）。

示例（max_length=10）：
输入：
[1]小悦: 哈哈看来你今天早上起来很不容易

输出：["[1]哈哈 看来", "[1]你今天早上", "[1]起来很不容易"]

示例（max_length=15）：
输入：
[1]小悦: 大家好，我是小悦！欢迎来到今天的《大白话中文》！
[2]小明: 今天我们聊一个有趣的话题。

输出：["[1]大家好 我是小悦", "[1]欢迎来到今天的《大白话中文》", "[2]今天我们聊一个有趣的话题"]

示例（max_length=15）：
输入：
[1]Leo: Leo，早上好！你看上去很累，昨晚没睡好吗？

输出：["[1]Leo 早上好", "[1]你看上去很累 昨晚没睡好吗？"]

待处理文本：
{text}

输出（直接返回JSON数组）："""
    )

    parser = JsonOutputParser()
    chain = prompt | get_llm(provider=provider)

    raw_output = await chain.ainvoke({
        "text": combined,
        "max_length": max_length
    })

    logger.info(f"[AI断句-批量] 输入行数: {len(non_empty)}")
    logger.info(f"[AI断句-批量] 原始输出: {raw_output}")

    try:
        result = parser.invoke(raw_output)
    except Exception as parse_err:
        logger.error(f"[AI断句-批量] JSON解析失败: {parse_err}, 原始内容: {raw_output}")
        raise

    # 按行号标记分组
    sentences_map: dict = {ln["index"]: [] for ln in lines}
    if isinstance(result, list):
        for item in result:
            if not isinstance(item, str):
                continue
            item = item.strip()
            if not item:
                continue
            # 提取 [序号] 前缀
            if item.startswith("["):
                bracket_idx = item.index("]")
                try:
                    row_idx = int(item[1:bracket_idx])
                    sentence = item[bracket_idx + 1:].strip().replace('「', '"').replace('」', '"')
                    if row_idx in sentences_map:
                        sentences_map[row_idx].append(sentence)
                except ValueError:
                    # 没有有效的行号标记，整句归入第一行
                    sentences_map[non_empty[0]["index"]].append(item.replace('「', '"').replace('」', '"'))

    logger.info(f"[AI断句-批量] sentences_map: {sentences_map}")
    return sentences_map
