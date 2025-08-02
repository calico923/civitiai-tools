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

## 🔒 Git Safe Operations Guide (重要: ファイル消失・動作不良防止)

### ⚠️ Critical Rules - 必ず守るべきルール

#### 1. **事前確認の徹底 (Pre-Operation Verification)**
```bash
# どんなGit操作の前にも必ず実行
git status
git stash list
git branch -v
```

#### 2. **段階的マージ手順 (Safe Merge Workflow)**
```bash
# Step 1: 現在の状態を保存
git add .
git commit -m "WIP: before merge $(date +%Y%m%d-%H%M%S)"
git tag safety-before-merge-$(date +%Y%m%d-%H%M%S)

# Step 2: テスト実行
python -m pytest tests/  # または適切なテストコマンド

# Step 3: マージ実行
git merge --no-ff <branch-name>

# Step 4: 再度テスト
python -m pytest tests/

# Step 5: 動作確認
python -m src.cli.main --help  # メインエントリポイントの確認
```

#### 3. **ブランチ切り替え前の必須手順**
```bash
# 未コミット変更を必ず退避
git stash save "auto-save: switching to <target-branch> at $(date)"
git checkout <target-branch>
```

#### 4. **破壊的操作の禁止事項**
```bash
# ❌ 絶対に使用しない
git clean -fd              # → ファイルが消失
git reset --hard HEAD      # → 変更が失われる
git push --force          # → 他者の作業を破壊

# ✅ 代わりに使用
git clean -n              # まずドライラン
git clean -i              # インタラクティブモード
git stash                 # 変更を退避
git push --force-with-lease  # 安全なforce push
```

### 🛡️ 予防的コマンドセット

#### Git Aliases 設定 (プロジェクトルートで実行)
```bash
# 安全なマージ
git config alias.safe-merge '!f() { git status --porcelain | grep -q . && echo "⚠️  Uncommitted changes!" && return 1; git merge --no-ff "$@"; }; f'

# チェックポイント作成
git config alias.checkpoint '!git tag checkpoint-$(date +%Y%m%d-%H%M%S) && echo "✅ Checkpoint created"'

# 安全なブランチ切り替え
git config alias.safe-switch '!f() { git stash save "auto-stash: $(date)" && git checkout "$1"; }; f'

# 状態確認
git config alias.verify '!echo "=== Status ===" && git status -s && echo -e "\n=== Recent commits ===" && git log --oneline -5 && echo -e "\n=== Branches ===" && git branch -v'
```

### 🚨 トラブル発生時の復旧手順

#### ファイルが消失した場合
```bash
# 1. 直前の操作を確認
git reflog --date=iso

# 2. 安全な状態に戻す
git reset --hard HEAD@{1}  # 1つ前の状態

# 3. stashを確認
git stash list
git stash show -p stash@{0}  # 内容確認
git stash apply stash@{0}    # 必要なら適用
```

#### コードが動かなくなった場合
```bash
# 1. どのコミットで壊れたか特定
git bisect start
git bisect bad HEAD
git bisect good <動いていた時のコミットID>
# 自動的に問題のコミットを特定

# 2. 問題のコミットを確認
git show <問題のコミットID>

# 3. 修正または revert
git revert <問題のコミットID>
```

### 📋 チェックリスト (各作業セッション終了時)

- [ ] `git status` で未コミットファイルがないか確認
- [ ] `git stash list` で退避した変更がないか確認  
- [ ] テストが全てパスすることを確認
- [ ] メインエントリポイントが動作することを確認
- [ ] 必要に応じて `git checkpoint` でタグ作成

### 🎯 Claude Code 専用ルール

1. **複数ファイルの変更時**: 必ず段階的にコミット
2. **マージ前**: 必ずテスト実行と動作確認
3. **ブランチ操作**: 自動でstashを作成
4. **エラー発生時**: すぐに `git verify` で状態確認
5. **PR作成前**: `git log --oneline -10` で履歴確認

### ⚡ 推奨ワークフロー

```bash
# 朝の作業開始時
git verify
git pull --rebase

# 機能実装中（30分ごと）
git add .
git commit -m "WIP: <作業内容>"

# ブランチ切り替え時
git safe-switch <branch>

# マージ時
git checkpoint
git safe-merge <branch>

# 1日の終わり
git verify
git checkpoint
git push
```

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

