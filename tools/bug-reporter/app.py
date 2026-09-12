"""
Bug Reporter — Flask + SQLite
Полностью переработано по React-компоненту
"""
import sqlite3
import os
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, send_from_directory

app = Flask(__name__, static_folder='static', static_url_path='/static')
app.secret_key = "bug-reporter-secret-key-2026"

DB_PATH = os.path.join(os.path.dirname(__file__), 'bug_reports.db')

# app.py лежит в tools/bug-reporter/, корень репозитория — на два уровня выше
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    # Проверяем, существует ли таблица
    table_exists = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='bugs'"
    ).fetchone()
    
    # Проверяем, есть ли поле url
    columns = [row[1] for row in conn.execute("PRAGMA table_info(bugs)").fetchall()]
    
    if not table_exists:
        conn.execute("""
            CREATE TABLE bugs (
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
        # Список колонок вычислен ДО создания таблицы (для свежей базы
        # он был пуст) — пересчитываем, иначе ALTER ниже упадёт с
        # "duplicate column name".
        columns = [row[1] for row in conn.execute("PRAGMA table_info(bugs)").fetchall()]

    if 'url' not in columns:
        conn.execute("ALTER TABLE bugs ADD COLUMN url TEXT DEFAULT ''")
        conn.commit()

    if 'attachments' not in columns:
        conn.execute("ALTER TABLE bugs ADD COLUMN attachments TEXT DEFAULT ''")
        conn.commit()

    # Поля формы new_bug/edit_bug: полный отчёт хранится в БД, а не
    # только уходит в Telegram-уведомление. Существующие базы
    # мигрируются по одному столбцу через ALTER TABLE.
    form_columns = {
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
    for column, ddl in form_columns.items():
        if column not in columns:
            conn.execute(f"ALTER TABLE bugs ADD COLUMN {column} {ddl}")
    conn.commit()
    
    # Создаём таблицу комментариев если нет
    table_exists = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='comments'"
    ).fetchone()
    
    if not table_exists:
        conn.execute("""
            CREATE TABLE comments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                bug_id INTEGER NOT NULL,
                author TEXT DEFAULT 'QA Engineer',
                text TEXT NOT NULL,
                created_at TEXT DEFAULT (datetime('now', 'localtime')),
                FOREIGN KEY (bug_id) REFERENCES bugs(id)
            )
        """)
        conn.commit()
    
    conn.close()


def migrate_bugs():
    """Тестовые баги больше не загружаются автоматически."""
    pass


# ─── Routes ────────────────────────────────────────

@app.route('/')
def index():
    conn = get_db()
    bugs = conn.execute("""
        SELECT id, key, title, project, severity, priority, status, date, url, attachments, created_at
        FROM bugs ORDER BY id DESC
    """).fetchall()
    conn.close()

    total = len(bugs)
    open_count = sum(1 for b in bugs if b["status"] == "New")
    in_progress = sum(1 for b in bugs if b["status"] == "In Progress")
    resolved = sum(1 for b in bugs if b["status"] in ("Resolved", "Closed"))
    critical = sum(1 for b in bugs if b["severity"] in ("Blocker", "Critical"))

    # Загружаем список скриншотов из папки
    import glob
    screenshot_dir = os.path.join(REPO_ROOT, 'screenshots')
    all_screenshots = {}
    if os.path.isdir(screenshot_dir):
        for f in os.listdir(screenshot_dir):
            for key in ['BUG-001', 'BUG-002', 'BUG-003', 'BUG-004', 'BUG-005', 'BUG-006', 'BUG-007', 'BUG-008']:
                if f.startswith(key.lower()) or f.startswith(key.upper()):
                    if key not in all_screenshots:
                        all_screenshots[key] = []
                    all_screenshots[key].append(f)
    
    # Добавляем скриншоты к багам
    bugs_with_screenshots = []
    for bug in bugs:
        bug_dict = dict(bug)
        key_lower = bug['key'].lower()  # 'bug-001', 'bug-002', etc.
        key_nodash = key_lower.replace('-', '')  # 'bug001', 'bug002', etc.
        bug_dict['screenshots'] = []
        if os.path.isdir(screenshot_dir):
            for f in os.listdir(screenshot_dir):
                fn_lower = f.lower()
                if fn_lower.startswith(key_lower) or fn_lower.startswith(key_nodash):
                    bug_dict['screenshots'].append(f)
        bugs_with_screenshots.append(bug_dict)
    bugs = bugs_with_screenshots

    stats = {
        "total": total,
        "open": open_count,
        "in_progress": in_progress,
        "resolved": resolved,
        "critical": critical
    }
    return render_template('index.html', bugs=bugs, stats=stats)


@app.route('/bug/<int:bug_id>')
def bug_detail(bug_id):
    conn = get_db()
    bug = conn.execute("SELECT * FROM bugs WHERE id = ?", (bug_id,)).fetchone()
    conn.close()
    if bug is None:
        flash('Баг не найден', 'error')
        return redirect(url_for('index'))
    
    bug = dict(bug)
    
    # Загружаем предыдущий и следующий баги для навигации
    prev_bug = conn.execute("SELECT id, key, title FROM bugs WHERE id < ? ORDER BY id DESC LIMIT 1", (bug_id,)).fetchone()
    next_bug = conn.execute("SELECT id, key, title FROM bugs WHERE id > ? ORDER BY id ASC LIMIT 1", (bug_id,)).fetchone()
    bug['prev_bug'] = dict(prev_bug) if prev_bug else None
    bug['next_bug'] = dict(next_bug) if next_bug else None
    
    # Загружаем комментарии
    comments = conn.execute("SELECT * FROM comments WHERE bug_id = ? ORDER BY created_at ASC", (bug_id,)).fetchall()
    bug['comments'] = [dict(c) for c in comments]
    conn.close()
    
    # Загружаем скриншоты для этого бага
    import glob
    screenshot_dir = os.path.join(REPO_ROOT, 'screenshots')
    bug['screenshots'] = []
    if os.path.isdir(screenshot_dir):
        key_lower = bug['key'].lower()  # 'bug-001', 'bug-002', etc.
        key_nodash = key_lower.replace('-', '')  # 'bug001', 'bug002', etc.
        for f in os.listdir(screenshot_dir):
            fn_lower = f.lower()
            if fn_lower.startswith(key_lower) or fn_lower.startswith(key_nodash):
                bug['screenshots'].append(f)
    
    # Загружаем описание из markdown-файла
    import re
    bug_reports_dir = os.path.join(REPO_ROOT, 'bug-reports')
    bug['description_html'] = ''
    if os.path.isdir(bug_reports_dir):
        # Ищем файл по префиксу ключа бага (BUG-001, BUG-002, и т.д.)
        key_prefix = bug['key'] + '-'
        md_files = [f for f in os.listdir(bug_reports_dir) if f.startswith(key_prefix) and f.endswith('.md')]
        if md_files:
            md_filename = sorted(md_files)[0]  # Берём первый найденный
            md_path = os.path.join(bug_reports_dir, md_filename)
            with open(md_path, 'r', encoding='utf-8') as f:
                md_text = f.read()
            # Конвертируем markdown в HTML
            html = md_text
            
            # 1. СНАЧАЛА метаданные (до URL, чтобы regex мог найти **label:** value)
            html = re.sub(r'^- \*\*(.+?):\*\*\s*(.+)$', lambda m: '<div class="desc-meta"><strong>' + m.group(1) + ':</strong> ' + m.group(2) + '</div>', html, flags=re.MULTILINE)
            
            # 2. Горизонтальная линия
            html = re.sub(r'^---$', '<hr class="desc-hr">', html, flags=re.MULTILINE)
            
            # 3. Заголовки
            html = re.sub(r'^# (.+)$', lambda m: '<h1 class="desc-h1">' + m.group(1) + '</h1>', html, flags=re.MULTILINE)
            html = re.sub(r'^## (.+)$', lambda m: '<h2 class="desc-h2">' + m.group(1) + '</h2>', html, flags=re.MULTILINE)
            html = re.sub(r'^### (.+)$', lambda m: '<h3 class="desc-h3">' + m.group(1) + '</h3>', html, flags=re.MULTILINE)
            
            # 4. Жирный текст
            html = re.sub(r'\*\*(.+?)\*\*', lambda m: '<strong>' + m.group(1) + '</strong>', html)
            
            # 5. Теперь конвертируем все URL в кликабельные ссылки
            def make_urls_clickable(text):
                def replace_url(match):
                    url = match.group(0)
                    return '<a href="' + url + '" class="desc-link" target="_blank" rel="noopener">' + url + '</a>'
                return re.sub(r'https?://[^\s<>"\']+', replace_url, text)
            
            html = make_urls_clickable(html)
            
            # 6. Код в строке
            html = re.sub(r'`([^`]+)`', r'<code class="desc-code">\1</code>', html)
            
            # 7. Ссылки [text](url) -> кликабельные
            html = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'<a href="\2" class="desc-link" target="_blank" rel="noopener">\1</a>', html)
            
            # 8. Оборачиваем текстовые строки в параграфы
            def wrap_text_paragraphs(text):
                blocks = text.split('\n\n')
                result = []
                for block in blocks:
                    block = block.strip()
                    if not block:
                        continue
                    if block.startswith('<h') or block.startswith('<hr') or block.startswith('<div') or block.startswith('<p') or block.startswith('<code') or block.startswith('<a') or block.startswith('<strong') or block.startswith('<em'):
                        result.append(block)
                    else:
                        result.append('<p class="desc-p">' + block + '</p>')
                return '\n'.join(result)
            
            html = wrap_text_paragraphs(html)
            
            bug['description_html'] = html
    
    return render_template('bug_detail.html', bug=bug)


@app.route('/comment/<int:bug_id>', methods=['POST'])
def add_comment(bug_id):
    """Добавление комментария к багу."""
    data = request.form
    if not data.get('text', '').strip():
        flash('Комментарий не может быть пустым', 'error')
        return redirect(url_for('bug_detail', bug_id=bug_id))
    
    conn = get_db()
    # Проверяем что баг существует
    bug = conn.execute("SELECT id FROM bugs WHERE id = ?", (bug_id,)).fetchone()
    if not bug:
        conn.close()
        flash('Баг не найден', 'error')
        return redirect(url_for('index'))
    
    conn.execute("""
        INSERT INTO comments (bug_id, author, text)
        VALUES (?, ?, ?)
    """, (
        bug_id,
        data.get('author', 'QA Engineer'),
        data.get('text', '')
    ))
    conn.commit()
    conn.close()
    
    flash('Комментарий добавлен', 'success')
    return redirect(url_for('bug_detail', bug_id=bug_id))


@app.route('/delete-comment/<int:comment_id>', methods=['POST'])
def delete_comment(comment_id):
    """Удаление комментария."""
    conn = get_db()
    comment = conn.execute("SELECT bug_id FROM comments WHERE id = ?", (comment_id,)).fetchone()
    if comment:
        conn.execute("DELETE FROM comments WHERE id = ?", (comment_id,))
        conn.commit()
        flash('Комментарий удалён', 'success')
        return redirect(url_for('bug_detail', bug_id=comment['bug_id']))
    conn.close()
    flash('Комментарий не найден', 'error')
    return redirect(url_for('index'))


@app.route('/export/<int:bug_id>')
def export_bug(bug_id):
    """Экспорт бага в HTML для сохранения в PDF."""
    conn = get_db()
    bug = conn.execute("SELECT * FROM bugs WHERE id = ?", (bug_id,)).fetchone()
    conn.close()
    if not bug:
        flash('Баг не найден', 'error')
        return redirect(url_for('index'))
    
    bug = dict(bug)
    
    # Загружаем описание из markdown
    import re
    bug_reports_dir = os.path.join(REPO_ROOT, 'bug-reports')
    description_html = ''
    if os.path.isdir(bug_reports_dir):
        key_prefix = bug['key'] + '-'
        md_files = [f for f in os.listdir(bug_reports_dir) if f.startswith(key_prefix) and f.endswith('.md')]
        if md_files:
            md_path = os.path.join(bug_reports_dir, sorted(md_files)[0])
            with open(md_path, 'r', encoding='utf-8') as f:
                md_text = f.read()
            html = md_text
            html = re.sub(r'^- \*\*(.+?):\*\*\s*(.+)$', lambda m: '<div class="desc-meta"><strong>' + m.group(1) + ':</strong> ' + m.group(2) + '</div>', html, flags=re.MULTILINE)
            html = re.sub(r'^---$', '<hr class="desc-hr">', html, flags=re.MULTILINE)
            html = re.sub(r'^# (.+)$', lambda m: '<h1 class="desc-h1">' + m.group(1) + '</h1>', html, flags=re.MULTILINE)
            html = re.sub(r'^## (.+)$', lambda m: '<h2 class="desc-h2">' + m.group(1) + '</h2>', html, flags=re.MULTILINE)
            html = re.sub(r'^### (.+)$', lambda m: '<h3 class="desc-h3">' + m.group(1) + '</h3>', html, flags=re.MULTILINE)
            html = re.sub(r'\*\*(.+?)\*\*', lambda m: '<strong>' + m.group(1) + '</strong>', html)
            
            def make_urls_clickable(text):
                def replace_url(match):
                    url = match.group(0)
                    return '<a href="' + url + '" class="desc-link" target="_blank">' + url + '</a>'
                return re.sub(r'https?://[^\s<>"\']+', replace_url, text)
            
            html = make_urls_clickable(html)
            html = re.sub(r'`([^`]+)`', r'<code class="desc-code">\1</code>', html)
            html = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'<a href="\2" class="desc-link" target="_blank">\1</a>', html)
            
            def wrap_text_paragraphs(text):
                blocks = text.split('\n\n')
                result = []
                for block in blocks:
                    block = block.strip()
                    if not block:
                        continue
                    if block.startswith('<h') or block.startswith('<hr') or block.startswith('<div') or block.startswith('<p') or block.startswith('<code') or block.startswith('<a') or block.startswith('<strong') or block.startswith('<em'):
                        result.append(block)
                    else:
                        result.append('<p class="desc-p">' + block + '</p>')
                return '\n'.join(result)
            
            html = wrap_text_paragraphs(html)
            description_html = html
    
    # Загружаем скриншоты
    screenshot_dir = os.path.join(REPO_ROOT, 'screenshots')
    screenshots = []
    if os.path.isdir(screenshot_dir):
        key_lower = bug['key'].lower()
        key_nodash = key_lower.replace('-', '')
        for f in os.listdir(screenshot_dir):
            fn_lower = f.lower()
            if fn_lower.startswith(key_lower) or fn_lower.startswith(key_nodash):
                screenshots.append(f)
    
    return render_template('export.html', bug=bug, description_html=description_html, screenshots=screenshots)


@app.route('/new', methods=['GET', 'POST'])
def new_bug():
    if request.method == 'POST':
        data = request.form

        conn = get_db()
        last = conn.execute("SELECT key FROM bugs ORDER BY id DESC LIMIT 1").fetchone()
        if last:
            num = int(last["key"].split("-")[1]) + 1
        else:
            num = 1
        key = f"BUG-{num:03d}"

        today = request.form.get("date", None) or sqlite3.connect(DB_PATH).execute("SELECT date('now')").fetchone()[0]

        conn.execute("""
            INSERT INTO bugs (key, title, project, severity, priority, status, date, url, attachments,
                              type, component, assignee, reporter, environment, preconditions,
                              steps, expected_result, actual_result, user_impact, root_cause,
                              recommendations, labels, comments)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            key,
            data.get("title", ""),
            data.get("project", ""),
            data.get("severity", "Major"),
            data.get("priority", "Medium"),
            data.get("status", "New"),
            today,
            data.get("url", ""),
            data.get("attachments", ""),
            data.get("type", ""),
            data.get("component", ""),
            data.get("assignee", ""),
            data.get("reporter", ""),
            data.get("environment", ""),
            data.get("preconditions", ""),
            data.get("steps", ""),
            data.get("expected_result", ""),
            data.get("actual_result", ""),
            data.get("user_impact", ""),
            data.get("root_cause", ""),
            data.get("recommendations", ""),
            data.get("labels", ""),
            data.get("comments", "")
        ))
        conn.commit()
        bug_id = conn.execute("SELECT id FROM bugs WHERE key = ?", (key,)).fetchone()[0]
        conn.close()

        # Виджет формы -> Python -> Telegram: карточка бага уходит в чат
        # со всеми деталями из формы (шаги, ожидаемый/фактический
        # результат, влияние) — этих колонок в БД нет, поэтому отчёт
        # собирается из данных формы, а не из строки базы.
        # Без настроенного Telegram баг всё равно создаётся:
        # send_bug_notification возвращает (False, причина), не бросая
        # исключений.
        try:
            from telegram_notifier import send_bug_notification
        except ImportError:
            send_bug_notification = None

        flash(f'Баг {key} создан!', 'success')
        if send_bug_notification is not None:
            ok, detail = send_bug_notification({
                "key": key,
                "title": data.get("title", ""),
                "project": data.get("project", ""),
                "severity": data.get("severity", "Major"),
                "priority": data.get("priority", "Medium"),
                "status": data.get("status", "New"),
                "url": data.get("url", ""),
                "environment": data.get("environment", ""),
                "steps": data.get("steps", ""),
                "expected_result": data.get("expected_result", ""),
                "actual_result": data.get("actual_result", ""),
                "user_impact": data.get("user_impact", ""),
                "reporter": data.get("reporter", ""),
            })
            if ok:
                flash('Уведомление в Telegram отправлено.', 'success')
            else:
                flash(f'Telegram: {detail}', 'info')

        return redirect(url_for('bug_detail', bug_id=bug_id))

    return render_template('new_bug.html')


@app.route('/edit/<int:bug_id>', methods=['GET', 'POST'])
def edit_bug(bug_id):
    conn = get_db()
    bug = conn.execute("SELECT * FROM bugs WHERE id = ?", (bug_id,)).fetchone()
    if bug is None:
        conn.close()
        flash('Баг не найден', 'error')
        return redirect(url_for('index'))

    if request.method == 'POST':
        data = request.form
        conn.execute("""
            UPDATE bugs SET
                title=?, project=?, severity=?, priority=?, status=?, date=?, url=?, attachments=?,
                type=?, component=?, assignee=?, reporter=?, environment=?, preconditions=?,
                steps=?, expected_result=?, actual_result=?, user_impact=?, root_cause=?,
                recommendations=?, labels=?, comments=?, updated_at=datetime('now', 'localtime')
            WHERE id=?
        """, (
            data.get("title", ""),
            data.get("project", ""),
            data.get("severity", "Major"),
            data.get("priority", "Medium"),
            data.get("status", "New"),
            data.get("date", ""),
            data.get("url", ""),
            data.get("attachments", ""),
            data.get("type", ""),
            data.get("component", ""),
            data.get("assignee", ""),
            data.get("reporter", ""),
            data.get("environment", ""),
            data.get("preconditions", ""),
            data.get("steps", ""),
            data.get("expected_result", ""),
            data.get("actual_result", ""),
            data.get("user_impact", ""),
            data.get("root_cause", ""),
            data.get("recommendations", ""),
            data.get("labels", ""),
            data.get("comments", ""),
            bug_id
        ))
        conn.commit()
        conn.close()
        flash('Баг обновлён!', 'success')
        return redirect(url_for('bug_detail', bug_id=bug_id))

    conn.close()
    return render_template('edit_bug.html', bug=bug)


@app.route('/change-status/<int:bug_id>', methods=['POST'])
def change_status(bug_id):
    """Изменение статуса бага через AJAX."""
    new_status = request.form.get("status")
    if not new_status:
        return jsonify({"error": "Status required"}), 400

    conn = get_db()
    bug = conn.execute("SELECT id FROM bugs WHERE id = ?", (bug_id,)).fetchone()
    if not bug:
        conn.close()
        return jsonify({"error": "Bug not found"}), 404

    conn.execute("UPDATE bugs SET status = ?, updated_at = datetime('now', 'localtime') WHERE id = ?",
                 (new_status, bug_id))
    conn.commit()
    conn.close()

    return jsonify({"success": True, "status": new_status})


@app.route('/change-status-get/<int:bug_id>/<status>')
def change_status_get(bug_id, status):
    """Изменение статуса бага через GET запрос."""
    valid_statuses = ['New', 'In Progress', 'Resolved', 'Closed']
    if status not in valid_statuses:
        flash('Неверный статус', 'error')
        return redirect(url_for('index'))

    conn = get_db()
    bug = conn.execute("SELECT id FROM bugs WHERE id = ?", (bug_id,)).fetchone()
    if not bug:
        conn.close()
        flash('Баг не найден', 'error')
        return redirect(url_for('index'))

    conn.execute("UPDATE bugs SET status = ?, updated_at = datetime('now', 'localtime') WHERE id = ?",
                 (status, bug_id))
    conn.commit()
    conn.close()

    flash(f'Статус бага {bug["key"]} изменён на "{status}"', 'success')
    return redirect(url_for('index'))


@app.route('/delete/<int:bug_id>', methods=['POST'])
def delete_bug(bug_id):
    conn = get_db()
    bug = conn.execute("SELECT key FROM bugs WHERE id = ?", (bug_id,)).fetchone()
    if bug:
        conn.execute("DELETE FROM bugs WHERE id = ?", (bug_id,))
        conn.commit()
        flash(f'Баг {bug["key"]} удалён', 'success')
    conn.close()
    return redirect(url_for('index'))


# ─── Static files ────────────────────────────────────────

@app.route('/screenshots/<path:filename>')
def serve_screenshots(filename):
    """Обслуживание скриншотов из папки screenshots/."""
    screenshot_dir = os.path.join(REPO_ROOT, 'screenshots')
    return send_from_directory(screenshot_dir, filename)


if __name__ == '__main__':
    init_db()
    migrate_bugs()
    app.run(debug=True, port=5000)