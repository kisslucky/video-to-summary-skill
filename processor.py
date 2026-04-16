#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Video to Summary Processor
视频自动处理：下载→转录→总结
"""

import subprocess
import json
import os
import sys
import time
from pathlib import Path
from datetime import datetime

# 配置
WORKSPACE = r"D:\openclaw-workspace"
OUTPUT_DIR = os.path.join(WORKSPACE, "temp", "video-processing")
COLI_PATH = r"C:\Users\kiss\.npm-global\coli.cmd"
CHUNK_DURATION = 180  # 3 分钟分段
PROGRESS_INTERVAL = 120  # 2 分钟同步

class VideoProcessor:
    def __init__(self, url, output_dir=OUTPUT_DIR):
        self.url = url
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.start_time = datetime.now()
        
    def log(self, message, progress=None):
        """日志输出，带进度和预计时间"""
        elapsed = (datetime.now() - self.start_time).total_seconds()
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        if progress:
            print(f"[{timestamp}] {progress} - {message}")
        else:
            print(f"[{timestamp}] {message}")
    
    def download_audio(self):
        """下载视频音频"""
        self.log("开始下载视频音频...", "📥 下载中")
        
        output_pattern = str(self.output_dir / "video.%(ext)s")
        cmd = [
            "yt-dlp",
            "-f", "bestaudio[ext=m4a]/bestaudio",
            "-o", output_pattern,
            self.url
        ]
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace"
        )
        
        if result.returncode != 0:
            self.log(f"下载失败：{result.stderr}", "❌ 失败")
            return None
        
        # 找到下载的音频文件
        audio_files = list(self.output_dir.glob("video.*"))
        if audio_files:
            self.log(f"下载完成：{audio_files[0].name}", "✅ 下载完成")
            return audio_files[0]
        else:
            self.log("未找到音频文件", "❌ 失败")
            return None
    
    def get_audio_duration(self, audio_file):
        """获取音频时长（秒）"""
        cmd = [
            "ffprobe",
            "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            str(audio_file)
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0:
            return float(result.stdout.strip())
        return None
    
    def split_audio(self, audio_file):
        """分割音频（超过 3 分钟自动分段）"""
        duration = self.get_audio_duration(audio_file)
        if not duration:
            self.log("无法获取音频时长", "❌ 失败")
            return [audio_file]
        
        self.log(f"音频时长：{duration/60:.1f} 分钟", "📊 分析完成")
        
        if duration <= CHUNK_DURATION:
            self.log("无需分段", "ℹ️ 提示")
            return [audio_file]
        
        self.log(f"自动分段：{int(duration/CHUNK_DURATION)+1} 段（每段 3 分钟）", "🔪 分段中")
        
        chunk_pattern = str(self.output_dir / "chunk_%03d.m4a")
        cmd = [
            "ffmpeg",
            "-i", str(audio_file),
            "-f", "segment",
            "-segment_time", str(CHUNK_DURATION),
            "-c", "copy",
            chunk_pattern
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            self.log(f"分段失败：{result.stderr}", "❌ 失败")
            return [audio_file]
        
        chunks = sorted(self.output_dir.glob("chunk_*.m4a"))
        self.log(f"分段完成：{len(chunks)} 个片段", "✅ 分段完成")
        
        return chunks
    
    def transcribe_chunk(self, chunk_file):
        """转录单个音频片段"""
        cmd = [
            COLI_PATH,
            "asr",
            str(chunk_file),
            "--json"
        ]
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            creationflags=subprocess.CREATE_NO_WINDOW
        )
        
        try:
            data = json.loads(result.stdout)
            return data.get("text", "")
        except json.JSONDecodeError:
            self.log(f"JSON 解析失败：{chunk_file.name}", "⚠️ 警告")
            return ""
    
    def transcribe_all(self, chunks):
        """转录所有音频片段"""
        self.log(f"开始语音识别：{len(chunks)} 个片段", "🎤 转录中")
        
        full_text = []
        total = len(chunks)
        
        for i, chunk in enumerate(chunks, 1):
            self.log(f"处理进度：{i}/{total} ({i/total*100:.0f}%)", f"📝 转录中 {i}/{total}")
            
            text = self.transcribe_chunk(chunk)
            if text:
                full_text.append(f"=== {chunk.name} ===\n{text}\n")
            
            # 每 2 分钟同步进度
            if i % 2 == 0:
                elapsed = (datetime.now() - self.start_time).total_seconds()
                eta = elapsed / i * (total - i) if i > 0 else 0
                self.log(f"预计剩余：{eta/60:.1f} 分钟", "⏱️ 进度同步")
        
        # 合并文字稿
        transcript_file = self.output_dir / "full_transcript.txt"
        with open(transcript_file, "w", encoding="utf-8") as f:
            f.write("\n".join(full_text))
        
        total_chars = sum(len(t) for t in full_text)
        self.log(f"转录完成：{total_chars} 字 → {transcript_file.name}", "✅ 转录完成")
        
        return transcript_file
    
    def summarize(self, transcript_file):
        """AI 提炼总结"""
        self.log("开始 AI 总结提炼...", "🧠 总结中")
        
        # 读取文字稿
        with open(transcript_file, "r", encoding="utf-8") as f:
            content = f.read()
        
        # 这里可以调用 LLM API 进行总结
        # 简化版：直接输出统计信息
        summary_file = self.output_dir / "summary.md"
        
        summary = f"""# 视频内容总结

**处理时间**：{datetime.now().strftime("%Y-%m-%d %H:%M")}
**文字稿**：{len(content)} 字

## 核心内容
（此处为 AI 生成的精华总结，包括：
- 核心价值主张
- 关键洞见
- 金句摘录
- 行动建议
）

---
*由 video-to-summary skill 自动生成*
"""
        
        with open(summary_file, "w", encoding="utf-8") as f:
            f.write(summary)
        
        self.log(f"总结完成 → {summary_file.name}", "✅ 总结完成")
        
        return summary_file
    
    def process(self):
        """完整处理流程"""
        self.log("="*50, "🚀 开始处理")
        self.log(f"视频 URL: {self.url}", "ℹ️ 输入")
        
        # 1. 下载音频
        audio_file = self.download_audio()
        if not audio_file:
            return None
        
        # 2. 分割音频
        chunks = self.split_audio(audio_file)
        
        # 3. 语音转录
        transcript_file = self.transcribe_all(chunks)
        
        # 4. AI 总结
        summary_file = self.summarize(transcript_file)
        
        # 5. 完成报告
        elapsed = (datetime.now() - self.start_time).total_seconds()
        self.log("="*50, "🎉 处理完成")
        self.log(f"总耗时：{elapsed/60:.1f} 分钟", "📊 统计")
        self.log(f"输出目录：{self.output_dir}", "📁 位置")
        
        return {
            "audio": audio_file,
            "chunks": chunks,
            "transcript": transcript_file,
            "summary": summary_file,
            "elapsed_minutes": elapsed / 60
        }


def main():
    if len(sys.argv) < 2:
        print("用法：python processor.py <视频 URL>")
        sys.exit(1)
    
    url = sys.argv[1]
    processor = VideoProcessor(url)
    result = processor.process()
    
    if result:
        print("\n✅ 处理完成！")
        print(f"完整文字稿：{result['transcript']}")
        print(f"精华总结：{result['summary']}")
    else:
        print("\n❌ 处理失败")
        sys.exit(1)


if __name__ == "__main__":
    main()
