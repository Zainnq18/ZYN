# ============================================================
#  Lexical Analyzer (Lexer)
# ============================================================

import re

# Token types
TT_PROGRAM    = 'PROGRAM'
TT_ID         = 'ID'
TT_INTEGER    = 'INTEGER'
TT_STRING     = 'STRING'
TT_RESERVED   = 'RESERVED'
TT_DELIMITER  = 'DELIMITER'
TT_ASSIGNOP   = 'ASSIGNOP'
TT_RELOP      = 'RELOP'
TT_ADDOP      = 'ADDOP'
TT_MULOP      = 'MULOP'
TT_EOF        = 'EOF'
TT_UNKNOWN    = 'UNKNOWN'

RESERVED_WORDS = {
    'and', 'array', 'begin', 'integer', 'do', 'else', 'end',
    'function', 'if', 'of', 'or', 'not', 'procedure', 'program',
    'read', 'then', 'var', 'while', 'write'
}

COMPOUND_SYMBOLS = {':=', '<>', '<=', '>='}
SINGLE_DELIMITERS = set('()[]:.,*-+/<=>;')


class Token:
    def __init__(self, ttype, value, line):
        self.ttype = ttype
        self.value = value
        self.line  = line

    def __repr__(self):
        return f'Token({self.ttype}, {self.value!r}, line={self.line})'


class LexerError(Exception):
    def __init__(self, message, line):
        super().__init__(message)
        self.line = line


class Lexer:
    def __init__(self, source_code):
        self.source_lines = source_code.splitlines()
        self.tokens = []
        self.errors = []

    def tokenize(self):
        for lineno, line in enumerate(self.source_lines, start=1):
            self._tokenize_line(line, lineno)
        self.tokens.append(Token(TT_EOF, 'EOF', len(self.source_lines) + 1))
        return self.tokens, self.errors

    def _tokenize_line(self, line, lineno):
        i = 0
        # Strip comment
        comment_idx = line.find('!')
        if comment_idx != -1:
            line = line[:comment_idx]

        while i < len(line):
            ch = line[i]

            # Skip whitespace
            if ch in ' \t\r':
                i += 1
                continue

            # String literal
            if ch == "'":
                tok, advance, err = self._read_string(line, i, lineno)
                if err:
                    self.errors.append(err)
                else:
                    self.tokens.append(tok)
                i += advance
                continue

            # Number
            if ch.isdigit():
                j = i
                while j < len(line) and line[j].isdigit():
                    j += 1
                self.tokens.append(Token(TT_INTEGER, int(line[i:j]), lineno))
                i = j
                continue

            # Identifier or reserved word
            if ch.isalpha() or ch == '_':
                j = i
                while j < len(line) and (line[j].isalnum() or line[j] == '_'):
                    j += 1
                word = line[i:j]
                # Truncate to 32 chars for distinction
                key = word[:32].lower()
                if key in RESERVED_WORDS:
                    self.tokens.append(Token(TT_RESERVED, key, lineno))
                else:
                    self.tokens.append(Token(TT_ID, word, lineno))
                i = j
                continue

            # Compound symbols
            two = line[i:i+2]
            if two in COMPOUND_SYMBOLS:
                if two == ':=':
                    self.tokens.append(Token(TT_ASSIGNOP, two, lineno))
                elif two in ('<>', '<=', '>='):
                    self.tokens.append(Token(TT_RELOP, two, lineno))
                i += 2
                continue

            # Single-char delimiters / operators
            if ch in SINGLE_DELIMITERS:
                if ch in ('+', '-'):
                    self.tokens.append(Token(TT_ADDOP, ch, lineno))
                elif ch in ('*', '/'):
                    self.tokens.append(Token(TT_MULOP, ch, lineno))
                elif ch in ('<', '>', '='):
                    self.tokens.append(Token(TT_RELOP, ch, lineno))
                else:
                    self.tokens.append(Token(TT_DELIMITER, ch, lineno))
                i += 1
                continue

            # Unknown character
            self.errors.append(LexerError(
                f"Lexical Error: Unknown character '{ch}'", lineno))
            i += 1

    def _read_string(self, line, start, lineno):
        """Read a quoted string, handling escape sequences."""
        i = start + 1  # skip opening quote
        result = []
        while i < len(line):
            ch = line[i]
            if ch == '\\':
                if i + 1 < len(line):
                    nxt = line[i+1]
                    if nxt == 'n':
                        result.append('\n')
                    elif nxt == 't':
                        result.append('\t')
                    else:
                        result.append(nxt)
                    i += 2
                else:
                    result.append('\\')
                    i += 1
            elif ch == "'":
                # closing quote
                tok = Token(TT_STRING, ''.join(result), lineno)
                return tok, (i - start + 1), None
            else:
                result.append(ch)
                i += 1
        err = LexerError("Lexical Error: Unterminated string literal", lineno)
        return None, (i - start), err
