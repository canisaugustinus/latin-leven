import typing
import os
import pathlib
import json
import math
import requests
import gzip
from tqdm import tqdm


class WiktextractParser:
    DIRECTORY = pathlib.Path(__file__).parent.parent.resolve()
    LINK = r'https://kaikki.org/dictionary/raw-wiktextract-data.jsonl.gz'
    CHUNK_SIZE = 8192
    WIKTEXTRACT_DATA_GZ = os.path.join(DIRECTORY, "wiktionary_latin_py", "database", os.path.basename(LINK))
    WIKTEXTRACT_DATA = os.path.join(DIRECTORY, "wiktionary_latin_py", "database", "raw-wiktextract-data.jsonl")
    LATIN_WORDS = os.path.join(DIRECTORY, "wiktionary_latin_py", "database", "latin_words.txt")

    def __init__(self):
        pass

    @classmethod
    def download_raw_wiktextract_data_jsonl(cls) -> bytes | None:
        try:
            response = requests.get(cls.LINK, stream=True)
            response.raise_for_status() # error?

            total_size = int(response.headers.get('content-length', 0))
            downloaded_size = 0
            with open(cls.WIKTEXTRACT_DATA_GZ, "wb") as f_out:
                for chunk in tqdm(
                        response.iter_content(chunk_size=cls.CHUNK_SIZE),
                        total=total_size // cls.CHUNK_SIZE,
                        unit='KB',
                        desc="Downloading"):
                    if chunk:
                        f_out.write(chunk)
                        downloaded_size += len(chunk)
        except requests.exceptions.RequestException as e:
            print(f"Error downloading file: {e}")

    @classmethod
    def parse_latin_word_list_helper(cls, f_in) -> list[str]:
        """ From the raw-wiktextract-data.jsonl data, pick out Latin words. """
        latin_words = {}  # use a dict as an ordered set
        file_size = os.path.getsize(cls.WIKTEXTRACT_DATA)
        progress_bar = tqdm(desc="Loading Latin List", total=file_size)
        f_in_tell_prev = 0
        line = f_in.readline()
        while line:
            data = json.loads(line)
            try:
                if data['lang_code'] == 'la':
                    word = data['word'].strip()
                    latin_words[word] = None
            except KeyError:
                pass
            f_in_tell = f_in.tell()
            progress_bar.update(f_in_tell - f_in_tell_prev)
            f_in_tell_prev = f_in_tell
            line = f_in.readline()

        latin_words = list(latin_words.keys())
        with open(cls.LATIN_WORDS, 'w', encoding="utf-8") as f_out:
            for word in latin_words:
                f_out.write(word + '\n')
        progress_bar.close()
        return latin_words

    @classmethod
    def parse_latin_word_list_from_file(cls) -> list[str]:
        with open(cls.WIKTEXTRACT_DATA, 'r', encoding="utf-8") as f_in:
            return cls.parse_latin_word_list_helper(f_in)

    @classmethod
    def parse_latin_word_list_from_url(cls) -> list[str]:
        cls.download_raw_wiktextract_data_jsonl()
        with gzip.open(cls.WIKTEXTRACT_DATA_GZ, 'rt', encoding='utf-8') as f_in:
            return cls.parse_latin_word_list_helper(f_in)


if __name__ == '__main__':
    WiktextractParser.parse_latin_word_list_from_url()
