"""
Создаёт ПОЛНЫЙ скриншот консоли PowerShell (видно и скрипт, и вывод).
1. PowerShell выводит сам скрипт (Get-Content себя) + выполняет аудит 666 ссылок.
2. В конце сохраняет ВЕСЬ буфер консоли (включая прокрученное) в JSON.
3. Python рендерит буфер в PNG через Pillow.
"""
import subprocess
import time
import os
import json
from PIL import Image, ImageDraw, ImageFont

# PowerShell-скрипт: выводит себя + выполняет аудит + сохраняет буфер
ps_script = r'''
# Увеличиваем буфер консоли, чтобы влезло всё
try {
    $Host.UI.RawUI.BufferSize = New-Object Management.Automation.Host.Size(170, 220)
    $Host.UI.RawUI.WindowSize = New-Object Management.Automation.Host.Size(170, 50)
} catch {}

# === Выводим сам скрипт (как будто введён пользователем) ===
Write-Host "=== ВВЕДЁННЫЙ СКРИПТ ===" -ForegroundColor Cyan
Get-Content $MyInvocation.MyCommand.Path | ForEach-Object { Write-Host $_ -ForegroundColor DarkGray }
Write-Host "=== КОНЕЦ СКРИПТА — НАЧАЛО ВЫПОЛНЕНИЯ ===" -ForegroundColor Cyan
Write-Host ""

# === Тело скрипта (аудит) ===
Write-Host "==================================================" -ForegroundColor Cyan
Write-Host "   ПРОВЕРКА ССЫЛОК БЛОГА GetCourse                " -ForegroundColor Cyan
Write-Host "==================================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "Загружаем Google Таблицу..." -ForegroundColor Yellow
$csvUrl = "https://docs.google.com/spreadsheets/d/e/2PACX-1vTT26be3k3-KkD859vPjLPrTPlsoGaO-SgYUZ2VQxg6PT3Hd0cE37qRi4X4pJ2Jt5YeNWS2_bYg0Stn/pub?output=csv"

try {
    $csvData = Invoke-WebRequest -Uri $csvUrl -UseBasicParsing -ErrorAction Stop
    Write-Host "Таблица загружена: $($csvData.Content.Length) байт" -ForegroundColor Green
} catch {
    Write-Host "ОШИБКА загрузки таблицы: $($_.Exception.Message)" -ForegroundColor Red
    exit
}

Write-Host "Извлекаем ссылки..." -ForegroundColor Yellow
$csv = $csvData.Content | ConvertFrom-Csv
$links = $csv | Where-Object { $_.link -like "*getcourse.ru*" } | Select-Object -ExpandProperty link -Unique
Write-Host "Найдено ссылок: $($links.Count)" -ForegroundColor Green

Write-Host ""
Write-Host "===============================================" -ForegroundColor Cyan
Write-Host "  ПРОВЕРКА ССЫЛОК" -ForegroundColor Cyan
Write-Host "===============================================" -ForegroundColor Cyan
Write-Host "Начинаем проверку $($links.Count) ссылок..." -ForegroundColor White
Write-Host ""

$results = @()
$counter = 0
$stats = @{ Working = 0; Redirects = 0; BrokenRedirects = 0; NotFound = 0; Errors = 0 }

foreach ($url in $links) {
    $counter++
    try {
        $response = Invoke-WebRequest -Uri $url -MaximumRedirection 0 -UseBasicParsing -ErrorAction SilentlyContinue
        $status = [int]$response.StatusCode
        $location = if ($response.Headers.Location) { $response.Headers.Location } else { "" }
    }
    catch {
        if ($_.Exception.Response) {
            $status = [int]$_.Exception.Response.StatusCode
            $location = if ($_.Exception.Response.Headers.Location) { $_.Exception.Response.Headers.Location.ToString() } else { "" }
        } else {
            $status = "ERROR"
            $location = $_.Exception.Message
        }
    }

    $isBroken = $false
    $color = "Gray"
    switch ($status) {
        200 { $stats.Working++; $color = "Green" }
        301 {
            if ($location -eq "https://getcourse.ru/pl/blog" -or $location -eq "https://getcourse.ru/") {
                $stats.BrokenRedirects++; $isBroken = $true; $color = "Red"
            } else { $stats.Redirects++; $color = "Yellow" }
        }
        302 { $stats.Redirects++; $color = "Yellow" }
        404 { $stats.NotFound++; $isBroken = $true; $color = "Red" }
        default { $stats.Errors++; $color = "Magenta" }
    }

    if ($counter % 50 -eq 0 -or $isBroken) {
        Write-Host "[$counter/$($links.Count)] $status | $url" -ForegroundColor $color
        if ($location) { Write-Host "               -> $location" -ForegroundColor DarkGray }
    }

    $results += [PSCustomObject]@{ URL=$url; Status=$status; Location=$location; IsBroken=$isBroken }
    Start-Sleep -Milliseconds 100
}

Write-Host ""
Write-Host "===============================================" -ForegroundColor Cyan
Write-Host "  СТАТИСТИКА" -ForegroundColor Cyan
Write-Host "===============================================" -ForegroundColor Cyan
Write-Host "Рабочие (200):        $($stats.Working)" -ForegroundColor Green
Write-Host "Редиректы (301/302):  $($stats.Redirects)" -ForegroundColor Yellow
Write-Host "Битые редиректы:      $($stats.BrokenRedirects)" -ForegroundColor Red
Write-Host "Не найдено (404):     $($stats.NotFound)" -ForegroundColor Red
Write-Host "Ошибки:               $($stats.Errors)" -ForegroundColor Magenta
Write-Host ""

Write-Host "=== БИТЫЕ РЕДИРЕКТЫ (301 -> /pl/blog или /) ===" -ForegroundColor Red
$brokenRedirects = $results | Where-Object {
    $_.Status -eq 301 -and ($_.Location -eq "https://getcourse.ru/pl/blog" -or $_.Location -eq "https://getcourse.ru/")
}
if ($brokenRedirects.Count -gt 0) {
    $brokenRedirects | Format-Table URL, Status, Location -AutoSize
    Write-Host "НАЙДЕНО БИТЫХ РЕДИРЕКТОВ: $($brokenRedirects.Count)" -ForegroundColor Red
} else {
    Write-Host "Битых редиректов не найдено!" -ForegroundColor Green
}
Write-Host ""

Write-Host "=== ОШИБКИ 404 ===" -ForegroundColor Red
$notFound = $results | Where-Object { $_.Status -eq 404 }
if ($notFound.Count -gt 0) { Write-Host "ВСЕГО 404: $($notFound.Count)" -ForegroundColor Red }
else { Write-Host "Ошибок 404 не найдено!" -ForegroundColor Green }
Write-Host ""
Write-Host "ГОТОВО!" -ForegroundColor Green
Write-Host ""

# === Сохраняем ВЕСЬ буфер консоли в JSON ===
$bs = $Host.UI.RawUI.BufferSize
$rect = New-Object Management.Automation.Host.Rectangle 0, 0, ($bs.Width - 1), ($bs.Height - 1)
$buf = $Host.UI.RawUI.GetBufferContents($rect)
$h = $buf.GetLength(0); $w = $buf.GetLength(1)
$rows = @()
for ($r = 0; $r -lt $h; $r++) {
    $spans = @()
    $lastFg = $null; $lastBg = $null; $text = ""
    for ($c = 0; $c -lt $w; $c++) {
        $cell = $buf[$r, $c]
        if ($cell.ForegroundColor -ne $lastFg -or $cell.BackgroundColor -ne $lastBg) {
            if ($text -ne "") { $spans += @{ Fg = [string]$lastFg; Bg = [string]$lastBg; T = $text } }
            $text = ""; $lastFg = $cell.ForegroundColor; $lastBg = $cell.BackgroundColor
        }
        $text += $cell.Character
    }
    if ($text -ne "") { $spans += @{ Fg = [string]$lastFg; Bg = [string]$lastBg; T = $text } }
    $rows += @{ Spans = $spans }
}
$obj = @{ Width = $w; Height = $h; Rows = $rows }
$obj | ConvertTo-Json -Depth 6 | Out-File "$env:TEMP\gc_console_buffer.json" -Encoding UTF8
Write-Host "Буфер сохранён: $env:TEMP\gc_console_buffer.json ($h строк)" -ForegroundColor Green
'''

# Маппинг цветов ConsoleColor → RGB
COLORS = {
    'Black': (0, 0, 0),
    'DarkBlue': (0, 0, 128),
    'DarkGreen': (0, 128, 0),
    'DarkCyan': (0, 128, 128),
    'DarkRed': (128, 0, 0),
    'DarkMagenta': (128, 0, 128),
    'DarkYellow': (128, 128, 0),
    'Gray': (192, 192, 192),
    'DarkGray': (128, 128, 128),
    'Blue': (0, 0, 255),
    'Green': (0, 255, 0),
    'Cyan': (0, 255, 255),
    'Red': (255, 0, 0),
    'Magenta': (255, 0, 255),
    'Yellow': (255, 255, 0),
    'White': (255, 255, 255),
}
BG_DEFAULT = (1, 36, 86)  # #012456 — фон PowerShell

# Сохраняем PS-скрипт
script_path = os.path.join(os.environ["TEMP"], "_bug008_audit_full.ps1")
with open(script_path, "w", encoding="utf-8-sig") as f:
    f.write(ps_script)

print("Запускаю PowerShell (аудит 666 ссылок, ~5 минут)...")
proc = subprocess.Popen(
    ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", script_path],
    stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    text=True, encoding="utf-8", errors="replace",
)

# Ждём завершения (666 ссылок × ~0.5с запрос + 0.1с пауза ≈ 400с + GetBufferContents)
stdout, stderr = proc.communicate(timeout=900)
print("PowerShell завершён.")
if stderr.strip():
    print("STDERR:", stderr[:500])

buffer_json = os.path.join(os.environ["TEMP"], "gc_console_buffer.json")
if not os.path.exists(buffer_json):
    print("ОШИБКА: буфер не сохранён!")
    exit(1)

print("Рендерю буфер в PNG...")
with open(buffer_json, encoding="utf-8-sig") as f:
    data = json.load(f)

w = data["Width"]
h = data["Height"]
rows = data["Rows"]

char_w = 9
char_h = 18
font = ImageFont.truetype("C:/Windows/Fonts/consola.ttf", 14)

img_w = w * char_w
img_h = h * char_h
img = Image.new("RGB", (img_w, img_h), BG_DEFAULT)
draw = ImageDraw.Draw(img)

for r_idx, row in enumerate(rows):
    spans = row["Spans"]
    x = 0
    y = r_idx * char_h
    for span in spans:
        text = span["T"]
        fg = COLORS.get(span["Fg"], (255, 255, 255))
        bg = COLORS.get(span["Bg"], BG_DEFAULT)
        # Заливаем фон для этой группы символов
        tw = len(text) * char_w
        draw.rectangle([x, y, x + tw, y + char_h], fill=bg)
        # Рисуем текст
        draw.text((x, y - 2), text, fill=fg, font=font)
        x += tw

out_path = "screenshots/bug008-powershell-audit-666-links.png"
img.save(out_path)
print(f"Скриншот сохранён: {out_path} ({img_w}x{img_h})")

# Чистим
os.remove(script_path)
os.remove(buffer_json)
print("Готово!")
