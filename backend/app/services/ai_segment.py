"""
MiniMax AI 服务 - 使用 LangChain 进行智能断句
"""
import os
import json
import logging
from datetime import datetime
from typing import List

from langchain_openai import ChatOpenAI
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import JsonOutputParser

MINIMAX_API_KEY = os.getenv("MINIMAX_API_KEY", "")
MINIMAX_BASE_URL = "https://api.minimaxi.com/v1"

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


def get_llm():
    """获取 MiniMax LLM 实例"""
    if not MINIMAX_API_KEY:
        raise ValueError("未配置 MINIMAX_API_KEY 环境变量")

    return ChatOpenAI(
        model="MiniMax-M2.7",
        api_key=MINIMAX_API_KEY,
        base_url=MINIMAX_BASE_URL,
        temperature=0.3,
        max_tokens=2048,
        extra_body={"reasoning_split": True}
    )


async def split_sentences_with_ai(text: str, max_length: int = 40) -> List[str]:
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
1. 长度限制： 每行字幕不超过 {max_length} 个汉字（不含空格）。
2. 合并优先： 在长度允许的前提下，尽量将相邻的短语合并成一行，避免产生过短的字幕（少于4个字的行应尽量与相邻行合并）。
3. 标点清理： 删除原文中所有的句号、逗号、感叹号、顿号。仅保留问号（？）。
4. 空格代标点： 删除标点后，所有原标点位置（包括句号、逗号、感叹号、顿号）一律替换为一个半角空格，用空格模拟说话停顿感。多个短句合并成一行时，句与句之间同样用空格连接，不能直接拼接。
5. 书名号保护： 书名号《》及其内部内容视为整体，禁止从中途断开。
6. 语义断句： 必须换行时，优先在语义完整处断开（如句末、主谓之间）。
7. 输出格式： 仅返回一个 JSON 字符串数组，每项为一行字幕。

示例（max_length=15）：
输入：大家好，我是小悦！欢迎来到今天的《大白话中文》！
输出：["大家好 我是小悦", "欢迎来到今天的《大白话中文》"]

待处理文本：
{text}

请直接返回JSON数组，不要有任何解释："""
    )

    parser = JsonOutputParser()

    chain = prompt | get_llm() | parser

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
    max_length: int = 40
) -> List[List[str]]:
    """
    批量使用 AI 对多段文本进行智能断句

    Args:
        lines: [{"speaker": "角色名", "text": "文本"}, ...]
        max_length: 每句最大字符数

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
            sentences = await split_sentences_with_ai(text, max_length)
            results.append(sentences)
        except Exception as e:
            logger.error(f"AI断句失败 [{speaker}]: {e}")
            results.append([])

    return results
