import functools
import urllib.request
import json
import math
import os
import time


SCRIPT_PATH = os.path.dirname(os.path.realpath(__file__)) + '/'
INTERMEDIARY_PATH = SCRIPT_PATH + 'intermediary.txt'
INTERMEDIARY_TEMP_PATH = SCRIPT_PATH + 'intermediary.tmp'
KEY = os.environ['LIBRARIESIO_KEY']
ROOT = 'https://libraries.io'


def main():
    raw_dependencies_count = 0

    page = 1
    raw_dependencies = query_libraries_io('/api/maven/com.google.guava:guava/dependents?page=' + str(page))
    while len(raw_dependencies) > 0:
        print('Got ' + str(len(raw_dependencies)) + ' packages on page ' + str(page))
        for dependency in raw_dependencies:
            output = {
                'name': dependency['platform'] + '/' + dependency['name'],
                'source': dependency['repository_url'],
                'versions': list(map(lambda version_info: version_info['number'], dependency['versions']))
            }
            raw_dependencies_count += 1

            with open(INTERMEDIARY_PATH, 'a') as f:
                f.write(json.dumps(output) + '\n')

        page += 1
        raw_dependencies = query_libraries_io('/api/maven/com.google.guava:guava/dependents?page=' + str(page))

    print(f'Fetched {raw_dependencies_count} packages')

    while True:
        source = None
        versions = {}

        with open(INTERMEDIARY_PATH) as intermediary:
            with open(INTERMEDIARY_TEMP_PATH, 'a') as intermediary_temp:
                for line in intermediary:
                    project = json.loads(line)
                    if project['source'] == None:
                        continue

                    if source == None or source == '':
                        source = project['source']

                    if project['source'] == source:
                        for new_version in project['versions']:
                            if new_version not in versions:
                                versions[new_version] = project['name']
                    else:
                        intermediary_temp.write(line)

        if not source:
            break

        with open(SCRIPT_PATH + 'projects.txt', 'a') as result:
            # Sort in the hope that preprocess.py will take less time checking out
            version_list = sorted(list(versions.items()), key=functools.cmp_to_key(cmp_version))
            result.write(json.dumps({'source': source, 'versions': version_list}) + '\n')
            print('Saved ' + source)

        os.replace(INTERMEDIARY_TEMP_PATH, INTERMEDIARY_PATH)

    os.remove(INTERMEDIARY_PATH)
    os.remove(INTERMEDIARY_TEMP_PATH)


# Need to handle when querying too fast
def query_libraries_io(path, root = ROOT, key = KEY):
    url = root + path + ('&' if '?' in path else '?')

    params = {
        'per_page': '100',
        'api_key': key
    }
    for key, value in params.items():
        url += key + '=' + value + '&'
    url = url[:-1]

    retries = 0
    while True:
        try:
            result = get_json(url)
            break
        except urllib.error.HTTPError as e:
            print(f'Fetching {url} returns {e.code}')
            if math.floor(e.code / 100) == 5 and retries < 7:
                time.sleep(10)
                retries += 1
            elif e.code != 429:
                raise e
            elif retries < 7:
                time.sleep(10)
                retries += 1
            else:
                raise e
    return result


def get_json(url):
    print('Fetching: ' + url)
    req = urllib.request.Request(url)
    # Parsing response
    r = urllib.request.urlopen(req).read()
    cont = json.loads(r.decode('utf-8'))
    return cont


def cmp_version(version_a, version_b):
    version_a_list = process_version(version_a[0])
    version_b_list = process_version(version_b[0])
    for i in range(min(len(version_a_list), len(version_b_list))):
        try:
            result = compare(version_a_list[i], version_b_list[i])
            if result != 0:
                return result
        except TypeError:
            result = compare(str(version_a_list[i]), str(version_b_list[i]))
            if result != 0:
                return result
    
    return compare(len(version_a_list), len(version_b_list))


def process_version(version):
    components = version.split('.')
    result = []
    for c in components:
        try:
            i = int(c)
        except ValueError:
            i = c
        result.append(i)
    
    return result


def compare(a, b):
    if a > b:
        return 1
    elif a < b:
        return -1
    return 0


if __name__ == "__main__":
    main()
