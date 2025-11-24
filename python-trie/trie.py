class TrieNode:
    """
    A single node in the trie.

    Attributes:
        children (dict[str, TrieNode]):
            Mapping from a character to the next TrieNode.
        is_end (bool):
            True if this node marks the end of a valid word.
    """
    __slots__ = ("children", "is_end")

    def __init__(self):
        self.children = {}
        self.is_end = False


class Trie:
    """
    A simple trie (prefix tree) supporting insertion, search,
    prefix checks, deletion, prefix-based retrieval, and iteration
    over all stored words.
    """

    def __init__(self):
        """Initialize an empty trie."""
        self.root = TrieNode()

    # -------------------------------------------------------------
    # Core Operations
    # -------------------------------------------------------------

    def insert(self, word: str) -> None:
        """
        Insert a word into the trie.

        Args:
            word (str): The word to insert.

        Returns:
            None
        """
        node = self.root
        for ch in word:
            if ch not in node.children:
                node.children[ch] = TrieNode()
            node = node.children[ch]
        node.is_end = True

    def search(self, word: str) -> bool:
        """
        Determine whether a word exists in the trie.

        Args:
            word (str): The word to search for.

        Returns:
            bool: True if the word exists, False otherwise.
        """
        node = self.root
        for ch in word:
            if ch not in node.children:
                return False
            node = node.children[ch]
        return node.is_end

    def starts_with(self, prefix: str) -> bool:
        """
        Check if any word in the trie begins with the given prefix.

        Args:
            prefix (str): The prefix to test.

        Returns:
            bool: True if at least one word begins with the prefix.
        """
        node = self.root
        for ch in prefix:
            if ch not in node.children:
                return False
            node = node.children[ch]
        return True

    # -------------------------------------------------------------
    # Additional Functionalities
    # -------------------------------------------------------------

    def delete(self, word: str) -> bool:
        """
        Delete a word from the trie.

        Args:
            word (str): The word to delete.

        Returns:
            bool: True if the word was deleted,
                  False if the word was not present.
        """

        def _delete(node, word, idx):
            if idx == len(word):
                if not node.is_end:
                    return False, False
                node.is_end = False
                return True, len(node.children) == 0

            ch = word[idx]
            if ch not in node.children:
                return False, False

            deleted, should_prune = _delete(node.children[ch], word, idx + 1)

            if not deleted:
                return False, False

            if should_prune:
                del node.children[ch]

            prune_self = len(node.children) == 0 and not node.is_end
            return True, prune_self

        deleted, _ = _delete(self.root, word, 0)
        return deleted

    def words_with_prefix(self, prefix: str) -> list[str]:
        """
        Retrieve all words in the trie that share a given prefix.

        Args:
            prefix (str): The prefix to match.

        Returns:
            list[str]: All words that begin with the prefix.
        """

        def _collect(node, path, out):
            if node.is_end:
                out.append("".join(path))
            for ch, nxt in node.children.items():
                path.append(ch)
                _collect(nxt, path, out)
                path.pop()

        node = self.root
        for ch in prefix:
            if ch not in node.children:
                return []
            node = node.children[ch]

        result = []
        _collect(node, list(prefix), result)
        return result

    def __iter__(self):
        """
        Iterate over all words stored in the trie.

        Yields:
            str: Next word in the trie.
        """

        def _walk(node, path):
            if node.is_end:
                yield "".join(path)
            for ch, nxt in node.children.items():
                path.append(ch)
                yield from _walk(nxt, path)
                path.pop()

        yield from _walk(self.root, [])
