#!/bin/bash

# 音声文字起こしアプリケーション起動スクリプト
echo "FastAPI + NVIDIA Parakeet ASR 文字起こしアプリケーションを起動します..."
echo "UvicornでFastAPIアプリを実行します"

# Uvicornを使用してアプリを起動（リロードモード有効）
uvicorn main:app --host 0.0.0.0 --port 5000 --reload