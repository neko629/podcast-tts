# 播客TTS生成器 (Podcast TTS Generator)

一个基于FastAPI后端和React前端的全栈Web应用，用于将播客对话剧本转换为高质量的语音音频。

![项目结构](docs/architecture.png)

## 功能特性

- **剧本上传**: 支持拖拽上传txt格式的剧本文件
- **角色声音配置**: 为每个角色单独选择Azure语音
- **批量生成**: 支持选择部分或全部台词进行生成
- **语速调节**: 可调节0.3-1.0倍的语速
- **实时进度**: 显示生成进度和状态
- **在线播放**: 直接在浏览器中播放生成的音频
- **单文件下载**: 支持单独下载每个音频文件
- **AI智能字幕**: 调用 MiniMax AI 对台词进行智能断句，生成 SRT 字幕文件

## 技术栈

### 后端
- **FastAPI** - 高性能Python Web框架
- **Azure Cognitive Services Speech SDK** - 语音合成
- **MiniMax AI (LangChain)** - 智能断句
- **Uvicorn** - ASGI服务器

### 前端
- **React 18** + **TypeScript**
- **Vite** - 快速构建工具
- **Tailwind CSS** - 实用优先的CSS框架
- **Axios** - HTTP客户端

## 快速开始

### 一键启动（推荐）

#### Windows

双击运行 `start.bat` 脚本，自动启动后端和前端服务：

```bash
# 一键启动
start.bat

# 一键停止
stop.bat

# 一键重启（自动停止再启动）
restart.bat
```

#### Linux / macOS

赋予脚本执行权限后运行：

```bash
# 赋予执行权限
chmod +x start.sh stop.sh restart.sh

# 一键启动
./start.sh

# 一键停止
./stop.sh

# 一键重启（自动停止再启动）
./restart.sh
```

启动后会自动打开浏览器访问 http://localhost:5173

### 手动启动

#### 1. 克隆项目

```bash
git clone <repository-url>
cd podcast-tools
```

### 2. 配置环境变量

复制 `.env.example` 为 `.env` 并填写你的Azure密钥：

```bash
cp .env .env.local
```

编辑 `.env` 文件：

```
AZURE_SPEECH_KEY=your_azure_key_here
AZURE_SPEECH_REGION=eastus
MINIMAX_API_KEY=your_minimax_key_here
```

### 3. 启动后端

```bash
# 安装依赖
pip install fastapi uvicorn python-multipart pydantic azure-cognitiveservices-speech python-dotenv aiofiles

# 启动服务
python backend/run.py
```

后端服务将在 http://localhost:8000 运行

### 4. 启动前端

```bash
cd frontend

# 安装依赖
npm install

# 启动开发服务器
npm run dev
```

前端服务将在 http://localhost:5173 运行

### 5. 访问应用

打开浏览器访问 http://localhost:5173

## 使用指南

1. **上传剧本**: 拖拽或点击上传txt格式的剧本文件
2. **选择台词**: 在剧本列表中选择要生成的台词（默认全选）
3. **配置声音**: 为每个角色选择合适的语音
4. **调整语速**: 拖动滑块调整语速（0.3-1.0倍）
5. **生成音频**: 点击"开始生成音频"按钮
6. **播放/下载**: 生成完成后可直接播放或下载音频文件
7. **生成字幕**: 点击"生成字幕"按钮，可先点击"AI 预览"查看断句效果，满意后点击"生成并下载"导出 SRT 文件

## 剧本格式

剧本文件应为纯文本格式（.txt），每行格式如下：

```
角色名: 台词内容
角色名：台词内容
```

示例：

```
小悦：大家好！欢迎来到今天的节目。
Leo: 大家好，我是Leo。
小悦：今天我们聊一个很有趣的话题。
```

支持中英文冒号分隔。

## API文档

启动后端后，访问 http://localhost:8000/docs 查看自动生成的Swagger API文档。

### 主要API端点

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/script/parse` | POST | 上传并解析剧本文件 |
| `/api/voices` | GET | 获取可用语音列表 |
| `/api/audio/generate` | POST | 提交音频生成任务 |
| `/api/audio/status/{task_id}` | GET | 查询任务状态 |
| `/api/audio/download/{filename}` | GET | 下载音频文件 |
| `/api/subtitle/preview` | POST | AI预览字幕断句效果 |
| `/api/subtitle/generate` | POST | 生成并下载SRT字幕文件 |

## 项目结构

```
podcast-tools/
├── backend/
│   ├── app/
│   │   ├── main.py          # FastAPI入口
│   │   ├── models/          # 数据模型
│   │   ├── routes/          # API路由
│   │   └── services/        # 业务逻辑（含AI断句）
│   ├── output/              # 生成音频/字幕输出
│   ├── logs/                # 运行日志
│   └── run.py               # 启动脚本
├── frontend/
│   ├── src/
│   │   ├── components/      # React组件（含SubtitleGenerator）
│   │   ├── pages/           # 页面
│   │   ├── services/        # API服务
│   │   └── types/           # TypeScript类型
│   └── package.json
├── start.bat / start.sh     # 一键启动
├── stop.bat / stop.sh       # 一键停止
├── restart.bat / restart.sh # 一键重启
└── README.md
```

## Azure语音服务

本项目使用Azure Cognitive Services Speech API进行语音合成。需要：

1. 在Azure门户创建Speech服务资源
2. 获取密钥和区域信息
3. 配置到.env文件中

支持的语音包括：
- 晓晓 (zh-CN-XiaoxiaoNeural) - 女声
- 云逸 (zh-CN-YunyiNeural) - 男声
- 以及其他多种中文语音

## 开发说明

### 后端开发

```bash
# 进入后端目录
cd backend

# 开发模式运行（热重载）
python run.py

# 运行测试
pytest
```

### 前端开发

```bash
# 进入前端目录
cd frontend

# 安装新依赖
npm install <package>

# 开发模式运行
npm run dev

# 构建生产版本
npm run build
```

## 许可证

MIT License

## 贡献

欢迎提交Issue和Pull Request！

## 致谢

- [Azure Cognitive Services](https://azure.microsoft.com/services/cognitive-services/speech/)
- [FastAPI](https://fastapi.tiangolo.com/)
- [React](https://react.dev/)
