@echo off
chcp 65001 > nul
title Agent Security Gate x402 - X Auto Promo Bot
echo ========================================================
echo   Agent Security Gate x402 - X (Twitter) Promo Bot
echo ========================================================

cd /d "%~dp0"

python x_promo_bot.py %*

pause
