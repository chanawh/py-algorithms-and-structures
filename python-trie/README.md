# Python Trie

A lightweight and readable implementation of a trie (prefix tree) in pure Python.  
This project provides the core trie operations: inserting words, searching, prefix checks, deleting entries, retrieving all words under a prefix, and iterating through the entire word set.

The code is simple, dependency-free, and suitable for learning, embedding into larger projects, or extending into more advanced data-structure libraries.

---

## Features

- **insert(word)**  
  Add a word to the trie.

- **search(word)**  
  Determine whether a word exists.

- **starts_with(prefix)**  
  Check whether any stored word begins with the given prefix.

- **delete(word)**  
  Remove a word and automatically prune unused nodes.

- **words_with_prefix(prefix)**  
  Return all words that share the given prefix.

- **Iteration**  
  Iterate through every word stored in the trie using Python’s iterator protocol.

---

## Project Structure

```

project/
│
├── trie.py        # Trie implementation with full docstrings
├── test_trie.py   # Test suite for all public methods
└── README.md      # Project documentation

```

---

## Usage Example

```python
from trie import Trie

t = Trie()
t.insert("apple")
t.insert("app")
t.insert("apply")

print(t.search("apple"))         # True
print(t.starts_with("ap"))       # True
print(t.words_with_prefix("ap")) # ['apple', 'app', 'apply']

t.delete("app")
print(t.search("app"))           # False

for word in t:
    print(word)                  # Iterates through stored words
```

---

## Running Tests

This project includes a test suite that validates all operations.

Install pytest if needed:

```bash
pip install pytest
```

Run the full test suite:

```bash
pytest test_trie.py
```

---

## Requirements

- Python **3.8+**
- No external dependencies

---

## Contributing

Contributions are welcome.
Possible areas for enhancement include:

- Storing values at nodes (string → value mapping)
- Longest prefix match utilities
- Compressed trie nodes
- Performance benchmarks

To contribute:

1. Fork the repository
2. Create a feature branch
3. Submit a pull request

---

## License

This project is released under the MIT License.
You may freely use, modify, and distribute it.

---

## About

This repository is intentionally minimal, focusing on correctness, clarity, and accessibility.
It serves as a simple standalone trie implementation or a foundation for further development.
