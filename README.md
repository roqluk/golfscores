# Golfshot Score Scraper

This script scrapes your golf scores from Golfshot.com and exports them with statistics like birdies, pars, bogeys, etc.

## ✅ Status: Ready to Use!

The script has been tested and confirmed working with Golfshot's data format. It extracts data from the embedded JSON in each round's page.

## Setup

1. **Install Python** (if you don't have it already)
   - Download from https://www.python.org/downloads/
   - Make sure Python 3.8 or newer is installed

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Install Playwright browsers**
   ```bash
   playwright install chromium
   ```

## Usage

Run the script:
```bash
python golfshot_scraper.py
```

You'll be prompted to enter your Golfshot email and password.

The script will:
1. Log into your Golfshot account
2. Navigate to your rounds list page
3. **Automatically navigate through ALL pages** of your rounds (handles pagination)
4. Find all your round URLs across all pages
5. Visit each round page and extract the embedded data
6. Calculate statistics (eagles, birdies, pars, bogeys, etc.)
7. Export to CSV and JSON

## Output Files

- **golfshot_scores.csv** - Summary statistics for each round
  - Columns: Date, Course, Total Score, Par, Score vs Par, Eagles or Better, Birdies, Pars, Bogeys, Double Bogeys, Triple+ Bogeys

- **golfshot_scores.json** - Detailed hole-by-hole data for each round

## What Gets Extracted

For each round, the script extracts:
- **Course name and date**
- **Hole-by-hole scores** (score and par for each of 18 holes)
- **Statistics**: 
  - Eagles or better (any score 2+ under par)
  - Birdies (1 under par)
  - Pars (even with par)
  - Bogeys (1 over par)
  - Double Bogeys (2 over par)
  - Triple Bogeys or worse (3+ over par)
- **Total score, par, and score vs par**

## Important Notes

⚠️ **Login Requirements:**
- Make sure you can log into play.golfshot.com with your email and password
- If you have 2-factor authentication enabled, you may need to disable it temporarily
- The script runs with the browser visible (`headless=False`) so you can see what's happening

🔒 **Privacy & Security:**
- Your credentials are only used locally on your computer
- No data is sent anywhere except to Golfshot.com to log in
- All extracted data stays on your computer

## Troubleshooting

**Login fails?**
- Verify your email and password are correct
- Check if Golfshot has any CAPTCHA or additional verification
- If you have 2FA enabled, you may need to disable it temporarily

**No rounds found?**
- Make sure you have rounds visible at https://play.golfshot.com/profiles/lOJZ5/rounds
- The script looks for all links containing "/rounds/" in the URL
- Check that rounds are publicly visible or you're logged in correctly

**Script crashes during scraping?**
- Some rounds might have incomplete data
- The script will continue even if individual rounds fail
- Check the console output to see which rounds had errors

## How It Works

The script uses Playwright to:
1. Open a Chrome browser
2. Navigate to the Golfshot login page
3. Enter your credentials and log in
4. Visit your rounds list page
5. **Extract all round URLs from the current page**
6. **Click "Next" to navigate through all pages of rounds**
7. **Continue until there are no more pages** (when Next button is disabled)
8. For each round URL collected:
   - Visit the round page
   - Extract the embedded JSON data containing all scores
   - Parse the data and calculate statistics
9. Export everything to CSV and JSON files

The script handles pagination automatically, so even if you have hundreds of rounds across many pages, it will get them all!

The data extraction is very reliable because Golfshot embeds all the scorecard data as JSON in the page source for their React application.

## Example Output

From the test run:
```
Course: Chambers Bay Golf Course
Date: Dec 14, 2025
Total Score: 91
Par: 72
Score vs Par: +19

Statistics:
- Eagles or Better: 0
- Birdies: 0
- Pars: 7
- Bogeys: 6
- Double Bogeys: 2
- Triple Bogeys or Worse: 3
```
