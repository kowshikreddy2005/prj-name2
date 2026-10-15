
import os
import uuid
import mysql.connector
from flask import Flask, render_template, request, redirect, url_for
import pandas as pd
import joblib
from flask import Flask, render_template, request
import joblib
import numpy as np   # <-- Add this line


# -------------------------
# Flask App
# -------------------------
app = Flask(__name__)
app.secret_key = 'admin'

# -------------------------
# MySQL Connection
# -------------------------
mydb = mysql.connector.connect(
    host="localhost",
    user="root",
    password="root",
    port="3306",
    database='Satlite'
)
mycursor = mydb.cursor()

# -------------------------
# Database Functions
# -------------------------
def executionquery(query, values):
    mycursor.execute(query, values)
    mydb.commit()

def retrivequery1(query, values):
    mycursor.execute(query, values)
    return mycursor.fetchall()

def retrivequery2(query):
    mycursor.execute(query)
    return mycursor.fetchall()

# -------------------------
# Routes
# -------------------------
@app.route('/')
def index():
    return render_template('index.html')


@app.route('/index2')
def index2():
    return render_template("index2.html")

@app.route('/register', methods=["GET", "POST"])
def register():
    message = ''
    if request.method == "POST":
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        c_password = request.form['c_password']

        if password != c_password:
            message = "Confirm password does not match!"
            return render_template('register.html', message=message)

        # Check if email exists
        query = "SELECT UPPER(email) FROM users"
        email_data = retrivequery2(query)
        email_list = [i[0] for i in email_data]

        if email.upper() in email_list:
            message = "This email ID already exists!"
            return render_template('register.html', message=message)

        # Insert new user (store name too if your DB has 'name' column)
        query = "INSERT INTO users (name, email, password) VALUES (%s, %s, %s)"
        executionquery(query, (name, email, password))

        message = "Successfully Registered!"
        return render_template('login.html', message=message)

    return render_template('register.html', message=message)

@app.route('/login', methods=["GET", "POST"])
def login():
    message = ''
    if request.method == "POST":
        email = request.form['email']
        password = request.form['password']

        query = "SELECT UPPER(email) FROM users"
        email_data = retrivequery2(query)
        email_list = [i[0] for i in email_data]

        if email.upper() not in email_list:
            message = "This email ID does not exist!"
            return render_template('login.html', message=message)

        query = "SELECT UPPER(password) FROM users WHERE email = %s"
        password_data = retrivequery1(query, (email,))
        if password.upper() != password_data[0][0]:
            message = "Invalid Password!!"
            return render_template('login.html', message=message)

        # Successful login
        global user_email
        user_email = email
        return redirect('/home')

    return render_template('login.html', message=message)

@app.route('/home')
def home():
    return render_template('uhome.html')

@app.route('/about')
def about():
    return render_template('about.html')


@app.route('/upload', methods=['GET', 'POST'])
def upload():
    if request.method == 'POST':
        # Check if a file is uploaded
        if 'file' not in request.files:
            return render_template('upload.html', msg="No file part")
        
        file = request.files['file']
        if file.filename == '':
            return render_template('upload.html', msg="No selected file")
        
        # If file is present, read the CSV
        try:
            df = pd.read_csv(file)
            dataset = df.head(500)  # Show only the first 100 rows
            columns = dataset.columns.values
            rows = dataset.values.tolist()
            return render_template('upload.html', columns=columns, rows=rows, msg="Dataset Uploaded Successfully")
        except Exception as e:
            return render_template('upload.html', msg=f"Error: {str(e)}")

    # Render the page with the file upload form
    return render_template('upload.html')


@app.route('/model', methods=['POST', 'GET'])
def model():
    if request.method == "POST":
        # Get selected algorithm
        algo = request.form['algo']

        # Store performance metrics
        metrics = {
            'random_forest': {"name": "Random Forest", "mse": 11.1807, "r2": 0.9985},
            'extra_trees': {"name": "Extra Trees Regressor", "mse": 10.9384, "r2": 0.9985},
            'lightgbm': {"name": "LightGBM Regressor", "mse": 10.8263, "r2": 0.9985},
            'lstm': {"name": "LSTM Regressor", "mse": 7436.0781, "r2": 0.7385},
            'knn': {"name": "K-Nearest Neighbors Regressor", "mse": 0.0101, "r2": 0.9944},
            'fnn': {"name": "Feedforward Neural Network (FNN)", "mse": 17.8211, "r2": 0.9976},
            'mlp': {"name": "Multi-Layer Perceptron (MLP)", "mse": 12.0854, "r2": 0.9984}
        }

        if algo in metrics:
            model_info = metrics[algo]
            msg = f"Model: {model_info['name']}"
            msg1 = f"Mean Squared Error (MSE): {model_info['mse']:.4f}"
            msg2 = f"R² Score: {model_info['r2']:.4f}"
            return render_template('model.html', msg=msg, msg1=msg1, msg2=msg2)
        else:
            msg = "⚠️ Please select a valid algorithm."
            return render_template('model.html', msg=msg)

    return render_template('model.html')



# -------------------------
@app.route('/prediction', methods=['GET', 'POST'])
def prediction():
    if request.method == 'POST':
        try:
            # Collect input values from form
            features = [
                float(request.form['cycle']),
                float(request.form['sensor_1']),
                float(request.form['sensor_2']),
                float(request.form['sensor_3']),
                float(request.form['sensor_4']),
                float(request.form['sensor_7']),
                float(request.form['sensor_8']),
                float(request.form['sensor_12']),
                float(request.form['sensor_14']),
                float(request.form['sensor_15']),
                float(request.form['sensor_18']),
                float(request.form['sensor_19'])
            ]

            # Load model
            model = joblib.load("ET.joblib")

            # Convert input into numpy array
            input_array = np.array(features).reshape(1, -1)

            # Predict RUL
            y_pred = model.predict(input_array)[0]

            # Classification logic
            def classify_rul(rul):
                if rul <= 30:
                    return "CRITICAL"
                elif rul <= 100:
                    return "WARNING"
                else:
                    return "NORMAL"

            status = classify_rul(y_pred)

            # Suggestions map
            suggestion_map = {
                "CRITICAL": "⚠️ Immediate inspection & maintenance required. Ground the engine and run diagnostics.",
                "WARNING": "🔧 Schedule maintenance soon. Increase monitoring and prepare spare parts.",
                "NORMAL": "✅ Engine is healthy. Continue regular monitoring."
            }
            suggestion = suggestion_map[status]

            # Send result to template
            return render_template(
                'prediction.html',
                predicted_beam=f"{y_pred:.2f}",
                probability="-",  # Not applicable here
                description=f"Status: {status} | Suggestion: {suggestion}"
            )

        except Exception as e:
            return render_template('prediction.html', error=f"Error: {str(e)}")

    return render_template('prediction.html')


if __name__=="__main__":
    app.run(debug=True)
