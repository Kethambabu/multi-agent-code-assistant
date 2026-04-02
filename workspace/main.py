from flask import Flask, render_template
import utils
import os
import sys

app = Flask(__name__)

@app.route('/')
def home():
    return render_template('index.html', title='Home')

@app.route('/about')
def about():
    return render_template('about.html', title='About')

@app.route('/contact')
def contact():
    return render_template('contact.html', title='Contact')

if __name__ == '__main__':
    # Check if running in test/runner mode (non-interactive)
    if os.getenv('FLASK_TEST_MODE') or os.getenv('RUNNER_MODE'):
        # Just verify the app loads successfully
        print(f"✅ Flask app loaded successfully with {len(app.url_map._rules)} routes")
        print(f"Routes: {[rule.rule for rule in app.url_map.iter_rules() if rule.endpoint != 'static']}")
        sys.exit(0)
    else:
        # Normal interactive mode
        app.run(debug=True)