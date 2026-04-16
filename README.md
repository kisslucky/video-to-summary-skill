# 🎥 Video to Summary Skill

**一键安装视频处理技能**

---

## 🚀 快速安装

```bash
cd D:\openclaw-workspace\skills\video-to-summary
node install-deps.js
```

---

## 📦 依赖项

### 自动安装
运行 `node install-deps.js` 会自动安装：

1. **Python 依赖**
   - yt-dlp（视频下载）
   - requests（HTTP 请求）

2. **Node.js 依赖**
   - @marswave/coli（语音识别）

3. **系统工具**
   - ffmpeg（音频处理）

### 手动安装（可选）

**Python 依赖**：
```bash
pip install yt-dlp requests
```

**Node.js 依赖**：
```bash
npm install -g @marswave/coli
```

**ffmpeg**：
```bash
# Windows
winget install ffmpeg

# macOS
brew install ffmpeg

# Linux
sudo apt install ffmpeg
```

---

## 💡 使用方式

### 方式 1：飞书消息
```
发送视频链接给阿淘
```

### 方式 2：命令行
```bash
node processor.js [视频 URL]
```

### 方式 3：OpenClaw 命令
```
/视频总结 [URL]
```

---

## 📁 输出文件

处理完成后输出 4 个文件：

1. `video.mp4` - 完整视频
2. `audio.m4a` - 纯音频
3. `full_transcript.txt` - 完整文字稿
4. `summary.md` - 精华总结

---

##  支持平台

| 平台 | 登录要求 | 说明 |
|------|---------|------|
| 哔哩哔哩 | ❌ 无需 | 直接处理 |
| YouTube | ❌ 无需 | 直接处理 |
| 抖音 | ✅ 需要 | Chrome 登录后关闭 |
| 快手 | ✅ 需要 | Chrome 登录后关闭 |
| 小红书 | ✅ 需要 | Chrome 登录后关闭 |

---

## 📊 处理时间

| 视频时长 | 预计耗时 |
|---------|---------|
| 5 分钟 | ~2 分钟 |
| 15 分钟 | ~5 分钟 |
| 30 分钟 | ~10 分钟 |
| 60 分钟 | ~20 分钟 |

---

## 🛠️ 故障排查

### 下载失败
- 检查链接是否有效
- 检查网络连接
- 会员视频需要 Cookie

### 转录失败
- 检查 ffmpeg 是否安装
- 检查 coli 是否安装
- 音频过长会自动分段

### 进程被终止
- 音频超过 3 分钟会自动分段
- 增加超时时间设置

---

## 📦 打包发布

### 打包
```bash
clawhub pack video-to-summary
```

### 发布
```bash
clawhub publish video-to-summary
```

### 安装
```bash
# 从 ClawHub
clawhub install video-to-summary

# 从 GitHub
clawhub install video-to-summary --repo kisslucky_taotao/video-to-summary
```

---

**版本**：1.0.0  
**作者**：阿淘  
**许可证**：MIT

---

*完整文档：SKILL-FULL.md*
