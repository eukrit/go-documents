#!/usr/bin/env bash
# Setup Pub/Sub topic + push subscription for submission events.
# Idempotent — safe to re-run.
set -euo pipefail

PROJECT="${PROJECT:-ai-agents-go}"
REGION="${REGION:-asia-southeast1}"
TOPIC="${TOPIC:-submission-events}"
SUB="${SUB:-submission-events-slack}"
SERVICE="${SERVICE:-go-documents}"
SA="${SA:-claude@${PROJECT}.iam.gserviceaccount.com}"

echo "Project: $PROJECT  Topic: $TOPIC  Sub: $SUB  Service: $SERVICE"

gcloud config set project "$PROJECT" >/dev/null

# 1. Create topic
if ! gcloud pubsub topics describe "$TOPIC" >/dev/null 2>&1; then
  echo "Creating topic $TOPIC..."
  gcloud pubsub topics create "$TOPIC"
else
  echo "Topic $TOPIC exists."
fi

# 2. Resolve Cloud Run URL for the push endpoint
RUN_URL="$(gcloud run services describe "$SERVICE" --region "$REGION" \
  --format='value(status.url)' 2>/dev/null || true)"

if [ -z "$RUN_URL" ]; then
  echo "WARN: Cloud Run service $SERVICE not deployed yet — subscription will not be created."
  echo "Re-run this script after the first successful deploy."
  exit 0
fi
PUSH_ENDPOINT="${RUN_URL%/}/pubsub/push"
echo "Push endpoint: $PUSH_ENDPOINT"

# 3. Allow Pub/Sub to invoke Cloud Run
gcloud run services add-iam-policy-binding "$SERVICE" \
  --region "$REGION" \
  --member="serviceAccount:$SA" \
  --role="roles/run.invoker" \
  --quiet || true

# 4. Create / update push subscription
if ! gcloud pubsub subscriptions describe "$SUB" >/dev/null 2>&1; then
  echo "Creating push subscription $SUB..."
  gcloud pubsub subscriptions create "$SUB" \
    --topic "$TOPIC" \
    --push-endpoint="$PUSH_ENDPOINT" \
    --push-auth-service-account="$SA" \
    --ack-deadline=60 \
    --message-retention-duration=1h \
    --min-retry-delay=10s \
    --max-retry-delay=600s
else
  echo "Updating push endpoint on existing subscription $SUB..."
  gcloud pubsub subscriptions update "$SUB" \
    --push-endpoint="$PUSH_ENDPOINT" \
    --push-auth-service-account="$SA"
fi

echo "Done."
