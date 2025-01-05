import argparse
import json
import logging
import os
import random
import sys
import time
from datetime import datetime, timedelta
from logging.handlers import RotatingFileHandler

import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from openai import OpenAI


def login_to_openwork(session, username, password, logger):
    """Logs in to the OpenWork website using provided credentials.

    Args:
        session (requests.Session): A requests session object.
        username (str): The OpenWork account username.
        password (str): The OpenWork account password.
        logger (logging.Logger): Logger instance for logging process details.

    Returns:
        requests.Session: The authenticated requests session object.

    Raises:
        RuntimeError: If the login page or the subsequent pages cannot be accessed.
        ValueError: If the required CSRF token is not found.
    """
    logger.info("Attempting to log in to OpenWork")
    login_page_url = "https://www.openwork.jp/login.php"
    login_check_url = "https://www.openwork.jp/login_check"
    my_top_url = "https://www.openwork.jp/my_top"

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.2 Safari/605.1.15"
        ),
    }

    try:
        login_page = session.get(login_page_url, headers=headers)
        login_page.raise_for_status()
    except requests.RequestException:
        logger.exception("Failed to fetch login page")
        raise RuntimeError("Could not access OpenWork login page")

    soup = BeautifulSoup(login_page.text, "html.parser")
    csrf_input = soup.find("input", {"name": "_csrf_token"})

    if not csrf_input or not csrf_input.get("value"):
        logger.error("CSRF token not found in login page")
        raise ValueError("CSRF token not found in login page")

    csrf_token = csrf_input["value"]
    payload = {
        "_username": username,
        "_password": password,
        "_remember_me": "1",
        "_csrf_token": csrf_token,
        "_target_path": "https://www.openwork.jp/",
    }

    try:
        login_response = session.post(login_check_url, data=payload, headers=headers)
        login_response.raise_for_status()

        my_top_response = session.get(my_top_url, headers=headers)
        my_top_response.raise_for_status()
    except requests.RequestException:
        logger.exception("Login request failed")
        raise RuntimeError("Failed to complete login process")

    if "ようこそ" not in my_top_response.text:
        logger.error("Login verification failed")
        raise RuntimeError("Login failed - could not verify logged-in state")

    logger.info("Successfully logged in to OpenWork")
    return session


def get_company_info(session, m_id, logger):
    """Fetches company name and introduction from OpenWork by company ID.

    Args:
        session (requests.Session): The authenticated requests session.
        m_id (str): The company ID used in the OpenWork URL.
        logger (logging.Logger): Logger instance for logging.

    Returns:
        tuple: A tuple (company_name, company_intro), "
        "where either may be None if not found.

    Raises:
        RuntimeError: If the company page cannot be fetched.
    """
    logger.info(f"Fetching company info for ID: {m_id}")
    url = f"https://www.openwork.jp/company_answer.php?m_id={m_id}"
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.2 Safari/605.1.15"
        ),
    }

    try:
        response = session.get(url, headers=headers)
        response.raise_for_status()
    except requests.RequestException:
        logger.exception("Failed to fetch company info")
        raise RuntimeError(f"Could not fetch company info for ID {m_id}")

    soup = BeautifulSoup(response.text, "html.parser")
    name_tag = soup.select_one("#mainTitle > h2 > a")
    intro_tag = soup.select_one(
        "#contentsHeader_text > div > p.mt-20.w-740.madblack.break-all"
    )

    company_name = name_tag.get_text(strip=True) if name_tag else None
    company_intro = intro_tag.get_text(strip=True) if intro_tag else None

    if not company_name:
        logger.warning(f"Company name not found for ID {m_id}")
    if not company_intro:
        logger.warning(f"Company introduction not found for ID {m_id}")

    return company_name, company_intro


def scrape_reviews(session, m_id, logger, max_pages=12):
    """Scrapes reviews from OpenWork for a given company ID "
    "up to a page limit or 2-year cutoff.

    Args:
        session (requests.Session): The authenticated requests session.
        m_id (str): The company ID on OpenWork.
        logger (logging.Logger): Logger instance for logging.
        max_pages (int): The maximum number of pages to scrape.

    Returns:
        list of dict: A list of review dictionaries with keys "date" and "content".
    """
    base_url = "https://www.openwork.jp/company_answer.php"
    all_reviews = []
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.2 Safari/605.1.15"
        ),
        "Referer": f"https://www.openwork.jp/company_answer.php?m_id={m_id}",
    }

    cutoff_date = datetime.now() - timedelta(days=2 * 365)  # 2 years
    page = 1

    while page <= max_pages:
        logger.info(f"Scraping page {page} of maximum {max_pages}")
        params = {"m_id": m_id, "sort_key": 1, "sort_val": -1, "next_page": page}

        try:
            response = session.get(base_url, headers=headers, params=params)
            if response.status_code != 200:
                logger.warning(
                    f"Request for page {page} failed with status code "
                    "{response.status_code}"
                )
                break

            soup = BeautifulSoup(response.text, "html.parser")
            anchor = soup.select_one("#anchor01")
            if not anchor:
                logger.warning(f"No reviews found on page {page}. Stopping.")
                break

            article_list = anchor.select("article.article")
            if not article_list:
                logger.warning(f"No review data found on page {page}. Stopping.")
                break

            stop_scraping = False
            for article in article_list:
                time_tag = article.select_one("div.article_header-white > p > time")
                date_str = time_tag.get("datetime") if time_tag else None

                if date_str:
                    review_date = datetime.strptime(date_str, "%Y-%m-%d")
                    if review_date < cutoff_date:
                        logger.info(
                            f"Review dated {date_str} is older than 2 years. "
                            "Stopping further scraping."
                        )
                        stop_scraping = True
                        break

                content_dd = article.select_one(
                    "div.article_body > dl > dd.article_answer"
                )
                content_text = content_dd.get_text(strip=True) if content_dd else ""

                review_data = {"date": date_str, "content": content_text}
                all_reviews.append(review_data)

            if stop_scraping:
                break

            page += 1
            time.sleep(random.uniform(0.5, 1.0))  # Simulate human-like behavior

        except Exception:
            logger.exception(f"Error occurred on page {page}")
            break

    return all_reviews


def summarize_reviews(
    client, logger, model_name, company_name, company_intro, reviews, lang
):
    """Generates a structured summary from a list of reviews using the OpenAI API.

    Args:
        client (OpenAI): The OpenAI client object.
        logger (logging.Logger): Logger instance for logging.
        model_name (str): The OpenAI model name.
        company_name (str): Name of the company.
        company_intro (str): Introduction or description of the company.
        reviews (list of str): The textual content of the reviews.
        lang (str): The language code ('ja', 'en', 'zh') for summarization.

    Returns:
        str: A summarized text of the given reviews with a specified format.

    Raises:
        ValueError: If no reviews are provided.
        RuntimeError: If OpenAI API call fails to generate a summary.
    """
    if not reviews:
        logger.error("No reviews provided for summarization")
        raise ValueError("Cannot summarize empty reviews")

    content = "\n\n".join([f'"""\n{r}\n"""' for r in reviews])
    logger.info("Preparing to send data to OpenAI for summarization")

    instructions_by_language = {
        "ja": (
            "あなたは非常に経験豊富なキャリアアドバイザーです。"
            "簡潔かつ洞察に富んだ要約を提供してください。"
            "就職活動中の求職者が自信をもって判断できるように、"
            "日本の職場レビューに基づいた有益な分析を行ってください。\n\n"
            "以下の要件に従ってください：\n"
            "1. 給与レベルは触れない。\n"
            "2. Markdown形式は使用しない。\n"
            "3. 必要に応じて会社の紹介文を補足できる。\n"
            "4. 全体的に矛盾のない情報整理を行う。\n"
            "5. 出力フォーマット例：\n"
            "名称：説明\n"
            "紹介：説明\n"
            "【企業文化】\n説明\n"
            "【WLB】\n説明\n"
            "【成長機会】\n説明\n"
            "【強みと弱点】\n- 強み: ...\n- 弱点: ...\n"
            "【注意点】\n- ... (最大3点)\n"
            "【適合する人材】\n...\n"
            "【推薦指数】⭐ n/5\n\n 理由\n"
            "6. 以下の企業評価は三重引用符で囲まれています。"
            "すべてを統合し、**日本語**でわかりやすく要約してください。\n\n"
        ),
        "en": (
            "You are a highly experienced career advisor. "
            "Provide concise and insightful summaries based on workplace reviews. "
            "Help job seekers make well-informed career decisions "
            "by offering meaningful analysis.\n"
            "Follow these requirements:\n"
            "1. Do not mention specific salary levels.\n"
            "2. Do not use Markdown formatting.\n"
            "3. You may add a brief introduction of the company if appropriate.\n"
            "4. Make sure the final summary is consistent and without conflicts.\n"
            "5. Suggested format:\n"
            "Name: ...\n"
            "Introduction: ...\n"
            "[Company Culture]\n...\n"
            "[WLB]\n...\n"
            "[Growth Opportunities]\n...\n"
            "[Strengths & Weaknesses]\n- Strengths: ...\n- Weaknesses: ...\n"
            "[Cautionary Points]\n- ... (up to 3)\n"
            "[Suitable for]\n...\n"
            "[Recommended Rating] ⭐ n/5\n\n Reason\n"
            "6. Summarize Japanese company reviews (each in triple quotes) "
            "in **English**.\n\n"
        ),
        "zh": (
            "你是一位经验丰富的职业顾问。"
            "基于工作场所评价提供简洁且富有洞察力的总结。"
            "务必提供有价值的分析，帮助求职者在做出职业决策时更加自信且信息充分。\n"
            "遵循以下要求:\n"
            "1. 不提及具体薪资水平。\n"
            "2. 不使用markdown格式。\n"
            "3. 可以适当补充公司简介。\n"
            "4. 保证总结内容逻辑一致。\n"
            "5. 输出示例:\n"
            "名称: ...\n"
            "简介: ...\n"
            "【企业文化】\n...\n"
            "【WLB】\n...\n"
            "【成长机会】\n...\n"
            "【强项与弱点】\n- 强项: ...\n- 弱点: ...\n"
            "【注意点】\n- ... (最多3点)\n"
            "【适合人群】\n...\n"
            "【推荐指数】⭐ n/5\n\n 原因\n"
            "6. 使用**中文**对日语的企业评价进行总结（每条评价以三引号包裹）。\n\n"
        ),
    }

    developer_content = instructions_by_language.get(
        lang, instructions_by_language["ja"]
    )
    developer_content += f"Name: {company_name}\nIntro: {company_intro}\n\n"
    user_content = content

    try:
        response = client.chat.completions.create(
            model=model_name,
            messages=[
                {
                    "role": "developer",
                    "content": developer_content,
                },
                {
                    "role": "user",
                    "content": user_content,
                },
            ],
            temperature=1.0,
            top_p=1.0,
        )
    except Exception:
        logger.exception("OpenAI API error")
        raise RuntimeError("Failed to generate summary using OpenAI API")

    summary = response.choices[0].message.content
    logger.info("Successfully generated summary")
    return summary


def setup_logging():
    """Sets up the logging configuration for the script.

    Returns:
        logging.Logger: Configured logger instance.
    """
    logger = logging.getLogger("openwork_review_summarizer")
    logger.setLevel(logging.DEBUG)
    logger.handlers.clear()

    formatter = logging.Formatter(
        fmt="%(asctime)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    file_handler = RotatingFileHandler(
        filename="openwork_review_summarizer.log",
        maxBytes=5 * 1024 * 1024,  # 5 MB
        backupCount=3,
        encoding="utf-8",
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    return logger


def safe_filename(name):
    """Converts a given string into a filename-safe format.

    Args:
        name (str): The original name (e.g., company name).

    Returns:
        str: A sanitized filename string containing only alphanumeric, "
        "hyphens, or underscores.
    """
    return "".join(c if c.isalnum() or c in ("-", "_") else "_" for c in name)


def parse_args():
    """Parses command-line arguments.

    Returns:
        argparse.Namespace: The parsed command-line arguments.
    """
    parser = argparse.ArgumentParser(
        description="OpenWork Review Summarizer using OpenAI models. "
        "Requires OpenAI API key and OpenWork user account "
        "with access to full reviews.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    parser.add_argument(
        "--company-id",
        help="Company ID to scrape. If omitted, you'll be prompted for it.",
    )
    parser.add_argument(
        "--username",
        help="Your OpenWork username. If omitted, will try environment or .env file.",
    )
    parser.add_argument(
        "--password",
        help="Your OpenWork password. If omitted, will try environment or .env file.",
    )
    parser.add_argument(
        "--model-name",
        default="gpt-4o",
        help="OpenAI model to use for summarization. 4o is recommended for this task.",
    )
    parser.add_argument(
        "--lang",
        choices=["ja", "en", "zh"],
        default="ja",
        help="Language for the summary output. Choices: ja, en, zh.",
    )

    return parser.parse_args()


if __name__ == "__main__":
    logger = setup_logging()

    args = parse_args()
    load_dotenv()

    os.makedirs("reviews", exist_ok=True)
    os.makedirs("summaries", exist_ok=True)

    try:
        username = args.username or os.getenv("OPENWORK_USERNAME")
        password = args.password or os.getenv("OPENWORK_PASSWORD")
        api_key = os.getenv("OPENAI_API_KEY")
        project_id = os.getenv("OPENAI_PROJECT_ID")  # optional usage

        if not all([api_key, username, password]):
            logger.error(
                "Missing required credentials (API key, username, or password)."
            )
            raise ValueError("Required credentials are not set (check CLI or env)")

        client = OpenAI(api_key=api_key)

        company_id = args.company_id
        if not company_id:
            company_id = input("Enter the company ID: ").strip()
            if not company_id:
                logger.error("No company ID provided")
                raise ValueError("Company ID is required")

        with requests.Session() as session:
            session = login_to_openwork(session, username, password, logger)
            company_name, company_intro = get_company_info(session, company_id, logger)

            if not company_name:
                logger.error(f"Could not find company with ID {company_id}")
                raise ValueError(f"Invalid company ID: {company_id}")

            safe_name = safe_filename(company_name)
            reviews_file = os.path.join("reviews", f"reviews_{safe_name}.json")
            summary_file = os.path.join("summaries", f"summary_{safe_name}.txt")

            if os.path.exists(summary_file):
                overwrite = (
                    input(
                        f"Summary file '{summary_file}' already exists. "
                        "Regenerate? [y/N]: "
                    )
                    .strip()
                    .lower()
                )
                if overwrite != "y":
                    logger.info("Skipping summary regeneration as per user choice.")
                    sys.exit(0)

            reviews = scrape_reviews(session, company_id, logger, max_pages=12)
            with open(reviews_file, "w", encoding="utf-8") as f:
                json.dump(reviews, f, ensure_ascii=False, indent=2)
            logger.info(f"Saved {len(reviews)} reviews to {reviews_file}")

            if reviews:
                summary = summarize_reviews(
                    client,
                    logger,
                    args.model_name,
                    company_name,
                    company_intro,
                    [r["content"] for r in reviews],
                    args.lang,
                )
                with open(summary_file, "w", encoding="utf-8") as f:
                    f.write(summary)
                logger.info(f"Saved summary to {summary_file}")
                print(f"\n{summary}")
            else:
                logger.warning("No reviews found for summarization")

    except KeyboardInterrupt:
        logger.info("Process interrupted by user")
        sys.exit(1)
    except Exception:
        logger.exception("An error occurred")
        sys.exit(1)
