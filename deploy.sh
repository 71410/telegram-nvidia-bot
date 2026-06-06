#!/bin/bash
# 在 Git Bash 中运行此脚本

cd "C:/Users/Admin/Desktop/tele_robot"

# 初始化 git
git init

# 添加所有文件（.env 已被 .gitignore 排除）
git add .

# 确认 .env 没被加入
git status

echo ""
echo "=== 请确认上面没有 .env 文件 ==="
echo "=== 按 Enter 继续提交 ==="
read

# 提交
git commit -m "Telegram AI Bot - NVIDIA NIM powered"

echo ""
echo "=== 接下来需要创建 GitHub 仓库 ==="
echo "1. 打开 https://github.com/new"
echo "2. Repository name 填: telegram-nvidia-bot"
echo "3. 不要勾选任何初始化选项（README, .gitignore 都不要）"
echo "4. 点 Create repository"
echo ""
echo "创建好后，复制仓库地址（类似 https://github.com/你的用户名/telegram-nvidia-bot.git）"
echo "粘贴到这里:"
read REPO_URL

# 推送到 GitHub
git remote add origin "$REPO_URL"
git branch -M main
git push -u origin main

echo ""
echo "=== 推送完成！==="
echo "现在去 Railway 连接这个 GitHub 仓库即可。"
