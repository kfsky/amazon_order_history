"""
login to amazon and scrape purchase history
"""

import time
import os
from selenium import webdriver
import pandas as pd
from selenium.common.exceptions import NoSuchElementException
import re

SAVE_DIR = "amazon_pdfs"
SAVE_FULL_DIR = os.getcwd() + "/" + SAVE_DIR  # directory


# return url path e.q. http://aaa/bbb/ccc.py -> http://aaa/bbb/
def get_url_path(url):
    return re.sub('/[^/]*$', '/', url)


# return Date (format is YYYYMMDD)
def pickDate(date):
    pattern = re.compile('([0-9]{4})年([0-9]{1,2})月([0-9]{1,2})日')
    result = pattern.search(date)
    if result:
        y, m, d = result.groups()
        return y + '{:02}'.format(int(m)) + '{:02}'.format(int(d))
    else:
        return None


# Firefox
browser = webdriver.Firefox()
browser.implicitly_wait(10)

# amazon url
url = "https://www.amazon.co.jp/ap/signin?_encoding=UTF8&accountStatusPolicy=P1&openid.assoc_handle=jpflex&openid.cla" \
      "imed_id=http%3A%2F%2Fspecs.openid.net%2Fauth%2F2.0%2Fidentifier_select&openid.identity=http%3A%2F%2Fspecs.ope" \
      "nid.net%2Fauth%2F2.0%2Fidentifier_select&openid.mode=checkid_setup&openid.ns=http%3A%2F%2Fspecs.openid.net%2Fa" \
      "uth%2F2.0&openid.ns.pape=http%3A%2F%2Fspecs.openid.net%2Fextensions%2Fpape%2F1.0&openid.pape.max_auth_age=0&op" \
      "enid.return_to=https%3A%2F%2Fwww.amazon.co.jp%2Fgp%2Fcss%2Forder-history%3Fie%3DUTF8%26ref_%3Dnav_orders_first" \
      "&pageId=webcs-yourorder&showRmrMe=1"

browser.get(url)

# get html info
email_elem = browser.find_element_by_id("ap_email")
email_elem.send_keys("your_email_address")
email_elem.submit()

password_elem = browser.find_element_by_id("ap_password")
password_elem.send_keys("your_password")
password_elem.submit()

# if other devices login click "続行"
# It is necessary to accept the sign-in in the other device.
# close
"""goods_url = "https://www.amazon.co.jp/gp/css/order-history?ie=UTF8&ref_=nav_orders_first&"

if browser.current_url != goods_url:
    browser.find_element_by_id("a-autoid-0").submit()"""

"""
select year.
click the id.

2020: orderFilter_2
2019: orderFilter_3
2018: orderFilter_4
"""

# select year
year_id_2020 = "orderFilter_2"

# click the select year bottom
elem2 = browser.find_element_by_id("a-autoid-1")
elem2.click()
time.sleep(3)

# click 2020
elem3 = browser.find_element_by_id(year_id_2020)
elem3.click()
time.sleep(5)

"""
define params
(select class...)
"""
goods_name = []
goods_url = []
goods_price = []
purchase_date = []


def get_item():

    container = browser.find_element_by_id("ordersContainer")
    name_element = container.find_elements_by_class_name("a-fixed-left-grid")

    for elem in name_element:
        if "注文の詳細" not in elem.text:
            name_elem = elem.find_element_by_class_name("a-col-right").find_elements_by_class_name("a-row")
            name = name_elem[0]
            pdt_url = name.find_element_by_class_name('a-link-normal').get_attribute('href')

            # append list
            goods_name.append(name.text)
            goods_url.append(pdt_url)

    return goods_name, goods_url


def get_order_info(order_info_element):
    order_info_list = [info_field.text for info_field in order_info_element.find_elements_by_class_name("value")]

    if len(order_info_list) < 4:
        order_id = order_info_list[2]
    else:
        order_id = order_info_list[3]

    date = order_info_list[0]
    order_price = order_info_list[1]

    return order_id, date, order_price


def get_digital(order_id):
    """
    checks if the order is digital (e.g. Amazon Video or Audio Book)
    :param order_id: the id of the order to check
    :return: True if order is digital, False if not
    """
    return order_id[:3] == "D01"


def get_price_date():

    order_container = browser.find_elements_by_class_name("order")

    for elem in order_container:
        order_info = elem.find_element_by_class_name("order-info")
        goods_id, goods_date, price = get_order_info(order_info)

        if get_digital(goods_id):
            purchase_date.append(goods_date)
            goods_price.append(price)

        else:
            purchase_date.append(goods_date)
            goods_price_elem = elem.find_elements_by_class_name('a-color-price')
            for i in goods_price_elem:
                goods_price.append(i.text)

    return goods_price, purchase_date


def concatenate_page_data():
    """
    concatenate the item info.
    fill nan(purchase date)
    """
    d = {"date": purchase_date, "item": goods_name, "price": goods_price, "link": goods_url}

    page_data = pd.DataFrame({key: pd.Series(value) for key, value in d.items()})
    if page_data["date"].isnull().any():
        page_data["date"].fillna(method='ffill', inplace=True)

    return page_data


def click_receipt_link():
    divs = browser.find_elements_by_xpath('//*[@id="ordersContainer"]/div')
    size = len(divs)
    for i in range(size):
        divs = browser.find_elements_by_xpath('//*[@id="ordersContainer"]/div')
        try:
            # ダイレクトに「領収書／購入明細書」リンクがある場合
            divs[i].find_element_by_xpath('div[1]/div/div/div/div[2]/div[2]/ul/span[1]/a').click()
        except:
            try:
                # 「領収書等」クリック後に「領収書／購入明細書」リンクがある場合
                divs[i].find_element_by_xpath('div[1]/div/div/div/div[2]/div[2]/ul/span[1]/span/a').click()
                browser.find_element_by_xpath('//*[@class="a-popover-content"]/ul/li/span/a[contains(text(), "領収書／購入明細書")]').click()
#                driver.find_element_by_xpath('//*[@class="a-popover-content"]/ul/li[2]/span/a').click()

            except:
                print("exit[i=" + str(i) + "]")
                continue
        get_receipt()


def get_receipt():
    try:
        order_date = browser.find_element_by_xpath('/html/body/table[1]/tbody/tr/td/table[1]/tbody/tr/td[contains(., "注文日")]').text
    except:
        order_date = browser.find_element_by_xpath('/html/body/div[1]/table[1]/tbody/tr[2]/td').text
    try:
        title = browser.find_element_by_xpath('/html/body/table[1]/tbody/tr/td/table[2]/tbody/tr/td/table/tbody/tr[2]/td/table/tbody/tr/td/table[2]/tbody/tr[2]/td[1]/i').text
    except:
        try:
            # 「領収書等」クリック後に「領収書／購入明細書」リンクがある場合の領収書画面
            title = browser.find_element_by_xpath('/html/body/div[1]/table[2]/tbody/tr[2]/td/table/tbody/tr/td/table/tbody/tr[2]/td[1]/b/a').text
        except:
            # アプリ用「領収書／購入明細書」リンクがある場合の領収書画面
            title = browser.find_element_by_xpath('/html/body/table[1]/tbody/tr/td/table[2]/tbody/tr/td/table/tbody/tr[3]/td/table/tbody/tr/td/table[2]/tbody/tr[2]/td[1]/i').text
    # 長いタイトルとスラッシュを削除
    title = title.replace('/', '')
    title = title[:20]

    # スクリーンショットの保存
    page_width = browser.execute_script('return document.body.scrollWidth')
    page_height = browser.execute_script('return document.body.scrollHeight') + 120
    browser.set_window_size(page_width, page_height)
    time.sleep(1)
    browser.save_screenshot(pickDate(order_date) + "_" + title + ".png")

    browser.back()


def scrape_orders():
    pages_remaining = True

    while pages_remaining:
        get_item()
        get_price_date()
        # click_receipt_link()

        try:
            next_page_button = browser.find_element_by_class_name("a-last")
            if 'a-disabled' in next_page_button.get_attribute('class'):
                break
            else:
                next_page_button.click()
                time.sleep(1)
        except NoSuchElementException:
            break

    item_list = concatenate_page_data()

    return item_list


item_orders = scrape_orders()

item_orders.to_csv("2020_goods_list.csv", encoding="utf-8_sig")

print("END")
