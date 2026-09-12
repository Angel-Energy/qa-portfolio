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
    
    # Извлекаем тип бага из общей информации
    type_match = re.search(r'- \*\*Тип бага:\*\* (.+)', content)
    bug_type = type_match.group(1).strip() if type_match else ''

    # Секции "## Заголовок" -> текст до следующего "##": из них берём
    # окружение, предусловия, шаги и результаты для колонок формы.
    sections = _extract_sections(content)
    environment = _find_section(sections, 'Окружение')
    preconditions = _find_section(sections, 'Предусловия')
    steps = _find_section(sections, 'Шаги')
    expected_result = _find_section(sections, 'Ожидаемый результат')
    actual_result = _find_section(sections, 'Фактический результат')
    user_impact = _find_section(sections, 'Влияние на пользователя')
    root_cause = _find_section(sections, 'Предположение о причине')
    recommendations = _find_section(sections, 'Рекомендации')

    return {
        'key': bug_key,
        'title': title,
        'project': project,
        'severity': severity,
        'priority': priority,
        'status': status,
        'date': date,
        'type': bug_type,
        'environment': environment,
        'preconditions': preconditions,
        'steps': steps,
        'expected_result': expected_result,
        'actual_result': actual_result,
        'user_impact': user_impact,
        'root_cause': root_cause,
        'recommendations': recommendations,
    }


def _extract_sections(content):
    """Разбирает markdown на {'Заголовок секции': 'тело'} по '## '."""
    sections = {}
    current = None
    buf = []
    for line in content.splitlines():
        if line.startswith('## '):
            if current is not None:
                sections[current] = '\n'.join(buf).strip()
            current = line[3:].strip()
            buf = []
        elif current is not None:
            buf.append(line)
    if current is not None:
        sections[current] = '\n'.join(buf).strip()
    return sections


def _find_section(sections, prefix):
    """Тело секции, чей заголовок начинается с prefix (без регистра)."""
    for title, body in sections.items():
        if title.lower().startswith(prefix.lower()):
            return body
    return ''


def import_bugs():
    """Импортирует все баги из markdown файлов в базу данных.

    Новые ключи вставляются, существующие — обновляются из markdown:
    источник истины по содержимому бага — репорт в bug-reports/.
    """
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
            url TEXT DEFAULT '',
            attachments TEXT DEFAULT '',
            type TEXT DEFAULT '',
            component TEXT DEFAULT '',
            assignee TEXT DEFAULT '',
            reporter TEXT DEFAULT '',
            environment TEXT DEFAULT '',
            preconditions TEXT DEFAULT '',
            steps TEXT DEFAULT '',
            expected_result TEXT DEFAULT '',
            actual_result TEXT DEFAULT '',
            user_impact TEXT DEFAULT '',
            root_cause TEXT DEFAULT '',
            recommendations TEXT DEFAULT '',
            labels TEXT DEFAULT '',
            comments TEXT DEFAULT '',
            created_at TEXT DEFAULT (datetime('now', 'localtime')),
            updated_at TEXT DEFAULT (datetime('now', 'localtime'))
        )
    """)
    conn.commit()

    # Миграция старых баз: таблица могла быть создана прошлой версией
    # скрипта без этих столбцов. Дополняем через ALTER TABLE.
    columns = [row[1] for row in conn.execute("PRAGMA table_info(bugs)").fetchall()]
    required_columns = {
        "url": "TEXT DEFAULT ''",
        "attachments": "TEXT DEFAULT ''",
        "type": "TEXT DEFAULT ''",
        "component": "TEXT DEFAULT ''",
        "assignee": "TEXT DEFAULT ''",
        "reporter": "TEXT DEFAULT ''",
        "environment": "TEXT DEFAULT ''",
        "preconditions": "TEXT DEFAULT ''",
        "steps": "TEXT DEFAULT ''",
        "expected_result": "TEXT DEFAULT ''",
        "actual_result": "TEXT DEFAULT ''",
        "user_impact": "TEXT DEFAULT ''",
        "root_cause": "TEXT DEFAULT ''",
        "recommendations": "TEXT DEFAULT ''",
        "labels": "TEXT DEFAULT ''",
        "comments": "TEXT DEFAULT ''",
    }
    for column, ddl in required_columns.items():
        if column not in columns:
            conn.execute(f"ALTER TABLE bugs ADD COLUMN {column} {ddl}")
    conn.commit()

    # Читаем все markdown файлы
    bugs_dir = Path(BUGS_DIR)
    if not bugs_dir.exists():
        print(f"Директория {BUGS_DIR} не найдена!")
        conn.close()
        return

    md_files = sorted(bugs_dir.glob('BUG-*.md'))
    print(f"Найдено {len(md_files)} файлов багов")

    existing_keys = {row[0] for row in conn.execute("SELECT key FROM bugs")}

    for md_file in md_files:
        try:
            bug = parse_bug_file(md_file)
            if bug['key'] in existing_keys:
                conn.execute("""
                    UPDATE bugs SET
                        title=?, project=?, severity=?, priority=?, status=?, date=?,
                        type=?, environment=?, preconditions=?, steps=?,
                        expected_result=?, actual_result=?, user_impact=?,
                        root_cause=?, recommendations=?, updated_at=datetime('now', 'localtime')
                    WHERE key=?
                """, (
                    bug['title'], bug['project'], bug['severity'], bug['priority'],
                    bug['status'], bug['date'], bug['type'], bug['environment'],
                    bug['preconditions'], bug['steps'], bug['expected_result'],
                    bug['actual_result'], bug['user_impact'], bug['root_cause'],
                    bug['recommendations'], bug['key'],
                ))
                print(f"  ↻ {bug['key']}: обновлён из markdown")
            else:
                conn.execute("""
                    INSERT INTO bugs (key, title, project, severity, priority, status, date,
                                      type, environment, preconditions, steps,
                                      expected_result, actual_result, user_impact,
                                      root_cause, recommendations)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    bug['key'], bug['title'], bug['project'], bug['severity'],
                    bug['priority'], bug['status'], bug['date'], bug['type'],
                    bug['environment'], bug['preconditions'], bug['steps'],
                    bug['expected_result'], bug['actual_result'], bug['user_impact'],
                    bug['root_cause'], bug['recommendations'],
                ))
                print(f"  ✓ {bug['key']}: {bug['title'][:60]}...")
        except Exception as e:
            print(f"  ✗ Ошибка парсинга {md_file.name}: {e}")

    conn.commit()
    total = conn.execute("SELECT COUNT(*) FROM bugs").fetchone()[0]
    print(f"\nИмпорт завершён! Всего в базе: {total} багов")
    conn.close()


if __name__ == '__main__':
    import_bugs()
