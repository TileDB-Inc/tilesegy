from typing import Dict, Iterable, Iterator, List, Optional, Tuple, Union, cast

import numpy as np
import tiledb

from ._singledispatchmethod import singledispatchmethod  # type: ignore

Index = Union[int, slice]


def tdb_meta_list_to_numpy(tdb: tiledb.Array, meta_key: str) -> np.ndarray:
    value = tdb.meta[meta_key]
    if not isinstance(value, tuple):
        value = (value,)
    return np.array(value)


class Sized:
    def __init__(self, tdb: tiledb.Array):
        self._tdb = tdb

    def __len__(self) -> int:
        return len(self._tdb)


class Header(Sized):
    @singledispatchmethod
    def __getitem__(self, i: object) -> None:
        raise NotImplementedError(f"Cannot index by {i.__class__}")  # pragma: nocover

    @__getitem__.register(int)
    def _get_one(self, i: int) -> int:
        return cast(int, np.asscalar(self._tdb[i]))

    @__getitem__.register(slice)
    def _get_many(self, i: slice) -> List[int]:
        return cast(List[int], self._tdb[i].tolist())


class Headers(Sized):
    @singledispatchmethod
    def __getitem__(self, i: object) -> None:
        raise NotImplementedError(f"Cannot index by {i.__class__}")  # pragma: nocover

    @__getitem__.register(int)
    def _get_one(self, i: int) -> Dict[str, int]:
        return cast(Dict[str, int], self._tdb[i])

    @__getitem__.register(slice)
    def _get_many(self, i: slice) -> List[Dict[str, int]]:
        headers = self._tdb[i]
        keys = headers.keys()
        columns = [v.tolist() for v in headers.values()]
        return [dict(zip(keys, row)) for row in zip(*columns)]


class Traces:
    def __init__(self, data_tdb: tiledb.Array, headers_tdb: tiledb.Array):
        self._data_tdb = data_tdb
        self._headers_tdb = headers_tdb

    def __len__(self) -> int:
        return len(self._data_tdb)

    def __getitem__(
        self, i: Union[Index, Tuple[Index, Index]]
    ) -> Union[np.number, np.ndarray]:
        return self._data_tdb[i]

    @property
    def headers(self) -> Headers:
        return Headers(self._headers_tdb)

    def header(self, name: str) -> Header:
        return Header(tiledb.DenseArray(self._headers_tdb.uri, attr=name))


class Lines:
    def __init__(
        self,
        data_tdb: tiledb.Array,
        headers_tdb: tiledb.Array,
        *,
        dimension: int,
        name: Optional[str] = None,
    ):
        self._dim = dimension
        self._data_tdb = data_tdb
        self._headers_tdb = headers_tdb
        self._name = name

    @property
    def indexes(self) -> np.ndarray:
        if self._name is not None:
            return tdb_meta_list_to_numpy(self._data_tdb, self._name)
        else:
            return np.arange(len(self))

    def __len__(self) -> int:
        return cast(int, self._data_tdb.shape[self._dim])


class FilteredRange:
    """Fast filtering of ranges.

    `FilteredRange(members)[start:stop:end]` returns an iterator over the values of
    `range(start, stop, end)` that are included in `members`.

    If `start` is None, it defaults to `min(members)` if `step` is increasing or `max(members)`
    if step is decreasing.

    If `stop` is None, it defaults to `max(members)+1` if `step` is increasing or `min(members)-1`
    if step is decreasing.
    """

    def __init__(self, members: Iterable[int]):
        members = set(members)
        self._min_val = min(members)
        self._max_val = max(members) + 1
        self._is_member = members.__contains__

    def __getitem__(self, i: Union[int, slice]) -> Iterator[int]:
        s = slice(i, i + 1) if not isinstance(i, slice) else i
        start, stop, step = s.start, s.stop, s.step
        min_val = self._min_val
        if step is None or step > 0:  # increasing step
            if start is None or start < min_val:
                start = min_val
        else:  # decreasing step
            if stop is None or stop < min_val - 1:
                stop = min_val - 1
        start, stop, step = slice(start, stop, step).indices(self._max_val)
        return filter(self._is_member, range(start, stop, step))
