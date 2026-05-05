import random
from app import create_app, db
from app.models import Candidate

app = create_app()
with app.app_context():
    candidates = Candidate.query.all()
    for c in candidates:
        c.post_utme_present = True
        c.post_utme_score = random.randint(40, 95)
    db.session.commit()
    print("Scores updated!")
