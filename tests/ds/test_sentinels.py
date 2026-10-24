import pickle
from functools import lru_cache

from escudeiro.ds.sentinels import Sentinel, _registry, sentinel


class TestSentinel:
    def test_repr_single_sentinel(self) -> None:
        @sentinel
        class MISSING:
            pass

        assert repr(MISSING) == "MISSING"

    def test_repr_enum_like_sentinel(self) -> None:
        @sentinel
        class STATUS:
            PENDING = 1
            COMPLETED = 2

        assert repr(STATUS.PENDING) == "1"
        assert repr(STATUS.COMPLETED) == "2"

    def test_reduce_single_sentinel(self) -> None:
        @sentinel
        class MISSING:
            pass

        reduced = MISSING.__reduce__()
        assert reduced[0] is Sentinel
        assert reduced[1] == (
            "MISSING",
            "tests.ds.test_sentinels",
            None,
        )

        pickled = pickle.dumps(MISSING)
        unpickled = pickle.loads(pickled)
        assert unpickled is MISSING

    def test_reduce_enum_like_sentinel(self) -> None:
        @sentinel
        class STATUS:
            PENDING = 1
            COMPLETED = 2

        reduced_pending = STATUS.PENDING.__reduce__()
        assert reduced_pending[0] is Sentinel
        assert reduced_pending[1] == (
            "STATUS.PENDING",
            "tests.ds.test_sentinels",
            1,
        )

        reduced_completed = STATUS.COMPLETED.__reduce__()
        assert reduced_completed[0] is Sentinel
        assert reduced_completed[1] == (
            "STATUS.COMPLETED",
            "tests.ds.test_sentinels",
            2,
        )

        pickled_pending = pickle.dumps(STATUS.PENDING)
        unpickled_pending = pickle.loads(pickled_pending)
        assert unpickled_pending is STATUS.PENDING

        pickled_completed = pickle.dumps(STATUS.COMPLETED)
        unpickled_completed = pickle.loads(pickled_completed)
        assert unpickled_completed is STATUS.COMPLETED


class TestSentinelDecorator:
    def setup_method(self) -> None:
        _registry.clear()

    def test_single_sentinel_creation(self) -> None:
        class _MISSING:
            pass

        MISSING = sentinel(_MISSING)

        assert isinstance(MISSING, Sentinel)
        assert repr(MISSING) == "_MISSING"
        assert MISSING is sentinel(_MISSING)  # Ensure uniqueness

    def test_single_sentinel_uniqueness_across_calls(self) -> None:
        @sentinel
        class MISSING_A:
            pass

        @sentinel
        class MISSING_B:
            pass

        assert MISSING_A is not MISSING_B

    def test_enum_like_sentinel_creation(self) -> None:
        @sentinel
        class STATUS:
            PENDING = 1
            COMPLETED = 2
            CANCELLED = "cancelled"

        assert hasattr(STATUS, "PENDING")
        assert hasattr(STATUS, "COMPLETED")
        assert hasattr(STATUS, "CANCELLED")

        assert STATUS.PENDING == 1
        assert STATUS.COMPLETED == 2
        assert STATUS.CANCELLED == "cancelled"

        assert repr(STATUS.PENDING) == "1"
        assert repr(STATUS.COMPLETED) == "2"
        assert repr(STATUS.CANCELLED) == "'cancelled'"

    def test_enum_like_sentinel_uniqueness(self) -> None:
        @sentinel
        class STATUS_A:
            PENDING = 1

        @sentinel
        class STATUS_B:
            PENDING = 1

        assert STATUS_A.PENDING is not STATUS_B.PENDING


    def test_sentinel_with_callable_members_ignored(self) -> None:
        @sentinel
        class MY_SENTINEL:
            VALUE = 1

            def my_method(self) -> int:
                return 10

        assert hasattr(MY_SENTINEL, "VALUE")
        assert not hasattr(MY_SENTINEL, "my_method")

    def test_sentinel_with_dunder_members_ignored(self) -> None:
        @sentinel
        class MY_SENTINEL:
            VALUE = 1
            __dunder_value__ = 2

        assert hasattr(MY_SENTINEL, "VALUE")
        assert not hasattr(MY_SENTINEL, "__dunder_value__")

    def test_sentinel_registry_persistence(self) -> None:
        @sentinel
        class FIRST_CALL:
            pass

        assert "tests.ds.test_sentinels:FIRST_CALL" in _registry
        assert _registry["tests.ds.test_sentinels:FIRST_CALL"] is FIRST_CALL

        @sentinel
        class STATUS_REGISTRY:
            ITEM = 1

        _ = STATUS_REGISTRY.ITEM

        assert "tests.ds.test_sentinels:STATUS_REGISTRY.ITEM" in _registry
        assert _registry["tests.ds.test_sentinels:STATUS_REGISTRY.ITEM"] == 1

        # assert first insertions were not replaced
        assert _registry["tests.ds.test_sentinels:FIRST_CALL"] is FIRST_CALL


class TestSentinelHash:
    def test_plain_sentinel_is_hashable(self) -> None:
        @sentinel
        class MISSING_HASH:
            pass

        assert hash(MISSING_HASH) == hash(MISSING_HASH)
        assert {MISSING_HASH: 1}[MISSING_HASH] == 1
        assert MISSING_HASH in {MISSING_HASH}

    def test_member_sentinels_are_dict_keys(self) -> None:
        @sentinel
        class HASHED_STATUS:
            A = 1
            B = 2

        mapping = {HASHED_STATUS.A: "a", HASHED_STATUS.B: "b"}
        assert mapping[HASHED_STATUS.A] == "a"
        # equal objects hash equal: a member equals its value
        assert HASHED_STATUS.A == 1
        assert hash(HASHED_STATUS.A) == hash(1)

    def test_usable_as_lru_cache_argument(self) -> None:
        @sentinel
        class CACHE_MISSING:
            pass

        @lru_cache
        def f(arg: object) -> object:
            return arg

        assert f(CACHE_MISSING) is CACHE_MISSING

    def test_unhashable_value_falls_back_to_identity(self) -> None:
        odd = Sentinel("odd", "tests.ds", [1, 2])
        assert hash(odd) == object.__hash__(odd)
