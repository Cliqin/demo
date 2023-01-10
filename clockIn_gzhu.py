import os
import sys
import traceback

import requests
import selenium.common
import selenium.webdriver
from loguru import logger
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.relative_locator import locate_with
from selenium.webdriver.support.wait import WebDriverWait


class ClockIn:
    """健康打卡"""

    def __init__(self) -> None:
        self.xuhao = os.environ["ID"]
        self.mima = os.environ["PW"]
        self.pushplus = os.environ["PP"]

        options = Options()
        options_list = [
            "--headless",
            "--enable-javascript",
            "start-maximized",
            "--disable-gpu",
            "--blink-settings=imagesEnabled=false",
            "--disable-extensions",
            "--no-sandbox",
            "--disable-browser-side-navigation",
            "--disable-dev-shm-usage",
        ]
        for option in options_list:
            options.add_argument(option)
        options.page_load_strategy = "none"
        options.add_experimental_option(
            "excludeSwitches", ["ignore-certificate-errors", "enable-automation"]
        )

        # self.path  = 'chromedriver.exe'
        self.driver = selenium.webdriver.Chrome(options=options)
        # self.driver = selenium.webdriver.Chrome()

        self.wdwait = WebDriverWait(self.driver, 30)
        self.titlewait = WebDriverWait(self.driver, 5)

        # self.page用来表示当前页面标题，0表示初始页面
        self.page = 0

        # self.fail表示打卡失败与否
        self.fail = False

    def __call__(self) -> None:
        retries = 1
        while True:
            try:
                logger.info(f"第{retries}次运行")
                if retries != 1:
                    self.refresh()
                if self.page == 4:
                    self.step_add_temp_page_4()
                if self.page == 0:
                    self.step0()
                if self.page <= 1:
                    self.step1()
                if self.page <= 2:
                    self.step2()
                if self.page <= 3:
                    self.step3()

                break
            except selenium.common.exceptions.TimeoutException:
                logger.error(traceback.format_exc())
                if not self.driver.title:
                    logger.error(f"第{retries}次运行失败，当前页面标题为空")
                else:
                    logger.error(f"第{retries}次运行失败，当前页面标题为：{self.driver.title}")

                if retries == 7:
                    self.fail = True
                    logger.error("健康打卡失败")
                    break

                retries += 1

        self.driver.quit()
        self.notify()

    def refresh(self) -> None:
        """刷新页面，直到页面标题不为空
        Raises:
            selenium.common.exceptions.TimeoutException: 页面刷新次数达到上限
        """
        refresh_times = 0

        while True:
            logger.info("刷新页面")
            self.driver.refresh()
            try:
                self.titlewait.until(
                    EC.presence_of_all_elements_located((By.TAG_NAME, "title"))
                )
            except selenium.common.exceptions.TimeoutException:
                pass
            title = self.driver.title

            match title:
                # Unified Identity Authentication也就是统一身份认证界面
                case "Unified Identity Authentication":
                    self.page = 1
                case "融合门户":
                    self.page = 2
                case "Loading..." | "表单填写与审批::加载中" | "填报健康信息 - 学生健康状况申报":
                    self.page = 3
                case "学生健康状况申报":
                    self.page = 4
                case "":
                    logger.info("当前页面标题为空")
                    refresh_times += 1
                    if refresh_times < 6:
                        continue
                    raise selenium.common.exceptions.TimeoutException("页面刷新次数达到上限")
                case _:
                    self.page = 0

            break

        logger.info(f"当前页面标题为：{title}")

    def step0(self) -> None:
        """跳转到统一身份认证界面"""
        logger.info("正在跳转到统一身份认证页面")
        self.driver.get(
            "https://newcas.gzhu.edu.cn/cas/\
login?service=https%3A%2F%2Fnewmy.gzhu.edu.cn%2Fup%2Fview%3Fm%3Dup"
        )

    def step1(self) -> None:
        """登录融合门户"""
        self.wdwait.until(
            EC.visibility_of_element_located(
                (By.XPATH, "//div[@class='robot-mag-win small-big-small']")
            )
        )

        logger.info("正在尝试登陆融合门户")
        for script in [
            f"document.getElementById('un').value='{self.xuhao}'",
            f"document.getElementById('pd').value='{self.mima}'",
            "document.getElementById('index_login_btn').click()",
        ]:
            self.driver.execute_script(script)

    def step2(self) -> None:
        """跳转到填报健康信息 - 学生健康状况申报页面"""
        self.titlewait.until(EC.title_contains("融合门户"))
        logger.info("正在跳转到填报健康信息 - 学生健康状况申报页面")
        # self.driver.get("https://yqtb.gzhu.edu.cn/infoplus/form/XNYQSB/start")
        #   //*[@id="preview_start_button"]
        self.driver.get("https://yqtb.gzhu.edu.cn/infoplus/form/XSJKZKSB/start?preview=true")
        self.wdwait.until(
            EC.element_to_be_clickable(
                (By.XPATH, "//*[@id='preview_start_button']")
            )
        )
        self.driver.find_element(By.XPATH,'//*[@id="preview_start_button"]').click()

    def step_add_temp_page_4(self) -> None:
        self.driver.get("https://yqtb.gzhu.edu.cn/infoplus/form/XSJKZKSB/start?preview=true")
        self.titlewait.until(EC.title_contains("学生健康状况申报"))
        self.wdwait.until(
            EC.element_to_be_clickable(
                (By.XPATH, "//*[@id='preview_start_button']")
            )
        )
        self.driver.find_element(By.XPATH, '//*[@id="preview_start_button"]').click()

    def step3(self) -> None:
        """填写并提交表单"""
        self.wdwait.until(
            EC.element_to_be_clickable(
                (By.XPATH, "//*[@id='V1_CTRL51']")
            )
        )

        logger.info("开始填表")
        for xpath in [
            "//*[@id='V1_CTRL51']",
            "//nobr[contains(text(), '提交')]/..",
        ]:
            self.driver.find_element(By.XPATH, xpath).click()

        self.wdwait.until(
            EC.element_to_be_clickable(
                (By.XPATH, "//button[@class='dialog_button default fr']")
            )
        ).click()

        #
        # form_error_content_list = self.driver.find_elements(
        #     By.XPATH, "//div[@class='line10']"
        # )
        # for form_error_content in form_error_content_list:
        #     button = self.driver.find_elements(
        #         locate_with(By.XPATH, "//input[@type='radio']").below(
        #             form_error_content
        #         )
        #     )[0]
        #     self.driver.execute_script("$(arguments[0]).click();", button)
        #
        # logger.info("提交表单")
        # self.driver.find_element(By.XPATH, "//nobr[contains(text(), '提交')]/..").click()
        #
        self.wdwait.until(
            EC.visibility_of_element_located(
                (By.XPATH, "//div[@class='dialog_content']")
            )
        )
        time.sleep(10)
        # //*[@id="dialog_container_843202"]/div[2]/button[1]
        # dialog_content
        # message = self.driver.execute_script(
        #     "return document.getElementsByClassName('form_do_action_error')[0]['textContent']"
        # )

        message = self.driver.execute_script(
            "return document.getElementsByClassName('dialog_content')[0]['textContent']"
        )

        print(message)

        if message == "办理成功!":
            logger.info("健康打卡成功")
        else:
            logger.error(f"弹出框消息不正确，为:{message}")
            logger.error("健康打卡失败")
            self.fail = True

    def notify(self) -> None:
        """通知健康打卡成功与失败"""
        if not self.pushplus:
            if self.fail:
                sys.exit("健康打卡失败")
            else:
                sys.exit()

        if self.fail:
            title = content = "八点打卡失败"
        else:
            title = content = "八点打卡成功"

        logger.info(f"推送{title}的消息")
        data = {"token": self.pushplus, "title": title, "content": content}
        url = "http://www.pushplus.plus/send/"
        logger.info(requests.post(url, data=data, timeout=10).text)


if __name__ == "__main__":
    cl = ClockIn()
    cl()