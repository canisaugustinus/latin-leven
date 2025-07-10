# get a list of all images associated with a topic (save as csv):
# https://petscan.wmcloud.org/?templates_yes=&links_to_no=&wikidata_item=no&add_image=on&interface_language=en&smaller=&cb_labels_yes_l=1&templates_any=&manual_list=&search_max_results=500&categories=Ancient+Rome%0D%0A&ores_prediction=any&edits%5Bflagged%5D=both&project=wikipedia&outlinks_no=&cb_labels_any_l=1&cb_labels_no_l=1&output_limit=&language=en&sortby=none&show_redirects=both&depth=3
# https://petscan.wmcloud.org/?search_wiki=&edits%5Banons%5D=both&cb_labels_yes_l=1&categories=Ancient_Rome%0D%0ARoman_Republic%0D%0ARoman_Empire%0D%0A&links_to_any=&ores_prediction=any&cb_labels_any_l=1&depth=1&manual_list=&language=commons&sitelinks_any=&ores_prob_to=&templates_no=&before=&search_max_results=500&wikidata_item=no&langs_labels_yes=&minlinks=&output_compatability=catscan&common_wiki=auto&sitelinks_yes=&interface_language=en&project=wikimedia&langs_labels_no=&sitelinks_no=&wikidata_source_sites=&page_image=yes&rxp_filter=&maxlinks=&sortorder=ascending&edits%5Bflagged%5D=both&show_disambiguation_pages=both&links_to_all=&add_image=on&smaller=&templates_any=&combination=union&active_tab=tab_pageprops&cb_labels_no_l=1&labels_yes=&search_query=&since_rev0=&templates_yes=

# the string with index 6 is the filename

# according to https://commons.wikimedia.org/wiki/Commons:FAQ#What_are_the_strangely_named_components_in_file_paths.3F
# add it and the fist/first_second of the MD5 hash to
# https://upload.wikimedia.org/wikipedia/commons/{first}/{first}{second}/{filename}

import time
import requests
import csv
import urllib.parse
import pathlib
import os
import hashlib
from tqdm import tqdm

HEADERS = {'User-Agent': 'ExampleBotName/0.0 (example@email.com)'}

DIRECTORY = pathlib.Path(__file__).parent.parent.resolve()
IMAGE_DIR = os.path.join(DIRECTORY, "wiktionary_latin_py", "static", "IMG")
ROME_IMAGES_CSV = os.path.join(DIRECTORY, "wiktionary_latin_py", "database", "rome_images.csv")


def get_new_filenames(
        image_list_filename: str,
        previous_image_lists: list[str] = None) -> set[str]:
    previous_files = set([f for f in os.listdir(IMAGE_DIR) if os.path.isfile(os.path.join(IMAGE_DIR, f))])
    if previous_image_lists is not None:
        for prev_file in previous_image_lists:
            previous_files = previous_files.union(get_valid_filenames(prev_file))

    new_files = get_valid_filenames(image_list_filename)
    return new_files.difference(previous_files)


def get_valid_filenames(image_list_filename: str) -> set[str]:
    valid_files = set()
    with open(image_list_filename, 'r', encoding="utf-8") as image_list:
        next(image_list)
        csv_images = csv.reader(image_list, delimiter=',')
        for line in csv_images:
            filename = line[-1]
            if filename:
                valid_files.add(filename)
    return valid_files


def generate_wikimedia_image_link(filename: str) -> str:
    encoded_string = filename.encode('utf-8')  # Encode the string to bytes
    md5_hash = hashlib.md5(encoded_string).hexdigest()
    first, second = md5_hash[0], md5_hash[1]
    filename = urllib.parse.quote(filename)
    return f'https://upload.wikimedia.org/wikipedia/commons/{first}/{first}{second}/{filename}'


if __name__ == '__main__':
    input(f"We're going to start downloading from Wikipedia with header={HEADERS}.\nContinue?")

    if not os.path.exists(IMAGE_DIR):
        os.makedirs(IMAGE_DIR)

    valid_files = get_new_filenames(ROME_IMAGES_CSV)
    print(len(valid_files))
    for file in tqdm(valid_files, desc="Downloading images"):
        url = generate_wikimedia_image_link(file)
        response = requests.get(url, headers=HEADERS, timeout=5)
        if response.status_code == 200:
            image_path = os.path.join(IMAGE_DIR, file)
            open(image_path, 'wb').write(response.content)
        time.sleep(1)  # be nice and wait, grab a coffee or something
