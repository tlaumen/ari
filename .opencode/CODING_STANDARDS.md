# Python · Coding Guidelines

> Inspired by TigerBeetle's engineering philosophy — **Safety. Performance. Explicitness.**

---

## 01 — Check Invariants Explicitly

Guard clauses are **executable documentation of invariants**. Check every precondition at the top of a function with explicit `if` statements and raise a meaningful error. Never rely on code "probably" working correctly.

**❌ Weak:**
```python
def transfer(src, dst, amount):
    src.balance -= amount
    dst.balance += amount
    return src, dst
```

**✅ TigerStyle:**
```python
def transfer(src, dst, amount):
    if amount <= 0:
        raise ValueError(f"amount must be positive, got {amount}")
    if src.balance < amount:
        raise ValueError(f"insufficient funds: balance {src.balance}, requested {amount}")
    if src is dst:
        raise ValueError("self-transfer is undefined")

    before = src.balance + dst.balance
    src.balance -= amount
    dst.balance += amount

    if src.balance + dst.balance != before:
        raise RuntimeError("transfer invariant violated: value was created or destroyed")

    return src, dst
```

---

## 02 — Catch Specifically, Raise Loudly

**Never catch `Exception` broadly.** Catching more than you intend is hiding bugs, not handling errors. Only catch the exact exception you know how to recover from — everything else should propagate and crash loudly.

Define **custom exception classes** for your domain. They make error handling precise, grep-friendly, and self-documenting.

**❌ Swallowed:**
```python
try:
    result = parse(data)
except Exception:
    log("parse failed")
    result = None  # silent failure — real error is now lost
```

**❌ Overly broad:**
```python
try:
    connect(host)
except Exception as e:
    raise RuntimeError("connection failed") from e  # obscures the real type
```

**✅ Custom exceptions + specific catching:**
```python
class ParseError(Exception):
    """Raised when input cannot be parsed."""

class InvalidEncodingError(ParseError):
    """Input is not valid UTF-8."""

class MalformedSchemaError(ParseError):
    """Input is valid UTF-8 but violates expected schema."""


try:
    result = parse(data)
except InvalidEncodingError:
    # We know how to handle this: re-encode and retry
    result = parse(data.encode("utf-8", errors="replace"))
# MalformedSchemaError and anything else: let it propagate and break
```

---

## 03 — Types Are Not Optional

Every function signature must be fully annotated. **Run `mypy --strict` in CI.** `Any` is a red flag requiring a comment justifying its use.

Use `TypeAlias`, `NewType`, and `Protocol` to make domain concepts first-class. Primitive obsession is a bug waiting to happen.

**❌ Untyped:**
```python
def send(user_id, message, retries=3):
    ...

def get_price(item, qty):
    ...
```

**✅ Typed domain:**
```python
UserId = NewType("UserId", int)
Cents  = NewType("Cents", int)

def send(user_id: UserId, message: str, retries: int = 3) -> None: ...

def get_price(item: Item, qty: int) -> Cents: ...
```

---

## 04 — Name for the Reader

Names should tell the reader *what* and *why*, not *how*. **Avoid abbreviations.** Prefer a 30-character name that eliminates a comment over a 3-character name that requires one.

Boolean variables must read as statements: `is_`, `has_`, `was_`. Functions that return booleans should form a predicate: `user.is_active()`.

**❌ Cryptic:**
```python
tmp = get(u)
ok = chk(tmp)
if ok:
    proc(tmp, 1)
```

**✅ Legible:**
```python
account = fetch_account_by_user_id(user_id)
is_eligible = account.is_eligible_for_transfer()
if is_eligible:
    initiate_transfer(account, batch_size=1)
```

---

## 05 — No Hidden Control Flow

**Magic methods, decorators, and metaclasses that alter control flow must be documented at the call site.** The reader should not need to hunt through three layers of abstraction to understand what happens when a function is called.

- Avoid `__getattr__`, dynamic dispatch, and monkey-patching in production code.
- Prefer composition and explicit delegation.
- `@property` must be free of side effects and O(1). If it can raise, document it. If it's expensive, make it a method.

---

## 06 — Bound Everything

**Loops, buffers, queues, and retries must have explicit upper bounds.** Unbounded behavior is how systems fail at 3 AM.

Use `itertools.islice`, sized collections, and explicit limits on retry logic. Document the reasoning behind each bound.

**❌ Unbounded:**
```python
while not success:
    success = try_connect()
    time.sleep(delay)
    delay *= 2
```

**✅ Bounded:**
```python
MAX_RETRIES = 8  # ~4 min total at exponential backoff
for attempt in range(MAX_RETRIES):
    if try_connect():
        break
    time.sleep(min(2 ** attempt, 60))
else:
    raise ConnectionError("max retries exceeded")
```

---

## 07 — Measure Before You Optimize

Performance intuition is almost always wrong. **Profile first with `cProfile` or `py-spy`**, then optimize the bottleneck, then measure again. Comments citing profiling data are required next to non-obvious optimizations.

- Avoid premature complexity: generators, `__slots__`, numpy arrays, and Cython should appear only where measurement demands it.
- Never optimize at the cost of correctness. A fast wrong answer is worse than a slow right one.

---

## 08 — One Source of Truth

**Derived state must be derived, not stored.** Storing both `items` and `item_count` as fields means one will eventually be wrong.

- Constants belong in one place. Configuration belongs in one place. Schema belongs in one place.
- Use `@dataclass(frozen=True)` for value objects. Immutability eliminates a whole class of bugs around shared state.

**❌ Duplicated state:**
```python
@dataclass
class Cart:
    items: list[Item]
    item_count: int   # will drift
    total_cents: int  # will drift
```

**✅ Derived:**
```python
@dataclass(frozen=True)
class Cart:
    items: tuple[Item, ...]

    @property
    def item_count(self) -> int:
        return len(self.items)

    @property
    def total_cents(self) -> Cents:
        return Cents(sum(i.price_cents for i in self.items))
```

---

## The Mantras

- Safety is not a feature — it is the foundation.
- If it can fail, assert that it won't, or handle that it might.
- Every `None` return is a question mark at the call site.
- Complexity is not cleverness. Clarity is.
- The bug is always in the code you were most confident about.
- Leave the codebase cleaner than you found it — measurably so.
- A comment that explains *why* is worth ten that explain *what*.

---

*Inspired by [TigerBeetle's TigerStyle](https://github.com/tigerbeetle/tigerbeetle/blob/main/docs/TIGER_STYLE.md)*
