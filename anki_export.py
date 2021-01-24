#!/usr/bin/env python3
# Initially created by airmack 21.Dec.2020

from bs4 import BeautifulSoup
import genanki
from genanki.model import Model

import time
import logging

MAJOR_VERSION = 0
MINOR_VERSION = 1
PATCH_LEVEL = 0

VERSION_STRING = str(MAJOR_VERSION) + "." + \
    str(MINOR_VERSION) + "." + str(PATCH_LEVEL)
__version__ = VERSION_STRING

japanese_fields = [
    {
        'name': 'Kana',
        'font': 'Arial',
    },
    {
        'name': 'English',
        'font': 'Arial',
    },
    {
        'name': 'Kanji',
        'font': 'Arial',
    },
    {
        'name': 'Japanese_Audio',
        'font': 'Arial',
    },
    {
        'name': 'English_Audio',
        'font': 'Arial',
    },

    {
        'name': 'Image',
        'font': 'Arial',
    },
    {
        'name': 'Example_Kanji',
        'font': 'Arial',
    },
    {
        'name': 'Example_Kana',
        'font': 'Arial',
    },
    {
        'name': 'Example_English',
        'font': 'Arial',
    },
    {
        'name': 'Example_Japanese_Audio',
        'font': 'Arial',
    },
    {
        'name': 'Example_English_Audio',
        'font': 'Arial',
    },
]


BASIC_AND_REVERSED_CARD_JP_MODEL = Model(
    # kana, english, kanji, japanese_audio, english_audio,image, example_Kanji, example_Kana, example_japanese_audio, example_englisch_audio
    12938896,
    'Basic (and reversed card) (genanki)',
    fields=japanese_fields,
    templates=[
        {
            'name': 'Card 1',
            'qfmt': '{{Image}}\n\n{{Kanji}}',
            'afmt': """
            {{FrontSide}}\n\n<hr id=answer>\n\n{{Kana}}{{Japanese_Audio}}<br>{{English}}\n\n
            {{Example_Kanji}}{{Example_Kana}}{{Example_Japanese_Audio}} {{Example_English}}{{Example_English_Audio}}
            """
        },
        {
            'name': 'Card 2',
            'qfmt': '{{Image}}\n\b{{English}}{{English_Audio}}',
            'afmt': """
            {{FrontSide}}\n\n<hr id=answer>\n\n{{Kanji}}<br>{{Kana}}{{Japanese_Audio}}\n\n
            {{Example_Kanji}}{{Example_Kana}}{{Example_Japanese_Audio}} {{Example_English}}{{Example_English_Audio}}
            """
        },
    ],
    css='.card {\n font-family: arial;\n font-size: 20px;\n text-align: center;\n color: black;\n background-color: white;\n}\n',
)


def createKeyIfNeeded(parent, cards):
    if cards.get(parent) == None:
        cards[parent] = dict()
    return cards


class Language:
    """Primitive class with abstract function.
       Scraper needs to return a list of files that need to be downloaded. The download itself need to be done somplace else.
       CreateDeck creates the anki deck from the vocabulary."""

    def __init__(self):
        self.language = ""

    def Scraper(self, root_url, lesson_soup):
        return []

    def CreateDeck(self, title):
        pass


class Japanese(Language):
    def __init__(self):
        """Several states need to be stored. They are defined here and later on used when creating the deck."""
        self.language = "Japanese"
        self.cards = dict()
        self.audio_files = []
        self.card_fields = []
        self.finalizedCards = dict()
        for i in japanese_fields:
            self.card_fields.append(i["name"])

    def GetKanji(self, lesson_soup):
        for i in lesson_soup.find_all("span",  {"lang": "ja", "class": None}):
            parent = hash(i.find_parent("tr"))
            self.cards = createKeyIfNeeded(parent, self.cards)
            self.cards[parent]["Kanji"] = i.get_text().strip()

    def GetEnglih(self, lesson_soup):
        for i in lesson_soup.find_all("span",  {"class": "lsn3-lesson-vocabulary__definition", "dir": "ltr"}):
            # we ignore sample sentences
            if i.find_parent("span", {"class": "lsn3-lesson-vocabulary__sample js-lsn3-vocabulary-examples"}):
                continue
            parent = hash(i.find_parent("tr"))
            self.cards = createKeyIfNeeded(parent, self.cards)
            self.cards[parent]["English"] = i.get_text().strip()

    def GetKana(self, lesson_soup):
        for i in lesson_soup.find_all("span",  {"lang": "ja", "class": "lsn3-lesson-vocabulary__pronunciation"}):
            parent = hash(i.find_parent("tr"))
            self.cards = createKeyIfNeeded(parent, self.cards)
            self.cards[parent]["Kana"] = i.get_text().strip()[
                1:-1].strip()

    def GetAudio(self, lesson_soup):
        needsToBeDownloaded = []
        for i in lesson_soup.find_all("button",  {"class": "js-lsn3-play-vocabulary", "data-type": "audio/mp3", "data-speed": None}):
            if i.find_parent("span", {"class": "lsn3-lesson-vocabulary__sample js-lsn3-vocabulary-examples"}) or i.find_parent("td", {"class": "lsn3-lesson-vocabulary__td--play05 play05"}):
                continue
            url_filename = i["data-src"].strip()
            needsToBeDownloaded.append(url_filename)
            name = url_filename.split('/')[-1]
            self.audio_files.append(name)

            parent = hash(i.find_parent("tr"))
            self.cards = createKeyIfNeeded(parent, self.cards)
            self.cards[parent]["Japanese_Audio"] = "[sound:" + name + "]"
            self.cards[parent]["audio_files"] = name
        return needsToBeDownloaded

    def Scraper(self, root_url, lesson_soup):
        """Parse through the vocabulary section and get kanji, kana, english definition and audio."""
        self.GetKanji(lesson_soup)
        self.GetKana(lesson_soup)
        self.GetEnglih(lesson_soup)
        needsToBeDownloaded = self.GetAudio(lesson_soup)

        self.SanityCheck()
        # self.FinalizeCards()

        return needsToBeDownloaded

    def SanityCheck(self):
        for i in self.cards:
            for j in self.card_fields:
                if self.cards[i].get(j) is None:
                    self.cards[i][j] = ""
                    logging.debug(j + " does not exist")

    def FinalizeCard(self, entry):
        finalizedCards = []
        for j in self.card_fields:
            finalizedCards.append(entry.get(j))
        return finalizedCards

    def CreateDeck(self, title):
        """Create a deck from all vocabulary entries"""
        deck = genanki.Deck(abs(hash(title)), title)
        for i in self.cards:
            final_card = self.FinalizeCard(self.cards[i])
            deck.add_note(genanki.Note(
                BASIC_AND_REVERSED_CARD_JP_MODEL, final_card))
        my_package = genanki.Package(deck)
        my_package.media_files = self.audio_files
        local_file = "".join(title.split()) + ".apkg"
        my_package.write_to_file(local_file, timestamp=time.time())
        logging.info("Created " + local_file)

    def Filler(self):
        pass


class MostFrequentWordsJapanese(Language):
    pass
