# Phase 7: デプロイメントガイド

## 概要

CivitAI Downloader v2 Phase 7では、プロダクション環境での安全で信頼性の高いデプロイメントを実現します。このガイドでは、Docker、Kubernetes、および従来のサーバー環境での展開方法を説明します。

## システム要件

### 最小要件
- **CPU**: 2コア (推奨: 4コア)
- **RAM**: 2GB (推奨: 4GB)
- **ストレージ**: 10GB (推奨: 50GB)
- **ネットワーク**: インターネット接続必須

### 推奨要件
- **CPU**: 4コア以上
- **RAM**: 8GB以上
- **ストレージ**: 100GB以上 (SSD推奨)
- **OS**: Ubuntu 20.04 LTS, CentOS 8, Docker対応OS

## Dockerを使用したデプロイメント

### 1. 基本デプロイメント

```bash
# リポジトリのクローン
git clone https://github.com/calico923/civitiai-tools.git
cd civitai-downloader-v2

# 環境設定
cp deployment/config/app_config.yml.example deployment/config/app_config.yml
cp .env.example .env

# 設定の編集
vim deployment/config/app_config.yml
vim .env

# コンテナの起動
docker-compose -f deployment/docker-compose.yml up -d
```

### 2. プロダクション構成

```bash
# フルスタック構成（DB + Redis + 監視）
docker-compose -f deployment/docker-compose.yml \
               -f deployment/docker-compose.prod.yml up -d

# ヘルスチェック
docker-compose ps
docker-compose logs civitai-downloader
```

### 3. 設定のカスタマイズ

```yaml
# deployment/config/app_config.yml
download:
  max_concurrent: 5
  base_directory: "/data/downloads"
  
security:
  encryption_level: "high"
  enable_access_control: true
  
monitoring:
  enabled: true
  thresholds:
    cpu_warning: 70
    memory_warning: 75
```

## Kubernetes デプロイメント

### 1. 基本マニフェスト

```yaml
# k8s/namespace.yaml
apiVersion: v1
kind: Namespace
metadata:
  name: civitai-downloader

---
# k8s/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: civitai-downloader
  namespace: civitai-downloader
spec:
  replicas: 1
  selector:
    matchLabels:
      app: civitai-downloader
  template:
    metadata:
      labels:
        app: civitai-downloader
    spec:
      containers:
      - name: civitai-downloader
        image: civitai/downloader-v2:latest
        ports:
        - containerPort: 8080
        env:
        - name: LOG_LEVEL
          value: "INFO"
        resources:
          requests:
            memory: "512Mi"
            cpu: "500m"
          limits:
            memory: "2Gi"
            cpu: "1000m"
        volumeMounts:
        - name: config
          mountPath: /app/config
        - name: data
          mountPath: /app/data
        - name: downloads
          mountPath: /app/downloads
      volumes:
      - name: config
        configMap:
          name: civitai-config
      - name: data
        persistentVolumeClaim:
          claimName: civitai-data
      - name: downloads
        persistentVolumeClaim:
          claimName: civitai-downloads
```

### 2. サービス設定

```yaml
# k8s/service.yaml
apiVersion: v1
kind: Service
metadata:
  name: civitai-downloader-service
  namespace: civitai-downloader
spec:
  selector:
    app: civitai-downloader
  ports:
  - port: 80
    targetPort: 8080
  type: ClusterIP

---
# k8s/ingress.yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: civitai-downloader-ingress
  namespace: civitai-downloader
  annotations:
    nginx.ingress.kubernetes.io/rewrite-target: /
spec:
  rules:
  - host: civitai-downloader.example.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: civitai-downloader-service
            port:
              number: 80
```

### 3. デプロイ実行

```bash
# マニフェストの適用
kubectl apply -f k8s/

# 状態確認
kubectl get pods -n civitai-downloader
kubectl logs -f deployment/civitai-downloader -n civitai-downloader

# サービスへのアクセス
kubectl port-forward svc/civitai-downloader-service 8080:80 -n civitai-downloader
```

## 従来のサーバーデプロイメント

### 1. 環境準備

```bash
# Python 3.11のインストール
sudo apt update
sudo apt install python3.11 python3.11-venv python3.11-dev

# 仮想環境の作成
python3.11 -m venv /opt/civitai-downloader
source /opt/civitai-downloader/bin/activate

# アプリケーションのインストール
git clone https://github.com/calico923/civitiai-tools.git /opt/civitai-downloader/app
cd /opt/civitai-downloader/app/civitai-downloader-v2
pip install -r requirements.txt
```

### 2. systemdサービス設定

```ini
# /etc/systemd/system/civitai-downloader.service
[Unit]
Description=CivitAI Downloader v2
After=network.target

[Service]
Type=simple
User=civitai
Group=civitai
WorkingDirectory=/opt/civitai-downloader/app/civitai-downloader-v2
Environment=PYTHONPATH=/opt/civitai-downloader/app/civitai-downloader-v2
ExecStart=/opt/civitai-downloader/bin/python -m src.main --config /etc/civitai-downloader/config.yml
Restart=always
RestartSec=10

# セキュリティ設定
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/var/lib/civitai-downloader
ReadWritePaths=/var/log/civitai-downloader

[Install]
WantedBy=multi-user.target
```

### 3. サービス起動

```bash
# ユーザー作成
sudo useradd -r -s /bin/false civitai
sudo mkdir -p /var/lib/civitai-downloader /var/log/civitai-downloader
sudo chown civitai:civitai /var/lib/civitai-downloader /var/log/civitai-downloader

# サービス有効化
sudo systemctl daemon-reload
sudo systemctl enable civitai-downloader
sudo systemctl start civitai-downloader

# 状態確認
sudo systemctl status civitai-downloader
sudo journalctl -u civitai-downloader -f
```

## セキュリティ設定

### 1. アクセス制御

```yaml
# security_policy.yml
security:
  access_control:
    enabled: true
    default_policy: "strict"
    roles:
      admin:
        permissions: ["all"]
      user:
        permissions: ["download", "search", "view"]
      guest:
        permissions: ["search", "view"]
    
  authentication:
    method: "password"  # password, key, ldap
    password_policy:
      min_length: 12
      require_special: true
      require_numbers: true
    session_timeout: 1800
    
  encryption:
    level: "high"
    key_rotation: true
    key_rotation_interval: 86400
```

### 2. ネットワークセキュリティ

```bash
# ファイアウォール設定 (UFW)
sudo ufw enable
sudo ufw allow 22/tcp    # SSH
sudo ufw allow 8080/tcp  # アプリケーション
sudo ufw deny 5432/tcp   # データベース（内部のみ）

# fail2ban設定
sudo apt install fail2ban
sudo cp deployment/security/fail2ban-civitai.conf /etc/fail2ban/jail.d/
sudo systemctl restart fail2ban
```

### 3. SSL/TLS設定

```nginx
# nginx/civitai-downloader.conf
server {
    listen 443 ssl http2;
    server_name civitai-downloader.example.com;
    
    ssl_certificate /etc/ssl/certs/civitai-downloader.crt;
    ssl_certificate_key /etc/ssl/private/civitai-downloader.key;
    
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;
    
    location / {
        proxy_pass http://127.0.0.1:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

## 監視とログ

### 1. メトリクス収集

```yaml
# monitoring/prometheus.yml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'civitai-downloader'
    static_configs:
      - targets: ['localhost:8080']
    metrics_path: '/metrics'
    scrape_interval: 5s
```

### 2. アラート設定

```yaml
# monitoring/alert-rules.yml
groups:
  - name: civitai-downloader
    rules:
      - alert: HighCPUUsage
        expr: cpu_usage_percent > 90
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High CPU usage detected"
          
      - alert: LowDiskSpace
        expr: disk_free_percent < 10
        for: 2m
        labels:
          severity: critical
        annotations:
          summary: "Low disk space"
```

### 3. ログ管理

```bash
# Logrotate設定
# /etc/logrotate.d/civitai-downloader
/var/log/civitai-downloader/*.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    create 0644 civitai civitai
    postrotate
        systemctl reload civitai-downloader
    endscript
}
```

## バックアップと復旧

### 1. データバックアップ

```bash
#!/bin/bash
# backup.sh
BACKUP_DIR="/backup/civitai-downloader"
DATE=$(date +%Y%m%d_%H%M%S)

# データベースバックアップ
sqlite3 /var/lib/civitai-downloader/civitai.db ".backup $BACKUP_DIR/db_$DATE.db"

# 設定ファイルバックアップ
tar -czf "$BACKUP_DIR/config_$DATE.tar.gz" /etc/civitai-downloader/

# ダウンロードファイルバックアップ（選択的）
rsync -av --link-dest="$BACKUP_DIR/downloads_latest" \
    /var/lib/civitai-downloader/downloads/ \
    "$BACKUP_DIR/downloads_$DATE/"

# 古いバックアップの削除（30日以上）
find "$BACKUP_DIR" -name "*.db" -mtime +30 -delete
find "$BACKUP_DIR" -name "*.tar.gz" -mtime +30 -delete
```

### 2. 自動バックアップ

```bash
# crontab -e
# 毎日2時にバックアップ実行
0 2 * * * /opt/civitai-downloader/scripts/backup.sh

# 毎週データベース最適化
0 3 * * 0 sqlite3 /var/lib/civitai-downloader/civitai.db "VACUUM;"
```

### 3. 復旧手順

```bash
# サービス停止
sudo systemctl stop civitai-downloader

# データベース復旧
cp /backup/civitai-downloader/db_YYYYMMDD_HHMMSS.db \
   /var/lib/civitai-downloader/civitai.db

# 設定復旧
tar -xzf /backup/civitai-downloader/config_YYYYMMDD_HHMMSS.tar.gz -C /

# 権限修正
sudo chown -R civitai:civitai /var/lib/civitai-downloader/
sudo chown -R civitai:civitai /etc/civitai-downloader/

# サービス開始
sudo systemctl start civitai-downloader
sudo systemctl status civitai-downloader
```

## トラブルシューティング

### 1. 一般的な問題

| 問題 | 原因 | 解決策 |
|------|------|--------|
| 起動失敗 | 設定ファイルエラー | `python -m src.main --validate-config` |
| メモリ不足 | リソース制限 | メモリ制限の調整 |
| ダウンロード失敗 | ネットワーク問題 | プロキシ設定確認 |
| 権限エラー | ファイル権限 | `chown` でユーザー修正 |

### 2. ログレベル調整

```yaml
# デバッグモード
logging:
  level: "DEBUG"
  loggers:
    "src.core.download": "DEBUG"
    "src.core.api": "DEBUG"
```

### 3. パフォーマンス最適化

```yaml
# 高性能設定
download:
  max_concurrent: 8
  chunk_size: 16384
  
cache:
  max_size_mb: 2000
  
limits:
  max_memory_mb: 4096
```

## 移行ガイド

### v1からv2への移行

```bash
# データ移行ツール実行
python -m src.tools.migration \
    --from-version 1.0 \
    --to-version 2.0 \
    --data-dir /old/data \
    --output-dir /new/data \
    --backup

# 設定変換
python -m src.tools.config_converter \
    --input /old/config.json \
    --output /new/config.yml
```

## まとめ

Phase 7のデプロイメントにより、CivitAI Downloader v2は以下の環境で安全かつ効率的に運用できます：

✅ **Docker環境**: 簡単なコンテナベースデプロイメント
✅ **Kubernetes**: スケーラブルなクラスター運用
✅ **従来サーバー**: systemdベースの安定運用
✅ **セキュリティ**: 多層防御とアクセス制御
✅ **監視**: 包括的なメトリクスとアラート
✅ **バックアップ**: 自動バックアップと復旧

このガイドに従うことで、プロダクション環境での信頼性の高い運用が実現できます。