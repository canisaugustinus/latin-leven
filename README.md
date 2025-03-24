You're searching for translations from a specific language to English on Wiktionary. You're tired of sifting through entries in other languages. You tried adding a custom search in your browser, e.g. bookmarking `https://en.wiktionary.org/wiki/%s#Latin` with a search keyword in Firefox, but were disappointed when you realized you had no spellcheck. If that's you, then this Latin (but you could tweak it to whatever language you want) Wiktionary entry searcher is for you.

For quick spellchecking, we use a key-position-weighted [Damerau-Levenstein distance](https://en.wikipedia.org/wiki/Damerau%E2%80%93Levenshtein_distance). 
There are a million (Damerau-)Levenstein distance Python packages, but this one has some useful features:
* It's weighted. The keys `a` and `s` are closer to each other than either is to `p`. Accordingly, it costs less to replace `a` with `s` than it does to replace it with `p`. These weights can be tuned in the Python code.
* It's a fast C++ implementation.
* Nothing about it is inherently tied to looking up Latin translations on Wiktionary, so I guess you can use it elsewhere.

--- 
Build Instructions
1. Clone this repo to some path, which we'll call {latin-leven repo}.
2. Install Visual Studio 2022 with the Python and C++ development tools. We're going to build a Python extension using PyBind11.
3. Install Python and use pip to get the packages referenced in this repository's *.py files.
4. Install npm.
5. Install socket.io: in {latin-leven repo}\wiktionary_latin_py\static, run `npm install socket.io`. Make sure `{latin-leven repo}\wiktionary_latin_py\static\node_modules\socket.io\client-dist\socket.io.js` now exists.
6. Install jquery: in {latin-leven repo}\wiktionary_latin_py\static, run `npm install jquery`. Make sure `{latin-leven repo}\wiktionary_latin_py\static\node_modules\jquery\dist\jquery.js` now exists.
7. Download the Wiktionary dump "raw-wiktextract-data.jsonl" from https://kaikki.org/dictionary/rawdata.html, and place it at {latin-leven repo}\wiktionary_latin_py\database\raw-wiktextract-data.jsonl.
8. Extract the Latin word entries from the Wiktionary dump: run {latin-leven repo}\tools\parse_wiktextract.py.
9. Get a list of Wikipedia images associated with Ancient Rome using https://petscan.wmcloud.org/. Example settings [here](https://petscan.wmcloud.org/?search_wiki=&edits%5Banons%5D=both&cb_labels_yes_l=1&categories=Ancient_Rome%0D%0ARoman_Republic%0D%0ARoman_Empire%0D%0A&links_to_any=&ores_prediction=any&cb_labels_any_l=1&depth=1&manual_list=&language=commons&sitelinks_any=&ores_prob_to=&templates_no=&before=&search_max_results=500&wikidata_item=no&langs_labels_yes=&minlinks=&output_compatability=catscan&common_wiki=auto&sitelinks_yes=&interface_language=en&project=wikimedia&langs_labels_no=&sitelinks_no=&wikidata_source_sites=&page_image=yes&rxp_filter=&maxlinks=&sortorder=ascending&edits%5Bflagged%5D=both&show_disambiguation_pages=both&links_to_all=&add_image=on&smaller=&templates_any=&combination=union&active_tab=tab_pageprops&cb_labels_no_l=1&labels_yes=&search_query=&since_rev0=&templates_yes=).
10. In the petscan.wmcloud.org "Output" tab, change the "Format" to "CSV." Save the output to {latin-leven repo}\wiktionary_latin_py\database\rome_images.csv.
11. Edit the `HEADERS` variable of the Python script {latin-leven repo}\tools\random_ancient_rome.py with the `'User-Agent'` bot name and email address of your choice. Follow Wikimedia's [User-Agent Policy](https://foundation.wikimedia.org/wiki/Policy:Wikimedia_Foundation_User-Agent_Policy).
12. Download the images by running {latin-leven repo}\tools\random_ancient_rome.py.
13. Build the projects defined in {latin-leven repo}\wiktionary_latin.sln.
14. Run {latin-leven repo}\wiktionary_latin_py\wiktionary_latin.py to start the server. Connect to http://localhost:5000/ to start searching with spellchecking powered by a fast weighted Damerau–Levenshtein implementation.
