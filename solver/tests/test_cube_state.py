import random

from solver import cube_state as cs


def _random_scramble(rng, length):
    return [rng.choice(cs.MOVES) for _ in range(length)]


def _random_physical_state(rng):
    return cs.apply_physical_alg(cs.PHYS_SOLVED, _random_scramble(rng, rng.randrange(1, 30)))


def test_24_rotations():
    assert len(cs.ROT_WORDS) == 24
    assert any(w == () for w in cs.ROT_WORDS)
    # every rotation is a full legal re-orientation: piece 7 returns to slot 7
    # with twist 0 exactly once the frame is fixed by the identity rotation.
    rng = random.Random(0)
    for _ in range(50):
        state = _random_physical_state(rng)
        frames = set()
        for w in cs.ROT_WORDS:
            p8, o8 = cs.apply_physical_alg(state, w)
            frames.add((p8, o8))
        assert len(frames) == 24


def test_18_moves():
    assert len(cs.MOVES) == 18
    assert cs.MOVES == (
        "U", "U'", "U2",
        "D", "D'", "D2",
        "L", "L'", "L2",
        "R", "R'", "R2",
        "F", "F'", "F2",
        "B", "B'", "B2",
    )


def test_inverse():
    for m in cs.MOVES:
        assert cs.inverse(cs.inverse(m)) == m
    assert cs.inverse("U") == "U'"
    assert cs.inverse("U'") == "U"
    assert cs.inverse("U2") == "U2"
    assert cs.inverse("F") == "F'"


def test_physical_round_trip_all_moves():
    rng = random.Random(1)
    states = [cs.PHYS_SOLVED]
    for _ in range(10):
        states.append(_random_physical_state(rng))
    for state in states:
        for m in cs.MOVES:
            after = cs.apply_physical(cs.apply_physical(state, m), cs.inverse(m))
            assert after == state, (state, m, after)
            back = cs.apply_physical(cs.apply_physical(state, cs.inverse(m)), m)
            assert back == state, (state, m)


def test_quarter_turn_power_4_is_identity():
    rng = random.Random(2)
    for _ in range(20):
        state = _random_physical_state(rng)
        for face in "UDLRFB":
            step = state
            for _ in range(4):
                step = cs.apply_physical(step, face)
            assert step == state, (face, state)


def test_move_actions_are_determined_by_the_definition():
    """Action compositions must match the cubing 2x2x2 definition record."""
    assert cs.ACTIONS["U"] == ((1, 2, 3, 0, 4, 5, 6, 7), (0,) * 8)
    # derived moves are the [g: h] = g h g^-1 conjugations from the record
    assert cs.ACTIONS["F"] == cs._conjugate(cs.ACTIONS["x"], cs.ACTIONS["U"])
    assert cs.ACTIONS["L"] == cs._conjugate(cs.ACTIONS["z"], cs.ACTIONS["U"])
    assert cs.ACTIONS["R"] == cs._conjugate(
        cs._inverse(cs.ACTIONS["z"]), cs.ACTIONS["U"]
    )
    assert cs.ACTIONS["B"] == cs._conjugate(
        cs._inverse(cs.ACTIONS["x"]), cs.ACTIONS["U"]
    )
    assert cs.ACTIONS["D"] == cs._conjugate(
        cs._compose(cs.ACTIONS["x"], cs.ACTIONS["x"]), cs.ACTIONS["U"]
    )


def test_canonical7_invariants():
    rng = random.Random(3)
    for _ in range(100):
        p8, o8 = _random_physical_state(rng)
        perm7, orient7 = cs.canonical7((p8, o8))
        assert set(perm7) == set(range(7))
        assert all(0 <= o <= 2 for o in orient7)
        assert sum(orient7) % 3 == 0
        # the canonical frame fixes piece 7 at slot 7 with twist 0
        full_p, full_o = cs.to_full(perm7, orient7)
        assert full_p[7] == 7 and full_o[7] == 0


def test_canonical7_of_solved_and_scrambled():
    assert cs.canonical7(cs.PHYS_SOLVED) == cs.SOLVED
    rng = random.Random(4)
    for _ in range(50):
        state = _random_physical_state(rng)
        c = cs.canonical7(state)
        # rotating the whole cube must not change the canonical representative
        for w in cs.ROT_WORDS:
            assert cs.canonical7(cs.apply_physical_alg(state, w)) == c


def test_is_solved():
    assert cs.is_solved_physical(cs.PHYS_SOLVED)
    rng = random.Random(5)
    for _ in range(20):
        state = _random_physical_state(rng)
        if state != cs.PHYS_SOLVED:
            assert not cs.is_solved_physical(state)


def test_apply_physical_alg_reaches_solved():
    rng = random.Random(6)
    for _ in range(20):
        seq = _random_scramble(rng, rng.randrange(1, 20))
        state = cs.apply_physical_alg(cs.PHYS_SOLVED, seq)
        back = cs.apply_physical_alg(
            state, [cs.inverse(m) for m in reversed(seq)]
        )
        assert back == cs.PHYS_SOLVED


def test_tables_match_direct_8corner_simulation():
    """Move tables must equal the physical 8-corner action on canonical states."""
    rng = random.Random(7)
    for _ in range(30):
        state = _random_physical_state(rng)
        perm7, orient7 = cs.canonical7(state)
        for m in cs.MOVES:
            got = cs.apply_move((perm7, orient7), m)
            full = cs.apply_physical(cs.to_full(perm7, orient7), m)
            expected = cs.canonical7(full)
            assert got == expected, (m, (perm7, orient7), got, expected)


def test_canonical_move_tables_are_state_independent():
    rng = random.Random(8)
    for _ in range(200):
        state = _random_physical_state(rng)
        for m in cs.MOVES:
            s1 = cs.apply_move(cs.canonical7(state), m)
            s2 = cs.apply_move(cs.canonical7(state), cs.inverse(m))
            # applying move then its inverse returns to the canonical frame
            assert cs.apply_move(s1, cs.inverse(m)) == cs.canonical7(state)
            assert cs.apply_move(s2, m) == cs.canonical7(state)


def test_orientation_and_permutation_validity():
    rng = random.Random(9)
    for _ in range(100):
        state = cs.apply_physical_alg(
            cs.PHYS_SOLVED, _random_scramble(rng, 20)
        )
        perm7, orient7 = cs.canonical7(state)
        assert all(0 <= o <= 2 for o in orient7)
        assert set(perm7) == set(range(7))