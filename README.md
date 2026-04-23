# Video to Summary

将视频链接处理为本地交付物：媒体文件、音频、文字稿，以及一份可继续加工的摘要草稿。

这个仓库现在聚焦“Skill 本体”，不再把后台服务、演示接口和运行产物混在主流程里。

## 当前定位

- 适合：视频下载、音频提取、语音转写、摘要草稿生成
- 不适合：直接当成完整 SaaS 服务或长期运行的后台队列
- 当前状态：已完成本地清理，适合继续朝公开 Skill 方向整理；暂不建议在未进一步拆分前作为最终公开版本发布

## 核心依赖

- `python >= 3.8`
- `yt-dlp`
- `ffmpeg`
- `coli`

## 快速开始

```bash
python processor.py "<video-url>"
```

如果是需要登录态的平台，可追加：

```bash
python processor.py "<video-url>" --cookies-from-browser chrome
```

## 输出结果

每次运行都会生成独立任务目录，默认在 `outputs/<job-id>/` 下，包含：

- `video.*`
- `audio.m4a`
- `transcript.txt`
- `summary.md`
- `result.json`

## Hermes 适配

适用于 Hermes，前提是 Hermes 会话具备终端能力并允许调用本地依赖。

- 适配方式：把仓库加入 Hermes 的外部 Skill 目录
- 运行方式：调用 `${HERMES_SKILL_DIR}/processor.py` 或在技能目录内直接运行 `python processor.py`
- 能力边界：Hermes 负责读文字稿并决定是否重写摘要；脚本本身只产出草稿和中间文件

## OpenClaw 适配

适用于 OpenClaw，但建议先把 `backend-api.py` 相关服务能力拆到独立目录或独立仓库，再做正式公开发布。

## 后续建议

1. 把 `backend-api.py` 拆成独立 demo/service 包
2. 增加更多平台说明和 Cookie 指引
3. 给摘要阶段接入真正的模型总结，而不只依赖本地草稿

## License

MIT
