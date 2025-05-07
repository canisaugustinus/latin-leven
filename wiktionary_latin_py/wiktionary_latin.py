# https://github.com/tatuylonen/wiktextract
# https://kaikki.org/dictionary/rawdata.html
# pybind11 stuff:
# https://learn.microsoft.com/en-us/visualstudio/python/working-with-c-cpp-python-in-visual-studio?view=vs-2022

# install this package:
# C:\Users\{USERNAME}\PycharmProjects\pythonProject\venv\Scripts\pip install {path}\weightdamleven_pybind11\weightdamleven\
# delete the auto-generated file:
# C:\Users\{USERNAME}\AppData\Local\JetBrains\PyCharmCE2021.3\python_stubs\{number}\weightdamleven.py
# then with THE "pybind11-stubgen" module:
# C:\Users\{USERNAME}\PycharmProjects\pythonProject\venv\Scripts\pybind11-stubgen -o {path_to_site-packages} weightdamleven
# and finally:
# make sure weightdamleven.pyi is in site-packages next to the .py file

import itertools
import os
import pathlib
import random
import threading
import time
from collections import defaultdict
import numpy as np
from send2trash import send2trash
from flask import Flask, request, render_template, make_response, redirect
from flask_socketio import SocketIO
import weightdamleven

print(f"weightdamleven library: {weightdamleven.__file__}")


class Latin:
    MAX_RESULTS = 100
    DIRECTORY = pathlib.Path(__file__).parent.resolve()
    LATIN_WORDS = os.path.join(DIRECTORY, "database", "latin_words.txt")
    LINKS = os.path.join(DIRECTORY, "database", "links.txt")
    if not pathlib.Path(LINKS).is_file():
        open(LINKS, 'w').close()

    def __init__(self):
        self._latin_words: list[str] = self.read_parsed_latin_words()  # list of latin words
        self._char_char_cost: defaultdict[tuple[str, str], complex] = self.calc_char_char_cost()  # the cost of replacing char1 with char2

        # str -> list[int] conversions because pybind11 wasn't playing nicely with (variable size) unicode
        self._char_int_dict: defaultdict[str, int] = self.calc_char_int_dict()  # maps from chars to encoding ints
        self._int_char_dict: dict[int, str] = self.calc_int_char_dict()  # maps from encoding ints to chars
        self._cost_matrix: list[list[float]] = self.calc_cost_matrix()  # self._cost_matrix[char_int_dict[char1]][char_int_dict[char2]] = the cost to turn char1 into char2
        self._latin_words_encoded: list[list[int]] = self.calc_latin_words_encoded()  # list of all words encoded as list[int]

    def get_int_char_dict(self) -> dict[int, str]:
        return self._int_char_dict

    def get_cost_matrix(self) -> list[list[float]]:
        return self._cost_matrix

    def get_latin_words_encoded(self) -> list[list[int]]:
        return self._latin_words_encoded

    def calc_char_set(self) -> dict[str, None]:
        """ char_set is the ordered set (dict[str, None]) of all characters used. """
        char_set = dict()  # use a dict to maintain insertion order

        # add all characters in the cost mapping --- critical to have these in char_set first
        for char_char in self._char_char_cost:
            for char in char_char:
                char_set[char] = None

        # add all characters in all latin words
        for word in self._latin_words:
            for char in word:
                char_set[char] = None
        return char_set

    def calc_char_int_dict(self) -> defaultdict[str, int]:
        """
        char_int_dict[char1] maps from char1 to encoding int1.
        Used this for cost matrix indexing:
        """
        char_set = self.calc_char_set()
        counter = 0
        char_int_dict = defaultdict(lambda: 0)
        for char in char_set:
            char_int_dict[char] = counter
            counter += 1
        # map unknown chars to space bar
        char_int_dict.default_factory = lambda: char_int_dict[' ']
        return char_int_dict

    def calc_int_char_dict(self) -> dict[int, str]:
        """
        int_char_dict[int1] maps from encoding int1 to char1.
        Turn the encoded words back into strings.
        cost_matrix[char_int_dict[char1]][char_int_dict[char2]] = the cost to turn char1 into char2.
        """
        int_char_dict = {}
        for char, val in self._char_int_dict.items():
            int_char_dict[val] = char
        return int_char_dict

    def calc_cost_matrix(self) -> list[list[float]]:
        """ cost_matrix[char_int_dict[char1]][char_int_dict[char2]] = the cost to turn char1 into char2. """
        char_set = set()
        for char_char in self._char_char_cost:
            for char in char_char:
                char_set.add(char)
        char_set_length = len(char_set)

        cost_matrix = [[0.0 for _j in range(char_set_length)] for _i in range(char_set_length)]
        for char_char in self._char_char_cost:
            char1, char2 = char_char
            i = self._char_int_dict[char1]
            j = self._char_int_dict[char2]
            cost_matrix[i][j] = self._char_char_cost[char_char]
        return cost_matrix

    def calc_latin_words_encoded(self) -> list[list[int]]:
        """ list of all words encoded as list[int]. """
        latin_words_encoded = []
        for word in self._latin_words:
            latin_words_encoded.append([self._char_int_dict[char] for char in word])
        return latin_words_encoded

    def get_random_word(self) -> str:
        """ Get a random Latin word. """
        return random.choice(self._latin_words)

    @classmethod
    def read_parsed_latin_words(cls) -> list[str]:
        """ Read in the saved list produced by WiktextractParser.parse_latin_word_list(). """
        with open(cls.LATIN_WORDS, 'r', encoding="utf-8") as f:
            latin_words = list(set(word.strip() for word in f.readlines()))
        return latin_words

    @classmethod
    def calc_char_char_cost(cls) -> defaultdict[tuple[str, str], complex]:
        """ char_char_cost[(char1, char2)] = the cost of replacing char1 with char2. """
        char_layout = [
            "qwertyuiop",
            "asdfghjkl",
            "zxcvbnm"]
        char_dict = defaultdict(lambda: 100.0 + 0j)  # complex values make finding the distance easier
        char_cols = [np.arange(len(row)) for row in char_layout]
        char_cols = [row + 0.5*i for i, row in enumerate(char_cols)]
        char_rows = [0.0, 1.0, 2.0]
        for row in range(len(char_layout)):
            for col in range(len(char_layout[row])):
                val = char_rows[row] + 1j*char_cols[row][col]
                char_dict[char_layout[row][col]] = val

        pairs = list(itertools.combinations(char_dict, 2))
        char_char_cost = defaultdict(lambda: 10.0)
        for a, b in pairs:
            cost = np.abs(char_dict[a] - char_dict[b])

            # all combinations of lower -> lower, lower -> upper, etc.
            a_up_low = [a.lower(), a.upper()]
            b_up_low = [b.lower(), b.upper()]
            for a in a_up_low:
                for b in b_up_low:
                    if a == b:
                        case_cost = 0.0
                    else:
                        case_cost = 0.1
                    char_char_cost[(a, b)] = cost + case_cost
                    char_char_cost[(b, a)] = cost + case_cost

        # change a given char from upper -> lower or lower -> upper
        for a in char_dict:
            a_up_low = [a.lower(), a.upper()]
            for a in a_up_low:
                for b in a_up_low:
                    if a == b:
                        case_cost = 0.0
                    else:
                        case_cost = 0.1
                    char_char_cost[(a, b)] = case_cost
                    char_char_cost[(b, a)] = case_cost
        return char_char_cost

    def convert_to_search_ints(self, word: str) -> list[int]:
        """ Remove long vowels and strip whitespace. Convert from unicode to ints. """
        text = self.convert_to_search_word(word)
        text_ints = [self._char_int_dict[char] for char in text]
        return text_ints

    @classmethod
    def create_url(cls, word: str) -> str:
        """ Get the wiktionary URL corresponding to "word." """
        return f'https://en.wiktionary.org/wiki/{word}#Latin'

    @classmethod
    def int_to_roman_numeral(cls, x: int) -> str:
        """ Convert a small int < 4000 to a Roman numeral. Yes, 'M' isn't strictly correct. """
        if x == 0:
            return " "
        if x < 0:
            raise ValueError("Roman numerals must be nonnegative.")
        if x >= 4000:
            print("This number is too large for the current implementation of Latin.int_to_roman_numeral()")
            return str(x)

        arabic = [1, 4, 5, 9, 10, 40, 50, 90, 100, 400, 500, 900, 1000]
        roman = ["I", "IV", "V", "IX", "X", "XL", "L", "XC", "C", "CD", "D", "CM", "M"]
        arabic_roman = list(zip(arabic, roman))[::-1]  # "[::-1]" because we want to start large
        result = ""
        for arabic_numeral, roman_numeral in arabic_roman:
            mult, x = x//arabic_numeral, x % arabic_numeral
            result += roman_numeral * mult  # repeat the current roman_numeral mult times
            if x == 0:
                break
        return result

    @classmethod
    def convert_to_search_word(cls, word: str) -> str:
        """ Remove long vowels and strip whitespace. """
        long_vowels_dict = {'ā': 'a', 'ē': 'e', 'ī': 'i', 'ō': 'o', 'ū': 'u'}
        long_vowels = set(long_vowels_dict.keys())
        for char in long_vowels:
            long_vowels_dict[char.upper()] = long_vowels_dict[char].upper()
        for long, short in long_vowels_dict.items():
            word = word.replace(long, short)
        return word.strip()

    @classmethod
    def load_links(cls) -> dict[str, str]:
        """ Load saved links. """
        links = {}
        with open(cls.LINKS, 'r') as f:
            for line in f:
                idx = line.find(',')
                if idx >= 0:
                    link = line[:idx].strip()
                    title = line[idx + 1:].strip()
                else:
                    link = line.strip()
                    title = link
                link = link.replace('"', '%22').replace("'", '%27')

                if not link:
                    continue
                links[title] = link
        return links

    @classmethod
    def save_links(cls, links: dict[str, str]):
        """ Save links in a database file. """
        with open(cls.LINKS, 'w') as f:
            for title, url in links.items():
                f.write(f"{url.strip()}, {title.strip()}\n")


def query_update_thread_func():
    """ An infinite loop that checks the latest 'query_update' """
    global latin_global
    global query_update_global
    global query_update_lock_global
    global wdl_global
    global wdl_suggestions_global

    while True:
        with query_update_lock_global:
            for request_sid in list(query_update_global.keys()):
                text = query_update_global.pop(request_sid)
                if not text:
                    socketio.emit('on_query_update_done', {'latin_words': []}, to=request_sid)
                    continue

                text_ints = latin_global.convert_to_search_ints(text)
                latin_words = wdl_suggestions_global.weighted_damerau_levenshtein_multithread(text_ints, 10)
                for i, ints in enumerate(latin_words):
                    latin_words[i] = ''.join([int_char_dict_global[ival] for ival in ints])
                suggestions = []
                for i, word in enumerate(latin_words):
                    suggestions.append([word, latin_global.create_url(word)])
                socketio.emit('on_query_update_done', {'suggestions': suggestions}, to=request_sid)
        time.sleep(0.001)


latin_global = Latin()
int_char_dict_global = latin_global.get_int_char_dict()
links_dict_global = latin_global.load_links()
images_total_global = {}
images_remaining_global = {}
searches_so_far_global = {}
query_update_lock_global = threading.Lock()
query_update_global = {}
query_update_thread = threading.Thread(target=query_update_thread_func)
query_update_thread.start()

is_cost_matrix = True
replace_cost = 10.0
insert_cost = 3.0
append_cost = 0.1
delete_cost = 3.0
transpose_cost = 2.0
wdl_global = weightdamleven.WeightDamLeven(
    latin_global.get_latin_words_encoded(),
    latin_global.get_cost_matrix(),
    is_cost_matrix,
    replace_cost,
    insert_cost,
    insert_cost,
    delete_cost,
    transpose_cost)
wdl_suggestions_global = weightdamleven.WeightDamLeven(
    latin_global.get_latin_words_encoded(),
    latin_global.get_cost_matrix(),
    is_cost_matrix,
    replace_cost,
    insert_cost,
    append_cost,
    delete_cost,
    transpose_cost)

app = Flask(__name__)
app.config["UPLOAD_FOLDER"] = os.path.join("static", "IMG")
socketio = SocketIO(app)


def random_image() -> str:
    global latin_global
    global images_total_global
    global images_remaining_global

    # check for any changes to the image folder content
    full_dir = os.path.join(latin_global.DIRECTORY, app.config["UPLOAD_FOLDER"])
    images_total_local = {}
    for image in os.listdir(full_dir):
        if os.path.isfile(os.path.join(full_dir, image)):
            images_total_local[image] = None

    # add new images to the ordered set
    for image in images_total_local:
        if image not in images_total_global:
            # a new image has been added to the folder
            images_total_global[image] = None
            images_remaining_global[image] = None

    # remove deleted images from the ordered set
    del_image_list = []
    for image in images_total_global:
        if image not in images_total_local:
            # an image has been deleted from the folder
            del_image_list.append(image)
    for image in del_image_list:
        del images_total_global[image]
        images_remaining_global.pop(image, None)

    # if we've exhausted the images, start over
    if not images_remaining_global:
        images_remaining_global = images_total_global.copy()

    # randomly choose an image without replacement
    image = random.choice(list(images_remaining_global.keys()))
    del images_remaining_global[image]
    return image


def get_query_or_random_word() -> str:
    global latin_global
    text = request.args.get('quaestio').strip()
    if not text: # the user didn't enter anything, try a random word
        text = latin_global.get_random_word()
    return text


def add_query_to_set(text: str) -> str:
    global searches_so_far_global
    searches_so_far_global[text] = None
    socketio.emit('searches_so_far', {'searches': list(searches_so_far_global.keys())})


@app.route('/')
def domus():
    return render_template(
        r'form_latin.html',
        image_logo=os.path.join(app.config["UPLOAD_FOLDER"], random_image()))


@app.route('/perquire')
def perquire():
    text = get_query_or_random_word()
    response = make_response(render_template(
        r'form_latin.html',
        image_logo=os.path.join(app.config["UPLOAD_FOLDER"], random_image()),
        query_value=text,
        titles_urls=[],
        link_urls=[]))
    # inefficient - skip caching so that the search field is repopulated correctly when the browser back button is hit
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response


@app.route('/sentio_felix')
def sentio_felix():
    global latin_global
    global int_char_dict_global
    global wdl_global

    text = get_query_or_random_word()
    print(f"'sentio_felix': {text}")
    add_query_to_set(text)
    text_ints = latin_global.convert_to_search_ints(text)
    latin_word = wdl_global.weighted_damerau_levenshtein_single_multithread(text_ints)
    latin_word = ''.join([int_char_dict_global[ival] for ival in latin_word])
    url = latin_global.create_url(latin_word)
    return redirect(url)


@socketio.on('domus')
def on_domus(data):
    global searches_so_far_global
    print(f"'domus'")
    socketio.emit('on_domus_done', {'searches': list(searches_so_far_global.keys())}, to=request.sid)


@socketio.on('perquire')
def on_perquire(data):
    global latin_global
    global int_char_dict_global
    global searches_so_far_global
    global wdl_global

    text = data['query']
    print(f"'perquire': {text}")
    add_query_to_set(text)
    text_ints = latin_global.convert_to_search_ints(text)
    latin_words = wdl_global.weighted_damerau_levenshtein_multithread(text_ints, latin_global.MAX_RESULTS)
    for i, ints in enumerate(latin_words):
        latin_words[i] = ''.join([int_char_dict_global[ival] for ival in ints])
    titles_urls = []
    for i, word in enumerate(latin_words):
        titles_urls.append([i, latin_global.int_to_roman_numeral(i + 1), word, latin_global.create_url(word)])
    socketio.emit('on_perquire_done', {'table': titles_urls, 'searches': list(searches_so_far_global.keys())}, to=request.sid)


@socketio.on('query_update')
def on_query_update(data):
    global query_update_lock_global
    global query_update_global
    with query_update_lock_global:
        query_update_global[request.sid] = data['query']


def on_add_delete_link_done():
    global links_dict_global

    link_urls = [[i, title, url] for i, (title, url) in enumerate(links_dict_global.items())]
    socketio.emit('on_add_link_done', {'urls': link_urls}, to=request.sid)


@socketio.on('get_link')
def on_get_link(_data):
    global latin_global
    global links_dict_global

    links_dict_global = latin_global.load_links()
    on_add_delete_link_done()


@socketio.on('add_link')
def on_add_link(data):
    global latin_global
    global links_dict_global

    title = data['title'].strip()
    url = data['url'].strip().replace('"', '%22').replace("'", '%27')
    if not title:
        title = url
    if not url.startswith("https://"):
        url = "https://" + url
    if url:
        links_dict_global[title] = url
        latin_global.save_links(links_dict_global)
        on_add_delete_link_done()


@socketio.on('delete_link')
def on_delete_link(data):
    global latin_global
    global links_dict_global

    title = data['title']
    url = data['url']
    if title in links_dict_global and url == links_dict_global[title]:
        del links_dict_global[title]
        latin_global.save_links(links_dict_global)
        on_add_delete_link_done()


@socketio.on('delete_image')
def on_delete_image(data):
    global latin_global

    image = data['image']
    print(f"'delete_image': {image}")
    full_dir = os.path.join(latin_global.DIRECTORY, app.config["UPLOAD_FOLDER"])
    full_path = os.path.join(full_dir, os.path.basename(image))
    send2trash(full_path)
    socketio.emit('on_delete_image_done', {}, to=request.sid)


if __name__ == "__main__":
    print("Ready.")
    #socketio.run(app, debug=True)
    socketio.run(app, debug=False, host='0.0.0.0', port=5000)
