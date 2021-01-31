#!/usr/bin/python

import asyncio
from dataclasses import dataclass, field, asdict
from typing import List
from requests import get
import json
import colorama
from math import floor
from requests.exceptions import ConnectionError, ReadTimeout
import queue

import concurrent.futures
from colorama import Fore, Back, Style


try:
    from secrets import API_KEY
except:
    API_KEY = ""

F_COLOR = Fore.YELLOW  # print text collor

MAX_PICTURES = 500  # max picture to download
WALLPAPER_PATH = "Pictures/wallpapers"  # path to download folder

MAX_PICTURES = (24, MAX_PICTURES)[MAX_PICTURES >= 24]


@dataclass(eq=False)
class url_parameters:
    apikey: str = API_KEY  # needed for getting NSFW pictures
    q: str = ""  # Search query - Your main way of finding what you're looking for
    categories: str = "111"  # 100/101/111* (general/anime/people)
    purity: str = "111"  # 100*/110/111(sfw/sketchy/nsfw)
    sorting: str = (
        "toplist"  # date_added*, relevance, random, views, favorites, toplist
    )
    order: str = "desc"  # desc*, asc
    topRange: str = "1M"  # 1d, 3d, 1w,1M*, 3M, 6M, 1y
    atleast: str = ""  # Minimum resolution allowed
    resolutions: str = ",".join(
        (lambda: ["1920x1080", "1920x1200"])()
    )  # List of exact wallpaper resolutions ,Single resolution allowed
    ratios: str = ",".join((lambda: ["16x9", "16x10"])())
    colors: str = ",".join((lambda: [])())
    page: str = "1"  # 24 pic per page
    seed: str = ""  # Optional seed for random results

    def __parse_get_request(self, url, params=None) -> str:
        # WALHAVEN_API_URL = "https://wallhaven.cc/api/v1/search"
        try:
            response = get(url, params=params, timeout=10)
        except (ConnectionError, ReadTimeout) as a:
            pass
        return response

    def __compose_picure_download_list(self, pages, seed):
        WALHAVEN_API_URL = "https://wallhaven.cc/api/v1/search"

        r = self.__parse_get_request(
            WALHAVEN_API_URL, self.__dict__
        ).json()  # get 1st page, plus metadata of query
        current_page, pages, per_page, total, query, seed = r.get("meta").values()
        if total == 0:
            return "0 search result for query:{}".format(query)
        elif pages == 1:  # only one page of pics to download
            return r.get("data")  # return list
        elif total > MAX_PICTURES:
            # limitig max pictures to download
            pages = int(floor(MAX_PICTURES / 24.0))

        pic_list = r.get("data")
        d = self.__dict__
        param_list = []
        for i in range(2, pages + 1):
            d["page"] = i
            param_list.append(d)
            self.__summon_worker_bees()
        return 0


def save_pic(url, id):
    r = get(url)
    with open(id, "wb+") as f:
        f.write(r.content)


from random import randint
from time import sleep


def download_page_data(url):
    sleep(0.5)

    data = requests.get(url, timeout=10)
    if data.status_code == 429:
        sleep(float(randint(5000, 10000)) / 1000)
        data = requests.get(url, timeout=10)
    if data.status_code != 200:
        return (
            "FAILED WITH STATUS CODE:{}{}".format(F_COLOR, data.status_code),
            False,
            url,
        )
    q = []
    for item in data.json().get("data"):
        q.append(item)
    return (
        "Finished page: {color}{page}".format(
            color=F_COLOR, page=data.json().get("meta").get("current_page")
        ),
        True,
        q,
    )


import pathlib


def download_picture(name, url, path):
    sleep(float(randint(5, 9) / 10))
    try:
        data = get(url, timeout=10)
    except (ReadTimeout, ConnectionError) as e:
        return (
            "Error:{}{}".format(F_COLOR, e),
            False,
            url,
        )
    if data.status_code == 429:
        sleep(float(randint(5000, 10000)) / 1000)
        data = requests.get(url, timeout=10)
    if data.status_code != 200:
        return (
            "FAILED WITH STATUS CODE:{}{}".format(F_COLOR, data.status_code),
            False,
            url,
        )
    with open(path / name, "wb+") as f:
        f.write(data.content)

    return "SUCCESS: {}{}".format(F_COLOR, path / name), True, url


def main():
    request = url_parameters()
    colorama.init(autoreset=True)
    print("Sending GET url:\n{color}{url}".format(color=F_COLOR, url=request))
    data = requests.get(request).json().get("meta")
    print(
        """max Pages: {color}{pages}{endcolor}
total pictures: {color}{total}{endcolor}""".format(
            color=F_COLOR,
            endcolor=Fore.RESET,
            pages=data.get("last_page"),
            total=data.get("total"),
        )
    )
    if data.get("total") > MAX_PICTURES:
        MAX_PAGES = floor(MAX_PICTURES / 24)
        print(
            "Limiting max picures to: {color}{max}{endcolor}, (pages: {color}{pages}{endcolor})".format(
                color=F_COLOR, max=MAX_PAGES * 24, endcolor=Fore.RESET, pages=MAX_PAGES
            )
        )
    else:
        MAX_PAGES = data.get("last_page")

    print(
        "Downloading {color}{pictures}{endcolor}".format(
            color=F_COLOR, endcolor=Fore.RESET, pictures=MAX_PAGES * 24
        )
    )
    q = generate_url_page_list(MAX_PAGES)
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
        futures = []
        fail = []
        succes = []
        for u in q:
            futures.append(executor.submit(download_page_data, u))
        for future in concurrent.futures.as_completed(futures):
            message, status, data = future.result()
            if status:
                succes.extend(data)
            else:
                fail.append(data)
            print(message)

        print(fail)

    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
        futures = []
        path = pathlib.Path.home() / pathlib.Path(WALLPAPER_PATH)

        for url in succes:
            f = path / pathlib.Path(url.get("resolution"))
            if not f.exists():
                f.mkdir(parents=True)

            name = pathlib.Path(
                "{}.{}".format(url.get("id"), url.get("file_type").split("/")[1])
            )
            futures.append(executor.submit(download_picture, name, url.get("path"), f))
        fail_pictures = []
        for future in concurrent.futures.as_completed(futures):
            message, status, data = future.result()
            if status:
                succes.append(data)
            else:
                fail_pictures.append(data)
            print(message)

    return 0


if __name__ == "__main__":
    print(main())