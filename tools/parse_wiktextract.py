import typing
import os
import pathlib
import json
import math
from tqdm import tqdm


class WiktextractParser:
    DIRECTORY = pathlib.Path(__file__).parent.parent.resolve()
    WIKTEXTRACT_DATA = os.path.join(DIRECTORY, "wiktionary_latin_py", "database", "raw-wiktextract-data.jsonl")
    LATIN_WORDS = os.path.join(DIRECTORY, "wiktionary_latin_py", "database", "latin_words.txt")

    def __init__(self):
        pass

    @classmethod
    def parse_latin_word_list(cls) -> list[str]:
        """ From the raw-wiktextract-data.jsonl data, pick out Latin words. """
        latin_words = set()
        file_size = os.path.getsize(cls.WIKTEXTRACT_DATA)
        progress_bar = tqdm(desc="Loading Latin List", total=file_size)
        with open(cls.WIKTEXTRACT_DATA, 'r', encoding="utf-8") as f_in, \
                open(cls.LATIN_WORDS, 'w', encoding="utf-8") as f_out:
            f_in_tell_prev = 0
            line = f_in.readline()
            while line:
                data = json.loads(line)
                try:
                    if data['lang_code'] == 'la':
                        word = data['word']
                        latin_words.add(word)
                        f_out.write(''.join([word, '\n']))
                except KeyError:
                    pass
                f_in_tell = f_in.tell()
                progress_bar.update(f_in_tell - f_in_tell_prev)
                f_in_tell_prev = f_in_tell
                line = f_in.readline()
        progress_bar.close()
        return list(latin_words)


if __name__ == '__main__':
    WiktextractParser.parse_latin_word_list()
