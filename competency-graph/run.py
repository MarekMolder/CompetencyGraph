from app import create_app
import os, sys
sys.path.insert(0, os.path.dirname(__file__))

app = create_app()

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=8000)