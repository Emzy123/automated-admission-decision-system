import os

from app import create_app, db
from app.models import AdmissionRule, Candidate, Programme, User

app = create_app(os.getenv("FLASK_ENV", "development"))


@app.shell_context_processor
def make_shell_context():
    return {
        "db": db,
        "User": User,
        "Programme": Programme,
        "Candidate": Candidate,
        "AdmissionRule": AdmissionRule,
    }


if __name__ == "__main__":
    app.run()
