
# OpenWork Review Summarizer

> [!NOTE]
> Contributions are welcome, and check the [CONTRIBUTING.md](CONTRIBUTING.md) for more information.

This tool helps jobseekers quickly perform enterprise analyses and scout decisions.  
It automatically uses your OpenWork account to retrieve up to two years of reviews and then employs large language models (LLM) to analyze and summarize those reviews.

## Requirements
- A valid [OpenWork](https://www.openwork.jp/) account with access to full reviews  
- A valid [OpenAI](https://platform.openai.com/) API key  

## Installation
1. Clone or Download the repository
   ```bash
   git clone https://github.com/ming-hao-xu/openwork-review-summarizer.git
   cd openwork-review-summarizer
   ```

2. (Optional) Create and activate a virtual environment

   Linux / Mac
   ```bash
   python -m venv venv
   source venv/bin/activate
   ```

   Windows
   ```bash
   python -m venv venv
   .\venv\Scripts\activate
   ```

3. Install dependencies
   ```bash
   pip install -r requirements.txt
   ```

4. Create and configure the `.env` file

   ```
   OPENAI_API_KEY=your_openai_api_key
   OPENAI_PROJECT_ID=optional
   OPENWORK_USERNAME=your_openwork_username
   OPENWORK_PASSWORD=your_openwork_password
   ```

> [!TIP]
> Do not include the `.env` file in your repository or upload it to public platforms.

## Usage (Approximately 6.5 JPY per run)

```bash
python openwork-review-summarizer.py --company-id=a09100000086PxW --lang=en
```

- `--company-id`: Extract the `m_id` from the OpenWork URL.  
  For example, in `https://www.openwork.jp/company.php?m_id=a09100000086PxW`, the `m_id` is `a09100000086PxW`.

- `--lang`: Specify the output language as `ja` (Japanese), `en` (English), or `zh` (Chinese).

The script outputs:  
- JSON reviews saved in the `reviews/` directory  
- Summarized text in the `summaries/` directory  
- Results displayed in the console  

[!screenshots](screenshots/utokyo_en.png)

### Customization

You can modify the `summarize_reviews()` function in `main.py` to customize the style, focus, or format of the summaries.

## Disclaimer
- **Source of Information**: This tool retrieves and summarizes reviews you already have access to on OpenWork.  
- **Responsibility**: The summaries are for reference only. Final decisions are the user's responsibility.  
- **Data Safety**: This tool does not share your credentials or reviews externally, but you must manage your `.env` file securely.  
- **Affiliation**: This tool is unofficial and is not affiliated with OpenWork or OpenAI.
