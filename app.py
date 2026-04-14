from flask import Flask, request, jsonify, send_from_directory
import sys, os

sys.path.insert(0, os.path.dirname(__file__))

from lexer  import Lexer
from parser import Parser
from icg    import IntermediateCodeGenerator
from codegen import CodeGenerator

app = Flask(__name__, static_folder='static')

@app.route('/')
def index():
    return send_from_directory('static', 'index.html')

@app.route('/compile', methods=['POST'])
def compile_code():
    data = request.get_json()
    source_code = data.get('source', '')

    result = {
        'tokens':  [],
        'ast':     None,
        'tac':     [],
        'asm':     '',
        'listing': [],
        'errors':  [],
        'success': False,
        'phases':  {
            'lexer':  {'done': False, 'error_count': 0},
            'parser': {'done': False, 'error_count': 0},
            'icg':    {'done': False, 'error_count': 0},
            'codegen':{'done': False, 'error_count': 0},
        }
    }

    source_lines = source_code.splitlines()
    all_errors = []

    # Phase 1
    try:
        lexer = Lexer(source_code)
        tokens, lex_errors = lexer.tokenize()
        for e in lex_errors:
            all_errors.append({'line': e.line, 'message': str(e), 'phase': 'Lexer'})
        result['tokens'] = [
            {'type': t.ttype, 'value': str(t.value), 'line': t.line}
            for t in tokens
        ]
        result['phases']['lexer']['done'] = True
        result['phases']['lexer']['error_count'] = len(lex_errors)
    except Exception as ex:
        all_errors.append({'line': 0, 'message': f'Lexer crashed: {ex}', 'phase': 'Lexer'})

    # Phase 2
    try:
        parser = Parser(tokens)
        ast, parse_errors = parser.parse()
        for e in parse_errors:
            all_errors.append({'line': e.line, 'message': str(e), 'phase': 'Parser'})
        result['phases']['parser']['done'] = True
        result['phases']['parser']['error_count'] = len(parse_errors)
    except Exception as ex:
        all_errors.append({'line': 0, 'message': f'Parser crashed: {ex}', 'phase': 'Parser'})
        ast = None

    # Phase 3
    tac_instructions = []
    if not all_errors and ast:
        try:
            icg = IntermediateCodeGenerator()
            tac_instructions, icg_errors = icg.generate(ast)
            for e in icg_errors:
                all_errors.append({'line': e.line, 'message': str(e), 'phase': 'ICG'})
            result['tac'] = [str(i) for i in tac_instructions]
            result['phases']['icg']['done'] = True
            result['phases']['icg']['error_count'] = len(icg_errors)
        except Exception as ex:
            all_errors.append({'line': 0, 'message': f'ICG crashed: {ex}', 'phase': 'ICG'})

    # Phase 4
    if not all_errors and tac_instructions:
        try:
            cg = CodeGenerator(tac_instructions)
            result['asm'] = cg.generate()
            result['phases']['codegen']['done'] = True
            result['phases']['codegen']['error_count'] = 0
        except Exception as ex:
            all_errors.append({'line': 0, 'message': f'CodeGen crashed: {ex}', 'phase': 'CodeGen'})

    # Build listing
    err_by_line = {}
    for e in all_errors:
        err_by_line.setdefault(e['line'], []).append(e)

    listing = []
    for idx, line in enumerate(source_lines, 1):
        listing.append({'lineno': idx, 'text': line, 'errors': err_by_line.get(idx, [])})
    if 0 in err_by_line:
        listing.append({'lineno': 0, 'text': '', 'errors': err_by_line[0]})

    result['listing'] = listing
    result['errors']  = all_errors
    result['success'] = len(all_errors) == 0

    return jsonify(result)

if __name__ == '__main__':
    app.run(debug=True, port=5050)
