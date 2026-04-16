---
name: video-to-summary
description: |
  视频自动处理技能：输入视频 URL → 下载 → 转录 → 总结
  支持 B 站/YouTube/抖音/快手等平台
  自动输出 4 个文件：视频 + 音频 + 文字稿 + 总结
metadata:
  openclaw:
    emoji: "🎥"
    category: "media"
    tags: ["video", "transcribe", "summary", "ai"]
    version: "1.0.0"
    author: "阿淘"
    
---

# 🎥 Video to Summary Skill

**功能**：输入视频 URL，自动完成下载→转录→总结，输出 4 个文件

**支持平台**：
- ✅ 哔哩哔哩（无需登录）
- ✅ YouTube（无需登录）
- ⚠️ 抖音（需要 Chrome 登录）
- ⚠️ 快手（需要 Chrome 登录）
- ⚠️ 小红书（需要 Chrome 登录）

---

## 📦 依赖项

### 必需依赖

| 依赖 | 类型 | 安装命令 | 用途 |
|------|------|---------|------|
| **yt-dlp** | Python 包 | `pip install yt-dlp` | 视频下载 |
| **ffmpeg** | 系统工具 | `winget install ffmpeg` | 音频提取/分段 |
| **coli** | npm 包 | `npm install -g @marswave/coli` | 语音识别（ASR） |

### 可选依赖

| 依赖 | 类型 | 安装命令 | 用途 |
|------|------|---------|------|
| **openai** | Python 包 | `pip install openai` | AI 总结（可选） |
| **requests** | Python 包 | `pip install requests` | HTTP 请求 |

---

## 🛠️ 安装步骤

### 方式 1：自动安装（推荐）

```bash
# 使用 OpenClaw 自动安装
node skills/install-dependencies.js video-to-summary
```

### 方式 2：手动安装

**第 1 步：安装 Python 依赖**
```bash
pip install yt-dlp requests
```

**第 2 步：安装系统工具**
```bash
# Windows
winget install ffmpeg

# macOS
brew install ffmpeg

# Linux
sudo apt install ffmpeg
```

**第 3 步：安装 Node.js 依赖**
```bash
npm install -g @marswave/coli
```

---

## 💡 使用方法

### 基本用法

```
输入视频 URL，自动处理全流程
```

**示例**：
- "处理这个视频：https://www.bilibili.com/video/BV1XXX/"
- "下载并总结：https://www.youtube.com/watch?v=xxx"
- "转录这个抖音视频：https://v.douyin.com/xxx"

### 高级选项

```
/视频总结 [URL] --output=飞书 --format=markdown
```

**输出选项**：
- `--output=飞书` - 发送到飞书文档
- `--output=本地` - 保存到 workspace（默认）
- `--output=邮箱` - 发送邮件附件
- `--format=markdown` - Markdown 格式（默认）
- `--format=text` - 纯文本格式

---

## 🔄 处理流程

```
1. 接收 URL → 验证链接有效性
   ↓
2. 下载视频音频 → 显示进度和预计时间
   ↓
3. 检测音频时长 → 决定是否分段（>3 分钟自动分段）
   ↓
4. 音频分段（如需要）→ 每段 3 分钟
   ↓
5. 逐段语音识别 → 合并文字稿
   ↓
6. AI 提炼总结 → 核心观点 + 金句 + 行动建议
   ↓
7. 输出结果 → 飞书/本地/邮箱 + 进度同步
```

---

## 📁 输出文件

**默认位置**：`D:\openclaw-workspace\temp\video-processing\{video-id}\`

| 文件 | 格式 | 说明 |
|------|------|------|
| `video.mp4` | MP4 | 完整视频原文件 |
| `audio.m4a` | M4A | 纯音频文件 |
| `full_transcript.txt` | TXT | 完整文字稿（逐字转录） |
| `summary.md` | Markdown | 精华总结（核心观点 + 金句） |

---

## ⏱️ 处理时间参考

| 视频时长 | 下载时间 | 转录时间 | 总耗时 |
|---------|---------|---------|--------|
| 5 分钟 | 30 秒 | 1 分钟 | ~2 分钟 |
| 15 分钟 | 1 分钟 | 3 分钟 | ~5 分钟 |
| 30 分钟 | 2 分钟 | 6 分钟 | ~10 分钟 |
| 60 分钟 | 3 分钟 | 12 分钟 | ~20 分钟 |

---

## 🚨 注意事项

### 1. 网络要求
- 国内视频（B 站/抖音/快手）：无需特殊网络
- YouTube 等境外平台：需要境外网络

### 2. 视频权限
- 公开视频：直接下载
- 会员专享：需要 Cookie 认证
- 私密视频：无法下载

### 3. 时长限制
- 推荐：<60 分钟
- 最长支持：120 分钟（自动分段）
- 超过 120 分钟：建议手动分段

### 4. 识别准确率
- 中文：95%+（sensevoice 模型）
- 英文：90%+（sensevoice 模型）
- 方言/口音：可能需要人工校对

---

## 🛠️ 故障排查

### 问题 1：下载失败
```
可能原因：
- 视频链接无效
- 平台限制（会员专享）
- 网络问题

解决方案：
- 检查链接是否可访问
- 使用 --cookies-from-browser chrome 选项
- 检查网络连接
```

### 问题 2：转录乱码
```
可能原因：
- Windows 编码问题
- coli 输出格式问题

解决方案：
- 使用 Python 脚本调用（绕过命令行）
- 使用 --json 选项 + 解析 JSON
```

### 问题 3：进程被终止
```
可能原因：
- 音频过长（超过超时限制）
- 系统资源不足

解决方案：
- 自动分段处理（每段 3 分钟）
- 增加超时时间
```

---

## 📝 示例输出

### 完整文字稿（片段）
```
=== chunk_000.m4a ===
我装的一个开源项目女娲 skill4 天，现在已经有 6000 多个 star...
```

### 精华总结（片段）
```markdown
# 视频内容提炼总结

**视频标题**：我蒸馏了 17 个大佬给我打工（开源免费）
**视频时长**：18 分 26 秒

## 🎯 核心价值主张
> 蒸馏任何人的思维方式，变成可反复调用的 AI 工具

## 💡 核心洞见
### 乔布斯谈 AI 时代赚钱（3 条）
1. 品味是护城河 - 工具民主化≠品味民主化
2. 做端到端的事 - 完整 APP > 100 人团队做提示词
3. 死亡过滤器 - 只对一件事说 YES，做到极致
```

---

## 🔗 相关技能

- **asr** - 语音识别（底层依赖）
- **video-processor** - 视频处理
- **html-card-generator** - 生成分享卡片
- **publish** - 多平台发布

---

## 📦 打包发布

### 打包命令
```bash
# 打包 skill
clawhub pack video-to-summary

# 发布到 ClawHub
clawhub publish video-to-summary
```

### 其他 Agent 安装
```bash
# 从 ClawHub 安装
clawhub install video-to-summary

# 从 GitHub 安装
clawhub install video-to-summary --repo kisslucky_taotao/video-to-summary
```

---

**版本**：1.0.0  
**创建时间**：2026-04-16  
**作者**：阿淘  
**许可证**：MIT

---

*由 Video to Summary Skill 自动生成*
