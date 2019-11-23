from dataknead import Knead
from pathlib import Path
import json
import xmltodict
import re

TITLE_SEPARATOR = ' - '
COLLECTION = 'RAA Elsinga'
EXTENSION = '.jpg'

KEY_MAPPING = {
    "dc:description": "description",
    "dc:date": "date",
    "dc:identifier": "accession_number",
    "dcterms:spatial": "depicted_place",
    "dc:creator": "artist",
    "europeana:isShownAt": "source",
    "europeana:type": "medium",
    "europeana:rights": "license",
    "europeana:isShownBy": "path",
}

LICENSES = {
    'https://creativecommons.org/publicdomain/zero/1.0/': '{{Cc-zero}}',
}

BATCH_SIZE = 500
apiKey = '6074ee2a-12da-11e7-a85c-60f81db16928'

def load_xml(path):
    with open(path, encoding="utf8") as f:
        return xmltodict.parse(f.read())

def parse(d):
    ret = {
        "identifier" : d["header"]["identifier"],
        "category" : 'Alkmaar',
    }

    for key in KEY_MAPPING:
        mapped_key = KEY_MAPPING[key]
        ret[mapped_key] = d["metadata"]["europeana:record"].get(key, None)

        # Sometimes items have multiple descriptions...
        if isinstance(ret[mapped_key], list):
            # Filter out items with value None
            ret[mapped_key] = list(filter((None).__ne__, ret[mapped_key]))
            # Join elements with a space
            ret[mapped_key] = ' '.join(ret[mapped_key])

        if ret[mapped_key] == None:
            if mapped_key in ("description","accession_number"):
                #print(f"Skipping {ret['identifier']} because no {mapped_key}")
                return {}

        if key == "dc:description" and ret[mapped_key] != None:
            # Clean up descriptions
            # Remove all line endings
            ret[mapped_key] = ret[mapped_key].replace('\n', ' ').replace('\r', '')
            # Remove all double spaces
            ret['description_raw'] = re.sub(' +', ' ', ret[mapped_key])
            ret[mapped_key] = '{{nl|1=' + ret['description_raw'] + '}}'
            if 'rijksmonument' in ret[mapped_key].lower():
                ret['category'] = 'Rijksmonumenten in Alkmaar'
                ret[mapped_key] = ret[mapped_key] + ' {{Possible Rijksmonument | plaats = Alkmaar | provincie = NH }}'

        if key == "dc:creator" and ret[mapped_key] == 'Elsinga, J.':
            ret[mapped_key] = '{{Creator:J. Elsinga}}'

        if key == "europeana:isShownAt" and ret[mapped_key] != None:
            ret[mapped_key] = 'View this picture on the website of the [' + ret[mapped_key] + ' Regional Archief Alkmaar] CC-O declaration can be found in the disclaimer of [https://www.regionaalarchiefalkmaar.nl/disclaimer?fbclid=IwAR248LwdG9Ecq3micqEqcJwJj3i4AlzmsVVR0b6Plur5tpC4CUu1EKvhNq4 the website of the archive].'

        if key == "europeana:rights" and ret[mapped_key] != None:
            if LICENSES.get(ret[mapped_key]):
                ret[mapped_key] = LICENSES.get(ret[mapped_key])

        if key == "europeana:isShownBy" and ret[mapped_key] != None:
            mediaId = ret['identifier'].split(':')[1]
            assetId = ret[mapped_key].split('/')[-1].split('.')[0]
            ret[mapped_key] = 'https://webservices.picturae.com/mediabank/media/'+mediaId+'/downloadoriginal/'+assetId+'?apiKey=' + apiKey

    ret['name'] = getTitle((ret))
    del ret['description_raw']

    return ret

def write_json(path, data):
    with open(path, "w") as f:
        f.write(json.dumps(data, indent = 4))

# Taken from https://github.com/multichill/toollabs/blob/master/bot/commons/wikidata_uploader.py
def cleanUpTitle(title):
	"""
	Clean up the title of a potential mediawiki page. Otherwise the title of
	the page might not be allowed by the software.
	"""
	title = title.strip()
	title = re.sub(u"[<{\\[]", u"(", title)
	title = re.sub(u"[>}\\]]", u")", title)
	title = re.sub(u"[ _]?\\(!\\)", u"", title)
	title = re.sub(u",:[ _]", u", ", title)
	title = re.sub(u"[;:][ _]", u", ", title)
	title = re.sub(u"[\t\n ]+", u" ", title)
	title = re.sub(u"[\r\n ]+", u" ", title)
	title = re.sub(u"[\n]+", u"", title)
	title = re.sub(u"[?!]([.\"]|$)", u"\\1", title)
	title = re.sub(u"[&#%?!]", u"^", title)
	title = re.sub(u"[;]", u",", title)
	title = re.sub(u"[/+\\\\:]", u"-", title)
	title = re.sub(u"--+", u"-", title)
	title = re.sub(u",,+", u",", title)
	title = re.sub(u"[-,^]([.]|$)", u"\\1", title)
	title = re.sub(u"^- ", u"", title)
	title = title.replace(u" ", u"_")
	return title


def getTitle(metadata):
    title = cleanUpTitle( TITLE_SEPARATOR.join( ( metadata['description_raw'][0:100], metadata['accession_number'], COLLECTION ) ) )
    title = title + EXTENSION

    return title

def main():
    results = []
    file_number = 1

    for path in Path(".").glob("download_data/*.xml"):
        data = load_xml(path)
        records = data["OAI-PMH"]["ListRecords"]["record"]
        records = [parse(r) for r in records]
        results = results + records

    chunks = [ results[i:i + BATCH_SIZE] for i in range(0, len(results), BATCH_SIZE) ]

    for index, chunk in enumerate(chunks):
        Knead(chunk).write(f"results-{str(index).zfill(5)}.csv")

    Knead(results).write("results.json")


if __name__ == "__main__":
    main()
