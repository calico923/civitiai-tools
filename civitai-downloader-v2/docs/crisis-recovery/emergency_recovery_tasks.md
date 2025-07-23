# 🚨 緊急復旧タスクリスト - Ultra Think実行計画

**作成日**: 2025-07-21  
**作成根拠**: [crisis_investigation_report.md](./crisis_investigation_report.md)  
**実行期限**: 24時間以内（CRITICAL）～ 2週間（MEDIUM）

---

## 📋 タスク概要

調査報告書で判明した根本原因に基づき、以下の3段階で緊急復旧を実施する：

1. **🔥 CRITICAL（24時間以内）**: ユニットテスト緊急修復
2. **🚨 HIGH（1週間以内）**: CI/CD体制構築  
3. **🔧 MEDIUM（2週間以内）**: 予防体制強化

---

## 🔥 CRITICAL タスク（24時間以内実行必須）

### **CRITICAL-1: アナリティクステスト緊急修復 - async/awaitエラー**

**問題**: `TypeError: 'coroutine' object is not iterable` 
**原因**: `record_event()`、`get_events()`がasync化されたが、テストが未対応

**実行内容**:
```python
# 修正対象ファイル
- tests/unit/test_analytics_comprehensive.py
- src/core/analytics/analyzer.py

# 修正内容例
# 修正前
events = self.collector.get_events(...)
self.collector.record_event(event_type, data)

# 修正後  
events = await self.collector.get_events(...)
await self.collector.record_event(event_type, data)
```

**成功条件**: アナリティクス関連テスト5件すべて成功

---

### **CRITICAL-2: アナリティクステーブル名修正**

**問題**: `sqlite3.OperationalError: no such table: events`
**原因**: テーブル名が`events` → `analytics_events`に変更されたが、テストが旧名称を参照

**実行内容**:
```python
# 修正対象ファイル
- tests/unit/test_analytics_comprehensive.py

# 修正内容
# 修正前
conn.execute("SELECT COUNT(*) FROM events WHERE...")

# 修正後
conn.execute("SELECT COUNT(*) FROM analytics_events WHERE...")
```

**成功条件**: データベース関連エラーゼロ

---

### **CRITICAL-3: 認証APIキーバリデーションバグ修正**

**問題**: `AssertionError: Invalid key '' should fail validation`
**原因**: `AuthManager.validate_api_key()`が空文字列を有効と誤判定

**実行内容**:
```python
# 修正対象ファイル  
- src/auth.py (推定ファイル名)

# 修正内容
def validate_api_key(self):
    # 修正前
    # 空文字列チェックなし
    
    # 修正後
    if not self.api_key or self.api_key.strip() == "":
        return False
    # 既存のバリデーションロジック続行
```

**成功条件**: 空文字列・None・空白文字列すべてで適切にFalseを返す

---

### **CRITICAL-4: CredentialStore初期化修正**

**問題**: `TypeError: CredentialStore.__init__() got an unexpected keyword argument 'storage_path'`
**原因**: `CredentialStore`のコンストラクタから`storage_path`引数が削除された

**実行内容**:
```python
# 修正対象ファイル
- tests/unit/test_authentication.py

# 修正内容  
# 修正前
store = CredentialStore(storage_path=test_storage_path)

# 修正後（APIシグネチャを確認して適切に修正）
store = CredentialStore()  # または他の適切な引数
```

**成功条件**: CredentialStore初期化エラーゼロ

---

### **CRITICAL-5: バルクダウンロードテスト非同期化対応**

**問題**: `assert False (isinstance(<coroutine object>, str))`
**原因**: `create_bulk_job()`がasync化されたが、テストが`await`なしで呼び出し

**実行内容**:
```python
# 修正対象ファイル
- tests/unit/test_bulk_download.py

# 修正内容
# 修正前
def test_create_bulk_job(self):
    job_id = self.bulk_manager.create_bulk_job(...)

# 修正後  
@pytest.mark.asyncio
async def test_create_bulk_job(self):
    job_id = await self.bulk_manager.create_bulk_job(...)
```

**成功条件**: バルクダウンロード関連テスト20件すべて成功

---

### **CRITICAL-6: 全ユニットテストスイート実行・検証**

**実行内容**:
```bash
python -m pytest tests/unit/ -v --tb=short
```

**成功条件**: 
- ❌ 失敗テスト: 0件
- ⚠️ 警告: 最小限に抑制
- 📊 成功率: 100%

**検証方法**: テスト結果のスクリーンショット保存 + ログ出力

---

## 🚨 HIGH タスク（1週間以内）

### **HIGH-1: CI/CDパイプライン導入**

**実行内容**:

1. **GitHub Actions設定ファイル作成**
```yaml
# .github/workflows/comprehensive-test.yml
name: Comprehensive Test Suite
on: 
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ['3.11']
    
    steps:
    - name: Checkout code
      uses: actions/checkout@v4
      
    - name: Set up Python ${{ matrix.python-version }}
      uses: actions/setup-python@v4
      with:
        python-version: ${{ matrix.python-version }}
        
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements.txt
        pip install pytest pytest-asyncio pytest-mock
        
    - name: Run unit tests
      run: |
        python -m pytest tests/unit/ -v --tb=short --strict-markers
        
    - name: Run integration tests  
      run: |
        python -m pytest tests/integration/ -v --tb=short --strict-markers
        
    - name: Fail on ANY test failure
      run: |
        if [ $? -ne 0 ]; then
          echo "❌ Tests failed - blocking merge"
          exit 1
        fi
```

2. **ブランチ保護ルール設定**
   - GitHub リポジトリ設定 > Branches
   - `main`ブランチに保護ルール適用
   - ステータスチェック必須: `test`ジョブ

**成功条件**: 新規PR/pushでテスト自動実行、失敗時マージブロック

---

### **HIGH-2: プレコミットフック設定**

**実行内容**:

1. **設定ファイル作成**
```yaml
# .pre-commit-config.yaml
repos:
  - repo: local
    hooks:
      - id: pytest-unit
        name: Run unit tests
        entry: python -m pytest tests/unit/ --tb=short -q
        language: system
        pass_filenames: false
        always_run: true
        
      - id: pytest-integration  
        name: Run integration tests
        entry: python -m pytest tests/integration/ --tb=short -q
        language: system
        pass_filenames: false
        always_run: true
```

2. **インストール手順書作成**
```bash
# 開発者向けセットアップ手順
pip install pre-commit
pre-commit install
pre-commit run --all-files  # 初回テスト実行
```

**成功条件**: コミット時に自動テスト実行、失敗時コミットブロック

---

## 🔧 MEDIUM タスク（2週間以内）

### **MEDIUM-1: テスト品質監視ダッシュボード構築**

**実行内容**:
- テスト実行結果の可視化スクリプト作成
- カバレッジレポート自動生成  
- 失敗パターン分析レポート

### **MEDIUM-2: リファクタリングプロトコル制定**

**実行内容**:
- リファクタリング時のテスト更新チェックリスト作成
- レビュー時のテスト品質確認項目定義
- 開発プロセス文書化

---

## 🎯 実行順序とマイルストーン

### **Day 1 (今日)**
- [ ] CRITICAL-1～5を順次実行
- [ ] CRITICAL-6で全体検証
- [ ] 緊急修復完了報告書作成

### **Week 1**  
- [ ] HIGH-1: CI/CDパイプライン導入
- [ ] HIGH-2: プレコミットフック設定
- [ ] チーム向け運用手順書作成

### **Week 2**
- [ ] MEDIUM-1～2実装
- [ ] 総合レビュー・改善提案
- [ ] 長期品質保証体制確立

---

## 🚨 エスカレーション条件

以下の場合は即座にエスカレーション:

1. **CRITICAL修復が24時間以内に完了しない**
2. **修復過程で新たな重大問題を発見**  
3. **CI/CD導入が1週間以内に完了しない**

---

## 📊 成功指標（KPI）

### **即座に確認可能**
- ✅ ユニットテスト成功率: 100%
- ✅ 統合テスト成功率: 100% (維持)

### **1週間後**
- ✅ CI/CDパイプライン稼働率: 100%  
- ✅ プレコミットフック導入率: 100%

### **2週間後**
- ✅ 新規PRテスト失敗率: <5%
- ✅ 開発者テスト実行習慣化: 90%+

---

**👥 Geminiレビュー待ち - この計画で緊急復旧を開始する準備が整いました**