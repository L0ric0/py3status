from __future__ import with_statement

import os

from collections import Iterable, Mapping
from pickle import dump, load
from tempfile import NamedTemporaryFile
from time import time


class Storage:

    data = {}
    initialized = False

    def init(self, py3_wrapper, is_python_2):
        self.is_python_2 = is_python_2
        self.py3_wrapper = py3_wrapper

        self.config = py3_wrapper.config
        py3_config = self.config.get('py3_config', {})
        storage_config = py3_config.get('py3status', {}).get('storage')

        if storage_config:
            storage_file = os.path.expanduser(storage_config)
            if '/' in storage_file:
                storage_path = None
            else:
                storage_path = os.environ.get('XDG_CACHE_HOME')
        else:
            storage_path = os.environ.get('XDG_CACHE_HOME')
            storage_file = 'py3status_cache.data'

        if not storage_path:
            storage_path = os.path.expanduser('~/.cache')
        self.storage = os.path.join(storage_path, storage_file)

        try:
            with open(self.storage, 'rb') as f:
                try:
                    # python3
                    self.data = load(f, encoding='bytes')
                except TypeError:
                    # python2
                    self.data = load(f)
        except IOError:
            pass
        self.py3_wrapper.log(
            'storage_path: {}\nstorage_data: {}'.format(self.storage, self.data)
        )
        self.initialized = True

    def save(self):
        """
        Save our data to disk. We want to always have a valid file.
        """
        with NamedTemporaryFile(
                dir=os.path.dirname(self.storage), delete=False
        ) as f:
            # we use protocol=2 for python 2/3 compatibility
            dump(self.data, f, protocol=2)
            f.flush()
            os.fsync(f.fileno())
            tmppath = f.name
        os.rename(tmppath, self.storage)

    def fix(self, item):
        """
        Make sure all strings are unicode for python 2/3 compatability
        """
        if not self.is_python_2:
            return item
        if isinstance(item, str):
            return item.decode('utf-8')
        if isinstance(item, unicode):  # noqa <-- python3 has no unicode
            return item
        if isinstance(item, Mapping):
            return dict(map(self.fix, item.items()))
        elif isinstance(item, Iterable):
            return type(item)(map(self.fix, item))

        return item

    def storage_set(self, module_name, key, value):
        if key.startswith('_'):
            raise ValueError('cannot set keys starting with an underscore "_"')

        key = self.fix(key)
        value = self.fix(value)
        if self.data.get(module_name, {}).get(key) == value:
            return

        if module_name not in self.data:
            self.data[module_name] = {}
        self.data[module_name][key] = value
        ts = time()
        if '_ctime' not in self.data[module_name]:
            self.data[module_name]['_ctime'] = ts
        self.data[module_name]['_mtime'] = ts
        self.save()

    def storage_get(self, module_name, key):
        key = self.fix(key)
        return self.data.get(module_name, {}).get(key, None)

    def storage_del(self, module_name, key=None):
        key = self.fix(key)
        if module_name in self.data and key in self.data[module_name]:
            del self.data[module_name][key]
            self.save()

    def storage_keys(self, module_name):
        return self.data.get(module_name, {}).keys()
