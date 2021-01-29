#!/usr/bin/env python3
# Initially created by airmack 21.Dec.2020

from bs4 import BeautifulSoup
import genanki
from genanki.model import Model

import time
import logging

import sys
from os.path import expanduser
from os import path

MAJOR_VERSION = 0
MINOR_VERSION = 2
PATCH_LEVEL = 0

VERSION_STRING = str(MAJOR_VERSION) + "." + \
    str(MINOR_VERSION) + "." + str(PATCH_LEVEL)
__version__ = VERSION_STRING


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

    def Scraper(self, lesson_soup):
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
        self.exampleCounter = 0

    def GetKanji(self, lesson_soup):
        for i in lesson_soup.find_all("span",  {"lang": "ja", "class": None}):
            parent = hash(i.find_parent("tr"))
            self.cards = createKeyIfNeeded(parent, self.cards)
            self.cards[parent]["Kanji"] = i.get_text().strip()

    def GetEnglish(self, lesson_soup):
        """Get the enlish translation of the vocabulary"""
        for i in lesson_soup.find_all("span",  {"class": "lsn3-lesson-vocabulary__definition", "dir": "ltr"}):
            # we ignore sample sentences
            if i.find_parent("span", {"class": "lsn3-lesson-vocabulary__sample js-lsn3-vocabulary-examples"}):
                continue
            parent = hash(i.find_parent("tr"))
            self.cards = createKeyIfNeeded(parent, self.cards)
            self.cards[parent]["English"] = i.get_text().strip()

    def GetKana(self, lesson_soup):
        """Get the kana version of the vocabulary"""
        for i in lesson_soup.find_all("span",  {"lang": "ja", "class": "lsn3-lesson-vocabulary__pronunciation"}):
            parent = hash(i.find_parent("tr"))
            self.cards = createKeyIfNeeded(parent, self.cards)
            self.cards[parent]["Kana"] = i.get_text().strip()[1:-1].strip()

    def GetExampleKanji(self, lesson_soup):
        """Extract all examples including the japanese audio. Don't care about the english audio"""
        exampleCounter = 0
        needsToBeDownloaded = []
        for i in lesson_soup.find_all("span",  {"lang": "ja", "class": "lsn3-lesson-vocabulary__term"}):
            parent = hash(i.find_parent("tr").find_parent("tr"))
            self.cards = createKeyIfNeeded(parent, self.cards)
            j = 0
            while "Example_Kanji_" + str(j) in self.cards[parent].keys():
                j += 1
            self.cards[parent]["Example_Kanji_" +
                               str(j)] = i.get_text().strip()
            x = i.parent.parent.find(
                "button", {"class": "js-lsn3-play-vocabulary", "data-type": "audio/mp3", "data-speed": None})
            self.exampleCounter = max(self.exampleCounter, j+1)
            if not x:
                continue

            url_filename = x["data-src"].strip()
            if url_filename.find("http://") == -1:
                url_filename = "https://www.japanesepod101.com/" + url_filename

            needsToBeDownloaded.append(url_filename)
            name = url_filename.split('/')[-1]
            self.audio_files.append(name)
            self.cards = createKeyIfNeeded(parent, self.cards)
            self.cards[parent]["Example_Japanese_Audio_" +
                               str(j)] = "[sound:" + name + "]"
            self.cards[parent]["audio_files"] = name

        return needsToBeDownloaded

    def GetExampleEnglish(self, lesson_soup):
        """Extract english translation of the exsample"""
        for i in lesson_soup.find_all("span",  {"dir": "ltr", "class": "lsn3-lesson-vocabulary__definition"}):
            if not i.find_parent("span", {"class": "lsn3-lesson-vocabulary__sample"}):
                continue
            parent = hash(i.find_parent("tr").find_parent("tr"))
            self.cards = createKeyIfNeeded(parent, self.cards)
            j = 0
            while "Example_English_" + str(j) in self.cards[parent].keys():
                j += 1
            self.cards[parent]["Example_English_" +
                               str(j)] = i.get_text().strip()

    def GetExamples(self, lesson_soup):
        needsToBeDownloaded = []
        needsToBeDownloaded += self.GetExampleKanji(lesson_soup)
        self.GetExampleEnglish(lesson_soup)
        return needsToBeDownloaded

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

    def Scraper(self, lesson_soup):
        """Parse through the vocabulary section and get kanji, kana, english definition and audio."""
        needsToBeDownloaded = []
        self.GetKanji(lesson_soup)
        self.GetKana(lesson_soup)
        self.GetEnglish(lesson_soup)
        needsToBeDownloaded += self.GetExamples(lesson_soup)
        needsToBeDownloaded += self.GetAudio(lesson_soup)
        self.CreateSaneFIeldNames()
        self.SanityCheck()

        return needsToBeDownloaded

    def CreateSaneFIeldNames(self):
        """Generate Sane values for all anki fields (amount of fields must match the amount of examples)"""
        self.japanese_fields = [
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
            }
        ]

        for i in range(self.exampleCounter):
            self.japanese_fields += [

                {
                    'name': 'Example_Kanji_' + str(i),
                    'font': 'Arial',
                },
                {
                    'name': 'Example_Kana_' + str(i),
                    'font': 'Arial',
                },
                {
                    'name': 'Example_English_' + str(i),
                    'font': 'Arial',
                },
                {
                    'name': 'Example_Japanese_Audio_' + str(i),
                    'font': 'Arial',
                },
                {
                    'name': 'Example_English_Audio_' + str(i),
                    'font': 'Arial',
                }
            ]
        for i in self.japanese_fields:
            self.card_fields.append(i["name"])

    def SanityCheck(self):
        """Fill in all the missing gaps in our cards"""
        for i in self.cards:
            for j in self.card_fields:
                if self.cards[i].get(j) is None:
                    self.cards[i][j] = ""
                    logging.debug(j + " does not exist")

    def FinalizeCard(self, entry):
        """Helper function to put all the entries for the card in the correct order"""
        finalizedCards = []
        for j in self.card_fields:
            finalizedCards.append(entry.get(j))
        return finalizedCards

    def CreateDynamicModel(self):
        """Creates a dynamic model depending on the maximum amount of samples that we have"""

        afmt_card1 = """{{FrontSide}}\n\n<hr id=answer>\n\n{{Kana}}{{Japanese_Audio}}<br>{{English}}\n\n"""
        afmt_card2 = """{{FrontSide}}\n\n<hr id=answer>\n\n{{Kanji}} <br> {{Kana}}{{Japanese_Audio}}\n\n"""
        examples = ""
        for i in range(self.exampleCounter):
            examples += "<br> {{Example_Kanji_" + str(i) + "}}{{Example_Kana_" + str(i) + "}}{{Example_Japanese_Audio_" + str(
                i) + "}} {{Example_English_" + str(i) + "}}{{Example_English_Audio_" + str(i) + "}}\n\n"

        templates = [
            {
                'name': 'Card 1',
                'qfmt': '{{Image}}\n\n{{Kanji}}',
                'afmt': afmt_card1 + examples
            },
            {
                'name': 'Card 2',
                'qfmt': '{{Image}}\n\n{{English}}{{English_Audio}}',
                'afmt': afmt_card2 + examples
            },
        ]
        card_model = Model(
            12938896 + self.exampleCounter,
            'Basic (and reversed card) (genanki)_' + str(self.exampleCounter),
            fields=self.japanese_fields,
            templates=templates,
            css='.card {\n font-family: arial;\n font-size: 20px;\n text-align: center;\n color: black;\n background-color: white;\n}\n',
        )
        return card_model

    def CreateDeck(self, title):
        """Create a deck from all vocabulary entries"""
        deck = genanki.Deck(abs(hash(title)), title)
        model = self.CreateDynamicModel()

        for i in self.cards:
            try:
                final_card = self.FinalizeCard(self.cards[i])
                deck.add_note(genanki.Note(model, final_card))
            except Exception as e:
                logging.error(e)
                logging.error(f"Can't create {final_card}")

        my_package = genanki.Package(deck)
        my_package.media_files = self.audio_files
        local_file = "".join(title.split()) + ".apkg"
        my_package.write_to_file(local_file, timestamp=time.time())
        logging.info("Created " + local_file)


class MostFrequentWordsJapanese(Japanese):
    def GetStuff(self, item, elment, dic, cardfield):
        kanji = item.find(
            elment, dic)
        if kanji == None:
            logging.warning("No Kanji content found")
            return

        parent = hash(kanji.find_parent(
            "div", {"class": "wlv-item js-wlv-item"}))
        self.cards = createKeyIfNeeded(parent, self.cards)
        self.cards[parent][cardfield] = kanji.get_text().strip()

    def GetImage(self, item):
        needsToBeDownloaded = []
        image_node = item.find("img", {"class": "wlv-item__image"})
        if image_node == None:
            logging.warning("No picture found")
            return needsToBeDownloaded

        parent = hash(image_node.find_parent(
            "div", {"class": "wlv-item js-wlv-item"}))
        self.cards = createKeyIfNeeded(parent, self.cards)
        url_filename = image_node["src"].strip()
        name = url_filename.split('/')[-1]
        self.audio_files.append(name)
        self.cards[parent]["Image"] = "<img src='" + name + "'>"

        needsToBeDownloaded.append(url_filename)
        return needsToBeDownloaded

    def GetAudioStuff(self, item, cardfield):
        needsToBeDownloaded = []
        audio_node = item.find("audio")
        if audio_node == None:
            logging.warning("No audio found")
            return needsToBeDownloaded

        parent = hash(audio_node.find_parent(
            "div", {"class": "wlv-item js-wlv-item"}))
        self.cards = createKeyIfNeeded(parent, self.cards)
        url_filename = audio_node["src"].strip()
        name = url_filename.split('/')[-1]
        self.audio_files.append(name)
        self.cards[parent][cardfield] = "[sound:" + name + "]"
        self.cards[parent]["audio_files"] = name

        needsToBeDownloaded.append(url_filename)
        return needsToBeDownloaded

    def Scraper(self, lesson_soup):
        """Parse through the vocabulary section and get kanji, kana, english definition and audio."""
        needsToBeDownloaded = []
        counter = 0
        for i in lesson_soup.find_all("div", {"class": "wlv-item js-wlv-item"}):
            needsToBeDownloaded += self.GetImage(i)
            needsToBeDownloaded += self.GetAudioStuff(i, "Japanese_Audio")
            self.GetStuff(
                i, "span", {"class": "wlv-item__word-zoom js-wlv-word-zoom"}, "Kanji")
            self.GetStuff(
                i, "span", {"class": "wlv-item__word-field js-wlv-word-field js-wlv-word-field-kana kana"}, "Kana")

            self.GetStuff(
                i, "span", {"class": "wlv-item__english js-wlv-english"}, "English")

            j = i.find("div", {"class", "wlv-item__samples"})
            if j == None:
                logging.warning("Can't find examples")
                continue

            self.GetStuff(
                j, "span", {"class": "wlv-item__word-zoom js-wlv-word-zoom"}, "Example_Kanji_0")

            self.GetStuff(
                j, "span", {"class": "wlv-item__word-field js-wlv-word-field kana"}, "Example_Kana_0")

            self.GetStuff(
                j, "span", {"class": "wlv-item__english"}, "Example_English_0")

            needsToBeDownloaded += self.GetAudioStuff(j, "Japanese_Audio")

        self.exampleCounter = 1  # only one sample for now
        self.CreateSaneFIeldNames()
        self.SanityCheck()

        return needsToBeDownloaded


def setupLogging():
    """ Provide setup logign in case we are running standalone"""
    logingpath = expanduser("~") + "/.local/share/languagepod101/"
    if not path.exists(logingpath):
        os.makedirs(logingpath)
    logging.basicConfig(level=logging.DEBUG,
                        format='%(asctime)s %(name)-12s %(levelname)-8s %(message)s',
                        datefmt='%m-%d %H:%M',
                        filename=logingpath + "lp101_anki.log",
                        filemode='w')
    console = logging.StreamHandler()
    console.setLevel(logging.INFO)
    formatter = logging.Formatter('%(name)-12s: %(levelname)-8s %(message)s')
    console.setFormatter(formatter)
    logging.getLogger('').addHandler(console)


def main(argv):
    """ Provide standalone main functionality"""
    data = ""
    lessons_soup = ""
    with open(argv[1]) as f:
        data = f.read()
    try:
        lessons_soup = BeautifulSoup(data, 'lxml')
    except Exception as e:
        logging.critical(e)
        logging.critical(
            'Failed to parse the webpage, "lxml" package might be missing.')
        exit(1)
    voc_scraper = MostFrequentWordsJapanese()
    downloadList = voc_scraper.Scraper(lessons_soup)
    save_name = "blobb.apkg"
    if argv[1].find(".") != -1:
        save_name = argv[1].split(".")[-2]

    voc_scraper.CreateDeck(save_name)


if __name__ == '__main__':
    if len(sys.argv) < 2:
        exit(1)
    setupLogging()
    main(sys.argv)
