# get a list of all images associated with a topic (save as csv):
# https://petscan.wmcloud.org/?templates_yes=&links_to_no=&wikidata_item=no&add_image=on&interface_language=en&smaller=&cb_labels_yes_l=1&templates_any=&manual_list=&search_max_results=500&categories=Ancient+Rome%0D%0A&ores_prediction=any&edits%5Bflagged%5D=both&project=wikipedia&outlinks_no=&cb_labels_any_l=1&cb_labels_no_l=1&output_limit=&language=en&sortby=none&show_redirects=both&depth=3
# https://petscan.wmcloud.org/?search_wiki=&edits%5Banons%5D=both&cb_labels_yes_l=1&categories=Ancient_Rome%0D%0ARoman_Republic%0D%0ARoman_Empire%0D%0A&links_to_any=&ores_prediction=any&cb_labels_any_l=1&depth=1&manual_list=&language=commons&sitelinks_any=&ores_prob_to=&templates_no=&before=&search_max_results=500&wikidata_item=no&langs_labels_yes=&minlinks=&output_compatability=catscan&common_wiki=auto&sitelinks_yes=&interface_language=en&project=wikimedia&langs_labels_no=&sitelinks_no=&wikidata_source_sites=&page_image=yes&rxp_filter=&maxlinks=&sortorder=ascending&edits%5Bflagged%5D=both&show_disambiguation_pages=both&links_to_all=&add_image=on&smaller=&templates_any=&combination=union&active_tab=tab_pageprops&cb_labels_no_l=1&labels_yes=&search_query=&since_rev0=&templates_yes=

# the string with index 6 is the filename

# according to https://commons.wikimedia.org/wiki/Commons:FAQ#What_are_the_strangely_named_components_in_file_paths.3F
# add it and the fist/first_second of the MD5 hash to
# https://upload.wikimedia.org/wikipedia/commons/{first}/{first}{second}/{filename}

import numpy as np
import time
import requests
import csv
import urllib.parse
import pathlib
import os
import hashlib


def get_new_filenames(
        image_list_filename: str,
        previous_image_lists: list[str] = None) -> set[str]:
    curr_dir = pathlib.Path(__file__).parent.resolve()
    img_path = os.path.join(curr_dir, 'static/IMG')

    previous_files = set([f for f in os.listdir(img_path) if os.path.isfile(os.path.join(img_path, f))])
    if previous_image_lists is not None:
        for prev_file in previous_image_lists:
            previous_files = previous_files.union(get_valid_filenames(prev_file))

    new_files = get_valid_filenames(image_list_filename)
    return new_files.difference(previous_files)


def get_valid_filenames(image_list_filename: str) -> set[str]:
    directory = pathlib.Path(__file__).parent.resolve()
    image_list_filepath = os.path.join(directory, image_list_filename)
    valid_files = set()
    with open(image_list_filepath, 'r', encoding="utf-8") as image_list:
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
    input("We're going to start downloading from Wikipedia. Continue?")
    directory = pathlib.Path(__file__).parent.resolve()
    headers = {'User-Agent': 'RomeImageBot/0.0 (canisaugustinus@gmail.com)'}

    valid_files = get_new_filenames("rome_images_refined.csv")
    print(len(valid_files))
    for i, file in enumerate(valid_files, 1):
        url = generate_wikimedia_image_link(file)
        response = requests.get(url, headers=headers, timeout=5)
        progress = i*100.0/len(valid_files)
        if response.status_code == 200:
            image_path = os.path.join(directory, 'static/IMG', file)
            open(image_path, 'wb').write(response.content)
            print(f'{progress:.2f}% Downloaded "{file}"')
        else:
            print(f'{progress:.2f}% Skipped "{file}"')
            print(f'Tried "{url}" with response {response.status_code}.')
        sleep = np.random.uniform(8.0, 12.0)
        print(f'Sleeping for {sleep} seconds.')
        time.sleep(sleep)
