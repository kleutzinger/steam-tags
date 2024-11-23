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

import json
import os
import random
import sys
from dataclasses import asdict, dataclass

from bs4 import BeautifulSoup
from pywebio import start_server
from pywebio.input import radio
from pywebio.output import output, put_html, put_markdown, toast
from pywebio.session import run_js, set_env

TAG_HTML_FILE = "./Steam Game Tags · SteamDB (11_22_2024 11：28：25 PM).html"


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


def append_tag_jsonl(tag: Tag, json_file="steam-tags.jsonl"):
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


def scrape_search_page():
    # use bs4 to parse TAG_HTML_FILE
    with open(TAG_HTML_FILE, "r") as f:
        soup = BeautifulSoup(f, "html.parser")
        """
        <div class="label" data-s="DRIVING">
        <a class="btn btn-outline tag-color-6" href="/tag/1644/"><span aria-hidden="true">🚗 </span>Driving</a>
        <span class="label-count">3067</span>
        </div>
        """
        tags = soup.find_all("div", class_="label")
        seen_ids = set()
        tag_store = []
        for tag in tags:
            name = tag.find("a").text
            name = " ".join(name.split(" ")[1:])  # rm emoji
            url = tag.find("a")["href"]
            num_games = int(tag.find("span", class_="label-count").text)
            tag_id = url.split("/")[-2]
            if tag_id in seen_ids:
                continue
            seen_ids.add(tag_id)
            tag = Tag(name=name, id=tag_id, url=url, num_games=num_games)
            tag_store.append(tag)
        tag_store = sorted(tag_store, key=lambda x: x.name)
        os.remove("steam-tags.jsonl")
        for tag in tag_store:
            append_tag_jsonl(tag)


def biased_random_tags():
    # choose two tags that tend to be close-ish in num_games
    tags = list(read_tag_jsonl())
    while True:
        tag0, tag1 = random.sample(tags, 2)
        if abs(tag0.num_games - tag1.num_games) < 1000:
            return tag0, tag1


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
            "[example search for tag 'Indie'](https://steamdb.info/tag/492/)\n"
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
            toast(f"Correct!!!: {more} > {less}", duration=10, position="right")
        else:
            toast(
                f"Incorrect! {more} > {less}",
                duration=10,
                color="error",
                position="right",
            )
        output(f"** {choice} **, {not_choice} ")


def main():
    if "s" in sys.argv:
        scrape_search_page()
    else:
        start_server(
            guess_tag,
            port=os.environ.get("PORT", 8081),
            debug=os.environ.get("DEBUG", False),
        )


if __name__ == "__main__":
    main()
