# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Status

This repository is currently empty and ready for initial project setup.

## Development Setup

Since this is a new repository, the development environment and tooling will be established as the project grows. Common setup tasks may include:

- Initialize project structure
- Set up package management (npm, yarn, pip, etc.)
- Configure build tools and linting
- Establish testing framework
- Set up version control workflows

## Architecture

The project architecture will be documented here as the codebase develops.

## Notes for Future Development

- This CLAUDE.md file should be updated as the project structure and tooling are established
- Add specific build, test, and lint commands once they are configured
- Document the main architectural patterns and folder structure as they emerge

## Gemini CLI 連携ガイド

### 目的
ユーザーが **「Geminiと相談しながら進めて」** （または類似表現）と指示した場合、
Claude は **Gemini CLI** を随時呼び出しながら、複数ターンにわたる協業を行う。
実装はGeminiに相談しなくても良い。

---

### トリガー
- 正規表現: `/Gemini.*相談しながら/`
- 一度トリガーした後は、ユーザーが明示的に終了を指示するまで **協業モード** を維持する。

---

### 協業ワークフロー (ループ可)
| # | 処理 | 詳細 |
|---|------|------|
| 1 | **PROMPT 準備** | 最新のユーザー要件 + これまでの議論要約を `$PROMPT` に格納 |
| 2 | **Gemini 呼び出し** | ```bash\ngemini <<EOF\n$PROMPT\nEOF\n```<br>必要に応じ `--max_output_tokens` 等を追加 |
| 3 | **出力貼り付け** | `Gemini ➜` セクションに全文、長い場合は要約＋原文リンク |
| 4 | **Claude コメント** | `Claude ➜` セクションで Gemini の提案を分析・統合し、次アクションを提示 |
| 5 | **継続判定** | ユーザー入力 or プラン継続で 1〜4 を繰り返す。<br>「Geminiコラボ終了」「ひとまずOK」等で通常モード復帰 |
---
### 形式テンプレート
```md
**Gemini ➜**
<Gemini からの応答>
**Claude ➜**
<統合コメント & 次アクション>