# ============================================================
#  Code Generator  (Assembly-like target code from TAC)
# ============================================================


class CodeGenerator:
    def __init__(self, tac_instructions):
        self.tac   = tac_instructions
        self.code  = []
        self._data_section = []   # strings / arrays declared
        self._string_map   = {}
        self._str_count    = 0

    def generate(self):
        self.code.append("; ====== Generated Assembly-like Target Code ======")
        self.code.append("")
        self.code.append("SECTION .data")
        # placeholder — filled after scan
        data_placeholder_idx = len(self.code)
        self.code.append("")
        self.code.append("SECTION .text")
        self.code.append("    GLOBAL main")
        self.code.append("")

        for instr in self.tac:
            self._emit_instr(instr)

        # Insert data declarations
        data_lines = self._data_section[:]
        if data_lines:
            for i, dl in enumerate(data_lines):
                self.code.insert(data_placeholder_idx + i, f"    {dl}")

        return '\n'.join(self.code)

    def _emit(self, line):
        self.code.append(line)

    def _str_label(self, s):
        if s not in self._string_map:
            self._str_count += 1
            lbl = f"str_{self._str_count}"
            self._string_map[s] = lbl
            escaped = s.replace('\\', '\\\\').replace('"', '\\"') \
                       .replace('\n', '\\n').replace('\t', '\\t')
            self._data_section.append(f'{lbl}  db  "{escaped}", 0')
        return self._string_map[s]

    def _emit_instr(self, instr):
        op = instr.op

        if op == 'LABEL':
            self._emit(f"\n{instr.result}:")
            return

        if op == 'GOTO':
            self._emit(f"    JMP {instr.result}")
            return

        if op == 'IFFALSE':
            self._emit(f"    MOV AX, {instr.arg1}")
            self._emit(f"    CMP AX, 0")
            self._emit(f"    JE  {instr.result}")
            return

        if op == 'IF':
            self._emit(f"    MOV AX, {instr.arg1}")
            self._emit(f"    CMP AX, 0")
            self._emit(f"    JNE {instr.result}")
            return

        if op == '=':
            self._emit(f"    MOV AX, {instr.arg1}")
            self._emit(f"    MOV {instr.result}, AX")
            return

        if op in ('+', '-', '*', '/'):
            self._emit(f"    MOV AX, {instr.arg1}")
            if op == '+':
                self._emit(f"    ADD AX, {instr.arg2}")
            elif op == '-':
                self._emit(f"    SUB AX, {instr.arg2}")
            elif op == '*':
                self._emit(f"    IMUL AX, {instr.arg2}")
            elif op == '/':
                self._emit(f"    MOV BX, {instr.arg2}")
                self._emit(f"    CWD")
                self._emit(f"    IDIV BX")
            self._emit(f"    MOV {instr.result}, AX")
            return

        if op in ('<', '>', '=', '<>', '<=', '>='):
            jmp_map = {'<':'JL', '>':'JG', '=':'JE',
                       '<>':'JNE', '<=':'JLE', '>=':'JGE'}
            true_lbl = f"_cmp_true_{len(self.code)}"
            end_lbl  = f"_cmp_end_{len(self.code)}"
            self._emit(f"    MOV AX, {instr.arg1}")
            self._emit(f"    CMP AX, {instr.arg2}")
            self._emit(f"    {jmp_map[op]} {true_lbl}")
            self._emit(f"    MOV {instr.result}, 0")
            self._emit(f"    JMP {end_lbl}")
            self._emit(f"{true_lbl}:")
            self._emit(f"    MOV {instr.result}, 1")
            self._emit(f"{end_lbl}:")
            return

        if op == 'and':
            self._emit(f"    MOV AX, {instr.arg1}")
            self._emit(f"    AND AX, {instr.arg2}")
            self._emit(f"    MOV {instr.result}, AX")
            return

        if op == 'or':
            self._emit(f"    MOV AX, {instr.arg1}")
            self._emit(f"    OR  AX, {instr.arg2}")
            self._emit(f"    MOV {instr.result}, AX")
            return

        if op == 'not':
            self._emit(f"    MOV AX, {instr.arg1}")
            self._emit(f"    XOR AX, 1")
            self._emit(f"    MOV {instr.result}, AX")
            return

        if op == '-' and instr.arg2 is None:   # unary minus
            self._emit(f"    MOV AX, {instr.arg1}")
            self._emit(f"    NEG AX")
            self._emit(f"    MOV {instr.result}, AX")
            return

        if op == 'READ':
            self._emit(f"    ; read integer -> {instr.result}")
            self._emit(f"    CALL read_int")
            self._emit(f"    MOV {instr.result}, AX")
            return

        if op == 'WRITE':
            val = instr.arg1
            if val.startswith("'") or val.startswith('"'):
                # string literal
                lbl = self._str_label(val.strip("'\""))
                self._emit(f"    MOV AX, OFFSET {lbl}")
                self._emit(f"    CALL write_str")
            else:
                self._emit(f"    MOV AX, {val}")
                self._emit(f"    CALL write_int")
            return

        if op == 'PARAM':
            self._emit(f"    PUSH {instr.arg1}")
            return

        if op == 'CALL':
            self._emit(f"    CALL {instr.arg1}")
            self._emit(f"    ADD SP, {int(instr.arg2) * 2}")
            self._emit(f"    MOV {instr.result}, AX")
            return

        if op == 'PROC_CALL':
            self._emit(f"    CALL {instr.arg1}")
            self._emit(f"    ADD SP, {int(instr.arg2) * 2}")
            return

        if op == 'RETURN':
            val = instr.arg1
            if val:
                self._emit(f"    MOV AX, {val}")
            self._emit(f"    RET")
            return

        if op == 'ARRAY_STORE':
            self._emit(f"    MOV AX, {instr.arg2}")
            self._emit(f"    MOV BX, 2")
            self._emit(f"    IMUL BX")
            self._emit(f"    MOV BX, AX")
            self._emit(f"    MOV AX, {instr.arg1}")
            self._emit(f"    MOV {instr.result}[BX], AX")
            return

        if op == 'ARRAY_LOAD':
            self._emit(f"    MOV AX, {instr.arg2}")
            self._emit(f"    MOV BX, 2")
            self._emit(f"    IMUL BX")
            self._emit(f"    MOV BX, AX")
            self._emit(f"    MOV AX, {instr.arg1}[BX]")
            self._emit(f"    MOV {instr.result}, AX")
            return

        # fallback
        self._emit(f"    ; [unhandled] {instr}")
