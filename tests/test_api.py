from typing import Iterator, Mapping

import numpy as np
import pytest
from segyio import SegyFile, TraceField
from tiledb.libtiledb import TileDBError

import tilesegy
from tests.conftest import parametrize_tilesegy_segyfiles, parametrize_tilesegys
from tilesegy import StructuredTileSegy, TileSegy


def assert_equal_arrays(a: np.ndarray, b: np.ndarray) -> None:
    assert a.dtype == b.dtype
    assert a.shape == b.shape
    np.testing.assert_array_equal(a, b)


def segy_gen_to_array(segy_gen: Iterator[np.ndarray]) -> np.ndarray:
    return np.array(list(map(np.copy, segy_gen)))


def stringify_keys(d: Mapping[int, int]) -> Mapping[str, int]:
    return {str(k): v for k, v in d.items()}


class TestTileSegy:
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

    @parametrize_tilesegys("t", structured=False)
    def test_repr(self, t: TileSegy) -> None:
        assert repr(t) == f"TileSegy('{str(t.uri)}')"


class TestTileSegyTraces:
    @parametrize_tilesegy_segyfiles("t", "s", structured=False)
    def test_len(self, t: TileSegy, s: SegyFile) -> None:
        assert len(t.traces) == len(s.trace) == s.tracecount

    @parametrize_tilesegy_segyfiles("t", "s", structured=False)
    def test_get_one_trace_all_samples(self, t: TileSegy, s: SegyFile) -> None:
        i = np.random.randint(0, s.tracecount)
        assert_equal_arrays(t.traces[i], s.trace[i])

    @parametrize_tilesegy_segyfiles("t", "s", structured=False)
    def test_get_one_trace_one_sample(self, t: TileSegy, s: SegyFile) -> None:
        i = np.random.randint(0, s.tracecount)
        x = np.random.randint(0, len(s.samples))
        assert t.traces[i, x] == s.trace[i, x]

    @parametrize_tilesegy_segyfiles("t", "s", structured=False)
    def test_get_one_trace_slice_samples(self, t: TileSegy, s: SegyFile) -> None:
        i = np.random.randint(0, s.tracecount)
        x = np.random.randint(0, len(s.samples) // 2)
        y = np.random.randint(x + 1, len(s.samples))

        assert_equal_arrays(t.traces[i, :], s.trace[i, :])
        assert_equal_arrays(t.traces[i, x:], s.trace[i, x:])
        assert_equal_arrays(t.traces[i, :y], s.trace[i, :y])
        assert_equal_arrays(t.traces[i, x:y], s.trace[i, x:y])

    @parametrize_tilesegy_segyfiles("t", "s", structured=False)
    def test_get_slice_traces_all_samples(self, t: TileSegy, s: SegyFile) -> None:
        i = np.random.randint(0, s.tracecount // 2)
        j = np.random.randint(i + 1, s.tracecount)

        assert_equal_arrays(t.traces[:], segy_gen_to_array(s.trace[:]))
        assert_equal_arrays(t.traces[i:], segy_gen_to_array(s.trace[i:]))
        assert_equal_arrays(t.traces[:j], segy_gen_to_array(s.trace[:j]))
        assert_equal_arrays(t.traces[i:j], segy_gen_to_array(s.trace[i:j]))

    @parametrize_tilesegy_segyfiles("t", "s", structured=False)
    def test_get_slice_traces_one_sample(self, t: TileSegy, s: SegyFile) -> None:
        i = np.random.randint(0, s.tracecount // 2)
        j = np.random.randint(i + 1, s.tracecount)
        x = np.random.randint(0, len(s.samples))

        assert_equal_arrays(t.traces[:, x], np.fromiter(s.trace[:, x], s.dtype))
        assert_equal_arrays(t.traces[i:, x], np.fromiter(s.trace[i:, x], s.dtype))
        assert_equal_arrays(t.traces[:j, x], np.fromiter(s.trace[:j, x], s.dtype))
        assert_equal_arrays(t.traces[i:j, x], np.fromiter(s.trace[i:j, x], s.dtype))

    @parametrize_tilesegy_segyfiles("t", "s", structured=False)
    def test_get_slice_traces_slice_samples(self, t: TileSegy, s: SegyFile) -> None:
        i = np.random.randint(0, s.tracecount // 2)
        j = np.random.randint(i + 1, s.tracecount)

        x = np.random.randint(0, len(s.samples) // 2)
        y = np.random.randint(x + 1, len(s.samples))

        assert_equal_arrays(t.traces[:, :], segy_gen_to_array(s.trace[:, :]))
        assert_equal_arrays(t.traces[:, x:], segy_gen_to_array(s.trace[:, x:]))
        assert_equal_arrays(t.traces[:, :y], segy_gen_to_array(s.trace[:, :y]))
        assert_equal_arrays(t.traces[:, x:y], segy_gen_to_array(s.trace[:, x:y]))

        assert_equal_arrays(t.traces[i:, :], segy_gen_to_array(s.trace[i:, :]))
        assert_equal_arrays(t.traces[i:, x:], segy_gen_to_array(s.trace[i:, x:]))
        assert_equal_arrays(t.traces[i:, :y], segy_gen_to_array(s.trace[i:, :y]))
        assert_equal_arrays(t.traces[i:, x:y], segy_gen_to_array(s.trace[i:, x:y]))

        assert_equal_arrays(t.traces[:j, :], segy_gen_to_array(s.trace[:j, :]))
        assert_equal_arrays(t.traces[:j, x:], segy_gen_to_array(s.trace[:j, x:]))
        assert_equal_arrays(t.traces[:j, :y], segy_gen_to_array(s.trace[:j, :y]))
        assert_equal_arrays(t.traces[:j, x:y], segy_gen_to_array(s.trace[:j, x:y]))

        assert_equal_arrays(t.traces[i:j, :], segy_gen_to_array(s.trace[i:j, :]))
        assert_equal_arrays(t.traces[i:j, x:], segy_gen_to_array(s.trace[i:j, x:]))
        assert_equal_arrays(t.traces[i:j, :y], segy_gen_to_array(s.trace[i:j, :y]))
        assert_equal_arrays(t.traces[i:j, x:y], segy_gen_to_array(s.trace[i:j, x:y]))

    @parametrize_tilesegy_segyfiles("t", "s", structured=False)
    def test_headers(self, t: TileSegy, s: SegyFile) -> None:
        i = np.random.randint(0, s.tracecount // 2)
        j = i + 20

        assert len(t.traces.headers) == len(s.header)
        assert t.traces.headers[i] == stringify_keys(s.header[i])
        assert t.traces.headers[i:j] == list(map(stringify_keys, s.header[i:j]))

    @parametrize_tilesegy_segyfiles("t", "s", structured=False)
    def test_header(self, t: TileSegy, s: SegyFile) -> None:
        str_attr = "TraceNumber"
        t_attrs = t.traces.header(str_attr)
        s_attrs = s.attributes(getattr(TraceField, str_attr))

        i = np.random.randint(0, s.tracecount // 2)
        j = np.random.randint(i + 1, s.tracecount)

        assert len(t_attrs) == len(s_attrs)
        assert t_attrs[i] == s_attrs[i]
        assert t_attrs[i:] == s_attrs[i:].tolist()
        assert t_attrs[:j] == s_attrs[:j].tolist()
        assert t_attrs[i:j] == s_attrs[i:j].tolist()


class TestStructuredTileSegy:
    @parametrize_tilesegys("t", structured=True)
    def test_repr(self, t: StructuredTileSegy) -> None:
        assert repr(t) == f"StructuredTileSegy('{str(t.uri)}')"

    @parametrize_tilesegy_segyfiles("t", "s", structured=True)
    def test_offsets(self, t: StructuredTileSegy, s: SegyFile) -> None:
        assert_equal_arrays(t.offsets, s.offsets)


class TestStructuredTileSegyIlines:
    @parametrize_tilesegy_segyfiles("t", "s", structured=True)
    def test_len(self, t: StructuredTileSegy, s: SegyFile) -> None:
        assert len(t.ilines) == len(s.iline)

    @parametrize_tilesegy_segyfiles("t", "s", structured=True)
    def test_indexes(self, t: StructuredTileSegy, s: SegyFile) -> None:
        assert_equal_arrays(t.ilines.indexes, s.ilines)


class TestStructuredTileSegyXlines:
    @parametrize_tilesegy_segyfiles("t", "s", structured=True)
    def test_len(self, t: StructuredTileSegy, s: SegyFile) -> None:
        assert len(t.xlines) == len(s.xline)

    @parametrize_tilesegy_segyfiles("t", "s", structured=True)
    def test_indexes(self, t: StructuredTileSegy, s: SegyFile) -> None:
        assert_equal_arrays(t.xlines.indexes, s.xlines)


class TestStructuredTileSegyDepths:
    @parametrize_tilesegy_segyfiles("t", "s", structured=True)
    def test_len(self, t: StructuredTileSegy, s: SegyFile) -> None:
        assert len(t.depths) == len(s.depth_slice)

    @parametrize_tilesegy_segyfiles("t", "s", structured=True)
    def test_indexes(self, t: StructuredTileSegy, s: SegyFile) -> None:
        assert_equal_arrays(t.depths.indexes, np.arange(len(s.samples)))