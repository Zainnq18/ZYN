# ============================================================
#  Intermediate Code Generator  (Three-Address Code / TAC)
# ============================================================

from parser import (ProgramNode, VarDeclNode, ArrayTypeNode, CompoundNode,
                    AssignNode, IfNode, WhileNode, ReadNode, WriteNode,
                    ProcCallNode, BinOpNode, UnOpNode, VarNode, IntNode,
                    StrNode, FunctionNode, ProcedureNode)


class TACInstruction:
    """Single three-address instruction."""
    def __init__(self, op, arg1=None, arg2=None, result=None):
        self.op     = op
        self.arg1   = arg1
        self.arg2   = arg2
        self.result = result

    def __str__(self):
        if self.op == 'LABEL':
            return f"{self.result}:"
        if self.op == 'GOTO':
            return f"    GOTO {self.result}"
        if self.op == 'IF':
            return f"    IF {self.arg1} GOTO {self.result}"
        if self.op == 'IFFALSE':
            return f"    IFFALSE {self.arg1} GOTO {self.result}"
        if self.op == 'PARAM':
            return f"    PARAM {self.arg1}"
        if self.op == 'CALL':
            return f"    {self.result} = CALL {self.arg1}, {self.arg2}"
        if self.op == 'PROC_CALL':
            return f"    CALL {self.arg1}, {self.arg2}"
        if self.op == 'RETURN':
            return f"    RETURN {self.arg1 or ''}"
        if self.op == 'READ':
            return f"    READ {self.result}"
        if self.op == 'WRITE':
            return f"    WRITE {self.arg1}"
        if self.op == 'ARRAY_STORE':
            return f"    {self.result}[{self.arg2}] = {self.arg1}"
        if self.op == 'ARRAY_LOAD':
            return f"    {self.result} = {self.arg1}[{self.arg2}]"
        if self.op == '=':
            return f"    {self.result} = {self.arg1}"
        # binary / unary
        if self.arg2 is not None:
            return f"    {self.result} = {self.arg1} {self.op} {self.arg2}"
        return f"    {self.result} = {self.op} {self.arg1}"


class ICGError(Exception):
    def __init__(self, message, line):
        super().__init__(message)
        self.line = line


class IntermediateCodeGenerator:
    def __init__(self):
        self.instructions = []
        self.errors       = []
        self._temp_count  = 0
        self._label_count = 0

    # ── helpers ──

    def _new_temp(self):
        self._temp_count += 1
        return f"t{self._temp_count}"

    def _new_label(self):
        self._label_count += 1
        return f"L{self._label_count}"

    def _emit(self, op, arg1=None, arg2=None, result=None):
        instr = TACInstruction(op, arg1, arg2, result)
        self.instructions.append(instr)
        return instr

    # ── entry point ──

    def generate(self, ast):
        self._visit_program(ast)
        return self.instructions, self.errors

    # ── visitors ──

    def _visit_program(self, node):
        self._emit('LABEL', result=f"program_{node.name}")
        for sub in node.subprograms:
            if isinstance(sub, FunctionNode):
                self._visit_function(sub)
            else:
                self._visit_procedure(sub)
        self._emit('LABEL', result='main')
        self._visit_compound(node.compound)
        self._emit('RETURN')

    def _visit_function(self, node):
        self._emit('LABEL', result=f"func_{node.name}")
        self._visit_compound(node.compound)
        self._emit('RETURN', arg1=node.name)

    def _visit_procedure(self, node):
        self._emit('LABEL', result=f"proc_{node.name}")
        self._visit_compound(node.compound)
        self._emit('RETURN')

    def _visit_compound(self, node):
        for stmt in node.statements:
            if stmt is not None:
                self._visit_statement(stmt)

    def _visit_statement(self, node):
        if isinstance(node, AssignNode):
            self._visit_assign(node)
        elif isinstance(node, IfNode):
            self._visit_if(node)
        elif isinstance(node, WhileNode):
            self._visit_while(node)
        elif isinstance(node, ReadNode):
            self._visit_read(node)
        elif isinstance(node, WriteNode):
            self._visit_write(node)
        elif isinstance(node, ProcCallNode):
            self._visit_proc_call(node)
        elif isinstance(node, CompoundNode):
            self._visit_compound(node)

    def _visit_assign(self, node):
        rhs = self._visit_expr(node.expr)
        var = node.var
        if var.index is not None:
            idx = self._visit_expr(var.index)
            self._emit('ARRAY_STORE', arg1=rhs, arg2=idx, result=var.name)
        else:
            self._emit('=', arg1=rhs, result=var.name)

    def _visit_if(self, node):
        cond = self._visit_expr(node.cond)
        else_label = self._new_label()
        end_label  = self._new_label()
        self._emit('IFFALSE', arg1=cond, result=else_label)
        self._visit_statement(node.then_s)
        if node.else_s:
            self._emit('GOTO', result=end_label)
        self._emit('LABEL', result=else_label)
        if node.else_s:
            self._visit_statement(node.else_s)
            self._emit('LABEL', result=end_label)

    def _visit_while(self, node):
        start_label = self._new_label()
        end_label   = self._new_label()
        self._emit('LABEL', result=start_label)
        cond = self._visit_expr(node.cond)
        self._emit('IFFALSE', arg1=cond, result=end_label)
        self._visit_statement(node.body)
        self._emit('GOTO', result=start_label)
        self._emit('LABEL', result=end_label)

    def _visit_read(self, node):
        for v in node.vars_:
            if v.index is not None:
                idx = self._visit_expr(v.index)
                tmp = self._new_temp()
                self._emit('READ', result=tmp)
                self._emit('ARRAY_STORE', arg1=tmp, arg2=idx, result=v.name)
            else:
                self._emit('READ', result=v.name)

    def _visit_write(self, node):
        for item in node.items:
            val = self._visit_expr(item)
            self._emit('WRITE', arg1=val)

    def _visit_proc_call(self, node):
        for arg in node.args:
            val = self._visit_expr(arg)
            self._emit('PARAM', arg1=val)
        self._emit('PROC_CALL', arg1=node.name, arg2=len(node.args))

    def _visit_expr(self, node):
        if isinstance(node, IntNode):
            return str(node.value)

        if isinstance(node, StrNode):
            return repr(node.value)

        if isinstance(node, VarNode):
            if node.index is not None:
                idx = self._visit_expr(node.index)
                tmp = self._new_temp()
                self._emit('ARRAY_LOAD', arg1=node.name, arg2=idx, result=tmp)
                return tmp
            return node.name

        if isinstance(node, UnOpNode):
            operand = self._visit_expr(node.operand)
            tmp = self._new_temp()
            self._emit(node.op, arg1=operand, result=tmp)
            return tmp

        if isinstance(node, BinOpNode):
            left  = self._visit_expr(node.left)
            right = self._visit_expr(node.right)
            tmp   = self._new_temp()
            self._emit(node.op, arg1=left, arg2=right, result=tmp)
            return tmp

        if isinstance(node, ProcCallNode):
            for arg in node.args:
                val = self._visit_expr(arg)
                self._emit('PARAM', arg1=val)
            tmp = self._new_temp()
            self._emit('CALL', arg1=node.name, arg2=len(node.args), result=tmp)
            return tmp

        self.errors.append(ICGError("ICG Error: Unknown AST node", 0))
        return "?"
