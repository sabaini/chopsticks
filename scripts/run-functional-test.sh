#!/bin/bash
set -e

# Functional test script for Chopsticks
# Can be run locally or in CI

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo "╔═══════════════════════════════════════════════════════════════════════╗"
echo "║            CHOPSTICKS FUNCTIONAL TEST                                  ║"
echo "╚═══════════════════════════════════════════════════════════════════════╝"
echo ""

# Default values
TEST_DURATION="${TEST_DURATION:-2m}"
OBJECT_SIZE="${LARGE_OBJECT_SIZE:-10}"
USERS="${TEST_USERS:-3}"
SPAWN_RATE="${TEST_SPAWN_RATE:-1}"

echo "Test Configuration:"
echo "  Duration:    ${TEST_DURATION}"
echo "  Object Size: ${OBJECT_SIZE}MB"
echo "  Users:       ${USERS}"
echo "  Spawn Rate:  ${SPAWN_RATE}/sec"
echo ""

# Check if MicroCeph is installed
if ! command -v microceph &> /dev/null; then
    echo "❌ MicroCeph not found. Please install it first."
    exit 1
fi

# Check if s5cmd is installed
if ! command -v s5cmd &> /dev/null; then
    echo "❌ s5cmd not found. Installing..."
    curl -L -o /tmp/s5cmd.tar.gz \
        https://github.com/peak/s5cmd/releases/download/v2.2.2/s5cmd_2.2.2_Linux-64bit.tar.gz
    sudo tar -xzf /tmp/s5cmd.tar.gz -C /usr/local/bin s5cmd
    sudo chmod +x /usr/local/bin/s5cmd
    rm /tmp/s5cmd.tar.gz
fi

# Check if RGW is enabled
echo "Checking MicroCeph RGW status..."
if ! sudo microceph status | grep -q "rgw"; then
    echo "⚠️  RGW not enabled. Please ensure MicroCeph is properly configured."
    exit 1
fi

# Get S3 credentials
echo "Setting up S3 credentials..."
if [ ! -f "/tmp/s3_user.json" ]; then
    sudo radosgw-admin user create \
        --uid=chopsticks-test \
        --display-name="Chopsticks Test" \
        --email=test@chopsticks.io > /tmp/s3_user.json || {
        # User might already exist, try to get info
        sudo radosgw-admin user info --uid=chopsticks-test > /tmp/s3_user.json
    }
fi

ACCESS_KEY=$(cat /tmp/s3_user.json | jq -r ".keys[0].access_key")
SECRET_KEY=$(cat /tmp/s3_user.json | jq -r ".keys[0].secret_key")

# Create S3 config
echo "Creating S3 configuration..."
mkdir -p "${PROJECT_ROOT}/config"
cat > "${PROJECT_ROOT}/config/s3_config.yaml" <<EOF
endpoint: http://127.0.0.1:80
access_key: ${ACCESS_KEY}
secret_key: ${SECRET_KEY}
bucket: chopsticks-test
region: default
driver: s5cmd
driver_config:
  s5cmd_path: /usr/local/bin/s5cmd
EOF

# Create bucket if it doesn't exist
echo "Creating S3 bucket..."
export S3_ENDPOINT_URL=http://127.0.0.1:80
export AWS_ACCESS_KEY_ID=${ACCESS_KEY}
export AWS_SECRET_ACCESS_KEY=${SECRET_KEY}
export AWS_REGION=default
s5cmd mb s3://chopsticks-test 2>/dev/null || echo "Bucket already exists"

# Run the test
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Starting Chopsticks test..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

cd "${PROJECT_ROOT}"
export LARGE_OBJECT_SIZE=${OBJECT_SIZE}

uv run locust \
    -f src/chopsticks/scenarios/s3_large_objects_with_metrics.py \
    --headless \
    --users ${USERS} \
    --spawn-rate ${SPAWN_RATE} \
    --run-time ${TEST_DURATION} \
    --html /tmp/chopsticks-test-report.html \
    --csv /tmp/chopsticks-test

# Validate results
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Validating test results..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

METRICS_FILE=$(ls /tmp/chopsticks_metrics/metrics_*.json | tail -1)

if [ ! -f "${METRICS_FILE}" ]; then
    echo "❌ Metrics file not found!"
    exit 1
fi

SUCCESS_RATE=$(cat ${METRICS_FILE} | jq -r '.summary.operations.success_rate')
TOTAL_OPS=$(cat ${METRICS_FILE} | jq -r '.summary.operations.total')
UPLOAD_COUNT=$(cat ${METRICS_FILE} | jq -r '.summary.by_operation.upload.count')
DOWNLOAD_COUNT=$(cat ${METRICS_FILE} | jq -r '.summary.by_operation.download.count')

echo "Test Results:"
echo "  Total Operations: ${TOTAL_OPS}"
echo "  Upload:           ${UPLOAD_COUNT}"
echo "  Download:         ${DOWNLOAD_COUNT}"
echo "  Success Rate:     ${SUCCESS_RATE}%"
echo ""

if [ "${SUCCESS_RATE}" != "100" ]; then
    echo "❌ FAILED: Success rate is not 100%!"
    exit 1
fi

if [ "${TOTAL_OPS}" -lt "10" ]; then
    echo "❌ FAILED: Too few operations completed (${TOTAL_OPS})"
    exit 1
fi

echo "✅ TEST PASSED!"
echo ""
echo "Reports generated:"
echo "  HTML:    /tmp/chopsticks-test-report.html"
echo "  Metrics: ${METRICS_FILE}"
echo ""
