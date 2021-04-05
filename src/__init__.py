"""pinterest-board-downloader

Download pinterest boards.
"""
import argparse
import json
import os
import sys

import lxml.html as html
import requests


def print_progress_bar(
        iteration, total, prefix='', suffix='', decimals=1, length=100,
        fill='#'):
    """Print iterations progress.

    Call in a loop to create terminal progress bar

    Args:
        iteration (int): current iteration
        total (int): total iterations
        prefix (str): prefix string (optional)
        suffix (str): suffix string (optional)
        decimals (int): positive number of decimals in percent complete (optional)
        length (int): character length of bar
        fill (str): bar fill character (optional)

    """
    percent = ("{0:." + str(decimals) + "f}").format(
        100 * (iteration / float(total))
    )
    filled_length = int(length * iteration // total)
    progress_bar = fill * filled_length + '-' * (length - filled_length)
    sys.stdout.write(
        '\r{} |{}| {}%% {}'.format(
            prefix,
            progress_bar,
            percent,
            suffix
      )
    )
    sys.stdout.flush()


def get_session():
    """requests.Session: Get requests session."""
    session = requests.Session()
    session.headers = {
        "Host": "www.pinterest.com",
        "Referer": "https://www.pinterest.com/",
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; WOW64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/70.0.3538.113 "
            "Safari/537.36 "
            "Vivaldi/2.1.1337.51"
        ),
        "X-APP-VERSION": "ab1af2a",
        "X-B3-SpanId": "183fc9cb02974b",
        "X-B3-TraceId": "14f603d2caa27c",
        "X-Pinterest-AppState": "active",
        "X-Requested-With": "XMLHttpRequest",
    }
    return session


def get_user_boards(username):
    """Get info for all boards of a user.

    Args:
        username (str): user to query for.

    Returns:
        list(dict): data response for multiple boards.
    """
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
    """Get all board paths for a user.

    Args:
        username (str): user to query for.

    Returns:
        list(str): board paths for user.
    """
    all_boards = get_user_boards(username)
    return [
        board["url"][1:-1]
        for board in all_boards
    ]


def get_board_info(board_name):
    """Get board info.

    Args:
        board_name (str): board name to query.

    Returns:
        dict: data response containing board info.
        ``"sections"`` added to prevent additional requests.
    """
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
        except (IndexError, KeyError) as _:
            # Board has no sections!
            pass
    elif "resources" in initial_data:
        board = (
            initial_data
            .get('resources')
            .get('data')
            .get('BoardPageResource')
        )
        board = board[list(board.keys())[0]]['data']
    return board


def fetch_images(get_url, board_url, options):
    """Run through get requests, iterating with bookmark hash.

    Args:
        get_url (str): Get request url.
        board_url (str): board url to request.
        options (dict): data to include in request.
    """
    session = get_session()
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


def fetch_boards(boards, force_update=False, path=None):
    """Download board image data.

    Fetches all images, downloads and writes to disk.
    Progress is logged to terminal.

    Args:
        boards (list(dict)): board image data.
        force_update (bool): re-download existing.
        path (str): path in the form "user/board/section".
    """
    images_by_directory = {}
    _, _, filter_section = (path.split("/") + [None, None, None])[:3]

    for board in boards:
        # Images in board.
        save_dir = os.path.join(
            "images",
            os.path.join(*board["url"][1:-1].split("/")),
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
                os.path.join(*board['url'][1:-1].split("/")),
                section
            )
            images_by_directory[save_dir] = fetch_images(
                "https://www.pinterest.com/resource/BoardSectionPinsResource/get",
                board["url"],
                {"section_id": section_id, "page_size": 25},
            )

        for i, (save_dir, images) in enumerate(images_by_directory.items(), 1):
            pinterest_path = "/".join(save_dir.split(os.path.sep)[1:])
            try:
                os.makedirs(save_dir)
            except OSError as _:
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
                        response = requests.get(url, stream=True)

                        with open(file_path, 'wb') as img:
                            for chunk in response:
                                img.write(chunk)
                else:
                    print("\nno image found: {}".format(image_id))
                    continue

                print_progress_bar(
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
