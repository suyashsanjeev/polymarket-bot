import pathlib


class FileHistory:
    """
    file-based storage for tracking seen market slugs in a text file 
    for persistent deduplication across bot restarts
    """

    def __init__(self, path: str):
        self.path = pathlib.Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._cache = self._load()

    # load existing history from file into memory cache
    def _load(self):
        if self.path.exists():
            return set(self.path.read_text().splitlines())
        return set()

    # add a market slug to the history if not already present
    def add(self, slug: str):
        if slug not in self._cache:
            with self.path.open("a") as f:
                f.write(slug + "\n")
            self._cache.add(slug)

    # check if a market slug has been seen before
    def __contains__(self, slug: str):
        return slug in self._cache

    # return the number of slugs in history
    def __len__(self):
        return len(self._cache)

