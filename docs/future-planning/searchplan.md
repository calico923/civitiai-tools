# CivitAI 総当たり検索計画書

## 検索対象パラメータ

### Base Models（優先順位順）
1. **Illustrious** (最優先)
2. **NoobAI** (2番目)
3. **Pony** (3番目)
4. **Animagine** (4番目)

### Model Types
- **Checkpoint**
- **LORA**
- **LyCORIS**

### Tags
- **style**
- **concept** 
- **pose**
- **nsfw**
- **sexy**
- **hentai**
- **anime**

### Sort Orders

#### 初回調査対象（Phase 1）
- **Highest Rated**
- **Most Downloaded**
- **Most Liked**

#### 2回目調査対象（Phase 2）
- **Most Images**
- **Most Collected**
- **Newest**
- **Oldest**

## 検索戦略

### 初回調査の組み合わせ計算
```
1 Base Model (Illustrious) × 3 Types × 8 Tags (style, concept, pose, nsfw, sexy, hentai, anime, notag) × 3 Sort Orders = 72 組み合わせ
```

### Type別独立調査の重要性
- **Checkpoint**、**LORA**、**LyCORIS**は独立したモデルタイプ
- 重複調査時に混在しないよう、Type別に分離して実行
- 出力ファイルも Type別に独立して生成

### 検索上限
- **各組み合わせあたり: 500モデル**
- **理論上最大: 252,000モデル**
- **重複除去後の実際の数: 調査対象**

### 検索実行順序
1. **Illustrious** + 全組み合わせ (126パターン)
2. **NoobAI** + 全組み合わせ (126パターン)
3. **Pony** + 全組み合わせ (126パターン)
4. **Animagine** + 全組み合わせ (126パターン)

## 検索詳細パターン

### Phase 1: Illustrious Type別独立調査
```
Illustrious + Checkpoint + [8 tags: style, concept, pose, nsfw, sexy, hentai, anime, notag] × [3 sort orders: Highest Rated, Most Downloaded, Most Liked]
Illustrious + LORA + [8 tags: style, concept, pose, nsfw, sexy, hentai, anime, notag] × [3 sort orders: Highest Rated, Most Downloaded, Most Liked]
Illustrious + LyCORIS + [8 tags: style, concept, pose, nsfw, sexy, hentai, anime, notag] × [3 sort orders: Highest Rated, Most Downloaded, Most Liked]
```

注：notag = タグを指定せずに検索（全タグ対象）

#### 出力ファイル形式（Phase 1）
Enhanced形式（CSV、HTML、JSON）で以下のファイル名パターンで出力：

```
outputs/enhanced/
├── illustrious_checkpoint_highest_rated_style.csv/html/json
├── illustrious_checkpoint_highest_rated_concept.csv/html/json
├── illustrious_checkpoint_highest_rated_pose.csv/html/json
├── illustrious_checkpoint_highest_rated_nsfw.csv/html/json
├── illustrious_checkpoint_highest_rated_sexy.csv/html/json
├── illustrious_checkpoint_highest_rated_hentai.csv/html/json
├── illustrious_checkpoint_highest_rated_notag.csv/html/json
├── illustrious_checkpoint_most_downloaded_[各タグ].csv/html/json
├── illustrious_checkpoint_most_liked_[各タグ].csv/html/json
├── illustrious_lora_[各ソート]_[各タグ].csv/html/json
└── illustrious_lycoris_[各ソート]_[各タグ].csv/html/json
```

**合計ファイル数**: 72組み合わせ × 3形式 = 216ファイル

### Phase 2以降: タグ別・Base Model別拡張調査
後続フェーズで他のBase ModelやTagの組み合わせを実行

## データ収集項目

### 各検索で記録する情報
- **Base Model**: 検索対象のベースモデル
- **Type**: モデルタイプ
- **Tag**: 検索タグ
- **Sort**: ソート順
- **Found Models**: 発見モデル数
- **Unique IDs**: ユニークなモデルID一覧
- **Search Time**: 検索実行時間
- **API Calls**: API呼び出し回数

### 出力ファイル形式
```
outputs/search_analysis/
├── illustrious_search_results.json
├── noobai_search_results.json
├── pony_search_results.json
├── animagine_search_results.json
├── comprehensive_summary.json
├── duplicate_analysis.json
└── final_unique_models.json
```

## 重複除去戦略

### 重複判定基準
- **Primary**: モデルID (`model['id']`)
- **Secondary**: モデル名 + 作成者名

### 重複分析項目
- **Total Found**: 全検索結果の合計数
- **Unique Models**: 重複除去後のユニーク数
- **Duplication Rate**: 重複率 (%)
- **Most Duplicated**: 最も重複の多いモデル
- **Base Model Coverage**: 各Base Modelでの発見率

## 実行コマンド例

### 総当たり検索実行
```bash
python scripts/analysis/comprehensive_search.py --base-models illustrious noobai pony animagine --limit 500 --output-dir outputs/search_analysis
```

### 重複分析実行
```bash
python scripts/analysis/duplicate_analyzer.py --input-dir outputs/search_analysis --output comprehensive_analysis.json
```

## 期待される成果

### 定量的目標
- **総検索数**: 500,000+ API呼び出し
- **発見モデル数**: 10,000-50,000 (重複込み)
- **ユニークモデル数**: 5,000-20,000 (重複除去後)
- **実行時間**: 5-10時間 (レート制限考慮)

### 分析レポート内容
1. **Base Model別統計**: 各Base Modelの発見モデル数
2. **Type別統計**: Checkpoint/LORA/LyCORIS分布
3. **Tag別統計**: 各タグでの発見率
4. **Sort効果分析**: ソート順による発見内容の違い
5. **重複パターン分析**: どの組み合わせで重複が多いか
6. **API効率分析**: 効率的な検索パターンの特定

## 注意事項

### API制限対策
- **レート制限**: 2秒間隔でAPI呼び出し
- **タイムアウト**: 30秒でリクエストタイムアウト
- **エラーハンドリング**: 失敗時の自動リトライ
- **プログレス保存**: 中断時の再開機能

### データ整合性
- **検索結果の保存**: 各検索後に即座にファイル保存
- **メタデータ記録**: 検索条件と結果の紐付け
- **エラーログ**: 失敗した検索の記録

## 実装チェックリスト

### Phase 1: 検索スクリプト作成
- [ ] 総当たり検索メインスクリプト
- [ ] プログレス表示機能
- [ ] 中断・再開機能
- [ ] 結果保存機能

### Phase 2: 分析スクリプト作成
- [ ] 重複分析スクリプト
- [ ] 統計レポート生成
- [ ] 可視化機能

### Phase 3: 実行・分析
- [ ] Illustrious検索実行
- [ ] NoobAI検索実行  
- [ ] Pony検索実行
- [ ] Animagine検索実行
- [ ] 総合分析・レポート作成

## スケジュール

### Day 1: スクリプト作成
- 総当たり検索スクリプト実装
- テスト実行（小規模）

### Day 2-3: 検索実行
- 各Base Modelの検索実行
- プログレス監視・エラー対応

### Day 4: 分析・レポート
- 重複分析実行
- 統計レポート作成
- 最終結果まとめ