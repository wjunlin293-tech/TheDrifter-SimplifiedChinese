@echo off
chcp 65001 >nul
title The Drifter 简体中文汉化 - 安装
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0install.ps1"
