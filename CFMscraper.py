import logging
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select, WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver import ActionChains
import pandas as pd
import time
import os
import random

class CFMScraper:

    def __init__(self, driver_path):
        self.driver_path = driver_path
        self.driver = self.inicializar_driver()
        self.url = "https://portal.cfm.org.br/busca-medicos"
        self.configurar_logger()

    def configurar_logger(self):
        self.logger = logging.getLogger("CFMScraper")
        self.logger.setLevel(logging.INFO)

        file_handler = logging.FileHandler("cfm_scraper.log", encoding='utf-8')
        file_handler.setLevel(logging.INFO)

        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)

        formatter = logging.Formatter('%(asctime)s | %(levelname)s | %(message)s')
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)

        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)

    def inicializar_driver(self):
        service = Service(self.driver_path)
        options = webdriver.ChromeOptions()
        options.add_argument("--start-maximized")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option("useAutomationExtension", False)

        driver = webdriver.Chrome(service=service, options=options)
        driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
            "source": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
        })
        return driver

    def fechar_popup_cookies(self):
        wait = WebDriverWait(self.driver, 5)
        try:
            botao_aceitar = wait.until(EC.element_to_be_clickable((By.XPATH, '//button[contains(text(), "Aceito")]')))
            botao_aceitar.click()
            time.sleep(random.uniform(1.5, 3.5))
        except:
            pass

    def mover_mouse_ate_elemento(self, element):
        actions = ActionChains(self.driver)
        actions.move_to_element(element).perform()
        time.sleep(random.uniform(0.5, 1.5))

    def buscar_medicos_estado_municipios(self, uf):
        self.logger.info(f"Iniciando busca para estado: {uf}")
        self.driver.get(self.url)
        wait = WebDriverWait(self.driver, 10)
        self.fechar_popup_cookies()

        try:
            wait.until(EC.presence_of_element_located((By.ID, "uf")))
            select_uf = Select(self.driver.find_element(By.ID, "uf"))
            select_uf.select_by_value(uf)
            time.sleep(random.uniform(1.5, 3.5))

            wait.until(EC.presence_of_element_located((By.ID, "municipio")))
            select_municipio = Select(self.driver.find_element(By.ID, "municipio"))
            municipios_valores = [opt.get_attribute("value") for opt in select_municipio.options if opt.get_attribute("value") != ""]

            self.logger.info(f"{uf} - Municípios encontrados: {len(municipios_valores)}")

        except Exception as e:
            self.logger.error(f"Erro ao preparar busca para {uf}: {e}")
            return

        for municipio_valor in municipios_valores:
            try:
                wait.until(EC.presence_of_element_located((By.ID, "municipio")))
                select_municipio = Select(self.driver.find_element(By.ID, "municipio"))
                select_municipio.select_by_value(municipio_valor)
                municipio_nome = select_municipio.first_selected_option.text.strip()

                self.logger.info(f"{uf} - Buscando médicos em: {municipio_nome}")

                time.sleep(random.uniform(1.5, 3))

                botao_enviar = wait.until(EC.presence_of_element_located(
                    (By.XPATH, '//*[@id="buscaForm"]/div/div[5]/div[2]/button')))
                self.driver.execute_script("arguments[0].scrollIntoView(true);", botao_enviar)
                self.mover_mouse_ate_elemento(botao_enviar)
                wait.until(EC.element_to_be_clickable(
                    (By.XPATH, '//*[@id="buscaForm"]/div/div[5]/div[2]/button')))
                botao_enviar.click()

                time.sleep(random.uniform(2, 4))

                try:
                    alerta = self.driver.find_element(By.XPATH, "//*[@id='content']/section/section[3]/div/div/div/div[1]/div/p")
                    if "Nenhum resultado encontrado" in alerta.text:
                        self.logger.info(f"{uf} - {municipio_nome}: Nenhum resultado encontrado.")

                        df = pd.DataFrame([{"Mensagem": "Nenhum resultado encontrado."}])
                        pasta_uf = uf
                        os.makedirs(pasta_uf, exist_ok=True)
                        nome_arquivo = f"{municipio_nome.replace(' ', '_').replace('/', '-')}.csv"
                        caminho_arquivo = os.path.join(pasta_uf, nome_arquivo)
                        df.to_csv(caminho_arquivo, index=False, encoding="utf-8-sig")
                        self.logger.info(f"{uf} - {municipio_nome}: CSV salvo com aviso de nenhum resultado em {caminho_arquivo}.")

                        self.driver.get(self.url)
                        time.sleep(random.uniform(2, 4))
                        wait.until(EC.presence_of_element_located((By.ID, "uf")))
                        select_uf = Select(self.driver.find_element(By.ID, "uf"))
                        select_uf.select_by_value(uf)
                        continue
                except:
                    pass

                wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, ".card-body")))

                medicos = []
                pagina = 1

                while True:
                    cards = self.driver.find_elements(By.CSS_SELECTOR, ".card-body")
                    if not cards:
                        break

                    for card in cards:
                        try:
                            nome = card.find_element(By.TAG_NAME, "h4").text.strip()
                        except:
                            nome = ""

                        try:
                            crm = card.find_element(By.XPATH, ".//div[contains(@class, 'row')]/div[contains(., 'CRM:')]").text.replace("CRM:", "").strip()
                        except:
                            crm = ""

                        try:
                            inscricao = card.find_element(By.XPATH, ".//div[contains(@class, 'row')]/div[contains(., 'Inscrição:')]").text.replace("Inscrição:", "").strip()
                        except:
                            inscricao = ""

                        try:
                            situacao = card.find_element(By.XPATH, ".//div[contains(@class, 'row')]/div[contains(., 'Situação:')]").text.replace("Situação:", "").strip()
                        except:
                            situacao = ""

                        try:
                            especialidade = card.find_element(By.XPATH, ".//div[contains(@class, 'row')]/div[contains(., 'Especialidades/Áreas de Atuação:')]").text.replace("Especialidades/Áreas de Atuação:", "").strip()
                        except:
                            especialidade = ""

                        medicos.append({
                            "Nome": nome,
                            "Especialidade": especialidade,
                            "CRM": crm,
                            "Inscrição": inscricao,
                            "Situação": situacao
                        })

                    self.logger.info(f"{uf} - {municipio_nome} - Página {pagina}: {len(cards)} médicos capturados.")

                    try:
                        proxima_pagina_num = pagina + 1
                        botao_proxima = self.driver.find_element(By.XPATH,
                            f"//li[@class='paginationjs-page J-paginationjs-page' and @data-num='{proxima_pagina_num}']/a")
                        self.mover_mouse_ate_elemento(botao_proxima)
                        self.driver.execute_script("arguments[0].click();", botao_proxima)
                        pagina += 1
                        time.sleep(random.uniform(2, 5))
                    except:
                        self.logger.info(f"{uf} - {municipio_nome}: fim das páginas na página {pagina}.")
                        break

                if medicos:
                    df = pd.DataFrame(medicos)
                    pasta_uf = uf
                    os.makedirs(pasta_uf, exist_ok=True)
                    nome_arquivo = f"{municipio_nome.replace(' ', '_').replace('/', '-')}.csv"
                    caminho_arquivo = os.path.join(pasta_uf, nome_arquivo)
                    df.to_csv(caminho_arquivo, index=False, encoding="utf-8-sig")
                    self.logger.info(f"{uf} - {municipio_nome}: CSV salvo com {len(medicos)} médicos em {caminho_arquivo}.")

                self.driver.get(self.url)
                time.sleep(random.uniform(2, 4))
                wait.until(EC.presence_of_element_located((By.ID, "uf")))
                select_uf = Select(self.driver.find_element(By.ID, "uf"))
                select_uf.select_by_value(uf)

            except Exception as e:
                self.logger.error(f"Erro em {uf} - {municipio_valor}: {e}")
                continue

    def encerrar(self):
        self.driver.quit()
        self.logger.info("Driver encerrado.")


# ---------- Execução ----------

if __name__ == "__main__":
    caminho_driver = os.path.join(os.getcwd(), "chromedriver-win64", "chromedriver.exe")
    scraper = CFMScraper(caminho_driver)

    scraper.buscar_medicos_estado_municipios("RJ")
    scraper.buscar_medicos_estado_municipios("SP")

    scraper.encerrar()

    print("Extração finalizada.")
