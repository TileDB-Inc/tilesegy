import itertools as it
from typing import Iterator, Mapping, Union

import numpy as np
import pytest
from segyio import SegyFile, TraceField
from tiledb.libtiledb import TileDBError

import tilesegy
from tests.conftest import parametrize_tilesegy_segyfiles, parametrize_tilesegys
from tilesegy import StructuredTileSegy, TileSegy


def assert_equal_arrays(
    a: Union[np.ndarray, np.number],
    b: Union[np.ndarray, np.number],
    reshape: bool = False,
) -> None:
    assert a.dtype == b.dtype
    if isinstance(a, np.number) or isinstance(b, np.number):
        assert isinstance(a, np.number) and isinstance(b, np.number)
        assert a == b
    elif not reshape:
        assert a.ndim == b.ndim
        assert a.shape == b.shape
    else:
        assert a.ndim == b.ndim + 1
        assert a.shape[0] * a.shape[1] == b.shape[0]
        assert a.shape[-2:] == b.shape[-2:]
        b = b.reshape(a.shape)
    np.testing.assert_array_equal(a, b)


def segy_gen_to_array(segy_gen: Iterator[np.ndarray]) -> np.ndarray:
    return np.array(list(map(np.copy, segy_gen)))


def stringify_keys(d: Mapping[int, int]) -> Mapping[str, int]:
    return {str(k): v for k, v in d.items()}


def iter_slices(i: int, j: int) -> Iterator[slice]:
    return (slice(*bounds) for bounds in it.product((None, i), (None, j)))


class TestTileSegy:
    @parametrize_tilesegy_segyfiles("t", "s")
    def test_sorting(self, t: TileSegy, s: SegyFile) -> None:
        assert t.sorting == s.sorting

    @parametrize_tilesegy_segyfiles("t", "s")
    def test_bin(self, t: TileSegy, s: SegyFile) -> None:
        assert t.bin == stringify_keys(s.bin)

    @parametrize_tilesegy_segyfiles("t", "s")
    def test_text(self, t: TileSegy, s: SegyFile) -> None:
        assert t.text == list(s.text)

    @parametrize_tilesegy_segyfiles("t", "s")
    def test_samples(self, t: TileSegy, s: SegyFile) -> None:
        assert_equal_arrays(t.samples, s.samples)

    @parametrize_tilesegys("t")
    def test_close(self, t: TileSegy) -> None:
        t.bin
        t.close()
        with pytest.raises(TileDBError):
            t.bin

    @parametrize_tilesegys("t")
    def test_context_manager(self, t: TileSegy) -> None:
        with tilesegy.open(t.uri) as t2:
            t2.bin
        with pytest.raises(TileDBError):
            t2.bin

    @parametrize_tilesegy_segyfiles("t", "s")
    def test_repr(self, t: TileSegy, s: SegyFile) -> None:
        if s.unstructured:
            assert repr(t) == f"TileSegy('{str(t.uri)}')"
        else:
            assert repr(t) == f"StructuredTileSegy('{str(t.uri)}')"


class TestTileSegyTrace:
    @parametrize_tilesegy_segyfiles("t", "s")
    def test_len(self, t: TileSegy, s: SegyFile) -> None:
        assert len(t.trace) == len(s.trace) == s.tracecount

    @parametrize_tilesegy_segyfiles("t", "s")
    def test_get(self, t: TileSegy, s: SegyFile) -> None:
        i = np.random.randint(0, s.tracecount // 2)
        j = np.random.randint(i + 1, s.tracecount)
        x = np.random.randint(0, len(s.samples) // 2)
        y = np.random.randint(x + 1, len(s.samples))

        # one trace, all samples
        assert_equal_arrays(t.trace[i], s.trace[i])

        # one trace, one sample
        assert_equal_arrays(t.trace[i, x], s.trace[i, x])

        # one trace, slice samples
        for sl in iter_slices(x, y):
            assert_equal_arrays(t.trace[i, sl], s.trace[i, sl])

        for sl in iter_slices(i, j):
            # slices traces, all samples
            assert_equal_arrays(t.trace[sl], segy_gen_to_array(s.trace[sl]))
            # slices traces, one sample
            assert_equal_arrays(t.trace[sl, x], segy_gen_to_array(s.trace[sl, x]))
            # slices traces, slice samples
            for sl2 in iter_slices(x, y):
                assert_equal_arrays(
                    t.trace[sl, sl2], segy_gen_to_array(s.trace[sl, sl2])
                )

    @parametrize_tilesegy_segyfiles("t", "s", structured=False)
    def test_header(self, t: TileSegy, s: SegyFile) -> None:
        i = np.random.randint(0, s.tracecount // 2)
        j = i + 20
        assert len(t.header) == len(s.header)
        assert t.header[i] == stringify_keys(s.header[i])
        assert t.header[i:j] == list(map(stringify_keys, s.header[i:j]))

    @parametrize_tilesegy_segyfiles("t", "s", structured=False)
    def test_attributes(self, t: TileSegy, s: SegyFile) -> None:
        str_attr = "TraceNumber"
        t_attrs = t.attributes(str_attr)
        s_attrs = s.attributes(getattr(TraceField, str_attr))

        i = np.random.randint(0, s.tracecount // 2)
        j = np.random.randint(i + 1, s.tracecount)
        assert len(t_attrs) == len(s_attrs)
        assert t_attrs[i] == s_attrs[i]
        for sl in iter_slices(i, j):
            assert t_attrs[sl] == s_attrs[sl].tolist()


class TestTileSegyDepth:
    @parametrize_tilesegy_segyfiles("t", "s")
    def test_len(self, t: StructuredTileSegy, s: SegyFile) -> None:
        assert len(t.depth) == len(s.depth_slice)

    @parametrize_tilesegy_segyfiles("t", "s")
    def test_get(self, t: StructuredTileSegy, s: SegyFile) -> None:
        i = np.random.randint(0, len(s.samples) // 2)
        j = np.random.randint(i + 1, len(s.samples))
        # one depth
        assert_equal_arrays(t.depth[i], s.depth_slice[i])
        # slice depths
        for sl in iter_slices(i, j):
            assert_equal_arrays(t.depth[sl], segy_gen_to_array(s.depth_slice[sl]))


class TestStructuredTileSegy:
    @parametrize_tilesegy_segyfiles("t", "s", structured=True)
    def test_offsets(self, t: StructuredTileSegy, s: SegyFile) -> None:
        assert_equal_arrays(t.offsets, s.offsets)

    @parametrize_tilesegy_segyfiles("t", "s", structured=True)
    def test_fast(self, t: StructuredTileSegy, s: SegyFile) -> None:
        if s.fast is s.iline:
            assert str(t.fast) == "Line('ilines')"
        else:
            assert s.fast is s.xline
            assert str(t.fast) == "Line('xlines')"

    @pytest.mark.parametrize("lines", ["ilines", "xlines"])
    @parametrize_tilesegy_segyfiles("t", "s", structured=True)
    def test_lines(self, lines: str, t: StructuredTileSegy, s: SegyFile) -> None:
        assert_equal_arrays(getattr(t, lines), getattr(s, lines))

    @pytest.mark.parametrize("line", ["iline", "xline"])
    @parametrize_tilesegy_segyfiles("t", "s", structured=True)
    def test_line_len(self, line: str, t: StructuredTileSegy, s: SegyFile) -> None:
        assert len(getattr(t, line)) == len(getattr(s, line))

    @pytest.mark.parametrize("line,lines", [("iline", "ilines"), ("xline", "xlines")])
    @parametrize_tilesegy_segyfiles("t", "s", structured=True)
    def test_line_get(
        self, line: str, lines: str, t: StructuredTileSegy, s: SegyFile,
    ) -> None:
        t_line, s_line = getattr(t, line), getattr(s, line)
        i, j = np.sort(np.random.choice(getattr(s, lines), 2, replace=False))
        x = np.random.choice(s.offsets)

        # one line, first offset
        assert_equal_arrays(t_line[i], s_line[i])
        # one line, x offset
        assert_equal_arrays(t_line[i, x], s_line[i, x])

        for sl in iter_slices(i, j):
            # slice lines, first offset
            assert_equal_arrays(t_line[sl], segy_gen_to_array(s_line[sl]))
            # slice lines, x offset
            assert_equal_arrays(t_line[sl, x], segy_gen_to_array(s_line[sl, x]))

            if len(s.offsets) > 1:
                x, y = s.offsets[1], s.offsets[3]
                for sl2 in iter_slices(x, y):
                    # one line, slice offsets
                    assert_equal_arrays(
                        t_line[i, sl2], segy_gen_to_array(s_line[i, sl2])
                    )
                    # slice lines, slice offsets
                    assert_equal_arrays(
                        t_line[sl, sl2],
                        segy_gen_to_array(s_line[sl, sl2]),
                        reshape=True,
                    )

    @parametrize_tilesegy_segyfiles("t", "s", structured=True)
    def test_depth_offsets(self, t: StructuredTileSegy, s: SegyFile) -> None:
        # segyio doesn't currently support offset indexing for depth

        if s.fast is s.iline:
            fast, slow = s.ilines, s.xlines
        else:
            fast, slow = s.xlines, s.ilines
        shape = tuple(map(len, (fast, slow)))

        i = np.random.randint(0, len(s.samples) // 2)
        j = np.random.randint(i + 1, len(s.samples))
        x = np.random.choice(s.offsets)

        # one line, x offset
        with pytest.raises(TypeError):
            s.depth_slice[i, x]
        assert t.depth[i, x].ndim == 2
        assert t.depth[i, x].shape == shape

        for sl in iter_slices(i, j):
            # slice lines, x offset
            with pytest.raises(TypeError):
                s.depth[sl, x]
            assert t.depth[sl, x].ndim == 3
            assert t.depth[sl, x].shape[-2:] == shape

            if len(s.offsets) > 1:
                x, y = s.offsets[1], s.offsets[3]
                for sl2 in iter_slices(x, y):
                    # one line, slice offsets
                    with pytest.raises(TypeError):
                        s.depth[i, sl2]
                    assert t.depth[i, sl2].ndim == 3
                    assert t.depth[i, sl2].shape[-2:] == shape

                    # slice lines, slice offsets
                    with pytest.raises(TypeError):
                        s.depth[sl, sl2]
                    assert t.depth[sl, sl2].ndim == 4
                    assert t.depth[sl, sl2].shape[-2:] == shape
