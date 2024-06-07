import psycopg2


con = psycopg2.connect(
    dbname='narod',
    user='erwyn_montgomery',
    password='*****',
    host='localhost',
    port='5432'
)

cur = con.cursor()

cur.execute("""
CREATE TABLE IF NOT EXISTS site (
    site_id SERIAL PRIMARY KEY,
    site_link TEXT
);
""")

cur.execute("""
CREATE TABLE IF NOT EXISTS page (
    page_id SERIAL PRIMARY KEY,
    site_id BIGINT,
    page_link TEXT,
    page_parent BIGINT,
    page_title TEXT,
    page_html TEXT,
    page_text TEXT,
    page_file_saved BOOLEAN,
    page_file TEXT,
    CONSTRAINT site_fk FOREIGN KEY (site_id) REFERENCES site(site_id),
    CONSTRAINT page_parent_fk FOREIGN KEY (page_parent) REFERENCES page(page_id)
);
""")

cur.execute("""
CREATE TABLE IF NOT EXISTS external_link (
    ext_link_id SERIAL PRIMARY KEY,
    page_id BIGINT,
    ext_link_link TEXT,
    CONSTRAINT page_fk FOREIGN KEY (page_id) REFERENCES page(page_id)
);
""")

cur.execute("""
CREATE TABLE IF NOT EXISTS file (
    file_id SERIAL PRIMARY KEY,
    page_id BIGINT,
    file_extension VARCHAR(5),
    file_link TEXT,
    file_saved BOOLEAN,
    file_path TEXT,
    CONSTRAINT page_fk FOREIGN KEY (page_id) REFERENCES page(page_id)
);
""")

cur.execute("""
CREATE TABLE IF NOT EXISTS main_page_screenshot (
    screenshot_id SERIAL PRIMARY KEY,
    site_id BIGINT,
    screenshot_path TEXT,
    CONSTRAINT site_fk FOREIGN KEY (site_id) REFERENCES site(site_id)
);
""")

cur.execute("""
CREATE TABLE IF NOT EXISTS page_screenshot (
    screenshot_id SERIAL PRIMARY KEY,
    page_id BIGINT,
    screenshot_path TEXT,
    CONSTRAINT page_fk FOREIGN KEY (page_id) REFERENCES page(page_id)
);
""")

con.commit()
con.close()
