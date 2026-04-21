#!/bin/bash
set -euo pipefail

export RESOURCE_GROUP="FriskyGhost-Production"
export CONTAINERAPPS_ENVIRONMENT="friskyghost-serverless-env"
export ACR_NAME="ca8360d6c250acr"
export IMAGE="ca8360d6c250acr.azurecr.io/clipflow-bot:latest"

echo "Log in to ACR"
ACR_PWD=$(/opt/homebrew/bin/az acr credential show -n $ACR_NAME --query 'passwords[0].value' -o tsv)

echo "Deleting old failed container app..."
/opt/homebrew/bin/az containerapp delete -n clipflow-bot -g $RESOURCE_GROUP -y || true

source .doppler.env

echo "Creating container app..."
/opt/homebrew/bin/az containerapp create \
  -n clipflow-bot \
  -g $RESOURCE_GROUP \
  --environment $CONTAINERAPPS_ENVIRONMENT \
  --image $IMAGE \
  --registry-server ca8360d6c250acr.azurecr.io \
  --registry-username ca8360d6c250acr \
  --registry-password $ACR_PWD \
  --cpu 1.0 \
  --memory 2.0Gi \
  --secrets "telegram-token-secret=$TELEGRAM_BOT_TOKEN" \
  --env-vars "TELEGRAM_BOT_TOKEN=secretref:telegram-token-secret" \
             "ENABLED_PROVIDERS=direct,youtube,tiktok,instagram,x" \
             "APP_ENV=production" \
             "DOPPLER_PROJECT=new-doppler-project" \
             "DOPPLER_CONFIG=dev_personal"
