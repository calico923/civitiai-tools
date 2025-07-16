#!/usr/bin/env python3
"""
殿堂入り枠付きのHTMLレポートを生成するスクリプト
"""

import pandas as pd
from datetime import datetime

def create_html_report():
    # データを読み込み
    hall_of_fame_df = pd.read_csv('/Users/kuniaki-k/Code/civitiai/outputs/enhanced/illustrious_checkpoint_hall_of_fame.csv')
    top99_df = pd.read_csv('/Users/kuniaki-k/Code/civitiai/outputs/enhanced/illustrious_checkpoint_top99_recalculated.csv')
    
    # 統計情報を計算
    hof_model = hall_of_fame_df.iloc[0]
    sfw_count = (~top99_df['nsfw']).sum()
    nsfw_count = top99_df['nsfw'].sum()
    total_models = len(top99_df)
    
    html_content = f"""<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Illustrious Checkpoint 殿堂入り＋Top99 ランキング</title>
    <style>
        body {{ 
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; 
            margin: 20px; 
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
        }}
        .container {{ 
            max-width: 1400px; 
            margin: 0 auto; 
            background: white; 
            padding: 30px; 
            border-radius: 15px; 
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
        }}
        h1 {{ 
            color: #2c3e50; 
            text-align: center; 
            border-bottom: 4px solid #3498db; 
            padding-bottom: 15px; 
            margin-bottom: 30px;
            font-size: 2.5em;
        }}
        h2 {{ 
            color: #34495e; 
            border-left: 5px solid #3498db; 
            padding-left: 15px; 
            margin-top: 40px;
        }}
        .update-notice {{
            background: linear-gradient(45deg, #ff6b6b, #ffa500);
            color: white;
            padding: 15px;
            border-radius: 10px;
            text-align: center;
            margin-bottom: 20px;
            font-weight: bold;
            font-size: 1.1em;
        }}
        .hall-of-fame {{
            background: linear-gradient(45deg, #ffd700, #ffed4e);
            color: #333;
            padding: 25px;
            border-radius: 15px;
            margin: 30px 0;
            border: 3px solid #ffd700;
            box-shadow: 0 8px 25px rgba(255, 215, 0, 0.3);
        }}
        .hall-of-fame h3 {{
            margin-top: 0;
            font-size: 1.8em;
            text-align: center;
            color: #b8860b;
        }}
        .hall-of-fame .model-info {{
            display: grid;
            grid-template-columns: 1fr 1fr 1fr;
            gap: 20px;
            margin-top: 15px;
        }}
        .hall-of-fame .metric {{
            text-align: center;
            padding: 10px;
            background: rgba(255,255,255,0.7);
            border-radius: 8px;
        }}
        .hall-of-fame .metric-value {{
            font-size: 24px;
            font-weight: bold;
            color: #b8860b;
        }}
        .stats {{ 
            display: grid; 
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            background: #f8f9fa; 
            padding: 25px; 
            border-radius: 10px; 
            margin: 30px 0;
        }}
        .stat-item {{ 
            text-align: center; 
            padding: 15px;
            background: white;
            border-radius: 8px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }}
        .stat-value {{ 
            font-size: 28px; 
            font-weight: bold; 
            color: #3498db; 
            display: block;
        }}
        .stat-label {{ 
            font-size: 14px; 
            color: #7f8c8d; 
            margin-top: 5px;
        }}
        .category-breakdown {{
            display: flex;
            justify-content: center;
            gap: 30px;
            margin: 20px 0;
        }}
        .category-item {{
            text-align: center;
            padding: 20px;
            border-radius: 10px;
            min-width: 120px;
        }}
        .sfw-category {{
            background: linear-gradient(45deg, #2ecc71, #27ae60);
            color: white;
        }}
        .nsfw-category {{
            background: linear-gradient(45deg, #e74c3c, #c0392b);
            color: white;
        }}
        table {{ 
            width: 100%; 
            border-collapse: collapse; 
            margin: 30px 0;
            background: white;
            border-radius: 10px;
            overflow: hidden;
            box-shadow: 0 4px 15px rgba(0,0,0,0.1);
        }}
        th {{ 
            background: linear-gradient(45deg, #3498db, #2980b9); 
            color: white; 
            padding: 15px 10px; 
            text-align: center;
            font-weight: bold;
        }}
        td {{ 
            padding: 12px 10px; 
            text-align: center; 
            border-bottom: 1px solid #ecf0f1;
        }}
        tr:nth-child(even) {{ 
            background-color: #f8f9fa; 
        }}
        tr:hover {{ 
            background-color: #e3f2fd; 
            transition: background-color 0.3s;
        }}
        .rank-column {{ 
            font-weight: bold; 
            color: #e67e22;
            width: 60px;
        }}
        .score-column {{ 
            font-weight: bold; 
            color: #27ae60;
            width: 80px;
        }}
        .nsfw-badge {{ 
            background: #e74c3c; 
            color: white; 
            padding: 4px 8px; 
            border-radius: 15px; 
            font-size: 0.8em;
            font-weight: bold;
        }}
        .sfw-badge {{ 
            background: #27ae60; 
            color: white; 
            padding: 4px 8px; 
            border-radius: 15px; 
            font-size: 0.8em;
            font-weight: bold;
        }}
        .model-link {{
            color: #3498db;
            text-decoration: none;
            font-weight: bold;
        }}
        .model-link:hover {{
            color: #2980b9;
            text-decoration: underline;
        }}
        .top-10-highlight {{
            background: linear-gradient(45deg, #fff3cd, #fef9e7) !important;
            border-left: 4px solid #f39c12;
        }}
        .methodology {{
            background: #ecf0f1;
            padding: 20px;
            border-radius: 10px;
            margin: 30px 0;
        }}
        .methodology h3 {{
            color: #34495e;
            margin-top: 0;
        }}
        .methodology ul {{
            color: #5d6d7e;
        }}
        @media (max-width: 768px) {{
            .container {{ padding: 15px; }}
            .stats {{ grid-template-columns: 1fr; }}
            .category-breakdown {{ flex-direction: column; align-items: center; }}
            .hall-of-fame .model-info {{ grid-template-columns: 1fr; }}
            table {{ font-size: 0.9em; }}
            th, td {{ padding: 8px 6px; }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="update-notice">
            🏆 殿堂入り枠を新設！WAI-NSFW-illustrious-SDXLを別枠として、残り99モデルでランキングを再計算
        </div>
        
        <h1>🏆 Illustrious Checkpoint 殿堂入り＋Top99 ランキング</h1>
        
        <div class="hall-of-fame">
            <h3>🌟 殿堂入り 🌟</h3>
            <div style="text-align: center; margin-bottom: 15px;">
                <a href="{hof_model['civitai_page_url']}" target="_blank" class="model-link" style="font-size: 1.3em;">
                    {hof_model['model_name']}
                </a>
                <div style="margin-top: 5px; color: #666;">作者: {hof_model['creator']}</div>
            </div>
            <div class="model-info">
                <div class="metric">
                    <div class="metric-value">{hof_model['thumbs_up_count']:,}</div>
                    <div>いいね数</div>
                </div>
                <div class="metric">
                    <div class="metric-value">{hof_model['updated_download_count']:,}</div>
                    <div>ダウンロード数</div>
                </div>
                <div class="metric">
                    <div class="metric-value">{hof_model['final_ranking_score']:.1f}</div>
                    <div>元スコア</div>
                </div>
            </div>
            <div style="text-align: center; margin-top: 15px; font-style: italic; color: #666;">
                突出したメトリクスにより殿堂入りとして別枠で表彰
            </div>
        </div>
        
        <h2>📊 Top99 統計情報</h2>
        <div class="stats">
            <div class="stat-item">
                <span class="stat-value">{total_models}</span>
                <div class="stat-label">総モデル数</div>
            </div>
            <div class="stat-item">
                <span class="stat-value">{top99_df.iloc[0]['thumbs_up_count']:,}</span>
                <div class="stat-label">最高いいね数<br>(1位)</div>
            </div>
            <div class="stat-item">
                <span class="stat-value">{top99_df['updated_download_count'].max():,}</span>
                <div class="stat-label">最高DL数</div>
            </div>
            <div class="stat-item">
                <span class="stat-value">{len(top99_df['creator'].unique())}</span>
                <div class="stat-label">作成者数</div>
            </div>
        </div>
        
        <h2>🎨 カテゴリ分布</h2>
        <div class="category-breakdown">
            <div class="category-item sfw-category">
                <div style="font-size: 2em; font-weight: bold;">{sfw_count}</div>
                <div>SFW モデル</div>
                <div style="font-size: 0.9em;">({sfw_count/total_models*100:.1f}%)</div>
            </div>
            <div class="category-item nsfw-category">
                <div style="font-size: 2em; font-weight: bold;">{nsfw_count}</div>
                <div>NSFW モデル</div>
                <div style="font-size: 0.9em;">({nsfw_count/total_models*100:.1f}%)</div>
            </div>
        </div>
        
        <h2>🏅 Top99 ランキング</h2>
        <table>
            <thead>
                <tr>
                    <th class="rank-column">順位</th>
                    <th style="width: 300px;">モデル名</th>
                    <th style="width: 120px;">作成者</th>
                    <th class="score-column">スコア</th>
                    <th style="width: 100px;">いいね</th>
                    <th style="width: 100px;">DL数</th>
                    <th style="width: 80px;">分類</th>
                </tr>
            </thead>
            <tbody>"""
    
    # Top99のテーブル行を生成
    for _, row in top99_df.iterrows():
        rank = int(row['rank'])
        nsfw_badge = f'<span class="nsfw-badge">NSFW</span>' if row['nsfw'] else f'<span class="sfw-badge">SFW</span>'
        row_class = ' class="top-10-highlight"' if rank <= 10 else ''
        
        html_content += f"""
                <tr{row_class}>
                    <td class="rank-column">{rank}</td>
                    <td style="text-align: left;">
                        <a href="{row['civitai_page_url']}" target="_blank" class="model-link">
                            {row['model_name']}
                        </a>
                    </td>
                    <td>{row['creator']}</td>
                    <td class="score-column">{row['final_ranking_score']:.1f}</td>
                    <td>{row['thumbs_up_count']:,}</td>
                    <td>{row['updated_download_count']:,}</td>
                    <td>{nsfw_badge}</td>
                </tr>"""
    
    html_content += f"""
            </tbody>
        </table>
        
        <div class="methodology">
            <h3>📋 ランキング方法</h3>
            <ul>
                <li><strong>殿堂入り枠:</strong> WAI-NSFW-illustrious-SDXL (いいね47,373、DL639,550) を別枠として表彰</li>
                <li><strong>スコア計算:</strong> いいね数(40%) + ダウンロード数(30%) + エンゲージメント(20%) + コメント(10%)</li>
                <li><strong>正規化:</strong> 99モデルの範囲で0-100点に正規化</li>
                <li><strong>NSFW判定:</strong> タグベース分類（nsfw, hentai, sexy, porn等）</li>
                <li><strong>フィルタリング:</strong> 'base model'タグを持つCheckpointのみ対象</li>
            </ul>
            <p style="margin-top: 15px; color: #666; font-style: italic;">
                生成日時: {datetime.now().strftime('%Y年%m月%d日 %H:%M:%S')} | 
                データソース: CivitAI API v1 | 
                作成者: Claude Code
            </p>
        </div>
    </div>
</body>
</html>"""
    
    return html_content

def main():
    html_content = create_html_report()
    
    output_file = '/Users/kuniaki-k/Code/civitiai/outputs/enhanced/illustrious_checkpoint_hall_of_fame_top99_report.html'
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    print(f"HTMLレポートを生成しました: {output_file}")

if __name__ == "__main__":
    main()