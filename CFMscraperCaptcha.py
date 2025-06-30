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


class CFMScraperCaptcha:

    def __init__(self, driver_path):
        self.driver_path = driver_path
        self.driver = self.inicializar_driver()
        self.url = "https://portal.cfm.org.br/busca-medicos"
        self.configurar_logger()

    def configurar_logger(self):
        """Configura o logger da aplicação."""
        self.logger = logging.getLogger("CFMScraperCaptcha")
        self.logger.setLevel(logging.INFO)

        # Handler para arquivo de log
        file_handler = logging.FileHandler("cfm_scraper_captcha.log", encoding="utf-8")
        file_handler.setLevel(logging.INFO)

        # Handler para console
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)

        # Formato do log
        formatter = logging.Formatter('%(asctime)s | %(levelname)s | %(message)s')
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)

        # Adicionar os handlers ao logger
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

    def detectar_captcha(self):
        """Detecta presença de CAPTCHA na página e pausa para resolução manual."""
        try:
            iframe = self.driver.find_element(By.XPATH, '//iframe[contains(@src, "captcha")]')
            if iframe.is_displayed():
                self.logger.warning("CAPTCHA detectado! Aguardando resolução manual.")
                self.driver.save_screenshot("captcha_detectado.png")
                input("Após resolver o CAPTCHA no navegador, pressione Enter para continuar...")
                return True
        except:
            pass
        return False

    def buscar_medicos_estado(self, uf):
        self.logger.info(f"Iniciando busca para estado: {uf}")
        self.driver.get(self.url)
        wait = WebDriverWait(self.driver, 10)
        self.fechar_popup_cookies()

        try:
            wait.until(EC.presence_of_element_located((By.ID, "uf")))
            select_uf = Select(self.driver.find_element(By.ID, "uf"))
            select_uf.select_by_value(uf)

            botao_enviar = wait.until(EC.presence_of_element_located(
                (By.XPATH, '//*[@id="buscaForm"]/div/div[5]/div[2]/button')))
            self.driver.execute_script("arguments[0].scrollIntoView(true);", botao_enviar)
            time.sleep(random.uniform(1.5, 3.5))

            self.mover_mouse_ate_elemento(botao_enviar)
            wait.until(EC.element_to_be_clickable(
                (By.XPATH, '//*[@id="buscaForm"]/div/div[5]/div[2]/button')))
            botao_enviar.click()

            time.sleep(random.uniform(2, 4))
            self.detectar_captcha()

            wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, ".card-body")))

        except Exception as e:
            self.logger.error(f"Erro ao preparar busca para {uf}: {e}")
            return []

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

            self.logger.info(f"{uf} - Página {pagina}: capturados {len(cards)} médicos.")

            try:
                proxima_pagina_num = pagina + 1
                botao_proxima = self.driver.find_element(By.XPATH,
                    f"//li[@class='paginationjs-page J-paginationjs-page' and @data-num='{proxima_pagina_num}']/a")
                self.mover_mouse_ate_elemento(botao_proxima)
                self.driver.execute_script("arguments[0].click();", botao_proxima)
                pagina += 1
                time.sleep(random.uniform(2, 5))

                self.detectar_captcha()

            except:
                self.logger.info(f"{uf} - Fim das páginas na página {pagina}.")
                break

        return medicos

    def encerrar(self):
        self.driver.quit()
        self.logger.info("Driver encerrado.")


# ---------- Execução ----------

if __name__ == "__main__":
    caminho_driver = os.path.join(os.getcwd(), "chromedriver-win64", "chromedriver.exe")
    scraper = CFMScraperCaptcha(caminho_driver)

    dados_rj = scraper.buscar_medicos_estado("RJ")
    dados_sp = scraper.buscar_medicos_estado("SP")

    scraper.encerrar()

    todos_medicos = dados_rj + dados_sp
    df = pd.DataFrame(todos_medicos)
    df.to_csv("Lista Médicos CFM - RJ e SP.csv", index=False, encoding="utf-8-sig")

    print(f"Total de médicos capturados: {len(df)}")
