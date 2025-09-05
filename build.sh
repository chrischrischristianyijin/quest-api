#!/bin/bash
# Render 部署构建脚本

echo "🚀 开始 Quest API 构建..."

# NLTK 数据目录已移除 - 不再需要 Sumy

# 更新 pip
echo "📦 更新 pip..."
pip install --upgrade pip

# 安装基础依赖
echo "📦 安装基础依赖..."
pip install -r requirements.txt

# NLTK 数据初始化已移除 - 不再需要 Sumy

echo "✅ 构建完成！"
