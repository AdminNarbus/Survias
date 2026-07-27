# Multiple Survías Accounts Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Process every numbered Survías account from `.env` sequentially in one execution.

**Architecture:** Discover complete `SURVIAS_RUT<n>` and `SURVIAS_PASSWORD<n>` pairs, ordered by their numeric suffix. Run the existing scraper once per pair so each account gets an isolated Chrome session, and continue after individual failures.

**Tech Stack:** Python, `python-dotenv`, Selenium, `unittest`.

## Global Constraints

- Never print passwords.
- Use a fresh browser session for every account.
- Continue processing remaining accounts after a failed account.
- Keep `.env` outside version control.

---

### Task 1: Account discovery and sequential execution

**Files:**
- Create: `account_runner.py`
- Create: `tests/test_multiple_accounts.py`
- Modify: `survias_scraper.py`
- Create: `.gitignore`

**Interfaces:**
- `account_runner.py` produces: `load_survias_accounts(environ=None) -> list[tuple[str, str]]`
- `account_runner.py` produces: `run_accounts(accounts, scrape_func) -> bool`

- [ ] **Step 1: Write failing tests**

Test numeric ordering, missing credential validation, and continuation after a failed account.

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m unittest discover -s tests -v`
Expected: FAIL because the two functions do not exist.

- [ ] **Step 3: Implement the minimal behavior**

Discover numbered pairs with a regular expression, validate pairs, iterate in order, and print a password-free summary.

- [ ] **Step 4: Run tests and syntax checks**

Run: `python -m unittest discover -s tests -v`
Run: `python -m py_compile survias_scraper.py`
Expected: all commands exit successfully.
