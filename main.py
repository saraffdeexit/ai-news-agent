"""
main.py — orchestrates the weekly AI news digest.

Run locally with the required env vars set, or via the GitHub Actions
workflow in .github/workflows/weekly.yml
"""

from fetch_news import fetch_articles
from summarize import summarize_articles
from send_email import send_digest


def main():
    print("Fetching articles...")
    articles = fetch_articles()
    print(f"Found {len(articles)} articles")

    print("Summarizing with Claude...")
    digest = summarize_articles(articles)

    print("Sending email...")
    send_digest(digest)

    print("Done.")


if __name__ == "__main__":
    main()
