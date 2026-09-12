"""Скрипт для импорта багов из markdown файлов в базу данных."""
import sqlite3
import os
import re
from pathlib import Path

DB_PATH = os.path.join(os.path.dirname(__file__), 'bug_reports.db')
# import_bugs.py лежит в tools/bug-reporter/, bug-reports/ — в корне репозитория
BUGS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    'bug-reports',
)


def parse_bug_file(filepath):
    """Парсит markdown файл баг-репорта."""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Извлекаем ключ из имени файла
    filename = os.path.basename(filepath)
    key_match = re.match(r'(BUG-\d+)', filename)
    bug_key = key_match.group(1) if key_match else 'BUG-???'
    
    # Извлекаем заголовок
    title_match = re.search(r'# (BUG-\d+): (.+)', content)
    title = title_match.group(2).strip() if title_match else 'Без заголовка'
    
    # Извлекаем проект
    project_match = re.search(r'- \*\*Проект:\*\* (.+)', content)
    project = project_match.group(1).strip() if project_match else ''
    
    # Извлекаем серьёзность
    severity_match = re.search(r'- \*\*Серьёзность:\*\* (.+)', content)
    severity_raw = severity_match.group(1).strip() if severity_match else 'Major'
    severity_map = {
        'Blocker': 'Blocker',
        'Critical': 'Critical',
        'Major': 'Major',
        'High': 'High',
        'Medium': 'Medium',
        'Low': 'Low',
        'Lowest': 'Lowest',
        'Minor': 'Minor',
        'Trivial': 'Trivial'
    }
    severity = severity_map.get(severity_raw, 'Major')
    
    # Извлекаем приоритет
    priority_match = re.search(r'- \*\*Приоритет:\*\* (.+)', content)
    priority_raw = priority_match.group(1).strip() if priority_match else 'Medium'
    priority = priority_raw  # Оставляем как есть
    
    # Извлекаем статус
    status_match = re.search(r'- \*\*Статус:\*\* (.+)', content)
    status_raw = status_match.group(1).strip() if status_match else 'New'
    # Убираем лишние данные после статуса
    status_raw = status_raw.split()[0] if status_raw else 'New'
    status_map = {
        'Reported': 'New',
        'In Progress': 'In Progress',
        'Resolved': 'Resolved',
        'Closed': 'Closed',
        'new': 'New',
        'in progress': 'In Progress',
        'resolved': 'Resolved',
        'closed': 'Closed'
    }
    status = status_map.get(status_raw, 'New')
    
    # Извлекаем дату
    date_match = re.search(r'- \*\*Дата обнаружения:\*\* (\d{2}\.\d{2}\.\d{4})', content)
    if date_match:
        date_str = date_match.group(1)
        # Конвертируем DD.MM.YYYY -> YYYY-MM-DD
        parts = date_str.split('.')
        date = f"{parts[2]}-{parts[1]}-{parts[0]}"
    else:
        date = '2026-01-01'
    
    return {
        'key': bug_key,
        'title': title,
        'project': project,
        'severity': severity,
        'priority': priority,
        'status': status,
        'date': date
    }


def import_bugs():
    """Импортирует все баги из markdown файлов в базу данных."""
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS bugs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            key TEXT UNIQUE NOT NULL,
            title TEXT NOT NULL,
            project TEXT DEFAULT '',
            severity TEXT DEFAULT 'Major',
            priority TEXT DEFAULT 'Medium',
            status TEXT DEFAULT 'New',
            date TEXT DEFAULT (date('now')),
            created_at TEXT DEFAULT (datetime('now', 'localtime')),
            updated_at TEXT DEFAULT (datetime('now', 'localtime'))
        )
    """)
    conn.commit()
    
    # Проверяем, есть ли уже баги
    existing = conn.execute("SELECT COUNT(*) FROM bugs").fetchone()[0]
    if existing > 0:
        print(f"В базе уже есть {existing} багов. Пропускаем импорт.")
        conn.close()
        return
    
    # Читаем все markdown файлы
    bugs_dir = Path(BUGS_DIR)
    if not bugs_dir.exists():
        print(f"Директория {BUGS_DIR} не найдена!")
        conn.close()
        return
    
    md_files = sorted(bugs_dir.glob('BUG-*.md'))
    print(f"Найдено {len(md_files)} файлов багов")
    
    for md_file in md_files:
        try:
            bug = parse_bug_file(md_file)
            try:
                conn.execute("""
                    INSERT INTO bugs (key, title, project, severity, priority, status, date)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    bug['key'], bug['title'], bug['project'],
                    bug['severity'], bug['priority'], bug['status'], bug['date']
                ))
                print(f"  ✓ {bug['key']}: {bug['title'][:60]}...")
            except sqlite3.IntegrityError:
                print(f"  ⊘ {bug['key']} уже существует")
        except Exception as e:
            print(f"  ✗ Ошибка парсинга {md_file.name}: {e}")
    
    conn.commit()
    total = conn.execute("SELECT COUNT(*) FROM bugs").fetchone()[0]
    print(f"\nИмпорт завершён! Всего в базе: {total} багов")
    conn.close()


if __name__ == '__main__':
    import_bugs()
