#!/usr/bin/env python3

"""
num_games_with_tag:
parseInt(document.querySelector('.btnv6_blue_hoverfade > span:nth-child(1)').innerText.split(" ")[2].replace(",", ""))

tag_name:
document.querySelector('.browse_tag_games > h3:nth-child(1) > a:nth-child(1)').innerText

all tags:
[... document.querySelectorAll('div.tag_browse_tag')]

todo: log guesses somewhere
todo: scrape without an initial list of tags
todo: add automated scraping (github action?, dokku predeploy?)
"""
import random
import sys
from dataclasses import dataclass, asdict
import json
import os
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait

from pywebio import start_server
from pywebio.output import *
from pywebio.input import *
from pywebio.session import run_js, set_env

STEAM_URL = "https://store.steampowered.com/tag/browse/"
FULL_TAG_SEARCH_PAGE = "https://store.steampowered.com/search/?&category1=998&ndl=1&tags=492&ignore_preferences=1"
TAG_SEARCH_PAGE = "https://store.steampowered.com/search/?&category1=998&ndl=1"


@dataclass
class Tag:
    name: str
    id: int
    url: str
    num_games: int = -1

    def __repr__(self):
        return f"{self.name} {self.num_games}"


def get_list_of_tags() -> list[Tag]:
    # todo: get list of tags from here: https://steamdb.info/tags/
    output = []
    for tag in read_tag_jsonl():
        output.append(tag)
    return output


def dump_tag_jsonl(tag: Tag, json_file="steam-tags.jsonl"):
    with open(json_file, "a") as f:
        json.dump(asdict(tag), f)
        f.write("\n")


def read_tag_jsonl(json_file="steam-tags.jsonl"):
    with open(json_file, "r") as f:
        for line in f:
            yield Tag(**json.loads(line))


def get_seen_ids() -> set[str]:
    list_of_tags = list(read_tag_jsonl())
    return set([t.id for t in list_of_tags])


def scrape_search_page(tag_list: list[Tag]):
    driver = webdriver.Chrome("/Users/MyUsername/Downloads/chromedriver")
    TAG_SEARCH_PAGE = "https://store.steampowered.com/search/?&category1=998&ndl=1&ignore_preferences=1"
    seen_ids = get_seen_ids()
    for tag in tag_list:
        if tag.id in seen_ids:
            continue
        url = TAG_SEARCH_PAGE + "&tags=" + str(tag.id)
        driver.get(url)
        num_el = WebDriverWait(driver, 4000).until(
            EC.presence_of_element_located(
                (By.CSS_SELECTOR, "#search_results_filtered_warning_persistent > div")
            )
        )
        num_games = int(num_el.text.split(" ")[0].replace(",", ""))
        tag.num_games = num_games
        dump_tag_jsonl(tag)
        seen_ids.add(tag.id)
    driver.close()


def guess_tag():
    set_env(title="Steam Tags Popularity Guesser")
    put_html(
        """
        <script type="text/javascript">
            (function () {
                const cdn_script_url = 'https://cdn.jsdelivr.net/npm/kevbadge/kevbadge.js';
                let kevbadge = document.createElement('script'); kevbadge.type = 'text/javascript'; kevbadge.async = true;
                kevbadge.src = cdn_script_url;
                let s = document.getElementsByTagName('script')[0]; s.parentNode.insertBefore(kevbadge, s);
            })();
        </script> """
    )
    put_markdown(
        (
            f"[example search for tag 'Indie']({FULL_TAG_SEARCH_PAGE}) \n"
            "(DLC, Software, are not included in the count)"
        )
    )
    all_tags = [t for t in read_tag_jsonl()]
    while True:
        tag0, tag1 = random.sample(all_tags, 2)
        more, less = (tag0, tag1) if tag0.num_games > tag1.num_games else (tag1, tag0)
        answer_name = None
        while answer_name not in [tag0.name, tag1.name]:
            answer_name = radio(
                "Which tag has more games on Steam?",
                options=[tag0.name, tag1.name],
                inline=True,
                onchange=lambda _: run_js(
                    'document.querySelector("button.btn:nth-child(1)").click()'
                ),
            )
        choice = tag0 if answer_name == tag0.name else tag1
        not_choice = tag0 if choice == tag1 else tag1
        if choice == more:
            toast(f"Correct: {more} > {less}", duration=5, position="right")
        else:
            toast(
                f"Incorrect! {more} > {less}",
                duration=5,
                color="error",
                position="right",
            )
        output(f"** {choice} **, {not_choice} ")


def main():
    if "s" in sys.argv:
        scrape_search_page(get_list_of_tags())
    else:
        start_server(
            guess_tag,
            port=os.environ.get("PORT", 8081),
            debug=os.environ.get("DEBUG", False),
        )


if __name__ == "__main__":
    main()
