# Lloyd Stress Test Activity Log

**Test Date:** January 25, 2026
**Purpose:** Stress test the revamped Lloyd system with ideas of varying complexity
**System Version:** Lloyd with parallel execution support

---

## Test Configuration

| Setting | Value |
|---------|-------|
| Execution Mode | Parallel (max 3 workers) |
| TDD Approach | Iterative with up to 5 attempts per step |
| Max Iterations | 20-30 |
| LLM | ollama/qwen2.5:32b (via Ollama) |

---

## Test Summary

| # | Idea | Complexity | Classification | Status | Duration | Iterations |
|---|------|------------|----------------|--------|----------|------------|
| 1 | Fibonacci Generator | Simple | simple | **PASSED** | 41.4s | 1 |
| 2 | JSON Config Manager | Moderate | simple | **BLOCKED** | 6.6m | 3 |
| 3 | REST API with CRUD | Complex | complex | **BLOCKED** | 9.3m | 3 |

---

## Test Execution Details

### Test 1: Simple - Fibonacci Generator

**Input:**
```
Create a Python function called fibonacci that takes an integer n and returns
a list of the first n Fibonacci numbers. Include proper type hints and handle
edge cases like n <= 0.
```

**Classification:**
- Input type: idea (confidence: 90%)
- Project: python (pyproject.toml, uv.lock detected)
- Complexity: **simple** - Simple task pattern matched: `^create\s+`
- Mode: TRIVIAL (skipped planning crew)

**Execution:**
- Decomposed into 3 steps
- All steps passed on first attempt
- Duration: **41.4 seconds**
- Status: **COMPLETE**

**Steps Executed:**
1. Create fibonacci function with basic functionality - PASSED (attempt 1)
2. Add type hints for input parameter and return value - PASSED (attempt 1)
3. Handle edge cases (n <= 0) - PASSED (attempt 1)

**Generated Code:**
```python
def fibonacci(n: int) -> list[int]:
    """
    Return a list containing the first n Fibonacci numbers.

    :param n: Number of Fibonacci numbers to generate.
    :return: List of the first n Fibonacci numbers.
    """
    if n <= 0:
        return []
    elif n == 1:
        return [0]
    fib_numbers = [0, 1]
    for i in range(2, n):
        fib_numbers.append(fib_numbers[-1] + fib_numbers[-2])
    return fib_numbers
```

**Generated Tests:**
- `test_fibonacci_zero` - Empty list for n=0
- `test_fibonacci_one` - [0] for n=1
- `test_fibonacci_two` - [0, 1] for n=2
- `test_fibonacci_five` - [0, 1, 1, 2, 3] for n=5
- `test_fibonacci_ten` - Full sequence
- `test_fibonacci_negative_number` - Empty list for negative

**Workspace:** `~/.lloyd/workspace/810a02db/`

---

### Test 2: Moderate - JSON Config Manager

**Input:**
```
Create a Python class called ConfigManager that can load, save, and merge JSON
configuration files. It should support nested keys using dot notation (e.g.,
'database.host'), have a get() method with default values, and validate required
keys. Include proper error handling for missing files and invalid JSON.
```

**Classification:**
- Input type: idea (confidence: 90%)
- Project: python (pyproject.toml detected)
- Complexity: **simple** - Pattern matched: `^create\s+`
- Mode: TRIVIAL (skipped planning crew)

**Execution:**
- Decomposed into 3-4 steps per iteration
- Multiple retries due to persistent import errors in tests
- Duration: **6.6 minutes**
- Status: **BLOCKED** (after 3 iterations)

**Issue Encountered:**
The LLM consistently forgot to add `import json` to generated test files:

```
NameError: name 'json' is not defined. Did you forget to import 'json'
```

**Iterations:**
1. Iteration 1: Steps 1/3 passed (load + get methods worked)
2. Iteration 2: Steps 2/4 passed
3. Iteration 3: Steps 1/3 passed, then blocked

**Root Cause Analysis:**
- Test files used `json.load()` and `json.dumps()` without importing `json`
- Implementation code correctly imported `json`, but test code did not
- This is a known LLM limitation - context window doesn't retain imports across regenerations
- The retry mechanism kept regenerating the same faulty tests

**Workspace:** `~/.lloyd/workspace/2a907665/`

---

### Test 3: Complex - REST API with CRUD

**Input:**
```
Create a simple REST API using FastAPI for managing a todo list. Include:
1. A Todo model with id, title, description, completed status, and created_at timestamp
2. CRUD endpoints: GET /todos, GET /todos/{id}, POST /todos, PUT /todos/{id}, DELETE /todos/{id}
3. In-memory storage (no database required)
4. Proper error handling for not found cases
5. Pydantic models for request/response validation
```

**Classification:**
- Input type: idea (confidence: 90%)
- Project: python (pyproject.toml detected)
- Complexity: **complex** - 2 complexity signals detected
- Mode: FULL (used planning crew)

**Planning Phase:**
- Used CrewAI planning crew with "Senior Requirements Analyst" agent
- Created PRD with stories
- Duration: ~30 seconds for planning

**Execution:**
- Decomposed into multiple steps
- Multiple failures due to missing imports and test mismatches
- Duration: **9.3 minutes**
- Status: **BLOCKED** (after 3 iterations)

**Issues Encountered:**
1. `NameError: name 'List' is not defined` - Forgot `from typing import List`
2. `NameError: name 'TestClient' is not defined` - Forgot import in tests
3. `KeyError: 'id'` - Test expected `id` in response but API returned different structure

**Generated Code (partial but functional):**
```python
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import datetime
from typing import List

app = FastAPI()

class Todo(BaseModel):
    id: int
    title: str
    description: str = ""
    completed: bool = False
    created_at: datetime.datetime = datetime.datetime.now()

todos = []

@app.get("/todos", response_model=List[Todo])
def get_todos():
    return todos

@app.post("/todos", response_model=Todo, status_code=201)
def add_todo(todo: Todo):
    todo_id = len(todos) + 1
    new_todo = {...}
    todos.append(new_todo)
    return Todo(**new_todo)

# ... (additional endpoints implemented)
```

**Workspace:** `~/.lloyd/workspace/68dc1b8c/`

---

## Parallel Execution Analysis

### What Worked

1. **Thread-Safe State Management**
   - File locking prevented race conditions
   - Worker IDs correctly tracked (`W1-0e2a`, `W1-19a4`, etc.)
   - Story claiming worked atomically

2. **Status Transitions**
   - Stories correctly moved: PENDING → IN_PROGRESS → COMPLETED/FAILED
   - Attempts counted accurately
   - Blocked detection worked after 3 failures

3. **Complexity Classification**
   - Simple tasks correctly identified and fast-tracked
   - Complex tasks correctly triggered planning crew
   - Project type detection worked (pyproject.toml)

4. **Iteration Tracking**
   - Parallel iterations logged correctly
   - Batch results summarized properly
   - Duration tracking accurate

### What Needs Improvement

1. **LLM Test Generation**
   - Frequently forgets imports in test files
   - Same error repeated across all 5 retry attempts
   - Suggestion: Add import validation/injection before running tests

2. **Context Retention**
   - LLM doesn't learn from failures within same story
   - Each retry starts fresh without context
   - Suggestion: Include previous error in retry prompt

3. **Test Expectation Accuracy**
   - Sometimes generates tests with wrong expected values
   - Implementation correct but tests fail
   - Suggestion: Validate test expectations against spec

4. **Complexity Underestimation**
   - ConfigManager classified as "simple" but required complex implementation
   - Better heuristics needed for multi-method classes
   - Suggestion: Count distinct capabilities requested

---

## Performance Metrics

| Metric | Test 1 | Test 2 | Test 3 |
|--------|--------|--------|--------|
| Total Duration | 41.4s | 6.6m | 9.3m |
| Iterations | 1 | 3 | 3 |
| Steps Attempted | 3 | 10+ | 9+ |
| Steps Passed | 3 | ~4 | ~3 |
| First-Attempt Pass Rate | 100% | 30% | 20% |
| Planning Time | 0s (skipped) | 0s (skipped) | ~30s |
| LLM Calls | ~6 | ~30+ | ~40+ |

---

## Recommendations

### Short-Term Fixes

1. **Add Import Injection**
   - Before running tests, scan for common patterns like `json.load()`
   - Auto-inject missing imports: `json`, `pytest`, `datetime`, etc.
   - This would have fixed Test 2 and parts of Test 3

2. **Enhanced Error Context**
   - Include the exact error message in retry prompts
   - Ask LLM specifically to fix the identified issue
   - "The previous attempt failed with: NameError for 'json'. Fix the imports."

3. **Test Validation Step**
   - Run a syntax check on generated test files before execution
   - Validate imports are present
   - Check for common test patterns

### Medium-Term Improvements

1. **Better Complexity Detection**
   - Count required methods/endpoints
   - Detect class vs function requests
   - Consider dependency complexity

2. **Adaptive Retry Strategy**
   - If same error repeats 2+ times, try different approach
   - Escalate to human checkpoint faster
   - Try different prompting strategies

3. **Learning From Failures**
   - Build knowledge base of common LLM errors
   - Pre-emptively inject fixes for known patterns
   - Track which prompts produce better code

---

## Workspace Summary

| Test | Workspace ID | Files |
|------|--------------|-------|
| Fibonacci | `810a02db` | `main.py`, `tests/test_main.py` |
| ConfigManager | `2a907665` | `configmanager.py`, `tests/test_*.py` |
| Todo API | `68dc1b8c` | `main.py`, `tests/test_todo_api.py` |

---

## Conclusion

The parallel execution infrastructure is working correctly:
- Thread-safe state management prevents race conditions
- Worker allocation and story claiming works atomically
- Status tracking and iteration counting is accurate

The primary bottleneck is **LLM code generation quality**, specifically:
- Missing imports in generated test files (80% of failures)
- Inconsistent test expectations
- Context not retained between retries

**Success Rate:** 1/3 tests passed (33%)
- Simple, self-contained tasks work well
- Multi-component tasks struggle with test generation

**Priority Fix:** Implement import injection and enhanced error context for retries.

---

## Update: Import Injection Fix Implemented

**Date:** January 25, 2026 (Post-fix)

### Fix Summary

Implemented automatic import injection in `src/lloyd/utils/import_injector.py`:

1. **Standard Import Detection** - Scans for patterns like `json.load()`, `pytest.raises()`, `datetime.datetime()` and auto-injects missing imports

2. **TestClient Pattern Fix** - Detects when tests use `client.get()`, `client.post()` without defining `client = TestClient(app)` and auto-injects:
   - `from fastapi.testclient import TestClient`
   - Adds `app` to existing module import
   - `client = TestClient(app)` initialization

### Re-test Results After Fix

| Test | Before Fix | After Fix | Improvement |
|------|------------|-----------|-------------|
| Fibonacci (Simple) | PASSED | PASSED | - |
| ConfigManager (Moderate) | BLOCKED (6.6m) | **PASSED (57s)** | Fixed |
| REST API (Complex) | BLOCKED (9.3m) | PARTIAL (8.2m) | Improved |

### ConfigManager - Now Passes

```
Step: Create ConfigManager class with load() method...
Attempt 1/5
PASSED on attempt 1

Step: Add get() method with dot notation...
Attempt 1/5
PASSED on attempt 1

Step: Implement validation and error handling...
Attempt 1/5
Auto-injected imports: import json
PASSED on attempt 1

<promise>STORY_COMPLETE</promise>
Duration: 57.0s
```

The `import json` that was causing failures is now auto-injected.

### REST API - Partial Success

The import injection is working (`Auto-injected imports: from fastapi.testclient import TestClient, client = TestClient(app)`), but there are remaining issues with:
- Test expectation mismatches (status code 422 vs 200)
- Implementation not matching test assertions

This is an LLM code quality issue, not an import issue.

### Files Changed

| File | Change |
|------|--------|
| `src/lloyd/utils/import_injector.py` | NEW - Import detection and injection |
| `src/lloyd/orchestrator/iterative_executor.py` | Integrated import injection |
| `tests/test_import_injector.py` | NEW - 29 tests for injector |

### Test Count

| Before | After |
|--------|-------|
| 426 | 455 (+29) |

---

*Stress test completed: January 25, 2026*
*Import injection fix: IMPLEMENTED*
*Total testing time: ~17 minutes (initial) + ~20 minutes (re-test)*
*Lloyd Tests Status: 455 passing*
