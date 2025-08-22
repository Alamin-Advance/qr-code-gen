from app.db import Base, engine
from app import models  # ensure models are imported and registered

def init():
    Base.metadata.create_all(bind=engine)

if __name__ == "__main__":
    init()
