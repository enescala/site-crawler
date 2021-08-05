#!/usr/bin/env python

import os
import json
import random
import requests
import sys
import time

from threading import Thread
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, TimeoutException


class PageParser(object):
    def __init__(self):
        self.is_cookie_closed = False
        self.threads = []
        self.driver = webdriver.Chrome()

        self.login_credentials = {
            'email': '',
            'password': ''
        }

        self.site = "https://adminv2.1stdibs.com/"
        self.inv_page = self.site + "dealers/inventory-management"
        self.pag_static = self.inv_page + "?page="

        self.user_agent = [
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_4) "
            "AppleWebKit/605.1.15 (KHTML, like Gecko)",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/78.0.3904.108 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/60.0.3112.78 Safari/537.36"
        ]

        self.savename = 'data.json'
        self.items = {}
        self.item_counter = 1

        # for testing only
        self.item_fname = 'product_4.html'
        self.inv_fname = 'inventory.html'

    def connect(self):
        try:
            self.login()
            self.parse_inv_page()
            for page in self.get_pags():
                self.load_page(page, "_70cef333"),
                self.parse_inv_page()
            self.save_file()
        finally:
            if self.threads:
                for thread in self.threads:
                    thread.join()
            self.driver.quit()

    def login(self):
        s_button = "_7bff02c7"

        self.load_page(self.inv_page, s_button)

        self.driver.find_element_by_name('email').send_keys(
            self.login_credentials['email']
        )
        self.driver.find_element_by_name('password').send_keys(
            self.login_credentials['password']
        )
        self.wait(3)
        self.driver.find_element_by_class_name(s_button).click()
        self.wait(10)

    def load_page(self, url, c_name):
        try:
            self.driver.get(url)
            WebDriverWait(self.driver, 20).until(
                EC.presence_of_element_located(
                    (By.CLASS_NAME, c_name)))
        except TimeoutException:
            self.driver.refresh()
        finally:
            self.wait(3)

    @staticmethod
    def wait(seconds):
        time.sleep(seconds)

    def close_modal(self):
        try:
            self.driver.find_element_by_id("Modal")
        except NoSuchElementException:
            return False
        self.driver.find_element_by_css_selector(
            "div[data-tn='modal-close-button']").click()

        return True

    def close_cookie_notify(self):
        if self.is_cookie_closed:
            return True
        try:
            element = self.driver.find_element_by_css_selector(
                "div[data-tn='cookie-notification-close']")
        except NoSuchElementException:
            return False
        element.click()

        return True

    def click_btn_to_load_image(self, clicks):
        try:
            self.driver.find_element_by_css_selector(
                "button[data-tn='carousel-next-arrow']")
        except NoSuchElementException:
            return False

        for i in range(0, clicks):
            self.driver.find_element_by_css_selector(
                "button[data-tn='carousel-next-arrow']").click()
            self.wait(1)
        self.wait(3)

        return True

    @staticmethod
    def get_item_link(item):
        return item.find("a", {"data-tn": "item-title"})

    @staticmethod
    def clear_price(price):
        price = price.replace(',', '')
        price = price.replace('€', '')
        return price

    def get_price(self, item):
        return self.clear_price(
            self.get_inv_el_details(item, "span", "list-price-value"))

    def get_offer_price(self, item):
        a_offer_class = "_9b10122"
        value = item.find("span", {"data-tn": "automatedOffer-price-value"})
        offer_price = value.find("span", class_=a_offer_class)

        if offer_price:
            price = offer_price
        else:
            offer_price = value.find("strong", class_=a_offer_class)
            if offer_price:
                price = offer_price
        if price:
            price = self.clear_price(
                price.get_text())
        else:
            price = ''

        return price

    @staticmethod
    def get_num_of_images(item):
        content = item.find("div", class_="_ba78c34f")
        res = content.get_text() if content else None
        if res:
            return int("".join([str(s) for s in res.split() if s.isdigit()]))
        return 0

    @staticmethod
    def get_categories(soup):
        exclude = ["Home", "Jewelry & Watches"]
        categories = []
        breadcrumbs = soup.find_all("a", {"data-tn": "breadcrumb-item"})
        for category in breadcrumbs:
            name = category.get_text().strip()
            if name not in exclude:
                categories.append(name)
        return ",".join(categories)

    @staticmethod
    def get_description(soup):
        desc = soup.find("span", {"data-tn": "pdp-item-description-content"})
        return desc.get_text() if desc else ''

    @staticmethod
    def get_item_details(soup, attr):
        content = []
        res = soup.find("div", {"data-tn": attr})
        if not res:
            return ""
        items = res.find_all("span")
        for item in items:
            el = item.get_text()
            if el not in content:
                content.append(el)
        return ",".join(content)

    @staticmethod
    def get_inv_el_details(item, el, attr):
        content = item.find(el, {"data-tn": attr})
        return content.get_text() if content else ''

    def parse_inv_page(self):
        page = self.driver.page_source
        soup = BeautifulSoup(page, 'html.parser')
        items = soup.find_all('div', class_="_70cef333")
        for item in items:
            link = self.get_item_link(item)
            url = link.get('href')
            ref_number = self.get_inv_el_details(
                item, "span", "reference-number")
            num_of_images = self.get_num_of_images(item)
            inv_data = dict([
                ('url', url),
                ('title', link.get_text()),
                ('price', self.get_price(item)),
                ('automated_private_offer', self.get_offer_price(item)),
                ('status', self.get_inv_el_details(item, "a", "publishing-details")),
                ('reference_number', ref_number),
                ('dealer_reference_number', self.get_inv_el_details(item, "span", "dealer-ref-number")),
                ('creator', self.get_inv_el_details(item, "span", "creator-name")),
                ('shipping', self.get_inv_el_details(item, "a", "shipping-details")),
                ('number_of_images', str(num_of_images))])

            self.load_page(url, "_c9c05aa3"),
            item_data = self.parse_item_page(
                num_of_images, ref_number)

            self.items.update([
                (f"item-{self.item_counter}", {**inv_data, **item_data})])
            self.item_counter += 1

    def parse_item_page(self, num_of_images, fname):
        self.close_modal()
        self.is_cookie_closed = self.close_cookie_notify()
        self.click_btn_to_load_image(num_of_images)
        item_data = {}
        images = {}
        page = self.driver.page_source
        soup = BeautifulSoup(page, 'html.parser')
        carousel = soup.find_all("div", class_="_402eacf8")
        for counter, image in enumerate(carousel, start=1):
            img = image.find("img", {"data-tn": "pdp-hero-carousel-image"})
            image_src = img['srcset'].split('?')[0] if img else None
            if image_src:
                filename = self.make_filename(
                    fname,
                    counter,
                    self.get_extension_from_url(image_src))
                thread = Thread(target=self.download_file, args=(
                    image_src,
                    self.make_filename_path(filename)))
                thread.start()
                self.threads.append(thread)
                images[f"image-{counter}"] = filename
        item_data = dict([
            ('images', images),
            ('categories', self.get_categories(soup)),
            ('description', self.get_description(soup)),
            ('in_the_style_of', self.get_item_details(soup, "pdp-spec-in-the-style-of")),
            ('place_of_origin', self.get_item_details(soup, "pdp-spec-place-of-origin")),
            ('date_of_manufacture', self.get_item_details(soup, "pdp-spec-date-of-manufacture")),
            ('period', self.get_item_details(soup, "pdp-spec-period")),
            ('metal', self.get_item_details(soup, "pdp-spec-metal")),
            ('stone', self.get_item_details(soup, "pdp-spec-stone")),
            ('stone_cut', self.get_item_details(soup, "pdp-spec-stone-cut")),
            ('condition', self.get_item_details(soup, "pdp-spec-condition")),
            ('dimensions', self.get_item_details(soup, "pdp-spec-dimensions")),
            ('diameter', self.get_item_details(soup, "pdp-spec-diameter")),
            ('length', self.get_item_details(soup, "pdp-spec-length")),
            ('weight', self.get_item_details(soup, "pdp-spec-weight")),
            ('seller_location', self.get_item_details(soup, "pdp-spec-seller-location"))])
        return item_data

    @staticmethod
    def make_filename_path(name):
        path = os.path.dirname(os.path.realpath(__file__))
        return f"{path}/images/{name}"

    @staticmethod
    def make_filename(name, num, extension):
        return f"{name}-{num}{extension}"

    @staticmethod
    def get_extension_from_url(url):
        parts = url.split('/')[-1]
        _, extension = os.path.splitext(parts)
        return extension.lower()

    def get_pags(self):
        result = []
        num_pages = 18
        for num in range(2, num_pages):
            url = self.pag_static + str(num)
            result.append(url)
        return result

    def download_file(self, url, fname):
        if os.path.exists(fname):
            return

        try:
            r = requests.get(
                url,
                allow_redirects=True,
                headers={'User-Agent': random.choice(self.user_agent)})
            with open(fname, 'wb') as f:
                f.write(r.content)
        except ConnectionError:
            r.raise_for_status()

    def open_file(self, filename):
        try:
            with open(filename, 'r') as f:
                return f.read()
        except IOError:
            print(f"Could not open file {filename}")

    def save_file(self):
        with open(self.savename, 'w') as f:
            f.write(json.dumps(self.items))

    def main(self):
        self.connect()


if __name__ == '__main__':
    PageParser().main()
