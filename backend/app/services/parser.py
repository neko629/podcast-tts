from typing import List, Set
from ..models.schemas import Line


def parse_script(file_content: str) -> List[Line]:
    """
    解析剧本文件，返回台词列表
    支持中英文冒号分隔
    """
    lines = []
    line_number = 0

    for raw_line in file_content.split('\n'):
        line = raw_line.strip()
        if not line:
            continue

        # 支持中英文冒号
        if ':' in line:
            parts = line.split(':', 1)
        elif '：' in line:
            parts = line.split('：', 1)
        else:
            continue

        line_number += 1
        lines.append(Line(
            index=line_number,
            speaker=parts[0].strip(),
            text=parts[1].strip()
        ))

    return lines


def extract_characters(lines: List[Line]) -> List[str]:
    """从台词列表中提取所有角色名"""
    characters: Set[str] = set()
    for line in lines:
        characters.add(line.speaker)
    return sorted(list(characters))
