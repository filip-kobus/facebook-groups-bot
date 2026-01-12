import csv
import os
from typing import List, Dict

CSV_FILE = "leads.csv"
FIELDNAMES = ["id", "author", "user_id", "content", "date", "group_id", "is_lead", "reasoning"]

def initialize_csv():
    if not os.path.exists(CSV_FILE):
        with open(CSV_FILE, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
            writer.writeheader()

def append_posts_to_csv(posts: List[Dict]):
    with open(CSV_FILE, 'a', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        for post in posts:
            writer.writerow({field: post.get(field, "") for field in FIELDNAMES})
