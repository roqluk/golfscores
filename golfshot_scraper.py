#!/usr/bin/env python3
"""
Golfshot Score Scraper
Extracts hole-by-hole scores from Golfshot.com and calculates scoring statistics
"""

import asyncio
import csv
import json
from datetime import datetime
from playwright.async_api import async_playwright
import os

class GolfshotScraper:
    def __init__(self, username, password):
        self.username = username
        self.password = password
        self.rounds_data = []
        
    async def login(self, page):
        """Login to Golfshot"""
        print("Navigating to login page...")
        await page.goto("https://play.golfshot.com/login")
        
        # Wait for login form and fill it
        print("Entering credentials...")
        await page.fill('input[type="email"]', self.username)
        await page.fill('input[type="password"]', self.password)
        
        # Click login button
        await page.click('button[type="submit"]')
        
        # Wait for navigation to complete
        await page.wait_for_load_state('networkidle')
        print("Login successful!")
        
    async def get_round_links(self, page):
        """Get all round URLs from the rounds page, handling pagination"""
        print("Fetching rounds list...")
        await page.goto("https://play.golfshot.com/profiles/lOJZ5/rounds")
        await page.wait_for_load_state('networkidle')
        
        all_round_links = []
        page_num = 1
        
        while True:
            print(f"\nScraping page {page_num}...")
            
            # Wait a bit for dynamic content to load
            await asyncio.sleep(2)
            
            # Extract round links from this page
            # The rounds are in table rows with data-href="/profiles/lOJZ5/rounds/{roundId}"
            round_links = await page.evaluate('''() => {
                const rows = Array.from(document.querySelectorAll('tr[data-href*="/rounds/"]'));
                return rows
                    .map(row => {
                        const href = row.getAttribute('data-href');
                        if (href && href.includes('/rounds/')) {
                            // Convert relative URL to absolute
                            return 'https://play.golfshot.com' + href;
                        }
                        return null;
                    })
                    .filter(href => href !== null);
            }''')
            
            print(f"  Found {len(round_links)} rounds on page {page_num}")
            all_round_links.extend(round_links)
            
            # Check if there's a "Next" button and if it's enabled
            # Need to check both the button exists and doesn't have 'disabled' class
            next_button_info = await page.evaluate('''() => {
                const nextButtons = document.querySelectorAll('a.btn-next');
                for (const btn of nextButtons) {
                    const classes = btn.className || '';
                    const href = btn.getAttribute('href') || '';
                    const isDisabled = classes.includes('disabled') || href === 'javascript:void(0)';
                    
                    if (!isDisabled && href && href !== 'javascript:void(0)') {
                        return {
                            exists: true,
                            disabled: false,
                            href: href
                        };
                    }
                }
                return { exists: false, disabled: true, href: null };
            }''')
            
            print(f"  Next button: exists={next_button_info['exists']}, disabled={next_button_info['disabled']}, href={next_button_info['href']}")
            
            if not next_button_info['exists'] or next_button_info['disabled']:
                print("  No more pages to scrape (next button disabled or missing)")
                break
            
            # Navigate to the next page using the href
            try:
                next_url = next_button_info['href']
                if not next_url.startswith('http'):
                    next_url = 'https://play.golfshot.com' + next_url
                
                print(f"  Navigating to: {next_url}")
                await page.goto(next_url)
                await page.wait_for_load_state('networkidle')
                page_num += 1
            except Exception as e:
                print(f"  Error navigating to next page: {e}")
                break
        
        # Remove duplicates while preserving order
        unique_links = []
        seen = set()
        for link in all_round_links:
            if link not in seen:
                unique_links.append(link)
                seen.add(link)
        
        print(f"\n{'='*60}")
        print(f"Total unique rounds found: {len(unique_links)} across {page_num} page(s)")
        print(f"{'='*60}\n")
        return unique_links
    
    def calculate_score_type(self, score, par):
        """Determine if score is eagle, birdie, par, bogey, etc."""
        diff = score - par
        if diff <= -2:
            return "Eagle or better"
        elif diff == -1:
            return "Birdie"
        elif diff == 0:
            return "Par"
        elif diff == 1:
            return "Bogey"
        elif diff == 2:
            return "Double Bogey"
        else:
            return "Triple Bogey or worse"
    
    async def scrape_round(self, page, round_url):
        """Scrape data from a single round"""
        print(f"Scraping round: {round_url}")
        await page.goto(round_url)
        await page.wait_for_load_state('networkidle')
        
        try:
            # Extract the embedded JSON data from the React hydration script
            data = await page.evaluate('''() => {
                // Find the script tag containing the scorecard data
                const scripts = document.querySelectorAll('script');
                for (const script of scripts) {
                    const text = script.textContent;
                    if (text.includes('Golfshot.Applications.Scorecard')) {
                        // Find the start of the JSON object
                        const startIdx = text.indexOf('React.createElement(Golfshot.Applications.Scorecard, ');
                        if (startIdx === -1) continue;
                        
                        // Find where the JSON starts (after the opening parenthesis)
                        const jsonStart = text.indexOf('{', startIdx);
                        if (jsonStart === -1) continue;
                        
                        // Find the matching closing brace for this JSON object
                        let braceCount = 0;
                        let jsonEnd = -1;
                        let inString = false;
                        let escapeNext = false;
                        
                        for (let i = jsonStart; i < text.length; i++) {
                            const char = text[i];
                            
                            if (escapeNext) {
                                escapeNext = false;
                                continue;
                            }
                            
                            if (char === '\\\\') {
                                escapeNext = true;
                                continue;
                            }
                            
                            if (char === '"' && !escapeNext) {
                                inString = !inString;
                                continue;
                            }
                            
                            if (!inString) {
                                if (char === '{') {
                                    braceCount++;
                                } else if (char === '}') {
                                    braceCount--;
                                    if (braceCount === 0) {
                                        jsonEnd = i + 1;
                                        break;
                                    }
                                }
                            }
                        }
                        
                        if (jsonEnd === -1) continue;
                        
                        const jsonStr = text.substring(jsonStart, jsonEnd);
                        
                        try {
                            return JSON.parse(jsonStr);
                        } catch (e) {
                            console.error('JSON parse error:', e.message);
                            continue;
                        }
                    }
                }
                return null;
            }''')
            
            if not data or not data.get('model'):
                print(f"Could not extract data from {round_url}")
                return None
            
            model = data['model']
            
            # Initialize round data structure
            round_data = {
                'url': round_url,
                'date': None,
                'course': None,
                'total_score': None,
                'total_par': None,
                'score_vs_par': None,
                'holes': [],
                'stats': {
                    'eagles': 0,
                    'birdies': 0,
                    'pars': 0,
                    'bogeys': 0,
                    'double_bogeys': 0,
                    'worse': 0
                }
            }
            
            # Extract course and date info
            if 'detail' in model:
                round_data['course'] = model['detail'].get('courseName', '')
                round_data['date'] = model['detail'].get('formattedStartTime', '')
            
            # Extract par values
            par_data = model.get('par', {})
            par_values = par_data.get('values', [])
            
            # Extract score values - from the first player in the game
            score_values = []
            if 'game' in model and 'teams' in model['game']:
                teams = model['game']['teams']
                if teams and len(teams) > 0:
                    players = teams[0].get('players', [])
                    if players and len(players) > 0:
                        scores = players[0].get('scores', [])
                        score_values = [s['score'] for s in scores]
            
            # Build hole-by-hole data
            for i, (par, score) in enumerate(zip(par_values, score_values), 1):
                hole_data = {
                    'hole': i,
                    'par': par,
                    'score': score
                }
                round_data['holes'].append(hole_data)
                
                # Calculate score type
                score_type = self.calculate_score_type(score, par)
                
                if score_type == "Eagle or better":
                    round_data['stats']['eagles'] += 1
                elif score_type == "Birdie":
                    round_data['stats']['birdies'] += 1
                elif score_type == "Par":
                    round_data['stats']['pars'] += 1
                elif score_type == "Bogey":
                    round_data['stats']['bogeys'] += 1
                elif score_type == "Double Bogey":
                    round_data['stats']['double_bogeys'] += 1
                else:
                    round_data['stats']['worse'] += 1
            
            # Calculate totals
            if round_data['holes']:
                round_data['total_score'] = sum(h['score'] for h in round_data['holes'])
                round_data['total_par'] = sum(h['par'] for h in round_data['holes'])
                round_data['score_vs_par'] = round_data['total_score'] - round_data['total_par']
            
            return round_data
            
        except Exception as e:
            print(f"Error scraping round {round_url}: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    async def scrape_all_rounds(self):
        """Main scraping function"""
        async with async_playwright() as p:
            # Launch browser (set headless=False to see what's happening)
            browser = await p.chromium.launch(headless=False)
            context = await browser.new_context()
            page = await context.new_page()
            
            try:
                # Login
                await self.login(page)
                
                # Get all round links
                round_links = await self.get_round_links(page)
                
                # Scrape each round
                for i, round_url in enumerate(round_links, 1):
                    print(f"Processing round {i}/{len(round_links)}")
                    round_data = await self.scrape_round(page, round_url)
                    if round_data:
                        self.rounds_data.append(round_data)
                    
                    # Be polite - wait a bit between requests
                    await asyncio.sleep(1)
                
            finally:
                await browser.close()
    
    def export_to_csv(self, filename='golfshot_scores.csv'):
        """Export scraped data to CSV"""
        if not self.rounds_data:
            print("No data to export")
            return
        
        with open(filename, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([
                'Date', 'Course', 'Total Score', 'Par', 'Score vs Par',
                'Eagles or Better', 'Birdies', 'Pars', 
                'Bogeys', 'Double Bogeys', 'Triple+ Bogeys'
            ])
            
            for round_data in self.rounds_data:
                writer.writerow([
                    round_data['date'],
                    round_data['course'],
                    round_data['total_score'],
                    round_data['total_par'],
                    round_data['score_vs_par'],
                    round_data['stats']['eagles'],
                    round_data['stats']['birdies'],
                    round_data['stats']['pars'],
                    round_data['stats']['bogeys'],
                    round_data['stats']['double_bogeys'],
                    round_data['stats']['worse']
                ])
        
        print(f"Data exported to {filename}")
    
    def export_to_json(self, filename='golfshot_scores.json'):
        """Export scraped data to JSON"""
        with open(filename, 'w') as f:
            json.dump(self.rounds_data, f, indent=2)
        print(f"Detailed data exported to {filename}")


async def main():
    # Get credentials
    username = input("Enter your Golfshot email: ")
    password = input("Enter your Golfshot password: ")
    
    # Create scraper instance
    scraper = GolfshotScraper(username, password)
    
    # Run scraping
    print("\nStarting scrape...")
    await scraper.scrape_all_rounds()
    
    # Export results
    scraper.export_to_csv()
    scraper.export_to_json()
    
    # Print summary
    print(f"\n{'='*50}")
    print(f"Scraping complete!")
    print(f"Total rounds scraped: {len(scraper.rounds_data)}")
    print(f"{'='*50}")


if __name__ == "__main__":
    asyncio.run(main())
