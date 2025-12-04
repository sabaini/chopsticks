#!/bin/bash
# Install s5cmd for S3 operations

set -e

INSTALL_DIR="${INSTALL_DIR:-$HOME/.local/bin}"
S5CMD_VERSION="${S5CMD_VERSION:-v2.2.2}"

echo "Installing s5cmd ${S5CMD_VERSION} to ${INSTALL_DIR}..."

# Detect OS and architecture
OS=$(uname -s)
ARCH=$(uname -m)

case $ARCH in
    x86_64)
        ARCH_SUFFIX="64bit"
        ;;
    aarch64|arm64)
        ARCH_SUFFIX="arm64"
        ;;
    *)
        echo "Unsupported architecture: $ARCH"
        exit 1
        ;;
esac

case $OS in
    Linux)
        OS_SUFFIX="Linux"
        ;;
    Darwin)
        OS_SUFFIX="macOS"
        ;;
    *)
        echo "Unsupported OS: $OS"
        exit 1
        ;;
esac

# Strip 'v' prefix from version for filenam
VERSION_NUM="${S5CMD_VERSION#v}"

DOWNLOAD_URL="https://github.com/peak/s5cmd/releases/download/${S5CMD_VERSION}/s5cmd_${VERSION_NUM}_${OS_SUFFIX}-${ARCH_SUFFIX}.tar.gz"

echo "Downloading from: ${DOWNLOAD_URL}"

# Create temp directory
TMP_DIR=$(mktemp -d)
trap "rm -rf ${TMP_DIR}" EXIT

# Download and extract, fail on http errors
curl -fL -o "${TMP_DIR}/s5cmd.tar.gz" "${DOWNLOAD_URL}"
tar -xzf "${TMP_DIR}/s5cmd.tar.gz" -C "${TMP_DIR}"

# Install
mkdir -p "${INSTALL_DIR}"
mv "${TMP_DIR}/s5cmd" "${INSTALL_DIR}/s5cmd"
chmod +x "${INSTALL_DIR}/s5cmd"

echo "s5cmd installed successfully to ${INSTALL_DIR}/s5cmd"
echo "Make sure ${INSTALL_DIR} is in your PATH"

# Test installation
"${INSTALL_DIR}/s5cmd" version
