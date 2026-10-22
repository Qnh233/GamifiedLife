#!/bin/sh
set -eu

# 中文注释：无域名模式开关，0 表示禁用自动申请（容器保活等待）
if [ "${LE_CERTBOT_ENABLED:-1}" != "1" ]; then
  echo "[certbot] LE_CERTBOT_ENABLED=0，已关闭自动申请证书。"
  while true; do sleep 1h; done
fi

# 中文注释：必须提供主域名和邮箱，否则无法申请证书
if [ -z "${LE_DOMAIN:-}" ] || [ -z "${LE_EMAIL:-}" ]; then
  echo "[certbot] LE_DOMAIN 或 LE_EMAIL 未配置，跳过证书申请。"
  while true; do sleep 1h; done
fi

staging_arg=""
if [ "${LE_STAGING:-0}" = "1" ]; then
  staging_arg="--staging"
fi

# 中文注释：支持附加域名，格式如 www.example.com,api.example.com
domain_args="-d ${LE_DOMAIN}"
if [ -n "${LE_ADDITIONAL_DOMAINS:-}" ]; then
  for d in $(echo "${LE_ADDITIONAL_DOMAINS}" | tr ',' ' '); do
    domain_args="${domain_args} -d ${d}"
  done
fi

while true; do
  cmd="certbot certonly --webroot -w /var/www/certbot --email ${LE_EMAIL} --agree-tos --no-eff-email --rsa-key-size 4096 --cert-name gamifiedlife ${staging_arg} ${domain_args} --keep-until-expiring"
  echo "[certbot] running: ${cmd}"

  if sh -c "${cmd}"; then
    cp /etc/letsencrypt/live/gamifiedlife/fullchain.pem /etc/nginx/certs/fullchain.pem
    cp /etc/letsencrypt/live/gamifiedlife/privkey.pem /etc/nginx/certs/privkey.pem
    echo "[certbot] certificate synced to /etc/nginx/certs"
  else
    echo "[certbot] issue/renew failed, retry in 1 hour"
    sleep 1h
    continue
  fi

  # 中文注释：Let's Encrypt 建议每天最多尝试两次续期，这里每 12 小时检查一次
  sleep 12h
done

