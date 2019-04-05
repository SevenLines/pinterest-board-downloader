Pinterest boards downloader
==

Simple script that downloads board images in current dir

Install
-------
```
pip install git+https://github.com/SevenLines/pinterest-board-downloader.git
```

Usage
---

To download all user boards, run

```
pinterest.py username
```

to download specific board run

```
pinterest.py username/boardname
```

by default it dont redownload already fetched images, but you can force overwrite by passing -f flag

 ```
pinterest.py username/boardname -f
```

