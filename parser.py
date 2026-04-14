# ============================================================
#  Parser  (Recursive-Descent)
# ============================================================

from lexer import (Token, TT_ID, TT_INTEGER, TT_STRING, TT_RESERVED,
                   TT_DELIMITER, TT_ASSIGNOP, TT_RELOP, TT_ADDOP,
                   TT_MULOP, TT_EOF)


class ParseError(Exception):
    def __init__(self, message, line):
        super().__init__(message)
        self.line = line


# ── AST node classes ──────────────────────────────────────────

class ProgramNode:
    def __init__(self, name, var_decls, subprograms, compound):
        self.name = name
        self.var_decls = var_decls          # list of VarDeclNode
        self.subprograms = subprograms      # list of FunctionNode / ProcedureNode
        self.compound = compound            # CompoundNode

class VarDeclNode:
    def __init__(self, names, vtype):
        self.names = names      # list of str
        self.vtype = vtype      # 'integer' | ArrayTypeNode

class ArrayTypeNode:
    def __init__(self, size):
        self.size = size        # int

class CompoundNode:
    def __init__(self, statements):
        self.statements = statements

class AssignNode:
    def __init__(self, var, expr, line):
        self.var = var; self.expr = expr; self.line = line

class IfNode:
    def __init__(self, cond, then_s, else_s, line):
        self.cond = cond; self.then_s = then_s; self.else_s = else_s; self.line = line

class WhileNode:
    def __init__(self, cond, body, line):
        self.cond = cond; self.body = body; self.line = line

class ReadNode:
    def __init__(self, vars_, line):
        self.vars_ = vars_; self.line = line

class WriteNode:
    def __init__(self, items, line):
        self.items = items; self.line = line

class ProcCallNode:
    def __init__(self, name, args, line):
        self.name = name; self.args = args; self.line = line

class BinOpNode:
    def __init__(self, op, left, right, line):
        self.op = op; self.left = left; self.right = right; self.line = line

class UnOpNode:
    def __init__(self, op, operand, line):
        self.op = op; self.operand = operand; self.line = line

class VarNode:
    def __init__(self, name, index, line):
        self.name = name; self.index = index; self.line = line   # index may be None

class IntNode:
    def __init__(self, value, line):
        self.value = value; self.line = line

class StrNode:
    def __init__(self, value, line):
        self.value = value; self.line = line

class FunctionNode:
    def __init__(self, name, params, ret_type, var_decls, compound, line):
        self.name = name; self.params = params; self.ret_type = ret_type
        self.var_decls = var_decls; self.compound = compound; self.line = line

class ProcedureNode:
    def __init__(self, name, params, var_decls, compound, line):
        self.name = name; self.params = params
        self.var_decls = var_decls; self.compound = compound; self.line = line


# ── Parser ────────────────────────────────────────────────────

class Parser:
    def __init__(self, tokens):
        self.tokens  = tokens
        self.pos     = 0
        self.errors  = []

    # ── helpers ──

    def _cur(self):
        return self.tokens[self.pos]

    def _peek(self, offset=1):
        idx = self.pos + offset
        return self.tokens[idx] if idx < len(self.tokens) else self.tokens[-1]

    def _advance(self):
        tok = self.tokens[self.pos]
        if self.pos < len(self.tokens) - 1:
            self.pos += 1
        return tok

    def _expect(self, ttype, value=None):
        tok = self._cur()
        if tok.ttype != ttype or (value and tok.value != value):
            expected = value if value else ttype
            err = ParseError(
                f"Syntax Error: Expected '{expected}' but got '{tok.value}'",
                tok.line)
            self.errors.append(err)
            return tok          # return current so caller can continue
        return self._advance()

    def _match(self, ttype, value=None):
        tok = self._cur()
        if tok.ttype == ttype and (value is None or tok.value == value):
            return self._advance()
        return None

    # ── grammar ──

    def parse(self):
        node = self._parse_program()
        self._expect(TT_EOF)
        return node, self.errors

    # program -> 'program' id ';' var_declarations subprogram_declarations compound_statement '.'
    def _parse_program(self):
        self._expect(TT_RESERVED, 'program')
        name_tok = self._expect(TT_ID)
        self._expect(TT_DELIMITER, ';')
        var_decls     = self._parse_var_declarations()
        subprograms   = self._parse_subprogram_declarations()
        compound      = self._parse_compound_statement()
        self._match(TT_DELIMITER, '.')
        return ProgramNode(name_tok.value, var_decls, subprograms, compound)

    # var_declarations -> 'var' var_decl_list | ε
    def _parse_var_declarations(self):
        decls = []
        if self._cur().ttype == TT_RESERVED and self._cur().value == 'var':
            self._advance()
            while self._cur().ttype == TT_ID:
                decls.append(self._parse_var_decl())
        return decls

    # var_decl -> identifier_list ':' type ';'
    def _parse_var_decl(self):
        names = [self._expect(TT_ID).value]
        while self._match(TT_DELIMITER, ','):
            names.append(self._expect(TT_ID).value)
        self._expect(TT_DELIMITER, ':')
        vtype = self._parse_type()
        self._expect(TT_DELIMITER, ';')
        return VarDeclNode(names, vtype)

    # type -> standard_type | 'array' '[' num ']' 'of' standard_type
    def _parse_type(self):
        if self._cur().ttype == TT_RESERVED and self._cur().value == 'array':
            self._advance()
            self._expect(TT_DELIMITER, '[')
            size_tok = self._expect(TT_INTEGER)
            self._expect(TT_DELIMITER, ']')
            self._expect(TT_RESERVED, 'of')
            self._parse_standard_type()
            return ArrayTypeNode(size_tok.value)
        return self._parse_standard_type()

    def _parse_standard_type(self):
        tok = self._expect(TT_RESERVED, 'integer')
        return tok.value

    # subprogram_declarations -> (subprogram_declaration)*
    def _parse_subprogram_declarations(self):
        subs = []
        while self._cur().ttype == TT_RESERVED and \
              self._cur().value in ('function', 'procedure'):
            subs.append(self._parse_subprogram())
        return subs

    def _parse_subprogram(self):
        line = self._cur().line
        kind = self._advance().value          # 'function' or 'procedure'
        name = self._expect(TT_ID).value
        params = self._parse_arguments()
        ret_type = None
        if kind == 'function':
            self._expect(TT_DELIMITER, ':')
            ret_type = self._parse_standard_type()
        self._expect(TT_DELIMITER, ';')
        var_decls   = self._parse_var_declarations()
        compound    = self._parse_compound_statement()
        self._expect(TT_DELIMITER, ';')
        if kind == 'function':
            return FunctionNode(name, params, ret_type, var_decls, compound, line)
        return ProcedureNode(name, params, var_decls, compound, line)

    # arguments -> '(' parameter_list ')' | '(' ')'
    def _parse_arguments(self):
        params = []
        if not self._match(TT_DELIMITER, '('):
            return params
        if self._cur().ttype == TT_ID:
            params.append(self._parse_var_decl_inline())
            while self._match(TT_DELIMITER, ';'):
                params.append(self._parse_var_decl_inline())
        self._expect(TT_DELIMITER, ')')
        return params

    def _parse_var_decl_inline(self):
        names = [self._expect(TT_ID).value]
        while self._match(TT_DELIMITER, ','):
            names.append(self._expect(TT_ID).value)
        self._expect(TT_DELIMITER, ':')
        vtype = self._parse_type()
        return VarDeclNode(names, vtype)

    # compound_statement -> 'begin' statement_list 'end'
    def _parse_compound_statement(self):
        self._expect(TT_RESERVED, 'begin')
        stmts = self._parse_statement_list()
        self._expect(TT_RESERVED, 'end')
        return CompoundNode(stmts)

    def _parse_statement_list(self):
        stmts = [self._parse_statement()]
        while self._match(TT_DELIMITER, ';'):
            # 'end' terminates the block
            if self._cur().ttype == TT_RESERVED and self._cur().value == 'end':
                break
            stmts.append(self._parse_statement())
        return stmts

    def _parse_statement(self):
        tok = self._cur()

        # compound
        if tok.ttype == TT_RESERVED and tok.value == 'begin':
            return self._parse_compound_statement()

        # if
        if tok.ttype == TT_RESERVED and tok.value == 'if':
            return self._parse_if()

        # while
        if tok.ttype == TT_RESERVED and tok.value == 'while':
            return self._parse_while()

        # read
        if tok.ttype == TT_RESERVED and tok.value == 'read':
            return self._parse_read()

        # write
        if tok.ttype == TT_RESERVED and tok.value == 'write':
            return self._parse_write()

        # assignment or procedure call
        if tok.ttype == TT_ID:
            return self._parse_assign_or_call()

        # empty statement
        return None

    def _parse_if(self):
        line = self._cur().line
        self._advance()          # consume 'if'
        cond = self._parse_expression()
        self._expect(TT_RESERVED, 'then')
        then_s = self._parse_statement()
        else_s = None
        if self._cur().ttype == TT_RESERVED and self._cur().value == 'else':
            self._advance()
            else_s = self._parse_statement()
        return IfNode(cond, then_s, else_s, line)

    def _parse_while(self):
        line = self._cur().line
        self._advance()
        cond = self._parse_expression()
        self._expect(TT_RESERVED, 'do')
        body = self._parse_statement()
        return WhileNode(cond, body, line)

    def _parse_read(self):
        line = self._cur().line
        self._advance()
        self._expect(TT_DELIMITER, '(')
        vars_ = [self._parse_variable()]
        while self._match(TT_DELIMITER, ','):
            vars_.append(self._parse_variable())
        self._expect(TT_DELIMITER, ')')
        return ReadNode(vars_, line)

    def _parse_write(self):
        line = self._cur().line
        self._advance()
        self._expect(TT_DELIMITER, '(')
        items = [self._parse_output_item()]
        while self._match(TT_DELIMITER, ','):
            items.append(self._parse_output_item())
        self._expect(TT_DELIMITER, ')')
        return WriteNode(items, line)

    def _parse_output_item(self):
        if self._cur().ttype == TT_STRING:
            tok = self._advance()
            return StrNode(tok.value, tok.line)
        return self._parse_expression()

    def _parse_assign_or_call(self):
        name_tok = self._advance()
        line = name_tok.line

        # array index or assignment?
        index = None
        if self._match(TT_DELIMITER, '['):
            index = self._parse_expression()
            self._expect(TT_DELIMITER, ']')

        if self._cur().ttype == TT_ASSIGNOP:
            self._advance()
            expr = self._parse_expression()
            return AssignNode(VarNode(name_tok.value, index, line), expr, line)

        # procedure call
        args = []
        if self._match(TT_DELIMITER, '('):
            if self._cur().ttype != TT_DELIMITER or self._cur().value != ')':
                args.append(self._parse_expression())
                while self._match(TT_DELIMITER, ','):
                    args.append(self._parse_expression())
            self._expect(TT_DELIMITER, ')')
        return ProcCallNode(name_tok.value, args, line)

    def _parse_variable(self):
        tok = self._expect(TT_ID)
        index = None
        if self._match(TT_DELIMITER, '['):
            index = self._parse_expression()
            self._expect(TT_DELIMITER, ']')
        return VarNode(tok.value, index, tok.line)

    # expression -> simple_expression (relop simple_expression)?
    def _parse_expression(self):
        left = self._parse_simple_expression()
        if self._cur().ttype == TT_RELOP:
            op_tok = self._advance()
            right = self._parse_simple_expression()
            return BinOpNode(op_tok.value, left, right, op_tok.line)
        return left

    # simple_expression -> term (addop term)*
    def _parse_simple_expression(self):
        # optional sign
        sign = None
        if self._cur().ttype == TT_ADDOP:
            sign = self._advance().value
        left = self._parse_term()
        if sign == '-':
            left = UnOpNode('-', left, left.line if hasattr(left,'line') else 0)
        while self._cur().ttype == TT_ADDOP or \
              (self._cur().ttype == TT_RESERVED and self._cur().value in ('or',)):
            op_tok = self._advance()
            right = self._parse_term()
            left = BinOpNode(op_tok.value, left, right, op_tok.line)
        return left

    # term -> factor (mulop factor)*
    def _parse_term(self):
        left = self._parse_factor()
        while self._cur().ttype == TT_MULOP or \
              (self._cur().ttype == TT_RESERVED and self._cur().value in ('and',)):
            op_tok = self._advance()
            right = self._parse_factor()
            left = BinOpNode(op_tok.value, left, right, op_tok.line)
        return left

    # factor -> id | id '[' expr ']' | id '(' args ')' | num | '(' expr ')' | 'not' factor
    def _parse_factor(self):
        tok = self._cur()

        if tok.ttype == TT_RESERVED and tok.value == 'not':
            self._advance()
            operand = self._parse_factor()
            return UnOpNode('not', operand, tok.line)

        if tok.ttype == TT_INTEGER:
            self._advance()
            return IntNode(tok.value, tok.line)

        if tok.ttype == TT_STRING:
            self._advance()
            return StrNode(tok.value, tok.line)

        if tok.ttype == TT_DELIMITER and tok.value == '(':
            self._advance()
            expr = self._parse_expression()
            self._expect(TT_DELIMITER, ')')
            return expr

        if tok.ttype == TT_ID:
            self._advance()
            # array index
            if self._match(TT_DELIMITER, '['):
                index = self._parse_expression()
                self._expect(TT_DELIMITER, ']')
                return VarNode(tok.value, index, tok.line)
            # function call
            if self._match(TT_DELIMITER, '('):
                args = []
                if not (self._cur().ttype == TT_DELIMITER and self._cur().value == ')'):
                    args.append(self._parse_expression())
                    while self._match(TT_DELIMITER, ','):
                        args.append(self._parse_expression())
                self._expect(TT_DELIMITER, ')')
                return ProcCallNode(tok.value, args, tok.line)
            return VarNode(tok.value, None, tok.line)

        # error recovery
        err = ParseError(
            f"Syntax Error: Unexpected token '{tok.value}' in expression", tok.line)
        self.errors.append(err)
        self._advance()
        return IntNode(0, tok.line)
