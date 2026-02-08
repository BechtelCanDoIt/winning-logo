---
name: get-next
description: Get the next card from the Planka "To Do" list on the Best Logo board and work on it
---

Get the next card from the Planka "To Do" list on the Best Logo board and work on it.

## IMPORTANT: Use the Python helper script

**NEVER use curl with inline tokens for Planka API calls.** Always use `planka_api.py` in the skill's scripts directory.
The helper handles auth, token refresh, and avoids bash token truncation / `!` shell expansion issues.

### Quick reference

```bash
# Get To Do cards
python3 /mnt/mega/dev/bestlogo/.claude/skills/get-next/scripts/planka_api.py todo

# Get card details
python3 /mnt/mega/dev/bestlogo/.claude/skills/get-next/scripts/planka_api.py card <card_id>

# Move card to a list
python3 /mnt/mega/dev/bestlogo/.claude/skills/get-next/scripts/planka_api.py move <card_id> <list_id>

# Add comment
python3 /mnt/mega/dev/bestlogo/.claude/skills/get-next/scripts/planka_api.py comment <card_id> "comment text"

# Check off a task
python3 /mnt/mega/dev/bestlogo/.claude/skills/get-next/scripts/planka_api.py check-task <task_id>

# Generic API call
python3 /mnt/mega/dev/bestlogo/.claude/skills/get-next/scripts/planka_api.py call <METHOD> <path> ['{"json":"body"}']
```

 - Only operate in the **Biz** project (id: `1527549879151232611`), board **Best Logo** (id: `1527550069992064613`)
### List IDs (importable from planka_api)
- To Do: `1527558345773287025`
- In Progress: `1527558484982236786`
- Review Me: `1705799394755872536`
- Done: `1527558498966046323`

## Steps

1. Fetch To Do cards: `python3 planka_api.py todo`
2. Pick the first/top card
3. Move it to In Progress: `python3 planka_api.py move <card_id> 1527558484982236786`
4. Get card details: `python3 planka_api.py card <card_id>`
5. Read the card description, task list, and tests — do the work described
6. Run tests — once all tests pass, move the card to Review Me: `python3 planka_api.py move <card_id> 1705799394755872536`
7. Check off tasks: `python3 planka_api.py check-task <task_id>` for each task
8. Add a comment summarizing what you did: `python3 planka_api.py comment <card_id> "summary"`
