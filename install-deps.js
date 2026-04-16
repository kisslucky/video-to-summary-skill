#!/usr/bin/env node
/**
 * Video to Summary Skill - 依赖安装脚本
 * 
 * 使用方式：
 * node install-deps.js
 */

const { execSync } = require('child_process');
const path = require('path');
const fs = require('fs');

const SKILL_DIR = path.dirname(__filename);
const ROOT_DIR = path.join(SKILL_DIR, '..', '..');

console.log('🎥 Video to Summary Skill - 依赖安装\n');

// 检查 Node.js
try {
  execSync('node --version', { stdio: 'ignore' });
  console.log('✅ Node.js 已安装');
} catch (e) {
  console.error('❌ Node.js 未安装，请先安装 Node.js: https://nodejs.org/');
  process.exit(1);
}

// 检查 Python
try {
  execSync('python --version', { stdio: 'ignore' });
  console.log('✅ Python 已安装');
} catch (e) {
  console.error('❌ Python 未安装，请先安装 Python: https://www.python.org/');
  process.exit(1);
}

// 安装 Python 依赖
console.log('\n📦 安装 Python 依赖...');
try {
  execSync('pip install yt-dlp requests', { stdio: 'inherit' });
  console.log('✅ Python 依赖安装完成');
} catch (e) {
  console.error('❌ Python 依赖安装失败');
}

// 安装 ffmpeg
console.log('\n🎬 检查 ffmpeg...');
try {
  execSync('ffmpeg -version', { stdio: 'ignore', shell: true });
  console.log('✅ ffmpeg 已安装');
} catch (e) {
  console.log('⚠️  ffmpeg 未安装，正在安装...');
  try {
    execSync('winget install ffmpeg --accept-source-agreements --accept-package-agreements', { stdio: 'inherit' });
    console.log('✅ ffmpeg 安装完成');
  } catch (e) {
    console.log('⚠️  ffmpeg 自动安装失败，请手动安装：');
    console.log('   Windows: winget install ffmpeg');
    console.log('   macOS: brew install ffmpeg');
    console.log('   Linux: sudo apt install ffmpeg');
  }
}

// 安装 coli
console.log('\n🎤 安装 coli CLI（语音识别）...');
try {
  execSync('npm install -g @marswave/coli', { stdio: 'inherit' });
  console.log('✅ coli CLI 安装完成');
} catch (e) {
  console.error('❌ coli CLI 安装失败');
}

console.log('\n✅ 所有依赖安装完成！');
console.log('\n使用方式：');
console.log('  1. 在飞书中发送视频链接');
console.log('  2. 自动处理：下载 → 转录 → 总结');
console.log('  3. 获得 4 个文件：视频 + 音频 + 文字稿 + 总结');
