import sqlite3

con = sqlite3.connect("data.db")
cur = con.cursor()

cur.execute("""
CREATE TABLE IF NOT EXISTS site (
    site_id INTEGER PRIMARY KEY,
    site_link TEXT
);
""")

cur.execute("""
CREATE TABLE IF NOT EXISTS page (
    page_id INTEGER PRIMARY KEY,
    site_id INTEGER,
    page_link TEXT,
    page_parent INTEGER,
    page_title TEXT,
    page_html TEXT,
    page_text TEXT,
    page_file_saved INTEGER,
    page_file TEXT,
    CONSTRAINT site_fk FOREIGN KEY (site_id) REFERENCES site(site_id),
    CONSTRAINT page_parent_fk FOREIGN KEY (page_parent) REFERENCES page(page_id)
);
""")

cur.execute("""
CREATE TABLE IF NOT EXISTS external_link (
    ext_link_id INTEGER PRIMARY KEY,
    page_id INTEGER,
    ext_link_link TEXT,
    CONSTRAINT page_fk FOREIGN KEY (page_id) REFERENCES page(page_id)
);
""")

cur.execute("""
CREATE TABLE IF NOT EXISTS file (
    file_id INTEGER PRIMARY KEY,
    page_id INTEGER,
    file_extension TEXT,
    file_link TEXT,
    file_saved INTEGER,
    file_path TEXT,
    CONSTRAINT page_fk FOREIGN KEY (page_id) REFERENCES page(page_id)
);
""")

cur.execute("""
CREATE TABLE IF NOT EXISTS main_page_screenshot (
    screenshot_id INTEGER PRIMARY KEY,
    site_id INTEGER,
    screenshot_path TEXT,
    CONSTRAINT site_fk FOREIGN KEY (site_id) REFERENCES site(site_id)
);
""")

cur.execute("""
CREATE TABLE IF NOT EXISTS page_screenshot (
    screenshot_id INTEGER PRIMARY KEY,
    site_id INTEGER,
    page_id INTEGER,
    screenshot_path TEXT,
    CONSTRAINT site_fk FOREIGN KEY (site_id) REFERENCES site(site_id),
    CONSTRAINT page_fk FOREIGN KEY (page_id) REFERENCES page(page_id)
);
""")

con.commit()
con.close()
