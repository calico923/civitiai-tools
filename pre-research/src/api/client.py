"""Civitai API client for model search and data retrieval"""

import requests
import time
import json
from typing import List, Dict, Optional
from urllib.parse import urlencode


class RateLimiter:
    """API呼び出しのレート制限を管理"""
    
    def __init__(self, calls_per_second: float = 0.5):
        """
        Args:
            calls_per_second: 1秒あたりの呼び出し回数（デフォルト: 0.5 = 2秒に1回）
        """
        self.min_interval = 1.0 / calls_per_second
        self.last_call = 0
    
    def wait_if_needed(self):
        """必要に応じて待機"""
        elapsed = time.time() - self.last_call
        if elapsed < self.min_interval:
            wait_time = self.min_interval - elapsed
            print(f"レート制限のため{wait_time:.1f}秒待機中...")
            time.sleep(wait_time)
        self.last_call = time.time()


class CivitaiClient:
    """Civitai APIクライアント"""
    
    def __init__(self, api_key: str):
        """
        Args:
            api_key: Civitai APIキー
        """
        self.api_key = api_key
        self.base_url = "https://civitai.com/api/v1"
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {api_key}",
            "User-Agent": "CivitaiModelDownloader/1.0"
        })
        self.rate_limiter = RateLimiter()
    
    def request(self, method: str, endpoint: str, params: Optional[Dict] = None, **kwargs) -> requests.Response:
        """
        汎用的なHTTPリクエストメソッド
        
        Args:
            method: HTTPメソッド (GET, POST, etc.)
            endpoint: APIエンドポイント (例: '/models')
            params: URLパラメータ
            **kwargs: requests.requestに渡す追加引数
            
        Returns:
            requests.Response オブジェクト
        """
        # レート制限チェック
        self.rate_limiter.wait_if_needed()
        
        # URL構築
        url = f"{self.base_url}{endpoint}"
        
        # パラメータをURL形式に変換（Unicode文字を適切にエンコード）
        if params:
            url_parts = []
            for key, value in params.items():
                if isinstance(value, list):
                    for item in value:
                        # UTF-8エンコーディングを明示的に指定
                        encoded_item = requests.utils.quote(str(item), safe='', encoding='utf-8')
                        url_parts.append(f"{key}={encoded_item}")
                else:
                    # UTF-8エンコーディングを明示的に指定
                    encoded_value = requests.utils.quote(str(value), safe='', encoding='utf-8')
                    url_parts.append(f"{key}={encoded_value}")
            
            if url_parts:
                url += "?" + "&".join(url_parts)
        
        print(f"APIリクエスト: {url}")
        
        try:
            response = self.session.request(method, url, timeout=30, **kwargs)
            response.raise_for_status()
            
            # レスポンスの文字エンコーディングを確認・修正
            if response.encoding is None:
                response.encoding = 'utf-8'
            
            return response
        
        except requests.exceptions.RequestException as e:
            print(f"APIリクエストエラー: {e}")
            if hasattr(e, 'response') and e.response is not None:
                print(f"レスポンス内容: {e.response.text[:500]}...")  # 長すぎるレスポンスは切り詰め
            raise
    
    def search_models(self, 
                     query: Optional[str] = None,
                     types: Optional[List[str]] = None,
                     tag: Optional[str] = None,
                     username: Optional[str] = None,
                     base_models: Optional[List[str]] = None,
                     sort: str = "Highest Rated",
                     limit: int = 100,
                     page: int = 1,
                     cursor: Optional[str] = None) -> Dict:
        """
        モデルを検索
        
        Args:
            query: 検索クエリ
            types: モデルタイプのリスト（例: ["Checkpoint", "LORA"]）
            tag: タグでフィルタリング
            username: 作成者のユーザー名
            base_models: ベースモデルのリスト
            sort: ソート順（"Most Downloaded", "Highest Rated", "Newest"）
            limit: 1ページあたりの結果数（最大100）
            page: ページ番号
            cursor: カーソルベースページネーション用
            
        Returns:
            APIレスポンス
        """
        # レート制限チェック
        self.rate_limiter.wait_if_needed()
        
        # パラメータ構築
        params = {
            "limit": limit,
            "sort": sort
        }
        
        # クエリ検索でない場合のみpageパラメータを追加
        if not query:
            params["page"] = page
        
        if query:
            params["query"] = query
        
        if types:
            params["types"] = types
        
        if tag:
            params["tag"] = tag
        
        if username:
            params["username"] = username
        
        if base_models:
            params["baseModels"] = base_models
        
        if cursor:
            params["cursor"] = cursor
        
        # URL構築（Unicode文字を適切にエンコード）
        from urllib.parse import quote_plus
        url_parts = []
        for key, value in params.items():
            if key in ["types", "baseModels"] and isinstance(value, list):
                for item in value:
                    # UTF-8エンコーディングを明示的に指定
                    encoded_item = quote_plus(str(item), encoding='utf-8')
                    url_parts.append(f"{key}={encoded_item}")
            else:
                # UTF-8エンコーディングを明示的に指定
                encoded_value = quote_plus(str(value), encoding='utf-8')
                url_parts.append(f"{key}={encoded_value}")
        
        url = f"{self.base_url}/models?" + "&".join(url_parts)
        
        print(f"APIリクエスト: {url}")
        
        try:
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            
            # レスポンスの文字エンコーディングを確認・修正
            if response.encoding is None:
                response.encoding = 'utf-8'
            
            # JSONデコード時のエラーハンドリング強化
            try:
                return response.json()
            except json.JSONDecodeError as json_err:
                print(f"JSON デコードエラー: {json_err}")
                print(f"レスポンス文字数: {len(response.text)}")
                print(f"エラー位置付近: {response.text[max(0, json_err.pos-50):json_err.pos+50]}")
                raise
        
        except requests.exceptions.RequestException as e:
            print(f"APIリクエストエラー: {e}")
            if hasattr(e, 'response') and e.response is not None:
                print(f"レスポンス内容: {e.response.text[:500]}...")  # 長すぎるレスポンスは切り詰め
            raise
    
    def search_models_with_cursor(self, 
                                 query: Optional[str] = None,
                                 types: Optional[List[str]] = None,
                                 tag: Optional[str] = None,
                                 username: Optional[str] = None,
                                 base_models: Optional[List[str]] = None,
                                 sort: str = "Highest Rated",
                                 limit: int = 100,
                                 max_pages: int = 50) -> List[Dict]:
        """
        カーソルベースのページネーションを使用して全データを取得
        
        Args:
            query: 検索クエリ
            types: モデルタイプのリスト
            tag: タグでフィルタリング
            username: 作成者のユーザー名
            base_models: ベースモデルのリスト
            sort: ソート順
            limit: 1ページあたりの結果数
            max_pages: 最大ページ数（安全のため）
            
        Returns:
            全モデルのリスト
        """
        all_models = []
        cursor = None
        page_count = 0
        
        while page_count < max_pages:
            page_count += 1
            print(f"ページ {page_count} を取得中...")
            
            try:
                # クエリ検索の場合はpageパラメータは使用しない
                if query:
                    response = self.search_models(
                        query=query,
                        types=types,
                        tag=tag,
                        username=username,
                        base_models=base_models,
                        sort=sort,
                        limit=limit,
                        cursor=cursor
                    )
                else:
                    response = self.search_models(
                        query=query,
                        types=types,
                        tag=tag,
                        username=username,
                        base_models=base_models,
                        sort=sort,
                        limit=limit,
                        page=1,  # カーソルを使う場合は常に1
                        cursor=cursor
                    )
                
                items = response.get("items", [])
                metadata = response.get("metadata", {})
                
                print(f"  取得数: {len(items)}")
                
                if not items:
                    print("  データがありません。終了します。")
                    break
                
                all_models.extend(items)
                
                # サンプル表示
                if items:
                    print(f"  サンプル: {items[0].get('name', 'Unknown')}")
                
                # 次のカーソルを取得
                next_cursor = metadata.get("nextCursor")
                if not next_cursor:
                    print("  nextCursorがありません。すべてのデータを取得しました。")
                    break
                
                cursor = next_cursor
                
            except Exception as e:
                print(f"  エラー: {e}")
                break
        
        print(f"\n取得完了: {len(all_models)}個のモデル")
        
        # 重複チェック
        model_ids = [model.get('id') for model in all_models]
        unique_ids = set(model_ids)
        if len(model_ids) != len(unique_ids):
            print(f"⚠️  重複除去: {len(model_ids) - len(unique_ids)}個")
            # 重複除去
            seen_ids = set()
            unique_models = []
            for model in all_models:
                if model.get('id') not in seen_ids:
                    unique_models.append(model)
                    seen_ids.add(model.get('id'))
            return unique_models
        
        return all_models
    
    def search_illustrious_checkpoints(self, max_requests: int = 3) -> List[Dict]:
        """
        illustriousタグ付きCheckpointを検索（Most Downloaded順）
        
        Args:
            max_requests: 最大リクエスト数
            
        Returns:
            モデルのリスト
        """
        all_models = []
        
        print(f"illustrious Checkpointを検索中...")
        
        try:
            print(f"\nillustriousタグ付きCheckpointを直接検索中...")
            
            # tagパラメータを使ってillustriousタグで直接フィルタリング
            response = self.search_models(
                types=["Checkpoint"],
                tag="illustrious",
                sort="Highest Rated",
                limit=100,
                page=1
            )
            
            items = response.get("items", [])
            print(f"  {len(items)}個のillustrious Checkpointを取得")
            
            for model in items:
                print(f"    発見: {model.get('name', 'Unknown')} (ID: {model.get('id')})")
                all_models.append(model)
            
            # 2ページ目以降も確認
            metadata = response.get("metadata", {})
            total_pages = metadata.get("totalPages", 1)
            total_items = metadata.get("totalItems", len(items))
            current_page = metadata.get("currentPage", 1)
            page_size = metadata.get("pageSize", len(items))
            
            print(f"  ページ情報:")
            print(f"    - 現在のページ: {current_page}")
            print(f"    - 総ページ数: {total_pages}")
            print(f"    - 総アイテム数: {total_items}")
            print(f"    - ページサイズ: {page_size}")
            
            if total_pages > 1 and max_requests > 1:
                for page in range(2, min(max_requests + 1, total_pages + 1)):
                    print(f"\nページ {page} を取得中...")
                    
                    response = self.search_models(
                        types=["Checkpoint"],
                        tag="illustrious",
                        sort="Highest Rated",
                        limit=100,
                        page=page
                    )
                    
                    items = response.get("items", [])
                    print(f"  {len(items)}個のillustrious Checkpointを追加取得")
                    
                    for model in items:
                        print(f"    発見: {model.get('name', 'Unknown')} (ID: {model.get('id')})")
                        all_models.append(model)
                    
        except Exception as e:
            print(f"検索に失敗: {e}")
        
        print(f"\n合計 {len(all_models)} 個のillustrious Checkpointを発見")
        return all_models
    
    def search_models_extended(self, tag: str, model_type: str = "Checkpoint", max_requests: int = 3, sort: str = "Most Downloaded", additional_tag: str = None) -> List[Dict]:
        """
        指定タグまたは名前にタグを含むモデルを検索
        
        Args:
            tag: メインの検索タグ
            model_type: モデルタイプ
            max_requests: 最大リクエスト数
            sort: ソート順
            additional_tag: 追加の検索タグ（両方のタグを持つモデルを検索）
            
        Returns:
            モデルのリスト
        """
        all_models = []
        model_ids = set()  # 重複除去用
        
        if additional_tag:
            print(f"{tag}+{additional_tag} {model_type}を拡張検索中...")
        else:
            print(f"{tag} {model_type}を拡張検索中...")
        
        try:
            # カーソルベースのページネーションを使用
            print(f"\n1. {tag}タグ付き{model_type}を検索中...")
            
            models = self.search_models_with_cursor(
                types=[model_type],
                tag=tag,
                sort=sort,
                limit=100,
                max_pages=max_requests * 10  # より多くのページを取得
            )
            
            print(f"  {len(models)}個のタグ付きモデルを発見")
            
            for model in models:
                # 追加タグの条件をチェック
                if additional_tag:
                    model_tags = [tag.lower() for tag in model.get('tags', [])]
                    if additional_tag.lower() not in model_tags:
                        continue
                
                if model['id'] not in model_ids:
                    all_models.append(model)
                    model_ids.add(model['id'])
                    
        except Exception as e:
            print(f"検索に失敗: {e}")
        
        if additional_tag:
            print(f"\n合計 {len(all_models)} 個の{tag}+{additional_tag}関連{model_type}を発見")
        else:
            print(f"\n合計 {len(all_models)} 個の{tag}関連{model_type}を発見")
        return all_models
    
    def get_model_by_id(self, model_id: int) -> Dict:
        """
        特定のモデルIDでモデル情報を取得
        
        Args:
            model_id: モデルID
            
        Returns:
            モデル情報
        """
        # レート制限チェック
        self.rate_limiter.wait_if_needed()
        
        try:
            response = self.request('GET', f'/models/{model_id}')
            
            # JSONデコード時のエラーハンドリング強化
            try:
                return response.json()
            except json.JSONDecodeError as json_err:
                print(f"JSON デコードエラー (Model ID: {model_id}): {json_err}")
                print(f"レスポンス文字数: {len(response.text)}")
                print(f"エラー位置付近: {response.text[max(0, json_err.pos-50):json_err.pos+50]}")
                raise
        
        except requests.exceptions.RequestException as e:
            print(f"モデル取得エラー (ID: {model_id}): {e}")
            raise
    
    def get_model_from_url(self, civitai_url: str) -> Dict:
        """
        CivitAI モデルページURLからモデル情報を取得
        
        Args:
            civitai_url: CivitAIモデルページURL (例: https://civitai.com/models/1369545)
            
        Returns:
            モデル情報
        """
        import re
        
        # URLからモデルIDを抽出
        pattern = r'https://civitai\.com/models/(\d+)'
        match = re.search(pattern, civitai_url)
        
        if not match:
            raise ValueError(f"無効なCivitAI URL: {civitai_url}")
        
        model_id = int(match.group(1))
        print(f"URLからモデルID {model_id} を抽出")
        
        return self.get_model_by_id(model_id)