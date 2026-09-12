import sqlite3

conn = sqlite3.connect('bug_reports.db')

# Check if column exists
cursor = conn.execute("PRAGMA table_info(bugs)")
columns = [row[1] for row in cursor.fetchall()]

if 'screenshots' not in columns:
    conn.execute("ALTER TABLE bugs ADD COLUMN screenshots TEXT DEFAULT ''")
    print("Added screenshots column")
else:
    print("Column screenshots already exists")

# Update screenshots for BUG-008 and BUG-009
screenshots = "bug008-link-886415-sms-seventech.png|bug008-link-1037908-addon-catalog.png|bug008-link-275858-form-transparent.png|bug008-link-275854-widget-height.png|bug008-link-298451-overcome-ceiling.png|bug008-redirect-result-pl-blog.png|bug008-powershell-audit-666-links.png"

conn.execute("UPDATE bugs SET screenshots = ? WHERE key = ?", (screenshots, "BUG-008"))
conn.execute("UPDATE bugs SET screenshots = ? WHERE key = ?", (screenshots, "BUG-009"))

conn.commit()
print("Updated BUG-008 and BUG-009 screenshots")

# Verify
cursor = conn.execute("SELECT key, screenshots FROM bugs WHERE key IN ('BUG-008', 'BUG-009')")
for row in cursor.fetchall():
    print(f"{row[0]}: {row[1][:50] if row[1] else 'None'}...")

conn.close()
