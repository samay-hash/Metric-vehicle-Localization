import os
import tokenize
import io
import re

def strip_python_comments(source_code):
    io_obj = io.StringIO(source_code)
    out = ""
    last_lineno = -1
    last_col = 0
    try:
        for tok in tokenize.generate_tokens(io_obj.readline):
            token_type = tok[0]
            token_string = tok[1]
            start_line, start_col = tok[2]
            end_line, end_col = tok[3]
            
            if start_line > last_lineno:
                last_col = 0
            if start_col > last_col:
                out += (" " * (start_col - last_col))
            
            if token_type == tokenize.COMMENT:
                pass
            elif token_type == tokenize.STRING:
                if token_string.startswith('"""') or token_string.startswith("'''"):
                    pass
                else:
                    out += token_string
            else:
                out += token_string
                
            last_lineno = end_line
            last_col = end_col
    except Exception as e:
        return source_code
        
    # Remove empty lines left by comments
    cleaned_lines = [line for line in out.split('\n') if line.strip() != '']
    return '\n'.join(cleaned_lines)

def strip_js_comments(source_code):
    # Regex to remove JS/JSX block and line comments
    # Also handles JSX comments {/* ... */}
    out = re.sub(r'/\*[\s\S]*?\*/|//.*', '', source_code)
    out = re.sub(r'\{/\*[\s\S]*?\*/\}', '', out)
    cleaned_lines = [line for line in out.split('\n') if line.strip() != '']
    return '\n'.join(cleaned_lines)

def process_dir(directory, is_js=False):
    for root, dirs, files in os.walk(directory):
        if 'venv' in root or 'node_modules' in root or '.git' in root:
            continue
        for f in files:
            if not is_js and f.endswith('.py'):
                path = os.path.join(root, f)
                with open(path, 'r') as file:
                    content = file.read()
                cleaned = strip_python_comments(content)
                with open(path, 'w') as file:
                    file.write(cleaned)
                print(f"Stripped {path}")
            elif is_js and f.endswith(('.js', '.jsx', '.css')):
                path = os.path.join(root, f)
                with open(path, 'r') as file:
                    content = file.read()
                cleaned = strip_js_comments(content)
                with open(path, 'w') as file:
                    file.write(cleaned)
                print(f"Stripped {path}")

process_dir('/Users/samaysamrat/bankcctv/backend', is_js=False)
process_dir('/Users/samaysamrat/bankcctv/frontend/src', is_js=True)
