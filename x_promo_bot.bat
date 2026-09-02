@echo off
chcp 65001 > nul
title Agent Security Gate x402 - X Auto Promo Bot
echo ========================================================
echo   Agent Security Gate x402 - X (Twitter) Promo Bot
echo ========================================================

if exist .venv\Scripts\python.exe (
    .venv\Scripts\python.exe x_promo_bot.py
) else (
    python x_promo_bot.py
)

pause
