"""Paged Coreless virtual RAM backed by persistent storage."""
PAGE_SIZE = 4096


class VirtualRAM:
    def __init__(self, size, image=None, name="ram"):
        if size <= 0 or size % PAGE_SIZE:
            raise ValueError("Coreless RAM size must be a positive page multiple")
        self.size = size
        self.image = image
        self.name = name
        self.cache = {}
        self.dirty = set()
        if image is not None:
            image.ensure_ram(name, size)

    def __len__(self):
        return self.size

    def _check(self, start, end):
        if start < 0 or end < start or end > self.size:
            raise IndexError("Coreless RAM access outside virtual RAM")

    def _page(self, number):
        if number not in self.cache:
            if self.image is not None:
                data = self.image.get_ram_page(self.name, number)
            else:
                data = bytes(PAGE_SIZE)
            self.cache[number] = bytearray(data)
        return self.cache[number]

    def _read(self, start, end):
        self._check(start, end)
        out = bytearray()
        while start < end:
            number, offset = divmod(start, PAGE_SIZE)
            count = min(end - start, PAGE_SIZE - offset)
            out.extend(self._page(number)[offset:offset + count])
            start += count
        return bytes(out)

    def _write(self, start, data):
        data = bytes(data)
        self._check(start, start + len(data))
        position = 0
        while position < len(data):
            number, offset = divmod(start + position, PAGE_SIZE)
            count = min(len(data) - position, PAGE_SIZE - offset)
            self._page(number)[offset:offset + count] = data[position:position + count]
            self.dirty.add(number)
            position += count

    def flush(self):
        if self.image is not None and self.dirty:
            for number in sorted(self.dirty):
                self.image.put_ram_page(self.name, number, self._page(number), sync=False)
            self.image.sync()
        self.dirty.clear()

    def __getitem__(self, key):
        if isinstance(key, slice):
            start, end, step = key.indices(self.size)
            if step != 1:
                return self._read(start, end)[::step]
            return self._read(start, end)
        if key < 0:
            key += self.size
        self._check(key, key + 1)
        return self._page(key // PAGE_SIZE)[key % PAGE_SIZE]

    def __setitem__(self, key, value):
        if isinstance(key, slice):
            start, end, step = key.indices(self.size)
            if step != 1 or len(value) != end - start:
                raise ValueError("Coreless RAM slice assignment must preserve length")
            self._write(start, value)
            return
        if key < 0:
            key += self.size
        self._write(key, bytes((value,)))
