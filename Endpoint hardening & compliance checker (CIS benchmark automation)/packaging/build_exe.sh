#!/usr/bin/env bash
# Build HardeningChecker.exe (run from project root: bash packaging/build_exe.sh)
set -e
cd "$(dirname "$0")/.."
pyinstaller --clean packaging/hardening-checker.spec
echo
echo "Output: dist/HardeningChecker.exe"
