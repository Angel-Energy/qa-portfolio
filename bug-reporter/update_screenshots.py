import sqlite3

conn = sqlite3.connect('bug_reports.db')
screenshots = "bug008-link-886415-sms-seventech.png|bug008-link-1037908-addon-catalog.png|bug008-link-275858-form-transparent.png|bug008-link-275854-widget-height.png|bug008-link-298451-overcome-ceiling.png|bug008-redirect-result-pl-blog.png|bug008-powershell-audit-666-links.png"

conn.execute("UPDATE bugs SET screenshots = ? WHERE key = ?", (screenshots, "BUG-008"))
conn.execute("UPDATE bugs SET screenshots = ? WHERE key = ?", (screenshots, "BUG-009"))

conn.commit()
print("Updated BUG-008 and BUG-009 screenshots")
conn.close()
