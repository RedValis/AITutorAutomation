import time
import tkinter as tk
from tkinter import simpledialog
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import (
    TimeoutException,
    NoSuchElementException,
    StaleElementReferenceException
)

# ----------- Config -----------
# ENTER YOUR CREDENTIALS HERE
USERNAME = "100068708"  # Change this
PASSWORD = "100068708mu"        # Change this

BASE_URL = "https://app.ku-ai-instructor.azzammourad.org"

COURSE_NAME = "MATH112"  # Change to your desired course

TARGET_PERCENTAGE = 100

WAIT_TIMEOUT = 15

# ----------- Manual Blacklist -----------
blacklisted_sections = {
    "9.5 - CALCULUS AND POLAR COORDINATES",
}

# ----------- Answer Memory -----------

quiz_memory = {}

# ----------- Session Section Memory -----------

session_completed_sections = {}
section_failure_counts = {}
MAX_SECTION_FAILURES = 3

# ----------- Automation -----------
def prompt_credentials():
    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)
    username = simpledialog.askstring("KU AI Tutor", "Username:", parent=root)
    password = simpledialog.askstring("KU AI Tutor", "Password:", parent=root, show="*")
    root.destroy()
    if not username or not password:
        return None, None
    return username.strip(), password

def setup_driver():
    chrome_options = Options()
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_argument("--disable-default-apps")
    chrome_options.add_argument("--no-first-run")
    chrome_options.add_argument("--disable-background-timer-throttling")
    driver = webdriver.Chrome(options=chrome_options)
    driver.set_page_load_timeout(30)
    return driver

# ----------- Login -----------
def login(driver, username, password):
    print("Logging in to KU AI Tutor...")
    
    try:
        driver.get(BASE_URL)
        time.sleep(2)
        username_field = WebDriverWait(driver, WAIT_TIMEOUT).until(
            EC.presence_of_element_located((By.NAME, "username"))
        )
        password_field = driver.find_element(By.NAME, "password")
        username_field.clear()
        username_field.send_keys(username)
        time.sleep(0.5)
        password_field.clear()
        password_field.send_keys(password)
        time.sleep(0.5)
        login_button = driver.find_element(By.XPATH, "//button[contains(text(), 'Login')]")
        login_button.click()
        time.sleep(3)
        print("[Login successful]")
        return True
    except TimeoutException:
        print("[Login failed: Timeout waiting for login elements]")
        return False
    except NoSuchElementException as e:
        print(f"[Login failed: Could not find login elements - {e}]")
        return False

# ----------- Navigations -----------
def select_course(driver, course_name):
    print(f"[Selecting course: {course_name}]")
    
    try:
        course_buttons = WebDriverWait(driver, WAIT_TIMEOUT).until(
            EC.presence_of_all_elements_located(
                (By.XPATH, "//div[contains(@class, 'MuiListItemButton-root')]")
            )
        )
        
        for button in course_buttons:
            button_text = button.text
            if course_name.upper() in button_text.upper():
                button.click()
                time.sleep(2)
                print(f"[Selected course: {button_text}]")
                return True
        
        print(f"[Course '{course_name}' not found]")
        return False
        
    except TimeoutException:
        print("[Timeout waiting for course list]")
        return False

def click_practice_exercises(driver):
    print("[Navigating to Practice Exercises]")
    
    try:
        practice_button = WebDriverWait(driver, WAIT_TIMEOUT).until(
            EC.element_to_be_clickable(
                (By.XPATH, "//button[contains(., 'Practice Exercises')]")
            )
        )
        practice_button.click()
        time.sleep(2)
        print("[Navigated to Practice Exercises]")
        return True
    except TimeoutException:
        print("[Timeout waiting for Practice Exercises button]")
        return False

# ----------- quiz selections -----------
def get_incomplete_sections(driver, ignored_titles=None):
    try:
        ignored_titles = ignored_titles or set()
        quiz_cards = driver.find_elements(
            By.XPATH, 
            "//a[contains(@class, 'MuiPaper-root')]"
        )
        
        incomplete_sections = []
        
        for card in quiz_cards:
            try:
                progress_text = card.find_element(
                    By.XPATH, 
                    ".//div[contains(@class, 'MuiTypography-caption')]"
                ).text
                title = card.find_element(
                    By.XPATH, 
                    ".//h6"
                ).text

                if title in ignored_titles:
                    continue
                
                if "%" in progress_text:
                    percentage = int(progress_text.replace("%", ""))
                    if percentage < TARGET_PERCENTAGE:
                        incomplete_sections.append({
                            'element': card,
                            'percentage': percentage,
                            'title': title
                        })
            except (NoSuchElementException, ValueError):
                continue
        
        return incomplete_sections
        
    except Exception as e:
        print(f"Error getting incomplete sections: {e}")
        return []

def click_quiz_section(driver, section_element):
    try:
        section_element.click()
        time.sleep(2)
        return True
    except StaleElementReferenceException:
        print("[Element became stale, refreshing]")
        return False
    except Exception as e:
        print(f"[Error clicking quiz section: {e}]")
        return False

def get_question_text(driver):
    try:
        question_selectors = [
            "//div[contains(@class, 'question-text')]",
            "//div[contains(@class, 'quiz-question')]",
            "//h5[contains(@class, 'MuiTypography-h5')]",  #heading chekc
            "//div[contains(@class, 'MuiTypography-body1')]"  # body text check
        ]
        for selector in question_selectors:
            try:
                question_element = driver.find_element(By.XPATH, selector)
                question_text = question_element.text.strip()
                if question_text and len(question_text) > 10:
                    return question_text
            except NoSuchElementException:
                continue
        quiz_options = driver.find_elements(By.XPATH, "//div[contains(@class, 'quiz-option-markdown-container')]")
        if quiz_options:
            combined_text = " ".join([opt.text.strip() for opt in quiz_options if opt.text.strip()])
            if combined_text:
                return combined_text[:200]
        return None
    except Exception as e:
        print(f"Error getting question text: {e}")
        return None

def check_answer_result(driver):
    try:
        incorrect_elements = driver.find_elements(
            By.XPATH,
            "//div[contains(@class, 'MuiPaper-root') and contains(@class, 'css-v5lcsy')]"
        )
        if incorrect_elements:
            return 'incorrect'
        correct_elements = driver.find_elements(
            By.XPATH,
            "//div[contains(@class, 'MuiPaper-root') and contains(@class, 'css-ffl264')]"
        )
        if correct_elements:
            return 'correct'
        return 'unknown'
    except Exception as e:
        print(f"Error checking answer result: {e}")
        return 'unknown'

def get_correct_answer(driver):
    try:
        correct_element = driver.find_element(
            By.XPATH,
            "//div[contains(@class, 'MuiPaper-root') and contains(@class, 'css-ffl264')]//div[contains(@class, 'quiz-option-markdown-container')]"
        )
        return correct_element.text.strip()
    except NoSuchElementException:
        return None

def save_to_memory(section_title, question_text, correct_answer):
    if section_title not in quiz_memory:
        quiz_memory[section_title] = {}
    
    quiz_memory[section_title][question_text] = correct_answer
    print(f"[Saved to memory: {correct_answer[:50]}]")

def get_from_memory(section_title, question_text):
    if section_title in quiz_memory and question_text in quiz_memory[section_title]:
        return quiz_memory[section_title][question_text]
    return None

def clear_section_memory(section_title):
    if section_title in quiz_memory:
        del quiz_memory[section_title]
        print(f"[Cleared memory for section: {section_title}]")

def remember_completed_section(section_title, reason):
    session_completed_sections[section_title] = reason
    section_failure_counts.pop(section_title, None)
    clear_section_memory(section_title)
    print(f"[Saved section state: {section_title} -> {reason}]")

def record_section_failure(section_title):
    failure_count = section_failure_counts.get(section_title, 0) + 1
    section_failure_counts[section_title] = failure_count
    print(f"[Section failed attempt {failure_count}/{MAX_SECTION_FAILURES}: {section_title}]")
    
    if failure_count >= MAX_SECTION_FAILURES:
        remember_completed_section(section_title, "skipped after repeated failures")
        return True
    
    return False

def select_smart_quiz_option(driver, section_title):
    try:
        print("[Selecting quiz option]")
        
        question_text = get_question_text(driver)
        
        quiz_options = WebDriverWait(driver, WAIT_TIMEOUT).until(
            EC.presence_of_all_elements_located(
                (By.XPATH, "//div[contains(@class, 'quiz-option-markdown-container')]")
            )
        )
        
        if not quiz_options:
            print("[No quiz options found]")
            return False
        if question_text:
            correct_answer = get_from_memory(section_title, question_text)
            if correct_answer:
                print("[Found in memory! Selecting correct answer]")
                for i, option in enumerate(quiz_options):
                    option_text = option.text.strip()
                    if option_text == correct_answer:
                        parent = option.find_element(By.XPATH, "./ancestor::div[contains(@class, 'MuiPaper-root')][1]")
                        parent.click()
                        time.sleep(1)
                        print(f"[Selected remembered correct answer (option {i+1})]")
                        return True
                print("[Correct answer from memory not found in options, falling back to first option]")
        
        # Default: select first option (later save to memory and pick the correct option if wrong :D)
        first_option_container = driver.find_element(
            By.XPATH, 
            "(//div[contains(@class, 'quiz-option-markdown-container')])[1]"
        )
        
        parent = first_option_container.find_element(By.XPATH, "./ancestor::div[contains(@class, 'MuiPaper-root')][1]")
        parent.click()
        
        time.sleep(1)
        print("[Selected first quiz option (default)]")
        return True
        
    except TimeoutException:
        print("[Timeout waiting for quiz options]")
        return False
    except Exception as e:
        print(f"[Error selecting quiz option: {e}]")
        return False

def get_quiz_progress(driver):
    try:
        progress_box = driver.find_element(
            By.XPATH,
            "//div[@aria-label='Current Progress']//h5[contains(@class, 'MuiTypography-h5')]"
        )
        progress_text = progress_box.text.strip()
        
        if "/" in progress_text:
            parts = progress_text.split("/")
            current = int(parts[0].strip())
            total = int(parts[1].strip())
            return current, total
    except (NoSuchElementException, ValueError, IndexError):
        pass
    
    return None, None

def submit_answer(driver):
    try:
        print("[Submitting answer]")
        submit_button = WebDriverWait(driver, WAIT_TIMEOUT).until(
            EC.element_to_be_clickable(
                (By.XPATH, "//button[contains(text(), 'Submit')]")
            )
        )
        submit_button.click()
        time.sleep(1)
        print("[Answer submitted]")
        return True
    except TimeoutException:
        print("[Timeout waiting for Submit button]")
        return False
    except Exception as e:
        print(f"[Error submitting answer: {e}]")
        return False

def is_goal_achieved(driver):
    try:
        goal_element = driver.find_element(
            By.XPATH,
            "//div[@aria-label='Goal Achieved! 🏆']"
        )
        return True
    except NoSuchElementException:
        return False

def click_next_button(driver):
    try:
        print("[Clicking Next button]")
        next_button = WebDriverWait(driver, WAIT_TIMEOUT).until(
            EC.element_to_be_clickable(
                (By.XPATH, "//button[contains(text(), 'Next')]")
            )
        )
        next_button.click()
        time.sleep(1)
        print("[Moved to next question]")
        return True
    except TimeoutException:
        print("[Timeout waiting for Next button]")
        return False
    except Exception as e:
        print(f"[Error clicking Next button: {e}]")
        return False

# ----------- Automation loop  -----------
def complete_single_quiz(driver, section_title):
    question_count = 0
    max_attempts = 50  # Safety limit to prevent infinite loops
    
    while question_count < max_attempts:
        if is_goal_achieved(driver):
            print("[Goal Achieved! Quiz section complete]")
            return "goal_achieved"
        current, total = get_quiz_progress(driver)
        if current is not None and total is not None:
            print(f"   Progress: {current}/{total}")
            if total > 0 and current >= total:
                print(f"[All available questions completed for this section ({current}/{total})]")
                return "all_available_questions_completed"
        
        question_count += 1
        print(f"\n   Question {question_count}:")
        
        if not select_smart_quiz_option(driver, section_title):
            print("[Could not select quiz option]")
            return "failed"
        
        if not submit_answer(driver):
            print("[Submission failed]")
            return "failed"
        
        time.sleep(1)
        
        result = check_answer_result(driver)
        if result == 'incorrect':
            print("[Answer was incorrect, learning correct answer]")
            question_text = get_question_text(driver)
            correct_answer = get_correct_answer(driver)
            if question_text and correct_answer:
                save_to_memory(section_title, question_text, correct_answer)
            else:
                print("[Could not extract question or correct answer]")
        elif result == 'correct':
            print("[Answer was correct]")
        if not click_next_button(driver):
            print("[Could not click Next button]")
            return "failed"
        
        time.sleep(2)
    
    print(f"[Quiz exceeded maximum attempts ({max_attempts})]")
    return "failed"

def run_automation(driver):
    print("\n[Starting Practice Quiz Automation...]\n")
    
    section_count = 0
    
    try:
        while True:
            print("\n" + "="*50)
            print(f"Checking for incomplete sections (Attempt {section_count + 1})...")
            print("="*50)
            
            ignored_titles = set(blacklisted_sections) | set(session_completed_sections)
            incomplete_sections = get_incomplete_sections(driver, ignored_titles=ignored_titles)
            
            if not incomplete_sections:
                print("\n[No more actionable sections remaining for this run]")
                if session_completed_sections:
                    for title, reason in session_completed_sections.items():
                        print(f"   - {title}: {reason}")
                break
            
            print(f"Found {len(incomplete_sections)} incomplete section(s)")
            
            section_info = incomplete_sections[0]
            section_count += 1
            
            print(f"\n[Processing Section {section_count}:]")
            print(f"   Title: {section_info['title']}")
            print(f"   Current Progress: {section_info['percentage']}%")
            
            if not click_quiz_section(driver, section_info['element']):
                print("[Section element became stale, retrying...]")
                continue
            quiz_result = complete_single_quiz(driver, section_info['title'])
            if quiz_result == "goal_achieved":
                remember_completed_section(section_info['title'], "goal achieved")
            elif quiz_result == "all_available_questions_completed":
                remember_completed_section(section_info['title'], "answered all available questions")
            else:
                if record_section_failure(section_info['title']):
                    print("[Section will be skipped for the rest of this run]")
                else:
                    print("[Failed to complete quiz section, continuing...]")
            
            try:
                practice_link = driver.find_element(
                    By.XPATH, 
                    "//a[contains(@href, '/student/practice_quiz')]"
                )
                practice_link.click()
                time.sleep(3)
            except NoSuchElementException:
                print("[Could not navigate back to practice exercises]")
                driver.get(f"{BASE_URL}/student/practice_quiz")
                time.sleep(3)
        
        return True
        
    except KeyboardInterrupt:
        print("\n\n[Automation interrupted by user]")
        return False
    except Exception as e:
        print(f"\n[Unexpected error: {e}]")
        return False

# ----------- Main Loop -----------
def main():
    driver = None
    
    try:
        print("="*60)
        print("KU AI TUTOR PRACTICE QUIZ AUTOMATION")
        print("="*60)
        
        username, password = prompt_credentials()
        if not username or not password:
            print("\n[ERROR: Username and password are required.]")
            return
        
        driver = setup_driver()
        print("[Chrome WebDriver initialized]\n")
        if not login(driver, username, password):
            print("[Login failed. Exiting...]")
            return
        if not select_course(driver, COURSE_NAME):
            print(f"[Could not select course '{COURSE_NAME}'. Exiting...]")
            return
        if not click_practice_exercises(driver):
            print("[Could not navigate to practice exercises. Exiting...]")
            return
        
        time.sleep(2)
        run_automation(driver)
        
        print("\n" + "="*60)
        print("[AUTOMATION COMPLETE]")
        print("="*60)
        
    except Exception as e:
        print(f"\n[Fatal error: {e}]")
    
    finally:
        if driver:
            print("\n[Closing browser...]")
            driver.quit()
            print("[Browser closed]")

if __name__ == "__main__":
    main()
