import argparse
import json
import os
import sys

import lxml.html as html
import requests


# Print iterations progress
def printProgressBar(iteration, total, prefix='', suffix='', decimals=1, length=100, fill='#'):
    """
    Call in a loop to create terminal progress bar
    @params:
        iteration   - Required  : current iteration (Int)
        total       - Required  : total iterations (Int)
        prefix      - Optional  : prefix string (Str)
        suffix      - Optional  : suffix string (Str)
        decimals    - Optional  : positive number of decimals in percent complete (Int)
        length      - Optional  : character length of bar (Int)
        fill        - Optional  : bar fill character (Str)
    """
    percent = ("{0:." + str(decimals) + "f}").format(100 * (iteration / float(total)))
    filledLength = int(length * iteration // total)
    bar = fill * filledLength + '-' * (length - filledLength)
    sys.stdout.write('\r{} |{}| {}%% {}'.format(prefix, bar, percent, suffix))
    sys.stdout.flush()


def get_session():
    s = requests.Session()
    s.headers = {
        "Host": "www.pinterest.com",
        "Referer": "https://www.pinterest.com/",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/70.0.3538.113 Safari/537.36 Vivaldi/2.1.1337.51",
        "X-APP-VERSION": "ab1af2a",
        "X-B3-SpanId": "183fc9cb02974b",
        "X-B3-TraceId": "14f603d2caa27c",
        "X-Pinterest-AppState": "active",
        "X-Requested-With": "XMLHttpRequest",
    }

    return s


def get_user_boards(username):
    s = get_session()
    r = s.get("https://www.pinterest.com/{}/".format(username))
    root = html.fromstring(r.content)
    tag = root.xpath("//script[@id='initial-state']")[0]
    initial_data = json.loads(tag.text)
    # UserProfileBoardResource
    boards = [i for i in initial_data['resourceResponses'] if i['name'] == 'UserProfileBoardResource']
    if boards:
        boards = boards[0]['response']['data']

    return boards


def get_board_info(board_name):
    s = get_session()

    r = s.get("https://www.pinterest.com/{}/".format(board_name))
    root = html.fromstring(r.content)
    tag = root.xpath("//script[@id='initial-state']")[0]
    initial_data = json.loads(tag.text)

    boards = initial_data['resources'] \
        ['data'] \
        ['BoardPageResource']

    boards = boards[list(boards.keys())[0]] \
        ['data']

    return [boards]


def fetch_boards(boards, force_update=False):
    s = get_session()

    for board_index, board in enumerate(boards):
        save_dir = os.path.join("images", board['owner']['username'], board['name'])

        bookmark = None

        images = []

        while bookmark != '-end-':
            options = {
                "board_id": board['id'],
                "page_size": 25,
            }

            if bookmark:
                options.update({
                    "bookmarks": [bookmark],
                })

            r = s.get("https://www.pinterest.com/resource/BoardFeedResource/get/", params={
                "source_url": board['url'],
                "data": json.dumps({
                    "options": options,
                    "context": {}
                }),
            })

            data = r.json()

            images += data["resource_response"]["data"]

            bookmark = data['resource']['options']['bookmarks'][0]


        try:
            os.makedirs(save_dir)
        except Exception:
            pass

        print("[{}/{}] board: {}, found {} images".format(board_index + 1, len(boards), board['url'], len(images)))

        for index, image in enumerate(images):
            image_id = image['id']

            if 'images' in image:
                url = image['images']['orig']['url']
                basename = os.path.basename(url)
                _, ext = basename.split(".")
                file_path = os.path.join(save_dir, "{}.{}".format(str(image_id), ext))

                if not os.path.exists(file_path) or force_update:
                    r = requests.get(url, stream=True)

                    with open(file_path, 'wb') as f:
                        for chunk in r:
                            f.write(chunk)
            else:
                print("no image found: {}".format(image_id))

            printProgressBar(index + 1, len(images), prefix='Progress:', suffix='Complete', length=50)

        print()


def main():
    parser = argparse.ArgumentParser(description='Download pin boards by username')
    parser.add_argument('path', type=str, help='pinterest username or username/boardname')
    parser.add_argument('-f', '--force', type=bool, default=False, help='force redownload even if image already exists')
    args = parser.parse_args()

    if '/' in args.path:
        boards = get_board_info(args.path)
    else:
        boards = get_user_boards(args.path)

    fetch_boards(boards, args.force)


if __name__ == '__main__':
    main()