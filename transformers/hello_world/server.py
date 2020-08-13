#!/usr/bin/env python3

from flask import Flask
app = Flask(__name__)

@app.route('/<path:text>',methods=['GET','PUT'])
def hello_world(text):
    return 'Hello World!'

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0',port=80)

