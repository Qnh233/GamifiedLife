# HTTPS 证书放置说明

Nginx 会读取以下文件路径：

- `/etc/nginx/certs/fullchain.pem`
- `/etc/nginx/certs/privkey.pem`

在宿主机上对应为：

- `deploy/certs/fullchain.pem`
- `deploy/certs/privkey.pem`

当你启用 `certbot` 自动申请后，会把 Let's Encrypt 证书自动同步到上述两个文件。

## 方式一：挂载正式证书（推荐）

把证书文件复制到 `deploy/certs` 目录并保持上述文件名。

## 方式二：本地自签名测试

```bash
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout deploy/certs/privkey.pem \
  -out deploy/certs/fullchain.pem \
  -subj "/CN=localhost"
```

> 自签名证书仅用于测试环境，浏览器会提示不受信任。

