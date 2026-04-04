# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a podcast audio generation tool that converts dialogue scripts into spoken audio using Azure Cognitive Services Text-to-Speech API.

## Development Commands

```bash
# Install dependencies
pip install azure-cognitiveservices-speech python-dotenv

# Run the TTS generator
python tts.py
```

## Architecture

### Core Flow
1. **Input**: `script.txt` - Plain text file with character dialogue
2. **Processing**: `tts.py` parses lines, maps characters to voices, calls Azure Speech API
3. **Output**: `output_audio/` - WAV files named `{line_number:03d}_{speaker_name}.wav`

### Script Format
Each line in `script.txt` follows the format:
```
角色名: 台词内容
CharacterName: Dialogue text
```
Both Chinese colon (`：` ) and English colon (`:`) are supported as separators.

### Voice Configuration (.env)
```
AZURE_SPEECH_KEY=your_key_here
{CHARACTER_NAME}_VOICE=voice_name
```

Example voice names for Chinese:
- `zh-CN-XiaoxiaoNeural` (female)
- `zh-CN-YunyiNeural` (male)
- `zh-CN-Xiaoxiao2:DragonHDFlashLatestNeural` (enhanced quality)

The script uses SSML with `<prosody rate="0.6">` for slower speech and outputs 48kHz 16-bit mono PCM WAV files.

### Audio Output Behavior
- Files are named with 3-digit line numbers to maintain script order
- Old files with the same line number prefix are auto-deleted before generating new ones
- If a character has no voice configured in `.env`, falls back to `zh-CN-XiaoxiaoNeural`

## Azure Speech Region

Hardcoded to `eastus` in `tts.py`. If your key belongs to a different region, update line 14.
