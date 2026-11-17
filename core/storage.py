"""Static file links carry the file's last change time, such as app.js?v=1794634117.

After an update the link changes, so the browser fetches the new file instead of an old saved copy.
No collectstatic step is needed for this, and links to files that can't be found stay as they were.
"""

import os

from django.contrib.staticfiles import finders
from django.contrib.staticfiles.storage import StaticFilesStorage


class VersionedStaticFilesStorage(StaticFilesStorage):
    def url(self, name):
        url = super().url(name)
        path = finders.find(name)
        if isinstance(path, list):
            path = path[0] if path else None
        if not path and self.exists(name):
            path = self.path(name)
        try:
            version = int(os.path.getmtime(path))
        except (OSError, TypeError):
            return url
        return f"{url}?v={version}"
