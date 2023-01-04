from flask import Flask,render_template, request
import main
app = Flask(__name__)
NameError
@app.route('/')
def index():
    return render_template("web.html")
@app.route('/',methods = ['POST'])
def getvalue():
    data = request.form['paragraph']
    if(data == "Type here"):
        f = request.files['myfile']
        data = f.read()
        f.close() 
    return render_template('output.html',x=data)
if __name__ == '__main__':
    app.debug =True
    app.run()