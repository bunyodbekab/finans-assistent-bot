# Finance Assist Bot

A Telegram bot for tracking income and expenses, generating reports, and managing personal finances. The bot supports Uzbek and Russian languages.

## Features

- Record income and expenses with comments.
- Generate weekly and monthly financial reports.
- Multi-language support (Uzbek and Russian).
- Simple command-based interface.

## Setup and Installation

### Prerequisites

- Python 3.7 or higher.
- Telegram bot token from [BotFather](https://core.telegram.org/bots#6-botfather).

### Clone the Repository

```bash
git clone https://github.com/your-username/finance-assist-bot.git
cd finance-assist-bot

Create a Virtual Environment (Optional but Recommended)

python -m venv venv

Activate the virtual environment:

    On Windows:

venv\Scripts\activate

On Unix or MacOS:

    source venv/bin/activate

Install Dependencies

pip install -r requirements.txt

Note: Create a requirements.txt file with the following content:

python-telegram-bot==13.15
pandas
openpyxl

Run the Bot
python bot.py

Usage

    Start the bot by sending /start in your Telegram client.
    Follow the prompts to select your language and begin using the bot.

License

This project is licensed under the MIT License - see the LICENSE file for details.
Contributing

Contributions are welcome! Please open an issue or submit a pull request.
Acknowledgments

    python-telegram-bot library.
    Pandas for data manipulation.
    OpenPyXL for Excel report generation.


---
Other files
bot_database.db