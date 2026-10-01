from pathlib import Path

from dataset.build import INPUT_DIRS, collect
from dataset.from_annotations import convert
from dataset.schema import Record, detect_script, read_jsonl, text_hash, validate, write_jsonl
from dataset.splits import deduplicate, split
from dataset.taxonomy import ATTACK_CATEGORIES, BENIGN_CATEGORIES


def attack(text: str, category: str = "instruction_override", language: str = "en", **kw) -> Record:
    return Record(text=text, label="attack", category=category, language=language, source="seed", **kw)


def test_record_fills_in_id_and_script() -> None:
    record = attack("Some attack text")
    assert record.id == f"seed:{text_hash('Some attack text')}"
    assert record.script == "latin"
    assert Record(text="नमस्ते दुनिया", label="benign", category="benign_plain", language="hi").script == "devanagari"


def test_detect_script_handles_each_language_and_mixing() -> None:
    assert detect_script("hello world") == "latin"
    assert detect_script("यह एक वाक्य है") == "devanagari"
    assert detect_script("இது ஒரு வாக்கியம்") == "tamil"
    assert detect_script("reset karne ke liye सिस्टम बटन दबाओ और छोड़ दो यहाँ") == "mixed"


def test_validate_accepts_good_records_and_flags_bad_ones() -> None:
    assert validate(attack("ok")) == []
    assert "bad label" in " ".join(validate(Record(text="x", label="weird", category="benign_plain")))
    assert "not valid for label" in " ".join(validate(Record(text="x", label="attack", category="benign_plain")))
    assert "unexpected for language" in " ".join(
        validate(Record(text="hello", label="attack", category="instruction_override", language="hi", script="latin"))
    )
    assert "benign records must not set a goal" in " ".join(
        validate(Record(text="x", label="benign", category="benign_plain", goal="action_hijack"))
    )
    assert "empty text" in " ".join(validate(attack("   ")))


def test_jsonl_round_trips_and_skips_comments(tmp_path: Path) -> None:
    path = tmp_path / "x.jsonl"
    records = [attack("one"), Record(text="two", label="benign", category="benign_plain")]
    assert write_jsonl(records, path) == 2
    path.write_text("// a comment\n" + path.read_text(encoding="utf-8"), encoding="utf-8")
    loaded = list(read_jsonl(path))
    assert [r.text for r in loaded] == ["one", "two"] and loaded[0].id == records[0].id


def test_deduplicate_keeps_byte_distinct_obfuscations() -> None:
    records = [attack("ignore this"), attack("ignore this"), attack("ignore​this")]
    unique, removed = deduplicate(records)
    assert removed == 1 and len(unique) == 2


def test_split_is_stratified_reproducible_and_holds_out_a_category() -> None:
    records = (
        [attack(f"override number {i}", "instruction_override") for i in range(20)]
        + [attack(f"encoded number {i}", "encoded_text") for i in range(20)]
        + [Record(text=f"benign number {i}", label="benign", category="benign_plain", source="seed") for i in range(20)]
    )
    result = split(records, heldout_category="encoded_text", seed=7)

    assert len(result.heldout) == 20
    assert all(r.category == "encoded_text" for r in result.heldout)
    assert not any(r.category == "encoded_text" for r in result.train + result.val + result.test)
    # 40 non-heldout records at 70/15/15.
    assert (len(result.train), len(result.val), len(result.test)) == (28, 6, 6)
    assert [r.id for r in split(records, "encoded_text", seed=7).train] == [r.id for r in result.train]
    assert [r.id for r in split(records, "encoded_text", seed=9).train] != [r.id for r in result.train]


def test_from_annotations_exports_only_approved_non_example_rows(tmp_path: Path) -> None:
    csv_path = tmp_path / "ann.csv"
    csv_path.write_text(
        "seed_id,category,goal,language,text,author,reviewer,review_status,notes\n"
        "EXAMPLE-x,benign_plain,,en,skip me,demo,,approved,example\n"
        "OVR-1,instruction_override,action_hijack,hi-Latn,approved attack text,asha,ravi,approved,\n"
        "OVR-2,instruction_override,action_hijack,hi-Latn,draft text,asha,,draft,\n"
        "BEN-1,benign_instructional,,hi-Latn,recipe text here,asha,ravi,approved,\n",
        encoding="utf-8",
    )
    records, errors = convert(csv_path)
    assert errors == []
    assert {r.text for r in records} == {"approved attack text", "recipe text here"}
    attack_record = next(r for r in records if r.label == "attack")
    assert attack_record.parent_id == "OVR-1" and attack_record.goal == "action_hijack"
    assert next(r for r in records if r.label == "benign").goal is None


def test_committed_data_is_valid_and_has_benign_hard_negatives() -> None:
    records, errors = collect(INPUT_DIRS)
    assert errors == [], errors
    benign = [r for r in records if r.label == "benign"]
    assert len(benign) >= 30
    categories = {r.category for r in benign}
    assert {"benign_instructional", "benign_quoted", "benign_technical"} <= categories
    assert {r.language for r in records} >= {"en", "hi", "hi-Latn", "ta", "ta-Latn"}


def test_taxonomy_has_the_planned_categories() -> None:
    assert {"instruction_override", "role_hijacking", "hidden_html", "encoded_text",
            "invisible_chars", "homoglyph", "image_text"} <= set(ATTACK_CATEGORIES)
    assert set(BENIGN_CATEGORIES) == {"benign_plain", "benign_instructional", "benign_quoted", "benign_technical"}
