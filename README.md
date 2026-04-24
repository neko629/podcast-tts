# 播客全能助手系统 (PodcastTTS)

**https://github.com/neko629/podcast-tts**

一个基于FastAPI后端和React前端的AI播客音频与字幕全栈处理系统，实现从剧本到高质量语音再到多语言字幕的完整自动化流程。

## 功能特性

### 核心功能
- **剧本上传与解析**: 支持拖拽上传txt格式剧本，自动识别角色和对话
- **角色声音配置**: 为每个角色单独选择Azure语音，内置 10 个标准 Neural 音色 + 16 个 Dragon HD/HD Flash 高清音色（含童声和多情感晓晓）
- **批量音频生成**: 支持选择部分或全部台词进行生成
- **语速调节**: 可调节0.3-1.0倍的语速
- **实时进度监控**: 显示生成进度和状态，支持停止任务
- **在线播放与下载**: 直接在浏览器中播放生成的音频，支持单独或批量下载
- **编辑重生成**: 支持编辑已生成台词的文字内容并重新生成音频，修改同步保存到剧本
- **失败自动重试**: 音频生成失败时自动重试最多2次，批量重试失败项时显示实时进度

### AI字幕处理
- **AI智能断句**: 调用DeepSeek/MiniMax大模型对台词进行智能语义断句，生成符合阅读习惯的字幕
- **拼音字幕**: 基于中文字幕自动生成带声调符号的拼音字幕（nǐ hǎo）
- **英文字幕**: 自动翻译中文字幕为英文，保持相同时间轴，专有名词精准翻译
- **文本预处理**: 对对话文本进行AI智能断句，去除角色名和标点，输出规范格式
- **可调节断句长度**: 支持自定义每行字幕字符数（10-40字可调）

### 时间轴与对齐
- **精准时间轴**: 使用Faster-Whisper大模型进行词级时间戳对齐，确保字幕与音频精确同步
- **无缝时间轴**: 自动消除相邻字幕之间的间隙
- **长音频合并**: 将分段音频智能合并，使用偏移量算法实现精确时间对齐
- **完整性验证**: 自动验证字幕条目数量与原始内容一致

## 技术栈

### 后端
- **Python** + **FastAPI** - 高性能Web框架
- **Azure Cognitive Services Speech SDK** - 语音合成
- **LangChain** + **DeepSeek/MiniMax API** - AI智能断句、拼音转换、英文翻译
- **Faster-Whisper** (Whisper Large) - GPU加速语音识别与时间戳对齐
- **Uvicorn** - ASGI服务器

### 前端
- **React 18** + **TypeScript** - 类型安全的前端框架
- **Vite** - 快速构建工具
- **Tailwind CSS** + **Radix UI** - 现代化UI组件库
- **Axios** - HTTP客户端
- **Vibe Coding** - AI辅助协作开发

## 快速开始

### 环境要求
- Python 3.10+
- Node.js 18+
- NVIDIA GPU (推荐RTX 3070及以上，支持CUDA加速)

### 一键启动（推荐）

#### Windows

```bash
# 一键启动
start.bat

# 一键停止
stop.bat

# 一键重启
restart.bat
```

#### Linux / macOS

```bash
# 赋予执行权限
chmod +x start.sh stop.sh restart.sh

# 一键启动
./start.sh
```

启动后会自动打开浏览器访问 http://localhost:5173

### 手动启动

#### 1. 克隆项目

```bash
git clone https://github.com/neko629/podcast-tts.git
cd podcast-tts
```

#### 2. 配置环境变量

复制 `.env.example` 为 `.env` 并填写密钥：

```bash
# Azure语音服务（必需）
AZURE_SPEECH_KEY=your_azure_key_here

# AI服务（至少配置一个）
MINIMAX_API_KEY=your_minimax_key_here
DEEPSEEK_API_KEY=your_deepseek_key_here

# Hugging Face Token（用于下载Whisper模型，可选）
HF_TOKEN=your_hf_token_here
```

#### 3. 启动后端

```bash
cd backend

# 安装依赖
pip install -r requirements.txt

# 启动服务
python run.py
```

后端服务将在 http://localhost:8000 运行

#### 4. 启动前端

```bash
cd frontend

# 安装依赖
npm install

# 启动开发服务器
npm run dev
```

前端服务将在 http://localhost:5173 运行

## 使用指南

### 基础工作流

1. **上传剧本**: 拖拽或点击上传txt格式的剧本文件
2. **选择台词**: 在剧本列表中选择要生成的台词（默认全选）
3. **配置声音**: 为每个角色选择合适的语音
4. **调整语速**: 拖动滑块调整语速（0.3-1.0倍）
5. **生成音频**: 点击"开始生成音频"按钮
6. **播放/下载**: 生成完成后可直接播放或下载音频文件

### 字幕生成工作流

1. **合并音频**（可选）: 点击"合并音频"按钮，将分段音频合成为完整文件
2. **生成中文字幕**: 选择AI引擎，预览断句效果后生成SRT字幕
3. **生成拼音/英文字幕**: 生成中文字幕后，可继续生成拼音字幕或英文字幕
4. **下载字幕**: 自动下载对应的字幕文件

### 文本预处理工作流

1. **上传对话文本**: 在顶部工具栏上传txt格式对话文件（包含角色名和冒号格式）
2. **设置断句长度**: 通过滑块调节每行字幕字符数（默认15字）
3. **AI智能断句**: 点击"AI智能断句"按钮，自动去除角色名、标点，进行语义断句
4. **下载处理结果**: 自动下载处理后的文本文件

## 剧本格式

剧本文件应为纯文本格式（.txt），支持两种冒号格式：

```
小悦：大家好！欢迎来到今天的节目。
Leo: 大家好，我是Leo。
小悦：今天我们聊一个很有趣的话题。
```

支持中英文冒号分隔。

## 项目结构

```
podcast-tts/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI入口
│   │   ├── models/              # 数据模型
│   │   ├── routes/              # API路由
│   │   └── services/            # 业务逻辑
│   │       ├── ai_segment.py    # AI断句、拼音、翻译
│   │       └── subtitle.py       # 字幕生成、Whisper对齐
│   ├── output/                  # 生成音频/字幕输出
│   ├── logs/                    # 运行日志
│   └── run.py                   # 启动脚本
├── frontend/
│   ├── src/
│   │   ├── components/          # React组件
│   │   │   ├── SubtitleGenerator.tsx  # 字幕生成组件
│   │   │   └── SubtitleToolbar.tsx   # 顶部工具栏
│   │   ├── pages/               # 页面
│   │   ├── services/            # API服务
│   │   └── types/               # TypeScript类型
│   └── package.json
├── docs/
│   └── architecture.png          # 架构图
├── start.bat / start.sh         # 一键启动
├── stop.bat / stop.sh           # 一键停止
├── restart.bat / restart.sh     # 一键重启
└── README.md
```

## 主要API端点

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/script/parse` | POST | 上传并解析剧本文件 |
| `/api/voices` | GET | 获取可用语音列表 |
| `/api/audio/generate` | POST | 提交音频生成任务 |
| `/api/audio/merge` | POST | 合并音频文件 |
| `/api/audio/status/{task_id}` | GET | 查询任务状态 |
| `/api/subtitle/preview` | POST | AI预览字幕断句效果 |
| `/api/subtitle/generate` | POST | 生成中文字幕 |
| `/api/subtitle/pinyin` | POST | 将中文字幕转换为拼音字幕 |
| `/api/subtitle/english` | POST | 将中文字幕翻译为英文字幕 |
| `/api/subtitle/process-text` | POST | AI文本预处理（智能断句） |

## 字幕文件名规则

字幕文件命名基于原始剧本文件名：

- **中文字幕**: `{脚本名}{4位随机数}.srt`
- **拼音字幕**: `{脚本名}{4位随机数}py.srt`
- **英文字幕**: `{脚本名}{4位随机数}en.srt`

## 开发说明

### 后端开发

```bash
cd backend

# 开发模式运行（热重载）
python run.py

# 查看日志
tail -f logs/ai_segment.log
```

### 前端开发

```bash
cd frontend

# 开发模式运行
npm run dev

# 构建生产版本
npm run build
```

## 技术亮点

### 1. 多AI模型协作
- 智能断句、拼音转换、英文翻译三个模块可分别选择不同AI引擎
- 支持DeepSeek和MiniMax两种AI提供商
- 分块处理机制支持超长内容（2万字符以上）完整转换

### 2. Whisper大模型时间轴对齐
- 使用Faster-Whisper Large模型进行GPU加速识别
- 词级时间戳确保字幕与音频精确同步
- 偏移量算法消除分段音频合并后的时间误差

### 3. Vibe Coding协作开发
- 全程采用AI辅助编程工作流
- 实时对话、代码审查与智能重构
- 快速迭代功能模块，提升开发效率

## 许可证

MIT License

## 致谢

- [Azure Cognitive Services](https://azure.microsoft.com/services/cognitive-services/speech/)
- [DeepSeek](https://deepseek.com/)
- [MiniMax](https://www.minimaxi.com/)
- [OpenAI Whisper](https://github.com/openai/whisper)
- [FastAPI](https://fastapi.tiangolo.com/)
- [React](https://react.dev/)
- [Vercel](https://vercel.com/)
