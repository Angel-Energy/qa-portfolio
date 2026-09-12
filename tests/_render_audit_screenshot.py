"""
Генерирует чистый скриншот PowerShell-аудита через Pillow.
Выводит сам скрипт + результат выполнения 666 ссылок.
Без захвата окон, без ошибок.
"""
import subprocess
import os
from PIL import Image, ImageDraw, ImageFont

# Цвета PowerShell
BG = (1, 36, 86)          # #012456 — фон консоли
FG_GRAY = (192, 192, 192) # DarkGray
FG_GREEN = (106, 153, 85)  # Green
FG_RED = (244, 71, 71)     # Red
FG_CYAN = (78, 201, 176)   # Cyan
FG_YELLOW = (220, 220, 220) # White (for text on dark bg)
FG_DARKCYAN = (0, 128, 128)
FG_MAGENTA = (180, 0, 150)

COLORS_MAP = {
    'Cyan': FG_CYAN,
    'Yellow': (200, 200, 100),
    'Green': FG_GREEN,
    'Red': FG_RED,
    'Gray': FG_GRAY,
    'DarkGray': FG_GRAY,
    'White': FG_YELLOW,
    'Magenta': FG_MAGENTA,
    'DarkCyan': FG_DARKCYAN,
    'DarkRed': (180, 50, 50),
}

# PowerShell-скрипт аудита
PS_SCRIPT = r'''
# ============================================================
# ПОЛНЫЙ СКРИПТ ПРОВЕРКИ ССЫЛОК ИЗ GOOGLE ТАБЛИЦЫ
# ============================================================

Write-Host ""
Write-Host "==================================================" -ForegroundColor Cyan
Write-Host "   ПРОВЕРКА ССЫЛОК БЛОГА GetCourse                " -ForegroundColor Cyan
Write-Host "==================================================" -ForegroundColor Cyan
Write-Host ""

# ШАГ 1: Загрузка ссылок из Google Таблицы
Write-Host "Загружаем Google Таблицу..." -ForegroundColor Yellow

$csvUrl = "https://docs.google.com/spreadsheets/d/e/2PACX-1vTT26be3k3-KkD859vPjLPrTPlsoGaO-SgYUZ2VQxg6PT3Hd0cE37qRi4X4pJ2Jt5YeNWS2_bYg0Stn/pub?output=csv"

try {
    $csvData = Invoke-WebRequest -Uri $csvUrl -UseBasicParsing -ErrorAction Stop
    Write-Host "Таблица загружена: $($csvData.Content.Length) байт" -ForegroundColor Green
} catch {
    Write-Host "ОШИБКА загрузки таблицы: $($_.Exception.Message)" -ForegroundColor Red
    exit
}

# ШАГ 2: Извлечение ссылок
Write-Host "Извлекаем ссылки..." -ForegroundColor Yellow

$csv = $csvData.Content | ConvertFrom-Csv
$links = $csv | Where-Object { $_.link -like "*getcourse.ru*" } | Select-Object -ExpandProperty link -Unique

Write-Host "Найдено ссылок: $($links.Count)" -ForegroundColor Green

# ШАГ 3: Проверка ссылок
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

# ШАГ 4: Статистика
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

# ШАГ 5: Битые редиректы
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

# ШАГ 6: Ошибки 404
Write-Host "=== ОШИБКИ 404 ===" -ForegroundColor Red
$notFound = $results | Where-Object { $_.Status -eq 404 }
if ($notFound.Count -gt 0) { Write-Host "ВСЕГО 404: $($notFound.Count)" -ForegroundColor Red }
else { Write-Host "Ошибок 404 не найдено!" -ForegroundColor Green }
Write-Host ""
Write-Host "ГОТОВО!" -ForegroundColor Green
Write-Host ""
'''

# Запускаем PowerShell для получения чистого вывода (без ошибок рендеринга)
print("Запускаю PowerShell (аудит 666 ссылок)...")
proc = subprocess.Popen(
    ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", PS_SCRIPT],
    stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    encoding="utf-8", errors="replace",
)
stdout, stderr = proc.communicate(timeout=600)
print("PowerShell завершён.")

# Форматируем вывод для рендеринга
lines = []

# Заголовок
lines.append(("cmdlet", "=================================================="))
lines.append(("cmdlet", "   ПРОВЕРКА ССЫЛОК БЛОГА GetCourse                "))
lines.append(("cmdlet", "=================================================="))
lines.append(("", ""))

# Скрипт (показываем как введённый)
lines.append(("comment", "=== ВВЕДЁННЫЙ СКРИПТ ==="))
for line in PS_SCRIPT.strip().split("\n"):
    lines.append(("comment", line))
lines.append(("comment", "=== КОНЕЦ СКРИПТА ==="))
lines.append(("", ""))

# Вывод PowerShell
for line in stdout.strip().split("\n"):
    # Определяем цвет по содержимому строки
    if "Рабочие (200)" in line:
        lines.append(("green", line))
    elif "Редиректы" in line and "301" in line:
        lines.append(("yellow", line))
    elif "Битые редиректы" in line:
        lines.append(("red", line))
    elif "Не найдено (404)" in line:
        lines.append(("red", line))
    elif "Ошибки:" in line:
        lines.append(("magenta", line))
    elif "Найдено ссылок" in line:
        lines.append(("green", line))
    elif "Таблица загружена" in line:
        lines.append(("green", line))
    elif "ГОТОВО" in line:
        lines.append(("green", line))
    elif "БИТЫЕ РЕДИРЕКТЫ" in line:
        lines.append(("red", line))
    elif "НАЙДЕНО БИТЫХ" in line:
        lines.append(("red", line))
    elif "ОШИБКИ 404" in line:
        lines.append(("red", line))
    elif "=== " in line and "=====" in line:
        lines.append(("cyan", line))
    elif "[" in line and "]" in line and " | " in line:
        lines.append(("red", line))  # битые ссылки красным
    elif " -> " in line and "getcourse.ru/pl/blog" in line:
        lines.append(("red", line))
    else:
        lines.append(("gray", line))

# Рендеринг в PNG
char_w = 9
char_h = 18
font = ImageFont.truetype("C:/Windows/Fonts/consola.ttf", 14)

# Вычисляем размеры
max_line_len = max(len(line[1]) for line in lines) if lines else 1
img_w = max_line_len * char_w + 40
img_h = len(lines) * char_h + 30

img = Image.new("RGB", (img_w, img_h), BG)
draw = ImageDraw.Draw(img)

y = 15
for color_name, text in lines:
    fg = COLORS_MAP.get(color_name, FG_GRAY)
    draw.text((20, y), text, fill=fg, font=font)
    y += char_h

out_path = "screenshots/bug008-powershell-audit-666-links.png"
img.save(out_path, "PNG")
print(f"Скриншот сохранён: {out_path} ({img_w}x{img_h})")
print(f"Строк: {len(lines)}")
