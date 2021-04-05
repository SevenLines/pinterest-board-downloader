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
    session = get_session()
    request = session.get(
        "https://www.pinterest.com/{}/".format(username)
    )
    root = html.fromstring(request.content)
    tag = root.xpath("//script[@id='initial-state']")[0]
    initial_data = json.loads(tag.text)
    # UserProfileBoardResource
    boards_resource = [
        resource for resource
        in initial_data['resourceResponses']
        if resource['name'] == 'UserProfileBoardResource'
    ]
    if boards_resource:
        boards = boards_resource[0]['response']['data']
    return boards


def get_user_board_paths(username):
    all_boards = get_user_boards(username)
    return [
        board["url"][1:-1]
        for board in all_boards
    ]

def get_board_info(board_name):
    session = get_session()
    response = session.get(
        "https://www.pinterest.com/{}/".format(board_name)
    )
    root = html.fromstring(response.content)
    tag = root.xpath("//script[@id='initial-state']")[0]
    initial_data = json.loads(tag.text)
    board = None
    if "resourceResponses" in initial_data:
        board = initial_data["resourceResponses"][0]["response"]["data"]
        try:
            sections = [
                (section["slug"], section["id"])
                for section in (
                    initial_data
                    .get("resourceResponses")[2]
                    .get("response")
                    .get("data")
                )
            ]
            board["sections"] = sections
        except (IndexError, KeyError) as e:
            # Board has no sections!
            pass
    elif "resources" in initial_data:
        board = (
                initial_data
                .get('resources')
                .get('data')
                .get('BoardPageResource')
        )[list(boards.keys())[0]]['data']
    return board


def fetch_boards(boards, force_update=False, path=None):

    session = get_session()

    def fetch_images(get_url, board_url, options):
        bookmark = None
        images = []
        while bookmark != '-end-':
            if bookmark:
                options.update({ "bookmarks": [bookmark], })
            response = session.get(
                get_url,
                params={
                    "source_url": board_url,
                    "data": json.dumps(
                        {"options": options, "context": {}}
                    ),
                }
            )
            data = response.json()
            images += data["resource_response"]["data"]
            bookmark = data['resource']['options']['bookmarks'][0]
        return images

    images_by_directory = {}
    filter_user, filter_board, filter_section = (path.split("/") + [None, None, None])[:3]

    for board_index, board in enumerate(boards):
        # Images in board.
        save_dir = os.path.join(
            "images",
            board['owner']['username'],
            board['name']
        )
        images_by_directory[save_dir] = fetch_images(
            "https://www.pinterest.com/resource/BoardFeedResource/get/",
            board["url"],
            {"board_id": board['id'], "page_size": 25}
        )
        for section, section_id in (board.get("sections") or ()):
            if filter_section and filter_section != section:
                # Skip any other sections if requesting specific one.
                continue
            # Images in board sections.
            save_dir = os.path.join(
                "images",
                board['owner']['username'],
                board['name'],
                section
            )
            directory = "/".join((board["url"][1:-1], section))
            images_by_directory[directory] = fetch_images(
                "https://www.pinterest.com/resource/BoardSectionPinsResource/get",
                board["url"],
                {"section_id": section_id, "page_size": 25},
            )

        for i, (save_dir, images) in enumerate(images_by_directory.items(), 1):
            pinterest_path = "/".join(save_dir.split(os.path.sep)[1:])
            try:
                os.makedirs(save_dir)
            except Exception:
                pass
            print(
                "[{}/{}] board: {}, found {} images".format(
                    i,
                    len(images),
                    pinterest_path,
                    len(images)
                )
            )

        for save_dir, images in images_by_directory.items():
            for i, image in enumerate(images, 1):
                image_id = image['id']

                if 'images' in image:
                    url = image['images']['orig']['url']
                    basename = os.path.basename(url)
                    _, ext = basename.split(".")
                    file_path = os.path.join(
                        save_dir, "{}.{}".format(str(image_id), ext))

                    if not os.path.exists(file_path) or force_update:
                        print(url)
                        r = requests.get(url, stream=True)

                        with open(file_path, 'wb') as f:
                            for chunk in r:
                                f.write(chunk)
                else:
                    print("no image found: {}".format(image_id))
                    continue

                printProgressBar(
                    i, len(images),
                    prefix='Progress:',
                    suffix='Complete',
                    length=50
                )

        print()


def get_parser():
    """argparse.ArgumentParser: Get argument parser."""
    parser = argparse.ArgumentParser(
        description='Download pin boards by username'
    )
    parser.add_argument(
        'path',
        type=str,
        help='pinterest username or username/boardname'
    )
    parser.add_argument(
        '-f',
        '--force',
        action="store_true",
        help='force redownload even if image already exists'
    )
    return parser


def main():
    """Main entry point."""
    args = get_parser().parse_args()
    if "/" not in args.path:
        paths = get_user_board_paths(args.path)
    else:
        paths = [args.path]

    boards = [get_board_info(path) for path in paths]
    fetch_boards(
        boards,
        force_update=args.force,
        path=args.path,
    )

if __name__ == '__main__':
    sys.exit(main())
