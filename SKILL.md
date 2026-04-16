---
name: video-to-summary
description: 视频链接自动处理：下载→转录→总结。支持 B 站/YouTube/抖音等平台，自动分段避免超时，实时进度同步。
metadata:
  openclaw:
    requires:
      bins: ["yt-dlp", "ffmpeg", "coli"]
    install:
      - id: yt-dlp
        kind: pip
        package: "yt-dlp"
        label: "Install yt-dlp (pip)"
      - id: ffmpeg
        kind: system
        package: "ffmpeg"
        label: "Install FFmpeg (system)"
      - id: coli
        kind: npm
        package: "@marswave/coli"
        label: "Install coli CLI (npm)"
---

# Video to Summary - 视频自动处理技能

**功能**：输入视频 URL → 自动下载→转录→总结 → 输出完整文字稿 + 精华总结

**支持平台**：B 站、YouTube、抖音、快手、视频号等（yt-dlp 支持的 1000+ 平台）

---

## 🎯 核心特性

### 1. 多平台支持
- B 站（bilibili.com）
- YouTube（youtube.com）
- 抖音（douyin.com）
- 快手（kuaishou.com）
- 视频号（channels.weixin.qq.com）
- 以及 yt-dlp 支持的 1000+ 平台

### 2. 自动分段处理
- 检测音频时长
- 超过 3 分钟自动分段（避免超时）
- 逐段转录后合并

### 3. 实时进度同步
- 每 2 分钟同步处理进展
- 关键节点告知（下载完成/转录中/总结中）
- 预计完成时间提示

### 4. 智能总结
- 完整文字稿（逐字转录）
- 精华总结（核心观点 + 金句 + 行动建议）
- 结构化输出（Markdown 格式）

---

## 📦 前置依赖

### 必需
- **yt-dlp**: `pip install yt-dlp`（视频下载）
- **ffmpeg**: 系统安装（音频处理）
- **coli**: `npm install -g @marswave/coli`（语音识别）

### 安装命令
```powershell
# Windows
pip install yt-dlp
winget install ffmpeg
npm install -g @marswave/coli

# macOS
pip install yt-dlp
brew install ffmpeg
npm install -g @marswave/coli

# Linux
pip install yt-dlp
sudo apt install ffmpeg
npm install -g @marswave/coli
```

---

## 💡 使用方法

### 基本用法
```
输入视频 URL，自动处理全流程
```

**示例**：
- "处理这个视频：https://www.bilibili.com/video/BV1BXQABNE4y/"
- "下载并总结：https://www.youtube.com/watch?v=xxx"
- "转录这个抖音视频：https://v.douyin.com/xxx"

### 高级选项
```
/视频总结 [URL] --output=飞书 --format=markdown
```

**输出选项**：
- `--output=飞书` - 发送到飞书文档
- `--output=本地` - 保存到 workspace（默认）
- `--format=markdown` - Markdown 格式（默认）
- `--format=text` - 纯文本格式

---

## 🔄 处理流程

```
1. 接收 URL → 验证链接有效性
   ↓
2. 下载视频音频 → 显示进度和预计时间
   ↓
3. 检测音频时长 → 决定是否分段
   ↓
4. 音频分段（如需要）→ 每段 3 分钟
   ↓
5. 逐段语音识别 → 合并文字稿
   ↓
6. AI 提炼总结 → 核心观点 + 金句 + 行动建议
   ↓
7. 输出结果 → 飞书/本地文件 + 进度同步
```

---

## ⏱️ 处理时间参考

| 视频时长 | 下载时间 | 转录时间 | 总耗时 |
|---------|---------|---------|--------|
| 5 分钟 | 30 秒 | 1 分钟 | ~2 分钟 |
| 15 分钟 | 1 分钟 | 3 分钟 | ~5 分钟 |
| 30 分钟 | 2 分钟 | 6 分钟 | ~10 分钟 |
| 60 分钟 | 3 分钟 | 12 分钟 | ~20 分钟 |

**说明**：实际时间取决于网络速度和设备性能

---

## 📁 输出文件

**默认位置**：`D:\openclaw-workspace\temp\video-processing\`

| 文件 | 说明 |
|------|------|
| `video.m4a` | 原始音频 |
| `chunk_000-XXX.m4a` | 分段音频（如需要） |
| `full_transcript.txt` | 完整文字稿 |
| `summary.md` | 精华总结 |

---

## 🚨 注意事项

### 1. 网络要求
- 国内视频：无需特殊网络
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
- 使用 --cookies-from-browser 选项
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
```
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

## 🚀 最佳实践

### 1. 进度同步
- 开始处理时：告知预计时间
- 每 2 分钟：同步当前进展
- 关键节点：下载完成/转录完成/总结完成
- 完成时：输出文件位置 + 核心摘要

### 2. 错误处理
- 下载失败：立即告知，提供替代方案
- 转录失败：自动重试或切换模型
- 总结失败：使用备用 LLM

### 3. 用户体验
- 清晰的进度条
- 预计完成时间
- 可随时中断
- 支持批量处理

---

## 🔗 相关技能

- **asr** - 语音识别（底层依赖）
- **video-processor** - 视频处理
- **html-card-generator** - 生成分享卡片
- **publish** - 多平台发布

---

**版本**：1.0.0  
**创建时间**：2026-04-16  
**作者**：阿淘（基于实际处理经验封装）
