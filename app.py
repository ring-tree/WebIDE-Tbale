from flask import Flask, request, jsonify
from flask_cors import CORS
import jedi

app = Flask(__name__)
CORS(app)

def get_completions(code, line, column):
    try:
        script = jedi.Script(code)
        completions = script.complete(line=line, column=column)
        return [{
            "name": completion.name,
            "description": completion.description
        } for completion in completions]
    except:
        return []

@app.route('/update', methods=['POST'])
def update_code():
    data = request.json
    code = data.get("code", "")
    line = data.get("line", 1)
    column = data.get("column", 1)
    
    print(f"Received code ({len(code)} chars) at line {line}, column {column}:")
    print(code)
    print("-" * 50)
    completions = get_completions(code, line, column - 1)
    print(completions)
    print("-" * 50)

    return jsonify({
        "status": "success",
        "completions": completions
    })

if __name__ == '__main__':
    print("Flask server starting on http://localhost:5000")
    app.run(host='0.0.0.0', port=5000)
