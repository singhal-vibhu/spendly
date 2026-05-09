# Delete User Command

Delete a user from the database with interactive conflict resolution when multiple matches are found.

## Usage

```
/delete-user <name-or-email>
```

## Instructions

**Do not use Python's `input()` or any interactive stdin prompts.** All user decisions are handled by you (Claude) asking the user in the conversation and waiting for their reply before running the next script.

Read `database/db.py` to understand the users table schema and the `get_db()` helper.

Then follow these steps:

---

### Step 1 — Search for the user (run a non-interactive Bash script)

Write and run a Python script via Bash that:
- Queries the `users` table for records where `name` OR `email` matches `$ARGUMENTS` (case-insensitive, partial match is fine).
- Prints the results as plain text to stdout in this exact format:

```
FOUND:<count>
ROW:id=<id>|name=<name>|email=<email>
ROW:id=<id>|name=<name>|email=<email>
...
```

- If no rows match, prints: `FOUND:0`
- The script must exit without prompting for anything.

---

### Step 2 — Parse the output and ask the user (conversation turn — no Bash)

Read the script output from Step 1 and handle each case entirely in the conversation — do NOT run any more scripts yet:

**If `FOUND:0`:**
- Tell the user: "No user found matching `$ARGUMENTS`. Nothing will be deleted."
- Stop here.

**If `FOUND:1`:**
- Show the user the single match:
  ```
  Found 1 user:
    ID:    <id>
    Name:  <name>
    Email: <email>
  ```
- Ask in the conversation: **"Confirm deletion? Reply `yes` to delete or `no` to cancel."**
- Wait for their reply before doing anything else.

**If `FOUND:2+`:**
- Show the user a numbered list:
  ```
  Found <N> users matching "$ARGUMENTS":

    [1]  ID: <id>  |  Name: <name>  |  Email: <email>
    [2]  ID: <id>  |  Name: <name>  |  Email: <email>
    ...
  ```
- Ask in the conversation: **"Which user should be deleted? Reply with a number, or `cancel` to abort."**
- Once they pick a number, show the selected user and ask: **"Confirm deletion of this user? Reply `yes` to delete or `no` to cancel."**
- Wait for their confirmation before doing anything else.

---

### Step 3 — Delete the user (run only after the user confirms with "yes")

Only after the user explicitly replies `yes` in the conversation:

Write and run a second Python script via Bash that:
- Uses the same `get_db()` helper from `database/db.py`.
- Deletes the user with the specific `id` chosen in Step 2 (hardcode the id value directly — never use name or email for deletion).
- The script must not use `input()` or prompt for anything.
- Prints on success:
  ```
  ✓ User deleted successfully.

    ID:    <id>
    Name:  <name>
    Email: <email>
  ```
- If the delete fails, prints the error message and exits with a non-zero code.

If the user replies `no` or `cancel` at any point, tell them "Aborted. No changes made." and stop — do not run Step 3.

---

## Notes

- **Never use `input()`, `sys.stdin`, or any blocking read in any Bash-executed script.** All interaction happens in the Claude conversation between script runs.
- Always delete by `id` (primary key), never by name or email, to prevent accidental multi-row deletion.
- Keep the two scripts separate: one for searching (Step 1), one for deleting (Step 3). Never combine them.
- Handle database errors gracefully — catch exceptions and print a clear message instead of a raw traceback.
