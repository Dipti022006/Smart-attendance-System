from app import create_app

app = create_app()

print("Flask App Starting...")

if __name__ == '__main__':
    app.run(debug=True)