#!/usr/bin/env python3
"""Backend API for the Video to Summary frontend."""

from __future__ import annotations

import json
import os
import smtplib
import subprocess
import sys
import threading
import uuid
import zipfile
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from typing import Any

from flask import Flask, jsonify, request, send_file


app = Flask(__name__)

WORK_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = WORK_DIR / "outputs"
PROCESSOR_PATH = WORK_DIR / "processor.py"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

SMTP_SERVER = "smtp.qq.com"
SMTP_PORT = 465
SMTP_USER = os.getenv("VIDEO_TO_SUMMARY_SMTP_USER", "")
SMTP_PASS = os.getenv("VIDEO_TO_SUMMARY_SMTP_PASS", "")
SMTP_ENABLED = bool(SMTP_USER and SMTP_PASS)

tasks: dict[str, dict[str, Any]] = {}

PLATFORM_RULES = [
    {
        "id": "bilibili",
        "label": "哔哩哔哩",
        "domains": ("bilibili.com", "b23.tv"),
        "route": "direct",
        "badge": "直连优先",
        "note": "公开视频通常可直接处理，失败再升级到浏览器辅助。",
    },
    {
        "id": "youtube",
        "label": "YouTube",
        "domains": ("youtube.com", "youtu.be"),
        "route": "cookie-assisted",
        "badge": "Cookie 辅助",
        "note": "可能需要浏览器 Cookie 或登录态，遇到 bot 检查再切到浏览器辅助。",
    },
    {
        "id": "douyin",
        "label": "抖音",
        "domains": ("douyin.com", "v.douyin.com"),
        "route": "browser-assisted",
        "badge": "浏览器辅助",
        "note": "优先用 web-access / CDP 获取字幕、媒体或页面信息。",
    },
    {
        "id": "kuaishou",
        "label": "快手",
        "domains": ("kuaishou.com", "kwai.com"),
        "route": "browser-assisted",
        "badge": "浏览器辅助",
        "note": "页面交互和登录态影响较大，适合先走浏览器辅助。",
    },
    {
        "id": "xiaohongshu",
        "label": "小红书",
        "domains": ("xiaohongshu.com", "xhslink.com"),
        "route": "browser-assisted",
        "badge": "浏览器辅助",
        "note": "反爬和交互较重，适合先用浏览器提取字幕或媒体。",
    },
    {
        "id": "wechat-channels",
        "label": "视频号 / 微信系页面",
        "domains": ("channels.weixin.qq.com", "mp.weixin.qq.com", "weixin.qq.com"),
        "route": "browser-assisted",
        "badge": "浏览器辅助",
        "note": "登录态和页面渲染限制明显，建议使用 CDP。",
    },
]


@app.after_request
def add_cors_headers(response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type"
    response.headers["Access-Control-Expose-Headers"] = "Content-Disposition, Content-Type"
    return response


@app.route("/api/process", methods=["POST", "OPTIONS"])
def process_video():
    if request.method == "OPTIONS":
        return ("", 204)

    data = request.get_json(silent=True) or {}
    url = (data.get("url") or "").strip()
    transcript_text = (data.get("transcript_text") or "").strip()
    strategy = (data.get("strategy") or "auto").strip()
    goal = (data.get("goal") or "summary-pack").strip()
    title = (data.get("title") or "").strip()
    page_url = (data.get("page_url") or url).strip()
    referer = (data.get("referer") or page_url).strip()
    cookies_from_browser = (data.get("cookies_from_browser") or "").strip()

    if not url and not transcript_text:
        return jsonify({"error": "缺少视频链接或文字稿"}), 400

    plan = build_route_plan(url, strategy, bool(transcript_text))
    task_id = uuid.uuid4().hex
    task_dir = OUTPUT_DIR / task_id
    task_dir.mkdir(parents=True, exist_ok=True)

    task = {
        "task_id": task_id,
        "status": "queued",
        "stage": "planning",
        "progress": 5,
        "url": url,
        "goal": goal,
        "strategy": strategy,
        "title": title or None,
        "page_url": page_url or None,
        "referer": referer or None,
        "plan": plan,
        "dir": str(task_dir),
        "files": {},
        "summary_preview": "",
        "transcript_preview": "",
        "error": None,
    }
    tasks[task_id] = task

    if transcript_text:
        thread = threading.Thread(
            target=run_task,
            args=(task_id, data, plan, transcript_text),
            daemon=True,
        )
        thread.start()
        return jsonify(task_payload(task))

    if plan["recommended_strategy"] == "browser-assisted" and strategy in {"auto", "browser-assisted"}:
        task["status"] = "action_required"
        task["stage"] = "awaiting_browser"
        task["progress"] = 15
        return jsonify(task_payload(task))

    thread = threading.Thread(
        target=run_task,
        args=(task_id, data, plan, ""),
        daemon=True,
    )
    thread.start()
    return jsonify(task_payload(task))


@app.route("/api/status/<task_id>", methods=["GET"])
def get_status(task_id: str):
    task = tasks.get(task_id)
    if not task:
        return jsonify({"error": "任务不存在"}), 404
    return jsonify(task_payload(task))


@app.route("/api/download/<task_id>", methods=["GET"])
def download_bundle(task_id: str):
    task = tasks.get(task_id)
    if not task:
        return jsonify({"error": "任务不存在"}), 404
    if task["status"] != "completed":
        return jsonify({"error": "处理未完成"}), 400

    zip_path = build_zip(task)
    return send_file(
        zip_path,
        as_attachment=True,
        download_name=f"video-summary-{task_id[:8]}.zip",
    )


@app.route("/api/download/<task_id>/<artifact>", methods=["GET"])
def download_single(task_id: str, artifact: str):
    task = tasks.get(task_id)
    if not task:
        return jsonify({"error": "任务不存在"}), 404
    if task["status"] != "completed":
        return jsonify({"error": "处理未完成"}), 400

    file_path = task.get("files", {}).get(artifact)
    if not file_path or not Path(file_path).exists():
        return jsonify({"error": f"文件不存在：{artifact}"}), 404

    return send_file(file_path, as_attachment=True, download_name=Path(file_path).name)


@app.route("/api/send-email", methods=["POST"])
def send_email():
    if not SMTP_ENABLED:
        return jsonify({"error": "当前未启用邮件发送"}), 400

    data = request.get_json(silent=True) or {}
    task_id = (data.get("task_id") or "").strip()
    email = (data.get("email") or "").strip()

    task = tasks.get(task_id)
    if not task:
        return jsonify({"error": "任务不存在"}), 404
    if task["status"] != "completed":
        return jsonify({"error": "处理未完成"}), 400
    if "@" not in email:
        return jsonify({"error": "邮箱地址无效"}), 400

    zip_path = build_zip(task)
    send_zip_email(email, zip_path, task)
    return jsonify({"status": "ok", "message": "邮件已发送"})


@app.route("/api/health", methods=["GET"])
def health():
    return jsonify(
        {
            "status": "ok",
            "message": "API running",
            "smtp_enabled": SMTP_ENABLED,
            "processor": str(PROCESSOR_PATH),
        }
    )


def detect_platform(url: str) -> dict[str, Any]:
    normalized = url.lower()
    for rule in PLATFORM_RULES:
        if any(domain in normalized for domain in rule["domains"]):
            return rule
    return {
        "id": "generic",
        "label": "通用视频源",
        "route": "direct",
        "badge": "自动判断",
        "note": "先尝试直连，失败后再升级到 Cookie 或浏览器辅助。",
    }


def build_route_plan(url: str, strategy: str, transcript_present: bool) -> dict[str, Any]:
    platform = detect_platform(url) if url else {
        "id": "transcript-only",
        "label": "文字稿输入",
        "route": "transcript-paste",
        "badge": "文字稿输入",
        "note": "用户直接提供了字幕或文字稿。",
    }

    recommended_strategy = platform["route"]
    if transcript_present:
        recommended_strategy = "transcript-paste"
    elif strategy and strategy != "auto":
        recommended_strategy = strategy

    instructions: list[str] = []
    if recommended_strategy == "browser-assisted":
        instructions = [
            "用 web-access / CDP 在浏览器里打开视频页",
            "优先展开字幕、文稿或评论区摘要，而不是盲目重试下载",
            "拿到字幕后直接粘贴到当前页面继续处理，或取得签名媒体地址后再重试",
            "如果 CDP / Proxy 不通，先处理 browser-troubleshooting",
        ]
    elif recommended_strategy == "cookie-assisted":
        instructions = [
            "先尝试浏览器 Cookie 辅助下载",
            "若仍被 bot 检查拦截，再升级到浏览器辅助模式",
        ]
    elif recommended_strategy == "transcript-paste":
        instructions = [
            "直接粘贴字幕或文字稿即可继续",
            "如果还有页面标题或原始链接，一并填写能提升交付质量",
        ]
    else:
        instructions = [
            "先走直连处理",
            "失败后再升级到 Cookie 或浏览器辅助，不要一开始就把所有复杂度堆满",
        ]

    return {
        "platform_id": platform["id"],
        "platform_label": platform["label"],
        "platform_badge": platform["badge"],
        "recommended_strategy": recommended_strategy,
        "note": platform["note"],
        "instructions": instructions,
    }


def run_task(task_id: str, data: dict[str, Any], plan: dict[str, Any], transcript_text: str) -> None:
    task = tasks[task_id]
    task["status"] = "processing"
    task["stage"] = "routing"
    task["progress"] = 20

    task_dir = Path(task["dir"])
    processor_command = [sys.executable, str(PROCESSOR_PATH), "--output-dir", str(task_dir)]

    page_url = (data.get("page_url") or data.get("url") or "").strip()
    title = (data.get("title") or "").strip()
    referer = (data.get("referer") or page_url).strip()
    cookies_from_browser = (data.get("cookies_from_browser") or "").strip()
    cookies_file = (data.get("cookies_file") or "").strip()

    if title:
        processor_command += ["--title", title]
    if page_url:
        processor_command += ["--page-url", page_url]

    if transcript_text:
        transcript_path = task_dir / "submitted-transcript.txt"
        transcript_path.write_text(transcript_text, encoding="utf-8")
        processor_command += ["--transcript-file", str(transcript_path)]
    else:
        source_url = (data.get("url") or "").strip()
        if not source_url:
            task["status"] = "failed"
            task["stage"] = "failed"
            task["progress"] = 0
            task["error"] = "缺少可处理的视频链接"
            return

        processor_command.append(source_url)
        if cookies_from_browser:
            processor_command += ["--cookies-from-browser", cookies_from_browser]
        if cookies_file:
            processor_command += ["--cookies-file", cookies_file]
        if referer:
            processor_command += ["--referer", referer]

    task["stage"] = "running_processor"
    task["progress"] = 55
    try:
        result = subprocess.run(
            processor_command,
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=3600,
        )
    except Exception as exc:
        task["status"] = "failed"
        task["stage"] = "failed"
        task["progress"] = 0
        task["error"] = str(exc)
        return

    if result.returncode != 0:
        error_message = parse_error(result.stdout, result.stderr)
        task["error"] = error_message
        if should_escalate_to_browser(error_message):
            task["status"] = "action_required"
            task["stage"] = "awaiting_browser"
            task["progress"] = 25
            task["plan"] = build_route_plan(task["url"], "browser-assisted", False)
        else:
            task["status"] = "failed"
            task["stage"] = "failed"
            task["progress"] = 0
        return

    payload = parse_processor_payload(result.stdout)
    task["stage"] = "packaging"
    task["progress"] = 85
    register_outputs(task, payload)
    build_zip(task)

    task["status"] = "completed"
    task["stage"] = "completed"
    task["progress"] = 100


def parse_processor_payload(stdout: str) -> dict[str, Any]:
    lines = [line.strip() for line in stdout.splitlines() if line.strip()]
    for line in reversed(lines):
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            return payload
    raise RuntimeError("Processor did not return a JSON payload")


def parse_error(stdout: str, stderr: str) -> str:
    for block in (stdout, stderr):
        for line in reversed(block.splitlines()):
            line = line.strip()
            if line:
                try:
                    payload = json.loads(line)
                    if isinstance(payload, dict) and payload.get("error"):
                        return str(payload["error"])
                except json.JSONDecodeError:
                    return line[:500]
    return "未知处理错误"


def should_escalate_to_browser(error_message: str) -> bool:
    lowered = error_message.lower()
    markers = [
        "sign in",
        "not a bot",
        "cookies",
        "403",
        "captcha",
        "login",
        "no media file was produced",
    ]
    return any(marker in lowered for marker in markers)


def register_outputs(task: dict[str, Any], payload: dict[str, Any]) -> None:
    file_keys = {
        "media": payload.get("media"),
        "audio": payload.get("audio"),
        "transcript": payload.get("transcript"),
        "summary": payload.get("summary"),
    }
    task["files"] = {
        key: value
        for key, value in file_keys.items()
        if isinstance(value, str) and value and Path(value).exists()
    }
    task["summary_preview"] = read_preview(task["files"].get("summary"))
    task["transcript_preview"] = read_preview(task["files"].get("transcript"), max_chars=1200)


def read_preview(path: str | None, max_chars: int = 900) -> str:
    if not path:
        return ""
    file_path = Path(path)
    if not file_path.exists():
        return ""
    return file_path.read_text(encoding="utf-8", errors="replace")[:max_chars]


def build_zip(task: dict[str, Any]) -> Path:
    task_dir = Path(task["dir"])
    zip_path = task_dir / "delivery-bundle.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as archive:
        for artifact, file_path in task.get("files", {}).items():
            path = Path(file_path)
            if path.exists():
                archive.write(path, f"{artifact}{path.suffix}")
    task["bundle"] = str(zip_path)
    return zip_path


def send_zip_email(target_email: str, zip_path: Path, task: dict[str, Any]) -> None:
    msg = MIMEMultipart()
    msg["From"] = SMTP_USER
    msg["To"] = target_email
    msg["Subject"] = f"Video to Summary Delivery - {task['task_id'][:8]}"
    msg.attach(MIMEText("附件中包含处理结果。", "plain", "utf-8"))

    part = MIMEBase("application", "zip")
    part.set_payload(zip_path.read_bytes())
    encoders.encode_base64(part)
    part.add_header("Content-Disposition", f'attachment; filename="{zip_path.name}"')
    msg.attach(part)

    with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT) as server:
        server.login(SMTP_USER, SMTP_PASS)
        server.sendmail(SMTP_USER, [target_email], msg.as_string())


def task_payload(task: dict[str, Any]) -> dict[str, Any]:
    payload = {
        "task_id": task["task_id"],
        "status": task["status"],
        "stage": task["stage"],
        "progress": task["progress"],
        "url": task["url"],
        "goal": task["goal"],
        "strategy": task["strategy"],
        "title": task["title"],
        "page_url": task["page_url"],
        "plan": task["plan"],
        "summary_preview": task.get("summary_preview", ""),
        "transcript_preview": task.get("transcript_preview", ""),
        "smtp_enabled": SMTP_ENABLED,
    }
    if task.get("error"):
        payload["error"] = task["error"]
    if task.get("files"):
        payload["files"] = task["files"]
        payload["downloads"] = {
            "bundle": f"/api/download/{task['task_id']}",
            **{
                key: f"/api/download/{task['task_id']}/{key}"
                for key in task["files"].keys()
            },
        }
    return payload


if __name__ == "__main__":
    print("Video to Summary API starting...")
    print(f"Work dir: {WORK_DIR}")
    print(f"Output dir: {OUTPUT_DIR}")
    print(f"SMTP enabled: {SMTP_ENABLED}")
    app.run(host="0.0.0.0", port=5000, debug=False)
