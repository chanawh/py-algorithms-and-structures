from trie import Trie

def test_insert_and_search():
    t = Trie()

    # Insert words
    t.insert("car")
    t.insert("card")
    t.insert("cart")
    t.insert("cat")

    # Search existing
    assert t.search("car") is True
    assert t.search("card") is True
    assert t.search("cart") is True
    assert t.search("cat") is True

    # Search non-existing
    assert t.search("ca") is False
    assert t.search("cars") is False
    assert t.search("dog") is False


def test_starts_with():
    t = Trie()
    t.insert("apple")
    t.insert("app")
    t.insert("apply")

    assert t.starts_with("ap") is True
    assert t.starts_with("app") is True
    assert t.starts_with("apple") is True
    assert t.starts_with("banana") is False


def test_delete():
    t = Trie()
    t.insert("bat")
    t.insert("batch")
    t.insert("bath")

    # Delete leaf word
    assert t.delete("bat") is True
    assert t.search("bat") is False
    assert t.search("batch") is True
    assert t.search("bath") is True

    # Delete internal branch word
    assert t.delete("batch") is True
    assert t.search("batch") is False
    assert t.search("bath") is True

    # Delete last word in the subtree
    assert t.delete("bath") is True
    assert t.search("bath") is False

    # Delete non-existing word
    assert t.delete("batman") is False


def test_words_with_prefix():
    t = Trie()
    words = ["dog", "door", "doom", "doll", "cat"]
    for w in words:
        t.insert(w)

    result = set(t.words_with_prefix("do"))
    expected = {"dog", "door", "doom", "doll"}
    assert result == expected

    assert t.words_with_prefix("c") == ["cat"]
    assert t.words_with_prefix("z") == []


def test_iter_all_words():
    t = Trie()
    words = ["apple", "banana", "orange", "grape"]
    for w in words:
        t.insert(w)

    result = set(iter(t))
    assert result == set(words)
