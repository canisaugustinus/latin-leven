# https://github.com/tatuylonen/wiktextract
# https://kaikki.org/dictionary/rawdata.html
# pybind11 stuff:
# https://learn.microsoft.com/en-us/visualstudio/python/working-with-c-cpp-python-in-visual-studio?view=vs-2022

# pip install {path}\weightdamleven_pybind11\weightdamleven\
# delete the auto-generated file:
# C:\Users\{USERNAME}\AppData\Local\JetBrains\PyCharmCE2021.3\python_stubs\{number}\weightdamleven.py
# then with THE "pybind11-stubgen" module:
# pybind11-stubgen -o {path_to_site-packages} weightdamleven
# and finally:
# make sure weightdamleven.pyi is in site-packages next to the .py file

import typing
import itertools
import os
import pathlib
import random
from collections import defaultdict
import numpy as np
from flask import Flask, request, render_template, make_response, redirect
from flask_socketio import SocketIO
import json
import weightdamleven

print(weightdamleven.__file__)


class Latin:
    MAX_RESULTS = 100
    DIRECTORY = pathlib.Path(__file__).parent.resolve()
    WIKTEXTRACT_DATA = os.path.join(DIRECTORY, "database", "raw-wiktextract-data.jsonl")
    LATIN_WORDS = os.path.join(DIRECTORY, "database", "latin_words.txt")

    def __init__(self):
        self._latin_words = self.read_parsed_latin_words()
        self._key_key_cost = self.key_key_cost()

        # c++ str -> list[int] conversions because pybind11 wasn't playing nicely with unicode
        self._char_int_dict = self.char_int_dict()
        self._int_char_dict = self.int_char_dict()
        self._cost_matrix = self.cost_matrix()
        self._latin_keys_encoded = self.latin_keys_encoded()

    def get_int_char_dict(self) -> dict[int, str]:
        return self._int_char_dict

    def get_cost_matrix(self) -> list[list[float]]:
        return self._cost_matrix

    def get_latin_keys_encoded(self) -> list[list[int]]:
        return self._latin_keys_encoded

    def char_set(self) -> dict[str, None]:
        """ char_set is the ordered set (dict[str, None]) of all characters used. """
        char_set = dict()  # use a dict to maintain insertion order

        # add all characters in the cost mapping --- critical to have these in char_set first
        for key in self._key_key_cost:
            for char in key:
                char_set[char] = None

        # add all characters in all latin words
        for key in self._latin_words:
            for char in key:
                char_set[char] = None
        return char_set

    def char_int_dict(self) -> defaultdict[str, int]:
        """
        char_int_dict[char1] maps from char1 to encoding int1.
        Used this for cost matrix indexing:
        """
        char_set = self.char_set()
        counter = 0
        char_int_dict = defaultdict(lambda: 0)
        for char in char_set:
            char_int_dict[char] = counter
            counter += 1
        # map unknown chars to space bar
        char_int_dict.default_factory = lambda: char_int_dict[' ']
        return char_int_dict

    def int_char_dict(self) -> dict[int, str]:
        """
        int_char_dict[int1] maps from encoding int1 to char1.
        Turn the encoded words back into strings.
        cost_matrix[char_int_dict[char1]][char_int_dict[char2]] = the cost to turn char1 into char2.
        """
        int_char_dict = {}
        for key, val in self._char_int_dict.items():
            int_char_dict[val] = key
        return int_char_dict

    def cost_matrix(self) -> list[list[float]]:
        """ cost_matrix[char_int_dict[char1]][char_int_dict[char2]] = the cost to turn char1 into char2. """
        key_set = set()
        for key in self._key_key_cost:
            for char in key:
                key_set.add(char)
        key_length = len(key_set)

        cost_matrix = [[0.0 for _j in range(key_length)] for _i in range(key_length)]
        for key in self._key_key_cost:
            char1, char2 = key
            i = self._char_int_dict[char1]
            j = self._char_int_dict[char2]
            cost_matrix[i][j] = self._key_key_cost[key]
        return cost_matrix

    def latin_keys_encoded(self) -> list[list[int]]:
        """ list of all keys encoded as list[int]. """
        latin_keys_encoded = []
        for key in self._latin_words:
            latin_keys_encoded.append([self._char_int_dict[char] for char in key])
        return latin_keys_encoded

    def read_parsed_latin_words(self) -> list[str]:
        """ Read in the saved list produced by self.parse_latin_word_list(). """
        with open(self.LATIN_WORDS, 'r', encoding="utf-8") as f:
            latin_words = list(set(word.strip() for word in f.readlines()))
        return latin_words

    def parse_latin_word_list(self) -> list[str]:
        """ From the raw-wiktextract-data.jsonl data, pick out Latin words. """
        count = self.line_count(self.WIKTEXTRACT_DATA)
        latin_words = set()
        with open(self.WIKTEXTRACT_DATA, 'r', encoding="utf-8") as f_in, \
                open(self.LATIN_WORDS, 'w', encoding="utf-8") as f_out:
            for count, line in tqdm(enumerate(f_in, start=1), desc="Parsing...", total=count):
                data = json.loads(line)
                try:
                    if data['lang_code'] == 'la':
                        word = data['word']
                        latin_words.add(word)
                        f_out.write(''.join([word, '\n']))
                except KeyError:
                    pass
        return list(latin_words)

    def get_random_word(self) -> str:
        """ Get a random Latin word. """
        return random.choice(self._latin_words)

    @classmethod
    def line_count(cls, filename: str):
        """ Count the number of lines in a file. """
        def blocks(file: typing.TextIO, size=65536):
            while True:
                block = file.read(size)
                if not block:
                    break
                yield block
        with open(filename, "r", encoding="utf-8", errors='ignore') as f:
            count = sum(block.count("\n") for block in blocks(f))
        return count

    @classmethod
    def key_key_cost(cls) -> defaultdict[tuple[str, str], complex]:
        """ key_key_cost[(char1, char2)] = the cost of replacing char1 with char2. """
        key_layout = [
            "qwertyuiop",
            "asdfghjkl",
            "zxcvbnm"]
        key_dict = defaultdict(lambda: 100.0 + 0j)  # complex values make finding the distance easier
        key_cols = [np.arange(len(row)) for row in key_layout]
        key_cols = [row + 0.5*i for i, row in enumerate(key_cols)]
        key_rows = [0.0, 1.0, 2.0]
        for row in range(len(key_layout)):
            for col in range(len(key_layout[row])):
                val = key_rows[row] + 1j*key_cols[row][col]
                key_dict[key_layout[row][col]] = val

        pairs = list(itertools.combinations(key_dict, 2))
        key_key_cost = defaultdict(lambda: 10.0)
        for a, b in pairs:
            cost = np.abs(key_dict[a] - key_dict[b])

            # all combinations of lower -> lower, lower -> upper, etc.
            a_up_low = [a.lower(), a.upper()]
            b_up_low = [b.lower(), b.upper()]
            for a in a_up_low:
                for b in b_up_low:
                    if a == b:
                        case_cost = 0.0
                    else:
                        case_cost = 0.1
                    key_key_cost[(a, b)] = cost + case_cost
                    key_key_cost[(b, a)] = cost + case_cost

        # change a given char from upper -> lower or lower -> upper
        for a in key_dict:
            a_up_low = [a.lower(), a.upper()]
            for a in a_up_low:
                for b in a_up_low:
                    if a == b:
                        case_cost = 0.0
                    else:
                        case_cost = 0.1
                    key_key_cost[(a, b)] = case_cost
                    key_key_cost[(b, a)] = case_cost
        return key_key_cost

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
        keys = set(long_vowels_dict.keys())
        for key in keys:
            long_vowels_dict[key.upper()] = long_vowels_dict[key].upper()
        for long, short in long_vowels_dict.items():
            word = word.replace(long, short)
        return word.strip()


latin = Latin()
int_char_dict_global = latin.get_int_char_dict()

is_key_cost = True
replace_cost = 10.0
insert_cost = 3.0
delete_cost = 3.0
transpose_cost = 2.0
wdl = weightdamleven.WeightDamLeven(
    latin.get_latin_keys_encoded(),
    latin.get_cost_matrix(),
    is_key_cost,
    replace_cost,
    insert_cost,
    delete_cost,
    transpose_cost)

searches_so_far = {}  # using a dictionary with None values as an ordered set

app = Flask(__name__)
app.config["UPLOAD_FOLDER"] = os.path.join("static", "IMG")
socketio = SocketIO(app)


def random_image() -> str:
    full_dir = os.path.join(latin.DIRECTORY, app.config["UPLOAD_FOLDER"])
    image_files = [f for f in os.listdir(full_dir) if os.path.isfile(os.path.join(full_dir, f))]
    return random.choice(image_files)


def get_query_or_random_word() -> str:
    text = request.args.get('quaestio').strip()
    if not text: # the user didn't enter anything, try a random word
        text = latin.get_random_word()
    return text


def add_query_to_set(text: str) -> str:
    searches_so_far[text] = None
    socketio.emit('searches_so_far', {'searches': list(searches_so_far.keys())})


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
        titles_urls=[]))
    # inefficient - skip caching so that the search field is repopulated correctly when the browser back button is hit
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response


@app.route('/sentio_felix')
def sentio_felix():
    text = get_query_or_random_word()
    print(f"'sentio_felix': {text}")
    add_query_to_set(text)
    text_ints = latin.convert_to_search_ints(text)
    latin_word = wdl.weighted_damerau_levenshtein_single_multithread(text_ints)
    latin_word = ''.join([int_char_dict_global[ival] for ival in latin_word])
    url = latin.create_url(latin_word)
    return redirect(url)


@socketio.on('domus')
def on_domus(data):
    print(f"'domus'")
    socketio.emit('on_domus_done', {'searches': list(searches_so_far.keys())}, to=request.sid)


@socketio.on('perquire')
def on_perquire(data):
    text = data['query']
    print(f"'perquire': {text}")
    add_query_to_set(text)
    text_ints = latin.convert_to_search_ints(text)
    latin_words = wdl.weighted_damerau_levenshtein_multithread(text_ints, latin.MAX_RESULTS)
    for i, key in enumerate(latin_words):
        latin_words[i] = ''.join([int_char_dict_global[ival] for ival in key])
    titles_urls = []
    for i, key in enumerate(latin_words):
        titles_urls.append([i, latin.int_to_roman_numeral(i + 1), key, latin.create_url(key)])
    socketio.emit('on_perquire_done', {'table': titles_urls, 'searches': list(searches_so_far.keys())}, to=request.sid)


if __name__ == "__main__":
    print("Ready.")
    #socketio.run(app, debug=True)
    socketio.run(app, debug=False, host='0.0.0.0', port=5000)
