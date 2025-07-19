# CivitAI API v1 完全仕様書

## 概要
CivitAI APIから取得可能なすべてのフィールドとその詳細

## トップレベルフィールド

- **id** (int)
- **name** (str)
- **description** (str)
- **allowNoCredit** (bool)
- **allowCommercialUse** (list)
- **allowDerivatives** (bool)
- **allowDifferentLicense** (bool)
- **type** (str)
- **minor** (bool)
- **sfwOnly** (bool)
- **poi** (bool)
- **nsfw** (bool)
- **nsfwLevel** (int)
- **availability** (str)
- **cosmetic** (NoneType)
- **supportsGeneration** (bool)
- **stats** (dict)
- **creator** (dict)
- **tags** (list)
- **modelVersions** (list)

## 基本情報

| フィールドパス | 型 | サンプル値/説明 |
|--------------|---|-------------|
| `creator` | dict | オブジェクト |
| `creator.image` | str | https://image.civitai.com/xG1nkqKTMzGDvpLrqFT7W... |
| `creator.username` | str | Ikena |
| `description` | str | <p>Hassaku aims to be a anime model with a brig... |
| `id` | int | 140272 |
| `modelVersions[0].baseModelType` | str | Standard |
| `modelVersions[0].description` | str | <p>Be aware that this is a WIP model, WIP means... |
| `modelVersions[0].files[0].id` | int | 1907803 |
| `modelVersions[0].files[0].name` | str | hassakuXLIllustrious_v30.safetensors |
| `modelVersions[0].files[0].type` | str | Model |
| `modelVersions[0].id` | int | 2010753 |
| `modelVersions[0].images[0].remixOfId` | NoneType | null |
| `modelVersions[0].images[0].type` | str | image |
| `modelVersions[0].images[0].width` | int | 1248 |
| `modelVersions[0].name` | str | v3.0 |
| `name` | str | Hassaku XL (Illustrious) |
| `type` | str | Checkpoint |

## ライセンス・権限

| フィールドパス | 型 | サンプル値/説明 |
|--------------|---|-------------|
| `allowCommercialUse` | list | 配列 (長さ: 3) |
| `allowDerivatives` | bool | True |
| `allowDifferentLicense` | bool | False |
| `allowNoCredit` | bool | False |

## 統計情報

| フィールドパス | 型 | サンプル値/説明 |
|--------------|---|-------------|
| `modelVersions[0].downloadUrl` | str | https://civitai.com/api/download/models/2010753 |
| `modelVersions[0].files[0].downloadUrl` | str | https://civitai.com/api/download/models/2010753 |
| `modelVersions[0].stats` | dict | オブジェクト |
| `modelVersions[0].stats.downloadCount` | int | 111 |
| `modelVersions[0].stats.rating` | int | 0 |
| `modelVersions[0].stats.ratingCount` | int | 0 |
| `modelVersions[0].stats.thumbsDownCount` | int | 0 |
| `modelVersions[0].stats.thumbsUpCount` | int | 263 |
| `modelVersions[0].status` | str | Published |
| `stats` | dict | オブジェクト |
| `stats.commentCount` | int | 296 |
| `stats.downloadCount` | int | 234606 |
| `stats.favoriteCount` | int | 0 |
| `stats.rating` | int | 0 |
| `stats.ratingCount` | int | 0 |
| `stats.thumbsDownCount` | int | 47 |
| `stats.thumbsUpCount` | int | 20546 |
| `stats.tippedAmountCount` | int | 71143 |

## バージョン情報

| フィールドパス | 型 | サンプル値/説明 |
|--------------|---|-------------|
| `modelVersions` | list | 配列 (長さ: 25) |
| `modelVersions[0].availability` | str | EarlyAccess |
| `modelVersions[0].baseModel` | str | Illustrious |
| `modelVersions[0].covered` | bool | False |
| `modelVersions[0].createdAt` | str | 2025-07-14T23:41:24.964Z |
| `modelVersions[0].files` | list | 配列 (長さ: 1) |
| `modelVersions[0].files[0].hashes` | dict | オブジェクト |
| `modelVersions[0].files[0].hashes.AutoV1` | str | A5828527 |
| `modelVersions[0].files[0].hashes.AutoV2` | str | B4FB5F829A |
| `modelVersions[0].files[0].hashes.AutoV3` | str | E45A888AA8F8 |
| `modelVersions[0].files[0].hashes.BLAKE3` | str | 52F094B47C384B4ED50B300EC1744CAAFE5ABF97E94E326... |
| `modelVersions[0].files[0].hashes.CRC32` | str | D163F6E0 |
| `modelVersions[0].files[0].hashes.SHA256` | str | B4FB5F829A46A91F8499A2C7C0A0653C0E8DE1632C0B032... |
| `modelVersions[0].files[0].metadata` | dict | オブジェクト |
| `modelVersions[0].files[0].metadata.format` | str | SafeTensor |
| `modelVersions[0].files[0].metadata.fp` | str | fp16 |
| `modelVersions[0].files[0].metadata.size` | str | pruned |
| `modelVersions[0].files[0].pickleScanMessage` | str | No Pickle imports |
| `modelVersions[0].files[0].pickleScanResult` | str | Success |
| `modelVersions[0].files[0].primary` | bool | True |
| `modelVersions[0].files[0].scannedAt` | str | 2025-07-15T00:53:22.014Z |
| `modelVersions[0].files[0].sizeKB` | float | 6775430.125 |
| `modelVersions[0].files[0].virusScanMessage` | NoneType | null |
| `modelVersions[0].files[0].virusScanResult` | str | Success |
| `modelVersions[0].images` | list | 配列 (長さ: 14) |
| `modelVersions[0].images[0].hasMeta` | bool | True |
| `modelVersions[0].images[0].hasPositivePrompt` | bool | True |
| `modelVersions[0].images[0].hash` | str | UIOehyPVc[$%8xS$Po-;%zIBInMx_NM|tRtR |
| `modelVersions[0].images[0].height` | int | 1608 |
| `modelVersions[0].images[0].minor` | bool | False |
| `modelVersions[0].images[0].nsfwLevel` | int | 2 |
| `modelVersions[0].images[0].onSite` | bool | False |
| `modelVersions[0].images[0].poi` | bool | False |
| `modelVersions[0].images[0].url` | str | https://image.civitai.com/xG1nkqKTMzGDvpLrqFT7W... |
| `modelVersions[0].index` | int | 0 |
| `modelVersions[0].nsfwLevel` | int | 23 |
| `modelVersions[0].publishedAt` | str | 2025-07-15T02:17:06.358Z |

## メタデータ

| フィールドパス | 型 | サンプル値/説明 |
|--------------|---|-------------|
| `minor` | bool | False |
| `nsfw` | bool | False |
| `nsfwLevel` | int | 31 |
| `poi` | bool | False |
| `tags` | list | 配列 (長さ: 7) |

## その他

| フィールドパス | 型 | サンプル値/説明 |
|--------------|---|-------------|
| `availability` | str | Public |
| `cosmetic` | NoneType | null |
| `sfwOnly` | bool | False |
| `supportsGeneration` | bool | True |

## 特筆すべき発見

### ライセンス・商用利用
- `allowCommercialUse`: 商用利用の詳細な許可レベル
  - 'Image': 生成画像の商用利用
  - 'Rent': モデルのレンタル
  - 'RentCivit': CivitAI上でのレンタル
  - 'Sell': モデルの販売
- `allowDerivatives`: 派生作品の作成許可
- `allowDifferentLicense`: 異なるライセンスでの再配布
- `allowNoCredit`: クレジット表記不要での使用

### 統計・メトリクス
- ダウンロード数、いいね数、コメント数など詳細な統計
- 評価（rating）とレビュー数
- お気に入り数とチップ数

### バージョン・ファイル管理
- 複数バージョンの管理
- 各バージョンごとのファイル情報
- ハッシュ値による整合性確認
- トレーニング設定の詳細

