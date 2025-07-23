# Post-Phase 8 追加実装計画書

## 📋 概要

Phase 1-8で完成したCivitAI Downloader v2に対して、事前調査資料で発見された追加機能・改善を実装する。

**基準文書**: `/Users/kuniaki-k/Code/civitiai/1st-coding/docs/pre-investigation/`
**現状**: 事前調査資料との間に8つの重大な不整合が存在

---

## 🎯 実装目標

### 主目標
事前調査で確認された機能をすべて実装し、CivitAI API の全機能を活用できるようにする

### 副目標
- パフォーマンス向上（カテゴリAPI送信など）
- セキュリティ強化（ハッシュ検証、NSFWレベル対応）
- ユーザビリティ向上（Relevancyソート、sortBy高度ソート）

---

## 📊 実装項目一覧

### 🚨 Priority 1: CRITICAL修正（必須）

#### 1. 商用利用フィールド修正
- **現状**: boolean として処理
- **正解**: `['Image', 'Rent', 'Sell']` 配列形式
- **影響**: ライセンス情報の誤取得
- **ファイル**: `src/core/search/advanced_search.py:263-267`

#### 2. Relevancyソートオプション追加
- **現状**: SortOption enum に存在しない
- **正解**: 事前調査で動作確認済み
- **影響**: 検索ページでの関連度ソートができない
- **ファイル**: `src/core/search/advanced_search.py:67-77`

#### 3. sortBy高度ソートシステム実装
- **現状**: 未実装
- **正解**: `models_v9:field:direction` 形式
- **影響**: WebUIの高度ソート機能が使えない
- **ファイル**: `src/core/search/advanced_search.py:282-286`

### ⚡ Priority 2: HIGH修正（重要）

#### 4. ページネーション論理修正
- **現状**: query有無で判定（不正確）
- **正解**: cursor有無で判定
- **影響**: ページネーション方式の誤選択
- **ファイル**: `src/core/search/advanced_search.py:247-250`

### 🔧 Priority 3: MEDIUM修正（改善）

#### 5. NSFWレベル数値フィルタリング
- **現状**: boolean のみ
- **正解**: 0-4の数値レベル対応
- **影響**: 詳細なNSFWフィルタリングができない

#### 6. ハッシュ検証システム実装
- **現状**: 未実装
- **正解**: 6種類のハッシュアルゴリズム対応
- **影響**: ファイル整合性検証不可

#### 7. バージョン専用エンドポイント実装
- **現状**: 未使用
- **正解**: `/model-versions/{versionId}` 活用
- **影響**: バージョン詳細取得の効率化

#### 8. カテゴリAPI送信実装
- **現状**: クライアント側フィルタのみ
- **正解**: APIパラメータとして送信
- **影響**: サーバー側フィルタリングでパフォーマンス向上

---

## 📅 実装フェーズ

### Phase A: Critical修正 (1-2日)
```
Day 1: 商用利用フィールド修正
Day 1: Relevancyソートオプション追加  
Day 2: sortBy高度ソートシステム実装
Day 2: ページネーション論理修正
```

### Phase B: 機能拡張 (2-3日)
```
Day 3: NSFWレベル数値フィルタリング
Day 4: ハッシュ検証システム実装
Day 5: バージョン専用エンドポイント実装
Day 5: カテゴリAPI送信実装
```

### Phase C: 検証・文書化 (1日)
```
Day 6: 全機能の統合テスト
Day 6: 実装完了ドキュメント作成
```

---

## 🔍 実装手順

### 事前準備
1. 事前調査資料の詳細確認
2. 現在のコードベース理解
3. 影響範囲分析

### 各項目の実装パターン
```python
# 1. 現在のコード確認
# 2. 事前調査資料の正解確認  
# 3. 修正実装
# 4. テスト実行・確認
# 5. 文書化
```

### 品質保証
- 各修正後に関連するCLIコマンドで動作確認
- 事前調査資料と同じ結果が得られることを検証
- 既存機能への影響がないことを確認

---

## 📋 成功基準

### Technical Success Criteria
- [ ] 商用利用フィールドが配列として正しく処理される
- [ ] Relevancyソートオプションが動作する
- [ ] sortBy高度ソートが WebUI と同じ結果を返す
- [ ] ページネーション論理が正しく動作する
- [ ] NSFWレベル 0-4 でフィルタリングできる
- [ ] 6種類のハッシュ検証が実装される
- [ ] /model-versions/{versionId} エンドポイントが活用される
- [ ] カテゴリがAPIパラメータとして送信される

### User Experience Success Criteria
- [ ] `python -m src.cli.main search "anime" --types Checkpoint` で期待される数の結果が返る
- [ ] 商用利用可能なモデルを正確に特定できる
- [ ] WebUIと同等の検索・ソート機能が使える
- [ ] ファイルの整合性を検証できる

---

## 🛠️ 開発環境・ツール

### 必要なツール
- 事前調査資料: `/Users/kuniaki-k/Code/civitiai/1st-coding/docs/pre-investigation/`
- CivitAI API: `https://civitai.com/api/v1/`
- テスト用コマンド: `python -m src.cli.main`

### 検証方法
1. **事前調査資料比較**: 実装結果を事前調査の確認済み動作と比較
2. **WebUI比較**: 同じパラメータでWebUIと同じ結果が得られるか確認
3. **CLI動作確認**: 実用的なコマンドで期待される動作をするか確認

---

## 📖 参考資料

### 事前調査資料 (必読)
- `civitai_api_comprehensive_specification.md`: API仕様の完全版
- `civitai_category_system_investigation.md`: カテゴリシステムの詳細
- `civitai_model_types_final_complete.md`: モデルタイプの完全リスト
- `illustrious_version_investigation_report.md`: バージョン取得方法

### 現在の実装
- `src/core/search/advanced_search.py`: 主要な修正対象
- `src/api/params.py`: パラメータ処理
- `src/cli/main.py`: CLI インターフェース

---

## 🚀 開始準備チェックリスト

- [ ] 事前調査資料をすべて確認済み
- [ ] 現在の実装状況を把握済み
- [ ] 影響範囲を分析済み
- [ ] 開発環境が準備済み
- [ ] Git ブランチが整理済み

---

**作成日**: 2025年1月23日  
**作成者**: Claude Code  
**ステータス**: 準備完了 - 実装開始可能  
**予想期間**: 6日間