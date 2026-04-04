# 共享状态存储
from typing import List
from .models.schemas import Line

# 全局变量存储最后上传的剧本
last_uploaded_script: List[Line] = []
