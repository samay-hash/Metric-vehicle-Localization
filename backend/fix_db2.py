import sys
import os
sys.path.insert(0, os.path.dirname(__file__))
from database import init_db
init_db()
print("Tables initialized!")
