from bs4 import BeautifulSoup as BS
import requests
import sqlite3
from urllib.parse import urljoin, urlparse
import re
import os
import copy
from selenium import webdriver  
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
import inspect
import time


class NarodParser:
    def __init__(self, site_id=1, page_id=1, ext_link_id=1,
                 file_id=1, main_screenshot_id=1, screenshot_id=1):
        # Идентификаторы нужны для сквозного прямого ключа в БД
        self.con = None
        self.cur = None
        self.site_id = site_id
        self.page_id = page_id
        self.ext_link_id = ext_link_id
        self.file_id = file_id
        self.main_screenshot_id = main_screenshot_id
        self.screenshot_id = screenshot_id
        # Настраимаевая максимальная глубина сайта
        self.max_depth = 25
        # Переменные сайта и страницы хранят ссылки для референса других функций
        self.site = None
        self.page = None 
        # Список просмотренных страниц для парсинга сайта
        self.visited_pages = set()
        self.parsed_files = set()
        self.driver = None
        self.page_error_ctr = 0
        self.page_screen_error_ctr = 0
        self.parsed_pages = 0

    def connect_to_db(self, db_path):
        """
        Функция для коннекта к БД.
        """
        if os.path.exists(db_path):
            self.con = sqlite3.connect(db_path)
            self.cur = self.con.cursor()

    def commit_db(self, close_db=False):
        """
        Функция для коммита и закрытия БД.
        """
        if self.cur:
            self.con.commit()
        if self.con and close_db:
            self.con.close()

    def write_to_log(self, type, *args):
        args = [str(arg) for arg in args]
        loc_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
        log = f"Success | Type: {type} | Site: {self.site} | Page: {self.page} | Args: {None if len(args) == 0 else '; '.join(args)} | {loc_time}"
        with open("log_file.txt", "a") as f:
            f.write(f"{log}\n")

    def write_err_to_log(self, error, type, *args):
        """
        Функция для логирования. Записывает сайт и страницу, где была ошибка, функцию, которая выполнялась, ошибку и любые другие аргументы.
        """
        error = str(error).replace("\n", "")
        caller = inspect.stack()[1].function
        args = [str(arg) for arg in args]
        loc_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
        log_err = f"Error | Type: {type} | Site: {self.site} | Page: {self.page} | Func: {caller} | Error: {error} | Args: {None if len(args) == 0 else '; '.join(args)} | {loc_time}"
        with open("log_file.txt", "a") as f:
            f.write(f"{log_err}\n")

    def non_parsed_site(self, error, *args):
        """
        Логирование нераспарсенных сайтов. На данной версии работает некорректно
        """
        args = [str(arg) for arg in args]
        loc_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
        log_err = f"Error | Site: {self.site} | Error: {error} | Args: {None if len(args) == 0 else '; '.join(args)} | {loc_time}"
        with open("non_parsed.txt", "a") as f:
            f.write(f"{log_err}\n")
    
    def is_internal_link(self, site, link):
        """
        Функция для определения того, ведет ли ссылка на этот же сайт.
        """
        check_1 = urlparse(link).netloc == urlparse(site).netloc
        check_2 = urlparse(link).netloc == f"www.{urlparse(site).netloc}"
        return check_1 or check_2

    def get_ex(self, path):
        """
        Функция для получения расширения (скопирована из Стакана).
        """
        ex = os.path.splitext(path)[1]
        if not ex:
            ex = None
        else:
            if ex.startswith("."):
                ex = ex[1:]
        return ex

    def setup_webdriver(self, timeout=5):
        """
        Функция для инициализации драйвера селениума.
        """
        # Запускаем в headless с fullhd разрешением и убираем уведомления со скроллбаром
        chrome_options = Options()
        chrome_options.add_argument("--headless")  
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("--hide-scrollbars")
        chrome_options.add_argument("--disable-notifications")
        chrome_service = Service(executable_path=r"/home/erwyn-montgomery/chromedriver-linux64/chromedriver")
        self.driver = webdriver.Chrome(service=chrome_service, options=chrome_options)
        self.driver.set_page_load_timeout(timeout)

    def close_webdriver(self):
        """
        Функция для закрытия драйвера селениума.
        """
        if self.driver:
            self.driver.close()

    def add_ext_link(self, link):
        """
        Функция для добавления внешней ссылки в БД.
        """
        # Добавляем айди ссылки; айди страницы, откуда она взята; ссылку
        query_data_ext_link = (self.ext_link_id, self.page_id, link) 
        try:
            self.cur.execute("INSERT INTO external_link VALUES(?, ?, ?)", query_data_ext_link)
            self.ext_link_id += 1            
        except Exception as e:
            self.write_err_to_log(e, "type_ext_link", link)

    def download_file(self, file, html=False, files_dir="files", html_dir="html_files"):
        try:
            file_ex = self.get_ex(file)
            if not os.path.exists(files_dir):
                os.makedirs(files_dir)
            if not os.path.exists(html_dir):
                os.makedirs(html_dir)
            if html:
                filename = f"html_file_{self.site_id}_{self.page_id}.html"
            elif file_ex:
                filename = f"file_{self.site_id}_{self.page_id}_{self.file_id}.{file_ex}"
            else:
                filename = f"file_{self.site_id}_{self.page_id}_{self.file_id}"
            file_response = requests.get(file, stream=True, timeout=5)
            if html:
                path_to_save = html_dir + "/" + filename
            else:
                path_to_save = files_dir + "/" + filename
            with open(path_to_save, "wb") as f:
                for chunk in file_response.iter_content(chunk_size=4096):
                    f.write(chunk)
            return path_to_save
        except Exception as e:
            self.write_err_to_log(e, "type_file_downloading", f"File downloading: {self.file_id}")

    def parse_files(self, soup):
        """
        Функция для парсинга и добавления файлов в БД.
        """
        # Указываем нужные теги и находим их
        files_list = ["img", "audio", "video", "object", "embed"]
        files = soup.find_all(files_list)
        self.downloaded_files = set()
        # Добавляем каждый тег в БД, соединяя его с родительской ссылкой
        for tag in files:
            try:
                if tag.name == "object":
                    link = tag.get("data")
                else:
                    link = tag.get("src")
                file_link = urljoin(self.site, link)
                if not file_link.startswith(self.site):
                    continue
                if file_link in self.parsed_files:
                    continue
                ext = self.get_ex(file_link)
                download_path = self.download_file(file_link)
                saved = 0
                try:
                    if os.path.exists(download_path):
                        saved = 1
                except Exception:
                    pass
                # Добавляем айди файла; айди страницы, где он лежит; ссылку на файл
                query_file = (self.file_id, self.page_id, ext, file_link, saved, download_path)
                self.cur.execute("INSERT INTO file VALUES(?, ?, ?, ?, ?, ?)", query_file)
                self.commit_db()
                self.write_to_log("type_file", f"id={self.file_id}", f"link={file_link}")
                self.file_id += 1
                self.parsed_files.add(file_link)
            except Exception as e:
                self.write_err_to_log(e, "type_file", tag)

    def take_main_screenshot(self, directory="screenshots-main"):
        """
        Функция для создания скриншота главной страницы.
        """
        try:
            # Проверяем, есть ли директория и создаем ее
            if not os.path.exists(directory):
                os.makedirs(directory)
            # Имя для скриншота
            path = f"{directory}/site_{self.site_id}_main_page.png"
            # Коннектимся к сайту и делаем скриншот
            self.driver.get(self.site)
            self.driver.get_screenshot_as_file(path)
            # Заполняем информацию о скриншоте (айди; айди сайта; путь) в БД
            query_screenshot = (self.main_screenshot_id, self.site_id, path)
            self.cur.execute("INSERT INTO main_page_screenshot VALUES(?, ?, ?)", query_screenshot)
            self.commit_db()
            self.main_screenshot_id += 1
            self.write_to_log("type_main_screen")
        except Exception as e:
            self.write_err_to_log(e, "type_main_screen")

    def take_page_screenshot(self, page, directory="screenshots_pages"):
        """
        Функция для создания скриншотов страницы.
        
        Сейчас не используется.
        """
        # Тот же самый процесс, что со скриншотом главной страницы сайта,
        #   только меняем айди сайта на айди страницы,
        #   также создаем новую директорию для каждого сайта с именем сайта
        try:
            if not os.path.exists(directory):
                os.makedirs(directory)
            path = f"{directory}/site_{self.site_id}_page_{self.page_id}.png"
            self.driver.get(page)
            self.driver.get_screenshot_as_file(path)
            query_screenshot = (self.screenshot_id, self.site_id, self.page_id, path)
            self.cur.execute("INSERT INTO page_screenshot VALUES(?, ?, ?, ?)", query_screenshot)
            self.commit_db()
            self.screenshot_id += 1
            self.write_to_log("type_page_screen")
            self.page_screen_error_ctr = 0
        except Exception as e:
            self.write_err_to_log(e, "type_page_screen")
            self.page_screen_error_ctr += 1

    def parse_site_pages(self, page, parent_id, depth):
        """
        Рекурсивная функция для парсинга страниц.

        Функция также считает глубину сайта и выводит ее в качестве вывода.
        """
        # Задаем ссылку на страницу для сквозного обращения внутри класса
        self.page = page
        # Проверяем, парсили ли уже эту страницу или достигли ли макс лимита
        if depth > self.max_depth or page in self.visited_pages:
            return depth
        if self.parsed_pages > 10000:
            self.write_err_to_log("Page count is over 10000", "type_page")
            return depth
        if (self.page_error_ctr > 50) and (self.page_error_ctr % 20 != 0):
            self.page_error_ctr += 1
            self.write_err_to_log("Page error counter is over limit", "type_page", f"page_error_ctr={self.page_error_ctr}")
            return depth
        # Пытаемся достучаться до страницы
        try:
            head_response = requests.head(page, allow_redirects=True, timeout=5)
            content_type = head_response.headers.get("Content-Type")
            if "html" in content_type:
                page_html = requests.get(page, timeout=5)
                self.page_error_ctr = 0
                if page_html.status_code != 200:
                    self.visited_pages.add(page)
                    self.write_err_to_log("Status code is not 200", "type_page", "status_not_200", f"status_code={page_html.status_code}")
                    return depth
            else:
                self.visited_pages.add(page)
                return depth
        except Exception as e:
            self.page_error_ctr += 1
            self.visited_pages.add(page)
            self.write_err_to_log(e, "type_page", f"page_error_ctr={self.page_error_ctr}")
            return depth
        # Пытаемся распарсить страницу супом
        try:
            soup = BS(page_html.text, "html.parser")
        except Exception as e:
            self.write_err_to_log(e, "type_page")
            self.visited_pages.add(page)
            return depth
        # Копируем айди, чтобы потом рекурсивно использовать его как для обращения к родительской страницы
        # Использовать сквозной айди нельзя, так как он поменяется при рекурсивной итерации и парсинге страниц-детей
        page_id = copy.deepcopy(self.page_id)
        # Добавляем страницу к посещенным
        self.visited_pages.add(page)
        # Извлекаем суп как строку, чтобы записать html код в БД
        try:
            html = soup.prettify()
        except Exception:
            html = None
        # Достаем заголовок страницы
        try:
            title = soup.find("title").get_text()
        except Exception:
            title = None
        # Достаем текст страницы, убираем лишние переносы
        try:
            text = re.sub(r"(\r?\n|\r){2,}", r"\n\n", soup.get_text())
        except Exception:
            text = None
        # Достаем все ссылки со страницы
        try:
            links = [urljoin(self.site, tag.get("href")) for tag in soup.find_all("a") if tag.get("href")]
        except Exception:
            links = []
        # Фильтруем внутренние ссылки
        try:
            internal_links = [link for link in links if self.is_internal_link(self.site, link)]
        except Exception:
            internal_links = []
        # Cохраняем страницу отдельным файлом (опционально)
        file_path = self.download_file(page, html=True)
        saved = 0
        try:
            if os.path.exists(file_path):
                saved = 1
        except Exception:
            pass
        # Добавляем информацию о странице в БД
        # айди страницы; айди сайта, откуда она; ссылка на страницу; айди родительской страницы (равна айди главной страницы);
        #   заголовок; html-код; текст
        query_data_page = (self.page_id, self.site_id, page, parent_id, title, html, text, saved, file_path)
        self.cur.execute("INSERT INTO page VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?)", query_data_page)
        self.commit_db()
        # Добавляем внешние ссылки со страницы в БД, предварительно убрав из них объекты JS
        try:
            external_links = [link for link in links if not self.is_internal_link(self.site, link)]
            external_links = [link for link in links if not link.startswith("javascript")]
            if len(external_links) > 0:
                for link in external_links:
                    self.add_ext_link(link)
        except Exception:
            external_links = []
        # Добавляем в БД файлы со страницы
        self.parse_files(soup)
        self.write_to_log("type_page")
        # Код для создания скриншотов страницы, откомментить для использования
        #if (self.page_screen_error_ctr <= 25) or (self.page_screen_error_ctr % 25 == 0):
        #    self.take_page_screenshot(page)
        #else:
        #    self.page_screen_error_ctr += 1
        #    self.write_err_to_log("Page screen error counter is over limit", "type_page_screen", f"page_screen_error_ctr={self.page_screen_error_ctr}")
        self.parsed_pages += 1
        self.page_id += 1
        # Если есть внутренние ссылки парсим их рекурсивно
        if len(internal_links) == 0:
            return depth
        else:
            return max([depth] + [self.parse_site_pages(link, page_id, depth + 1) for link in internal_links])


    def parse_sites(self, sites):
        """
        Функция для парсинга сайтов.

        Нужно отладить, чтобы логировались сайты, которые не распарсились.
        """
        # Флаг для понимания того, нужно ли увеличивать айди
        flag = False
        if not sites:
            return None
        for site in sites:
            # Пытаемся подключиться к сайту и передаем ее в сквозную переменную
            self.site = f"http://{site}.narod.ru"
            self.page_screen_error_ctr = 0
            self.page_error_ctr = 0
            self.parsed_pages = 0
            resp = None
            try:
                resp = requests.get(self.site, timeout=5)
            except Exception as e:
                self.non_parsed_site(e)
            if resp:
                if resp.status_code == 200:
                    try:
                        self.cur.execute("INSERT INTO site VALUES(?, ?)", (self.site_id, self.site))
                        self.commit_db()
                        flag = True
                        self.parse_site_pages(f"{self.site}/", self.page_id, 1)
                        self.visited_pages = set()
                        # Делаем скрин главной страницы
                        self.take_main_screenshot()
                    except Exception as e:
                        self.non_parsed_site(e)
                    # Если флаг поднят, увеличиваем сквозную нумерацию сайтов, опускаем флаг
                    if flag:
                        self.site_id += 1
                        flag = False
                        self.write_to_log("type_site")
                else:
                    self.non_parsed_site(f"Status code: {resp.status_code}")


def main(file):
    with open(file) as f:
        narod = [line.rstrip() for line in f]
    parser = NarodParser()
    parser.connect_to_db("data.db")
    parser.setup_webdriver()
    parser.parse_sites(narod)
    parser.close_webdriver()
    parser.commit_db(close_db=True)


if __name__ == "__main__":
    main("sample_domains.txt")