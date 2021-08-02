import urllib.request
import json
import math
import os
import time


SCRIPT_PATH = os.path.dirname(os.path.realpath(__file__)) + '/'
KEY = os.environ['LIBRARIESIO_KEY']
ROOT = 'https://libraries.io'


def main():
    dependencies = []

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
            dependencies.append(output)

            with open(SCRIPT_PATH + 'projects.txt', 'a') as f:
                f.write(json.dumps(output) + '\n')

        page += 1
        raw_dependencies = query_libraries_io('/api/maven/com.google.guava:guava/dependents?page=' + str(page))

    print(len(dependencies))


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



if __name__ == "__main__":
    main()
