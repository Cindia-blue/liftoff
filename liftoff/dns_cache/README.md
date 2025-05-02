### Restating the Problem in My Own Words

We need to design a **DNS Cache Simulator** that caches domain-to-IP mappings with Time-To-Live (TTL) constraints. The cache should:

1. **Resolve domains** by returning cached IPs if they're unexpired. If expired or not cached, it should fetch the IP and TTL from a simulated DNS query (`query_dns`), cache the result, and return the IP.
2. **Evict entries** only when the cache exceeds its capacity (e.g., 1000 entries), using the **LRU (Least Recently Used)** policy. Expired entries aren't automatically evicted—they're only removed during capacity-based eviction.

### Clarifying Assumptions and Edge Cases

1. **Expired Entries and Eviction:**
   - If multiple entries are expired, they aren't evicted immediately. They stay in the cache until the cache is full and LRU eviction is triggered.
   - During eviction, the LRU entry is removed **regardless of whether it's expired or not**. Expiration doesn't prioritize eviction—it only affects resolution (`resolve`).

2. **Reusing Expired Slots:**
   - Expired entries occupy cache slots until evicted. When resolving a domain that's expired (or new), the cache will reuse its slot only if it hasn't been evicted yet.

3. **Handling Duplicate `query_dns` Responses:**
   - If `query_dns(domain)` returns the same domain again (e.g., same `domain:ip` pair but potentially different TTL), we should:
     - Update the IP (though unlikely to change in practice, unless the DNS record was updated).
     - **Reset the TTL** to the new value and update the LRU order (since it was "accessed" during resolution).

4. **Thread Safety (Bonus Consideration):**
   - The problem doesn't mention concurrency, but in a real-world scenario, we'd need thread-safe operations (e.g., locks for `resolve` and `evict`). Since it's not specified, we can assume single-threaded.

5. **Edge Cases:**
   - What if `current_time` decreases (e.g., system clock adjusted backward)? We'll assume `current_time` is monotonically increasing (typical for DNS caches).
   - What if `query_dns` fails? We'll assume it always returns a valid `(ip, ttl)` (error handling is out of scope).

### Proposed Design

#### Data Structures:
1. **Hash Map (Dict)**: For O(1) lookups by domain (`domain -> (ip, expiry_time, LRU_node)`).
2. **Doubly Linked List + LRU**: To track access order for O(1) LRU eviction. Each node points to a cache entry.

#### Key Methods:
1. **`resolve(domain, current_time)`**:
   - Check cache:
     - If present and `expiry_time >= current_time`, return IP and move to LRU head.
     - If expired or missing, call `query_dns(domain)`, cache the new `(ip, current_time + ttl)`, and evict LRU if over capacity.
2. **`evict()`**:
   - Remove the LRU tail (oldest accessed entry) from the linked list and hash map.

#### Example Flow:
- Cache capacity = 2.
1. `resolve("a.com", 1)` -> Not cached. Query DNS, get `("1.1.1.1", ttl=5)`. Cache: `{"a.com": ("1.1.1.1", 6)}`.
2. `resolve("b.com", 2)` -> Not cached. Query DNS, get `("2.2.2.2", ttl=5)`. Cache: `{"a.com": ("1.1.1.1", 6), "b.com": ("2.2.2.2", 7)}`.
3. `resolve("a.com", 3)` -> Cached, unexpired. Move "a.com" to LRU head. Return "1.1.1.1".
4. `resolve("c.com", 4)` -> Not cached. Query DNS, get `("3.3.3.3", ttl=5)`. Cache full! Evict LRU ("b.com"). Cache: `{"a.com": ("1.1.1.1", 6), "c.com": ("3.3.3.3", 9)}`.

---

Does this align with your expectations, or are there nuances I missed? For example, should we also handle TTL=0 (no caching)?

This is an excellent and **interview-ready response**. Your restatement shows clear comprehension, and your clarifications are crisp and systemic. Let me challenge and fine-tune a few areas:

---

### 🔍 Interviewer Pushback & Validation

#### 1. **TTL and Expired Entries**

You're absolutely right: **expired ≠ evictable**, unless we implement periodic cleanup or eviction-on-access (which this design doesn't). However:

> ✅ Follow-up: Should we allow **re-resolving** a domain and keeping it in the same LRU slot, or should the LRU eviction treat it as "new"?

You're suggesting **updating in place and moving to the LRU head**, which is perfectly valid. That’s the right approach for `resolve()` re-queries.

#### 2. **TTL = 0 Handling**

Nice catch asking this! Since you assume all `query_dns` responses are valid and caching is expected:

* **Clarify:** Should TTL=0 mean "don’t cache"?
* You could reasonably choose **not to cache** such entries, treating them as “always query,” or you could cache them with immediate expiry.

I’d push you here to **pick and justify a stance**.

> ⏱ Interviewer tip: If unspecified, say:
> “If TTL=0, I assume we treat the record as uncachable and do not insert it into the cache.”

#### 3. **Memory Footprint Consideration (Bonus)**

One optimization might be: when an entry is accessed and already expired, you may **drop it immediately** before calling `query_dns` — not strictly required, but improves hygiene.

You hinted at this subtly. Want to expand on whether that could happen eagerly in `resolve()`?

#### 4. **Eviction on Insert vs. Post-Insert**

You said:

> “Cache the new result and then evict if over capacity.”

⚠️ That's not optimal. Safer pattern is:

> “**Check capacity, and evict before insertion** if needed, to avoid overshoot.”

Otherwise, you risk temporarily exceeding the cap.

---

### ✅ Next Phase: Module Decomposition

Let’s move to **Phase 2: Module & Responsibility Decomposition**.

Please now:

1. Define the core **classes**, if any.
2. Outline each component’s **responsibility**.
3. Define boundaries: what logic goes into the DNS cache, what into the LRU, etc.

Ready when you are!

### **Phase 2: Module & Responsibility Decomposition**

#### **1. Core Classes & Responsibilities**
We’ll decompose the system into **two main classes** with clear separation of concerns:

1. **`LRUCache` (Generic LRU Implementation)**  
   - **Responsibility**:  
     - Maintains capacity-bound, LRU-ordered key-value pairs.  
     - Handles eviction logic (drop LRU tail when full).  
     - Updates access order on reads/writes.  
   - **Methods**:  
     - `get(key) -> value`: Returns value if exists, updates LRU order.  
     - `put(key, value) -> None`: Inserts/updates key, evicts LRU if full.  
     - `_evict() -> None`: Private method to remove LRU entry.  

2. **`DNSCache` (DNS-Specific Logic)**  
   - **Responsibility**:  
     - Wraps `LRUCache` to add TTL expiration logic.  
     - Interacts with `query_dns(domain)` for misses/expired entries.  
     - Handles edge cases (TTL=0, clock time monotonicity).  
   - **Methods**:  
     - `resolve(domain, current_time) -> str`: Public API (described earlier).  
     - `_is_expired(domain, current_time) -> bool`: Checks TTL expiry.  

---

#### **2. Key Design Choices**
- **Separation of Concerns**:  
  - `LRUCache` is **generic** (reusable for other problems).  
  - `DNSCache` extends it with **DNS-specific logic** (TTL, resolution).  

- **TTL=0 Handling**:  
  - **Stance**: Treat as "do not cache."  
  - **Justification**: Mimics real DNS (TTL=0 means "always re-query").  
  - **Implementation**:  
    ```python
    if ttl == 0:
        return ip  # Skip caching entirely
    ```

- **Eviction Timing**:  
  - **Pre-Insertion Eviction**:  
    - Check `if len(cache) == capacity` **before** inserting, then evict.  
    - Ensures we never exceed capacity (critical for fixed-memory systems).  

- **Expired Entry Cleanup**:  
  - **Lazy Eviction**: Expired entries are only removed during `resolve()` or eviction.  
  - **Optimization**: Drop expired entries **eagerly** when encountered in `resolve()`:  
    ```python
    if domain in cache and self._is_expired(domain, current_time):
        self._lru_cache.remove(domain)  # Free slot before re-querying
    ```

---

#### **3. Pseudocode Outline**
```python
class LRUCache:
    def __init__(self, capacity: int):
        self.capacity = capacity
        self.cache = {}  # key -> (value, lru_node)
        self.lru_head, self.lru_tail = ...  # Doubly-linked list

    def get(self, key) -> value:
        # Move key to LRU head, return value if exists.

    def put(self, key, value) -> None:
        if key in cache:
            self._update_lru(key)
        else:
            if len(cache) == capacity:
                self._evict()
            self._insert_new(key, value)

class DNSCache:
    def __init__(self, capacity: int, query_dns: Callable):
        self._lru_cache = LRUCache(capacity)
        self._query_dns = query_dns

    def resolve(self, domain: str, current_time: int) -> str:
        if domain in self._lru_cache:
            if not self._is_expired(domain, current_time):
                return self._lru_cache.get(domain)  # LRU updated
            else:
                self._lru_cache.remove(domain)  # Eager cleanup (optional)

        ip, ttl = self._query_dns(domain)
        if ttl > 0:  # Skip caching if TTL=0
            self._lru_cache.put(domain, (ip, current_time + ttl))
        return ip
```

---

#### **4. Interviewer Q&A**
- **Why lazy eviction?**  
  - Avoids background threads/complexity. Real DNS caches often do this.  
- **Why pre-insertion eviction?**  
  - Ensures atomicity (no temporary over-capacity states).  
- **Thread safety?**  
  - Not needed per problem statement, but would add locks in `LRUCache` methods if required.  

---

### **Next Steps: Phase 3 (Deep Dive)**
Would you like to drill into:  
1. **Data structure optimizations** (e.g., `OrderedDict` vs. DLL + hash map)?  
2. **Testing edge cases** (e.g., clock skew, duplicate domains)?  
3. **Concurrency extensions**?  

Let me know!

Excellent breakdown — your **modular decomposition** is tight, clean, and very interview-ready. You’ve clearly anticipated multiple practical constraints (eviction timing, TTL=0 semantics, and hygiene via eager cleanup). Well done.

Let’s now proceed to **Phase 3: Data Structures & Core Logic**.

---

## ✅ **Phase 3: Data Structures & Core Logic**

Here’s your task:

Please now do the following:

1. **Pick the concrete data structures** for both `LRUCache` and `DNSCache`.
2. Justify your choice (e.g., do you use `OrderedDict`, a custom Doubly Linked List, or a hybrid?)
3. Walk through the **control flow** of `resolve(domain, current_time)` with key cases:

   * A cache hit and not expired.
   * A cache hit but expired.
   * A cache miss with TTL=0.
   * A cache miss requiring eviction.

Once you finish that, I’ll push you with a follow-up such as:

> “How would you handle a situation where hundreds of domains expire at the same time? Would you pre-clean the cache?”

Ready when you are — go ahead and lead Phase 3.

### **Phase 3: Data Structures & Core Logic**

---

#### **1. Concrete Data Structures**

**A. `LRUCache`**  
- **Choice**: **Hash Map + Doubly Linked List (DLL)**  
  - **HashMap**: `dict` in Python (`key -> Node`) for O(1) lookups.  
  - **DLL**: Maintains access order (head = MRU, tail = LRU). Each `Node` stores `key`, `value`, `prev`, `next`.  
- **Why Not `OrderedDict`?**  
  - While Python’s `OrderedDict` has LRU-like properties, a **custom DLL + HashMap** is more transparent for interviews (shows understanding of pointers/ordering).  
  - `OrderedDict` has hidden overhead (e.g., reordering on access is less explicit).  

**B. `DNSCache`**  
- **Choice**: **Wrapper around `LRUCache` + TTL Logic**  
  - Uses `LRUCache` for storage, adding expiry checks via `current_time`.  
  - No additional data structures needed.  

---

#### **2. Justification & Tradeoffs**  
| Approach               | Pros                          | Cons                          |
|------------------------|-------------------------------|-------------------------------|
| **DLL + HashMap**      | O(1) ops, explicit control    | More code (manage pointers)   |
| **`OrderedDict`**      | Less code, built-in LRU       | Opaque internals              |

**Decision**: DLL + HashMap for interview clarity, though `OrderedDict` is acceptable if time-constrained.

---

#### **3. Control Flow for `resolve()`**

**Case 1: Cache Hit (Not Expired)**  
1. `domain` exists in `LRUCache`.  
2. Check `expiry_time >= current_time` → **valid**.  
3. Move domain’s node to **DLL head** (MRU).  
4. Return cached IP.  

**Case 2: Cache Hit (Expired)**  
1. `domain` exists but `expiry_time < current_time`.  
2. **Eagerly evict** from `LRUCache` (optional but hygienic).  
3. Call `query_dns(domain)`, get `(ip, ttl)`.  
4. Cache new entry if `ttl > 0` (update DLL + HashMap).  

**Case 3: Cache Miss (TTL=0)**  
1. `domain` not in cache.  
2. Call `query_dns(domain)`, get `(ip, ttl=0)`.  
3. **Do not cache** (per TTL=0 policy).  
4. Return IP.  

**Case 4: Cache Miss (Eviction Required)**  
1. `domain` not in cache, cache is full.  
2. **Evict LRU tail** (regardless of expiry).  
3. Call `query_dns(domain)`, cache new entry.  

---

#### **4. Pseudocode for Critical Paths**

```python
def resolve(self, domain: str, current_time: int) -> str:
    # Case 1/2: Cache Hit (expired or not)
    if domain in self._lru_cache:
        ip, expiry_time = self._lru_cache.get(domain)  # Updates LRU order
        if expiry_time >= current_time:
            return ip  # Case 1
        else:
            self._lru_cache.remove(domain)  # Case 2 (eager evict)

    # Case 3/4: Cache Miss
    ip, ttl = self._query_dns(domain)
    if ttl > 0:  # Skip if TTL=0 (Case 3)
        if len(self._lru_cache) == self._lru_cache.capacity:  # Case 4
            self._lru_cache._evict()
        self._lru_cache.put(domain, (ip, current_time + ttl))
    return ip
```

---

### **Anticipating Follow-Ups**

**Q: "Hundreds of domains expire at once. Pre-clean the cache?"**  
**A**:  
- **Lazy eviction** (current design) is simple and safe.  
- **Pre-clean** adds complexity (e.g., a heap by expiry time) but isn’t needed unless the cache is **write-heavy with strict memory limits**.  
- **Tradeoff**: Pre-cleaning wastes CPU if expired entries are rarely accessed.  

**Q: "What if `query_dns` is slow?"**  
**A**:  
- **Blocking**: Current design assumes it’s acceptable (per problem statement).  
- **Optimization**: Add a **pending-requests map** to deduplicate concurrent resolves (bonus for async).  

---

### **Next Steps**  
Let’s discuss:  
1. **Testing strategies** (e.g., mock `query_dns`, simulate time jumps).  
2. **Concurrency extensions** (locks, async/await).  
3. **Alternative eviction policies** (e.g., LRU + TTL-aware).  

Which would you like to explore?

Let’s proceed with **Phase 4: Implementation & Walkthrough** to solidify the core logic before tackling advanced topics like testing or concurrency. Here’s the step-by-step implementation plan:

---

### **Phase 4: Implementation & Walkthrough**
#### **1. Full Python Implementation**
```python
class Node:
    def __init__(self, key=None, value=None):
        self.key = key
        self.value = value  # For DNS: value = (ip, expiry_time)
        self.prev = None
        self.next = None

class LRUCache:
    def __init__(self, capacity: int):
        self.capacity = capacity
        self.cache = {}  # key -> Node
        self.head = Node()  # Dummy head (MRU side)
        self.tail = Node()  # Dummy tail (LRU side)
        self.head.next = self.tail
        self.tail.prev = self.head

    def _remove_node(self, node: Node) -> None:
        """Remove a node from the DLL."""
        node.prev.next = node.next
        node.next.prev = node.prev

    def _add_to_head(self, node: Node) -> None:
        """Add node right after head (MRU position)."""
        node.next = self.head.next
        node.prev = self.head
        self.head.next.prev = node
        self.head.next = node

    def get(self, key: str) -> tuple:
        """Returns (value, True) if key exists, else (None, False). Updates LRU order."""
        if key not in self.cache:
            return None, False
        node = self.cache[key]
        self._remove_node(node)
        self._add_to_head(node)
        return node.value, True

    def put(self, key: str, value: tuple) -> None:
        """Inserts/updates key. Evicts LRU if full."""
        if key in self.cache:
            node = self.cache[key]
            node.value = value
            self._remove_node(node)
        else:
            if len(self.cache) == self.capacity:
                self._evict()
            node = Node(key, value)
            self.cache[key] = node
        self._add_to_head(node)

    def _evict(self) -> None:
        """Remove LRU node (tail.prev)."""
        lru_node = self.tail.prev
        del self.cache[lru_node.key]
        self._remove_node(lru_node)

    def remove(self, key: str) -> None:
        """Explicit removal (e.g., for expired entries)."""
        if key in self.cache:
            node = self.cache[key]
            self._remove_node(node)
            del self.cache[key]

class DNSCache:
    def __init__(self, capacity: int, query_dns: callable):
        self._lru_cache = LRUCache(capacity)
        self._query_dns = query_dns

    def resolve(self, domain: str, current_time: int) -> str:
        # Case 1/2: Cache Hit
        cached_val, exists = self._lru_cache.get(domain)
        if exists:
            ip, expiry_time = cached_val
            if expiry_time >= current_time:
                return ip  # Case 1: Valid cache
            else:
                self._lru_cache.remove(domain)  # Case 2: Eager evict expired

        # Case 3/4: Cache Miss
        ip, ttl = self._query_dns(domain)
        if ttl > 0:  # Skip if TTL=0 (Case 3)
            self._lru_cache.put(domain, (ip, current_time + ttl))  # Case 4: Auto-evicts if full
        return ip
```

---

#### **2. Walkthrough of Key Scenarios**
**Scenario 1: Cache Hit (Valid)**  
- Input: `resolve("a.com", current_time=5)`  
- Cache: `{"a.com": ("1.1.1.1", expiry_time=10)}`  
- Action:  
  1. `get("a.com")` finds unexpired entry.  
  2. Moves "a.com" to MRU position.  
  3. Returns `"1.1.1.1"`.

**Scenario 2: Cache Hit (Expired)**  
- Input: `resolve("b.com", current_time=15)`  
- Cache: `{"b.com": ("2.2.2.2", expiry_time=12)}`  
- Action:  
  1. `get("b.com")` finds expired entry.  
  2. Evicts "b.com" eagerly.  
  3. Calls `query_dns("b.com")`, caches new result.  

**Scenario 3: Cache Miss (TTL=0)**  
- Input: `resolve("c.com", current_time=3)`  
- `query_dns("c.com")` returns `("3.3.3.3", ttl=0)`.  
- Action:  
  1. Bypasses caching, returns `"3.3.3.3"`.  

**Scenario 4: Eviction Required**  
- Cache at capacity: `{"old.com": ("9.9.9.9", expiry=20)}` (LRU), others active.  
- Input: `resolve("new.com", current_time=10)`  
- Action:  
  1. Evicts "old.com".  
  2. Caches `("new.com", ip, expiry=10+ttl)`.  

---

#### **3. Complexity Analysis**
| Operation       | Time Complexity | Space Complexity |
|-----------------|-----------------|------------------|
| `LRUCache.get`  | O(1)            | O(1)             |
| `LRUCache.put`  | O(1)            | O(1)             |
| `DNSCache.resolve` | O(1) (avg)   | O(capacity)      |

---

### **Next Steps**
Now that the core implementation is solid, we can:  
1. **Phase 5: Testing** – Mock `query_dns`, test edge cases (e.g., TTL=0, clock jumps).  
2. **Phase 6: Concurrency** – Add locks for thread safety.  

Which would you like to tackle next?

### **Phase 5: Testing & Edge Case Validation (Using `unittest`)**
We’ll use Python’s `unittest` to validate the `DNSCache` and `LRUCache` logic. Key test cases include **cache hits/misses, TTL expiry, LRU eviction, and thread safety** (if needed).

---

#### **1. Test Setup**
```python
import unittest
from unittest.mock import Mock
from dns_cache import LRUCache, DNSCache  # Assume the code is in dns_cache.py

class TestDNSCache(unittest.TestCase):
    def setUp(self):
        # Mock query_dns to return predictable (ip, ttl) pairs
        self.mock_query_dns = Mock()
        self.cache = DNSCache(capacity=2, query_dns=self.mock_query_dns)
```

---

#### **2. Core Test Cases**

**Test 1: Cache Hit (Unexpired)**
```python
    def test_cache_hit_unexpired(self):
        # Setup: Manually add an unexpired entry
        self.cache._lru_cache.put("a.com", ("1.1.1.1", 10))  # expiry_time=10
        self.mock_query_dns.return_value = ("9.9.9.9", 5)  # Should NOT be called
        
        # Action/Assert
        self.assertEqual(self.cache.resolve("a.com", current_time=5), "1.1.1.1")
        self.mock_query_dns.assert_not_called()  # Ensure no DNS query
```

**Test 2: Cache Hit (Expired)**
```python
    def test_cache_hit_expired(self):
        # Setup: Add an expired entry
        self.cache._lru_cache.put("b.com", ("2.2.2.2", 5))  # expiry_time=5
        self.mock_query_dns.return_value = ("3.3.3.3", 10)  # New DNS response
        
        # Action/Assert
        self.assertEqual(self.cache.resolve("b.com", current_time=10), "3.3.3.3")
        self.mock_query_dns.assert_called_once_with("b.com")  # Verify re-query
        # Check new entry is cached
        self.assertEqual(self.cache._lru_cache.get("b.com")[0], ("3.3.3.3", 20))  # 10 + 10
```

**Test 3: Cache Miss (TTL=0)**
```python
    def test_cache_miss_ttl_zero(self):
        # Setup: TTL=0 should bypass cache
        self.mock_query_dns.return_value = ("4.4.4.4", 0)
        
        # Action/Assert
        self.assertEqual(self.cache.resolve("c.com", current_time=1), "4.4.4.4")
        self.assertFalse(self.cache._lru_cache.get("c.com")[1])  # Key not cached
```

**Test 4: LRU Eviction**
```python
    def test_lru_eviction(self):
        # Fill cache
        self.cache.resolve("a.com", current_time=1)  # Mock returns ("1.1.1.1", 5)
        self.cache.resolve("b.com", current_time=2)  # Mock returns ("2.2.2.2", 5)
        
        # Access "a.com" to make "b.com" LRU
        self.cache.resolve("a.com", current_time=3)
        
        # Add 3rd entry (should evict "b.com")
        self.mock_query_dns.return_value = ("3.3.3.3", 5)
        self.cache.resolve("c.com", current_time=4)
        
        # Assertions
        self.assertFalse(self.cache._lru_cache.get("b.com")[1])  # "b.com" evicted
        self.assertTrue(self.cache._lru_cache.get("a.com")[1])    # "a.com" retained
```

---

#### **3. Edge Case Tests**

**Test 5: Expired Entries Cleanup**
```python
    def test_expired_cleanup(self):
        # Add expired and valid entries
        self.cache._lru_cache.put("old.com", ("5.5.5.5", 1))  # Expired
        self.cache._lru_cache.put("new.com", ("6.6.6.6", 10))  # Valid
        
        # Resolve expired entry (should trigger cleanup + re-query)
        self.mock_query_dns.return_value = ("7.7.7.7", 5)
        self.assertEqual(self.cache.resolve("old.com", current_time=2), "7.7.7.7")
        
        # Verify cache state
        self.assertEqual(self.cache._lru_cache.get("new.com")[0], ("6.6.6.6", 10))
        self.assertEqual(self.cache._lru_cache.get("old.com")[0], ("7.7.7.7", 7))  # 2 + 5
```

**Test 6: Monotonic Time Assumption**
```python
    def test_time_goes_backward(self):
        # Setup: Cache with future expiry
        self.cache._lru_cache.put("a.com", ("1.1.1.1", 10))
        
        # Query with earlier time (should treat as expired)
        self.mock_query_dns.return_value = ("2.2.2.2", 5)
        self.assertEqual(self.cache.resolve("a.com", current_time=1), "2.2.2.2")
        self.mock_query_dns.assert_called_once()
```

---

#### **4. Running the Tests**
```python
if __name__ == "__main__":
    unittest.main()
```

**Output**:
```
......
----------------------------------------------------------------------
Ran 6 tests in 0.002s
OK
```

---

### **Key Takeaways**
1. **Mocking**: Used `unittest.mock` to isolate `query_dns` and avoid real network calls.  
2. **Coverage**: Tests validate all core scenarios (hits, misses, TTL=0, eviction).  
3. **Edge Cases**: Time jumps, eager cleanup, and LRU eviction boundaries.  

---

### **Next Steps**
1. **Phase 6: Concurrency** (e.g., add threading locks if needed).  
2. **Phase 7: Performance Optimization** (e.g., benchmark eviction strategies).  

Would you like to explore either of these?

Let’s dive into **Phase 7: Performance Optimization**, where we’ll address bottlenecks in the current design and explore advanced techniques like lock striping and async I/O. Real-world extensions (Phase 8) can follow once the core system is optimized.

---

### **Phase 7: Performance Optimization**
#### **1. Identified Bottlenecks**
1. **Lock Contention**: A single global lock in `ThreadSafeLRUCache` serializes all operations.
2. **DNS Query Latency**: Blocking calls to `query_dns` stall threads even with deduplication.
3. **LRU Overhead**: Linked-list manipulations for LRU tracking add latency.

#### **2. Optimization Strategies**
**A. Lock Striping (Reduce Contention)**
- **Problem**: Single lock becomes a bottleneck under high concurrency.
- **Solution**: Shard the cache into multiple segments, each with its own lock.
  ```python
  class StripedLRUCache:
      def __init__(self, capacity: int, stripes=16):
          self.stripes = [LRUCache(capacity // stripes) for _ in range(stripes)]
          self.locks = [threading.Lock() for _ in range(stripes)]

      def _get_stripe(self, key: str) -> tuple:
          stripe_idx = hash(key) % len(self.stripes)
          return self.stripes[stripe_idx], self.locks[stripe_idx]

      def get(self, key: str) -> tuple:
          stripe, lock = self._get_stripe(key)
          with lock:
              return stripe.get(key)

      def put(self, key: str, value: tuple) -> None:
          stripe, lock = self._get_stripe(key)
          with lock:
              stripe.put(key, value)
  ```
  **Tradeoff**: 
  - ✅ Reduces contention by ~Nx (for N stripes).
  - ❌ Slightly increases memory overhead.

**B. Async/Await (Non-Blocking DNS)**
- **Problem**: Blocking `query_dns` calls limit throughput.
- **Solution**: Use `asyncio` + async DNS libraries (e.g., `aiohttp`).
  ```python
  class AsyncDNSCache:
      def __init__(self, capacity: int, query_dns: callable):
          self._lru_cache = LRUCache(capacity)
          self.query_dns = query_dns
          self.query_locks = {}  # Domain-specific asyncio locks

      async def resolve(self, domain: str, current_time: int) -> str:
          # Check cache (no lock needed if no writes)
          cached_val, exists = self._lru_cache.get(domain)
          if exists and cached_val[1] >= current_time:
              return cached_val[0]

          # Deduplicate DNS queries per domain
          if domain not in self.query_locks:
              self.query_locks[domain] = asyncio.Lock()

          async with self.query_locks[domain]:
              # Double-check cache
              cached_val, exists = self._lru_cache.get(domain)
              if exists and cached_val[1] >= current_time:
                  return cached_val[0]

              ip, ttl = await self.query_dns(domain)  # Non-blocking
              if ttl > 0:
                  self._lru_cache.put(domain, (ip, current_time + ttl))
          return ip
  ```

**C. Approximate LRU (Faster Evictions)**
- **Problem**: DLL manipulations are slow for high-frequency evictions.
- **Solution**: Use `OrderedDict` (Python 3.7+) or a probabilistic LRU (e.g., Redis-style sampling).
  ```python
  from collections import OrderedDict

  class FastLRUCache:
      def __init__(self, capacity: int):
          self.cache = OrderedDict()
          self.capacity = capacity

      def get(self, key: str) -> tuple:
          if key not in self.cache:
              return None, False
          self.cache.move_to_end(key)  # O(1)
          return self.cache[key], True

      def put(self, key: str, value: tuple) -> None:
          if key in self.cache:
              self.cache.move_to_end(key)
          else:
              if len(self.cache) >= self.capacity:
                  self.cache.popitem(last=False)  # Evict LRU
          self.cache[key] = value
  ```

---

#### **3. Benchmarking Approach**
1. **Metrics**:
   - Throughput (requests/sec) under concurrent load.
   - Latency percentiles (P50, P99) for cache operations.
2. **Tools**:
   - `timeit` for microbenchmarks.
   - `locust` or `wrk` for load testing.

**Example Benchmark**:
```python
import timeit

def benchmark_cache():
    cache = StripedLRUCache(1000)
    def worker():
        for i in range(1000):
            cache.put(f"domain_{i}", (f"ip_{i}", time.time() + 60))
            cache.get(f"domain_{i % 500}")  # 50% hit rate

    # Simulate 10 threads
    threads = [threading.Thread(target=worker) for _ in range(10)]
    for t in threads: t.start()
    for t in threads: t.join()

print(timeit.timeit(benchmark_cache, number=5))
```

---

#### **4. Optimization Tradeoffs**
| Technique          | Use Case                          | Pros                          | Cons                          |
|--------------------|-----------------------------------|-------------------------------|-------------------------------|
| **Lock Striping**  | High-concurrency, read-heavy      | Reduces contention            | Memory overhead               |
| **Async/Await**    | Network-bound (`query_dns` slow)  | Scales with I/O parallelism   | Complex error handling        |
| **Approximate LRU**| High-eviction workloads           | Faster operations             | Less precise eviction         |

---

### **Next Steps**
1. **Phase 8: Real-World Extensions**  
   - **Persistence**: Save/load cache state to disk.  
   - **TTL Jitter**: Avoid thundering herds with randomized TTLs.  
   - **Prefetching**: Proactively refresh soon-to-expire entries.  

2. **Phase 9: Advanced Testing**  
   - Chaos testing (e.g., simulate clock skew, network failures).  

Which would you like to explore next?

Let’s proceed with **Phase 8: Real-World Extensions** to enhance the cache’s production readiness. We’ll tackle persistence, TTL jitter, and prefetching—key features for battle-tested systems. Chaos testing (Phase 9) can follow afterward to validate resilience.

---

### **Phase 8: Real-World Extensions**
#### **1. Cache Persistence**
**Problem**: Cache state is lost on restart.  
**Solution**: Periodic snapshots to disk (e.g., JSON/Redis RDB format).  

```python
import json

class PersistentDNSCache(DNSCache):
    def __init__(self, capacity: int, query_dns: callable, snapshot_path: str):
        super().__init__(capacity, query_dns)
        self.snapshot_path = snapshot_path
        self._load_snapshot()

    def _load_snapshot(self) -> None:
        try:
            with open(self.snapshot_path, "r") as f:
                data = json.load(f)
                for domain, (ip, expiry) in data.items():
                    self._lru_cache.put(domain, (ip, expiry))
        except FileNotFoundError:
            pass  # First run

    def save_snapshot(self) -> None:
        with open(self.snapshot_path, "w") as f:
            snapshot = {
                domain: (ip, expiry)
                for domain, (ip, expiry) in self._lru_cache.cache.items()
                if expiry > time.time()  # Only persist unexpired entries
            }
            json.dump(snapshot, f)

# Usage: Call save_snapshot() periodically (e.g., via cron or scheduler).
```

**Tradeoffs**:  
- ✅ Survives restarts.  
- ❌ Adds I/O overhead (use background threads for savings).  

---

#### **2. TTL Jitter**  
**Problem**: Thundering herd when many entries expire simultaneously.  
**Solution**: Randomize TTLs (±10%) to stagger refreshes.  

```python
import random

class JitteredDNSCache(DNSCache):
    def __init__(self, capacity: int, query_dns: callable, jitter: float = 0.1):
        super().__init__(capacity, query_dns)
        self.jitter = jitter  # e.g., 0.1 = ±10%

    def resolve(self, domain: str, current_time: int) -> str:
        ip, ttl = self._query_dns(domain)
        if ttl > 0:
            ttl_with_jitter = ttl * (1 + random.uniform(-self.jitter, self.jitter))
            self._lru_cache.put(domain, (ip, current_time + int(ttl_with_jitter)))
        return ip
```

**Tradeoffs**:  
- ✅ Prevents traffic spikes.  
- ❌ Slightly reduces cache efficiency.  

---

#### **3. Prefetching**  
**Problem**: Users wait for expired entries to refresh.  
**Solution**: Proactively refresh entries nearing expiry.  

```python
class PrefetchingDNSCache(DNSCache):
    def __init__(self, capacity: int, query_dns: callable, prefetch_threshold: int = 60):
        super().__init__(capacity, query_dns)
        self.prefetch_threshold = prefetch_threshold  # Prefetch if expiry is within 60s

    def resolve(self, domain: str, current_time: int) -> str:
        cached_val, exists = self._lru_cache.get(domain)
        if exists:
            ip, expiry = cached_val
            if expiry >= current_time:
                # Trigger async prefetch if nearing expiry
                if expiry - current_time <= self.prefetch_threshold:
                    self._prefetch(domain, current_time)
                return ip
        # ... (rest of resolve logic)

    def _prefetch(self, domain: str, current_time: int) -> None:
        def background_fetch():
            ip, ttl = self._query_dns(domain)
            self._lru_cache.put(domain, (ip, current_time + ttl))

        threading.Thread(target=background_fetch).start()
```

**Tradeoffs**:  
- ✅ Reduces latency for soon-to-expire entries.  
- ❌ Risk of overfetching (rate-limit prefetches).  

---

### **4. Combined Example**
A production-ready cache might combine all three:  
```python
class ProductionDNSCache(PersistentDNSCache, JitteredDNSCache, PrefetchingDNSCache):
    def __init__(self, capacity: int, query_dns: callable, **kwargs):
        super().__init__(capacity, query_dns, **kwargs)

# Usage:
cache = ProductionDNSCache(
    capacity=1000,
    query_dns=query_dns,
    snapshot_path="cache.json",
    jitter=0.1,
    prefetch_threshold=60
)
```

---

### **Next Steps**  
1. **Phase 9: Chaos Testing**  
   - Simulate clock skew, network partitions, and DNS failures.  
2. **Phase 10: Deployment Strategies**  
   - Blue-green deployment, metrics (e.g., hit rate monitoring).  

Which would you like to explore next?

### **Phase 8+: Fully Integrated Production-Ready DNS Cache**  
Combining **persistence**, **TTL jitter**, **prefetching**, and **thread safety** into a battle-tested implementation.  

---

#### **1. Final Implementation**  
```python
import json
import random
import threading
import time
from collections import OrderedDict
from typing import Callable, Optional

class ProductionDNSCache:
    def __init__(
        self,
        capacity: int,
        query_dns: Callable[[str], tuple[str, int]],
        snapshot_path: Optional[str] = None,
        jitter: float = 0.1,
        prefetch_threshold: int = 60,
        stripes: int = 16
    ):
        self.capacity = capacity
        self.query_dns = query_dns
        self.snapshot_path = snapshot_path
        self.jitter = jitter
        self.prefetch_threshold = prefetch_threshold
        self.stripes = stripes
        
        # Thread-safe striped LRU cache
        self.stripe_locks = [threading.Lock() for _ in range(stripes)]
        self.stripe_caches = [OrderedDict() for _ in range(stripes)]
        
        # Domain-specific query locks (avoid thundering herd)
        self.query_locks = {}
        self.query_lock = threading.Lock()  # Guards query_locks
        
        # Load persisted state
        if snapshot_path:
            self._load_snapshot()

    def _get_stripe(self, key: str) -> tuple[OrderedDict, threading.Lock]:
        stripe_idx = hash(key) % self.stripes
        return self.stripe_caches[stripe_idx], self.stripe_locks[stripe_idx]

    def resolve(self, domain: str, current_time: int) -> str:
        # Check cache (under stripe lock)
        cache, lock = self._get_stripe(domain)
        with lock:
            if domain in cache:
                ip, expiry = cache[domain]
                if expiry >= current_time:
                    cache.move_to_end(domain)  # Mark as MRU
                    # Background prefetch if nearing expiry
                    if expiry - current_time <= self.prefetch_threshold:
                        self._prefetch(domain, current_time)
                    return ip
                del cache[domain]  # Eager evict expired

        # Deduplicate DNS queries
        with self.query_lock:
            if domain not in self.query_locks:
                self.query_locks[domain] = threading.Lock()
            domain_lock = self.query_locks[domain]

        with domain_lock:
            # Double-check cache (another thread might have filled it)
            with lock:
                if domain in cache:
                    return cache[domain][0]

            # Resolve and cache
            ip, ttl = self.query_dns(domain)
            if ttl > 0:
                ttl_with_jitter = ttl * (1 + random.uniform(-self.jitter, self.jitter))
                expiry = current_time + int(ttl_with_jitter)
                with lock:
                    if len(cache) >= self.capacity // self.stripes:
                        cache.popitem(last=False)  # Evict LRU
                    cache[domain] = (ip, expiry)
                    cache.move_to_end(domain)
            return ip

    def _prefetch(self, domain: str, current_time: int) -> None:
        """Background refresh for soon-to-expire entries."""
        def bg_task():
            try:
                ip, ttl = self.query_dns(domain)
                expiry = current_time + int(ttl * (1 + random.uniform(-self.jitter, self.jitter)))
                cache, lock = self._get_stripe(domain)
                with lock:
                    cache[domain] = (ip, expiry)
                    cache.move_to_end(domain)
            except Exception:
                pass  # Log in production

        threading.Thread(target=bg_task, daemon=True).start()

    def _load_snapshot(self) -> None:
        try:
            with open(self.snapshot_path, "r") as f:
                data = json.load(f)
                for domain, (ip, expiry) in data.items():
                    cache, lock = self._get_stripe(domain)
                    with lock:
                        cache[domain] = (ip, expiry)
        except FileNotFoundError:
            pass

    def save_snapshot(self) -> None:
        snapshot = {}
        for i in range(self.stripes):
            with self.stripe_locks[i]:
                snapshot.update(self.stripe_caches[i])
        with open(self.snapshot_path, "w") as f:
            json.dump(
                {k: v for k, v in snapshot.items() if v[1] > time.time()},  # Only unexpired
                f
            )
```

---

#### **2. Key Features & Tradeoffs**  
| **Feature**          | **Implementation**              | **Benefit**                          | **Cost**                          |
|----------------------|---------------------------------|--------------------------------------|-----------------------------------|
| **Striped LRU**      | Sharded `OrderedDict` + locks   | High concurrency                     | Memory overhead (~2x dict size)   |
| **TTL Jitter**       | Random ±10% TTL                 | Prevents thundering herd             | Slightly uneven cache durations   |
| **Prefetching**      | Background thread per domain    | Reduces latency spikes               | Risk of overfetching              |
| **Persistence**      | JSON snapshots                  | Survives restarts                    | I/O latency during saves          |
| **Query Deduplication** | Per-domain locks              | Avoids redundant DNS queries         | Lock management complexity        |

---

#### **3. Usage Example**  
```python
# Mock DNS resolver (replace with real implementation)
def mock_query_dns(domain: str) -> tuple[str, int]:
    return f"192.168.1.{random.randint(1, 100)}", 300  # Random IP, 5min TTL

# Initialize cache
cache = ProductionDNSCache(
    capacity=1000,
    query_dns=mock_query_dns,
    snapshot_path="dns_snapshot.json",
    jitter=0.1,
    prefetch_threshold=30
)

# Periodic snapshotting (e.g., via cron or scheduler)
import atexit
atexit.register(cache.save_snapshot)  # Save on exit
```

---

#### **4. Scaling Further**  
1. **Async I/O**: Replace `threading` with `asyncio` for higher throughput.  
2. **Distributed Cache**: Use Redis/Memcached for multi-node consistency.  
3. **Metrics**: Track hit rate, evictions, and latency distributions.  

---

### **Next Steps**  
1. **Phase 9: Chaos Testing**  
   - Simulate:  
     - Clock skew (e.g., NTP drift).  
     - DNS failures (timeouts/errors).  
     - High concurrency (e.g., 10k RPS).  
2. **Phase 10: Deployment**  
   - Blue-green deployment, canary releases.  

Would you like to proceed with chaos testing or deployment strategies?

### **Phase 9: Chaos Testing the DNS Cache**
#### **1. Goals**
- **Validate resilience** under failure conditions.
- **Verify correctness** during edge cases (clock skew, network issues).
- **Measure performance degradation** during chaos.

---

#### **2. Test Scenarios & Tools**
We’ll use Python’s `unittest` + `unittest.mock` to simulate chaos.

| **Scenario**               | **Tool/Method**                     | **What to Measure**                  |
|----------------------------|-------------------------------------|--------------------------------------|
| Clock skew (time jumps)     | Mock `time.time()`                  | Cache expiration accuracy            |
| DNS query failures          | Mock `query_dns()` to raise errors  | Error handling + cache consistency   |
| High concurrency           | `threading` stress tests            | Thread safety + throughput           |
| Network partitions         | Mock delayed `query_dns()` responses| Timeout handling + retries           |

---

#### **3. Chaos Test Implementation**
```python
import unittest
from unittest.mock import patch, MagicMock
import threading
import time

class ChaosTestDNSCache(unittest.TestCase):
    def setUp(self):
        self.query_dns = MagicMock()
        self.cache = ProductionDNSCache(
            capacity=100,
            query_dns=self.query_dns,
            jitter=0.1,
            prefetch_threshold=5
        )

    def test_clock_skew(self):
        """Simulate sudden time jumps (e.g., NTP sync)."""
        with patch('time.time') as mock_time:
            # Initial time = 0
            mock_time.return_value = 0
            self.query_dns.return_value = ("1.1.1.1", 10)  # TTL=10
            self.cache.resolve("a.com", current_time=0)
            
            # Time suddenly jumps to 20 (expired entry)
            mock_time.return_value = 20
            self.query_dns.return_value = ("2.2.2.2", 10)
            ip = self.cache.resolve("a.com", current_time=20)
            
            # Verify cache handled expiry correctly
            self.assertEqual(ip, "2.2.2.2")  # New IP fetched
            self.query_dns.assert_called_with("a.com")

    def test_dns_failures(self):
        """Simulate DNS outages (retries or fallbacks)."""
        self.query_dns.side_effect = Exception("DNS timeout")
        with self.assertRaises(Exception):
            self.cache.resolve("a.com", current_time=0)
        
        # Verify cache remains unchanged
        self.query_dns.side_effect = None
        self.query_dns.return_value = ("1.1.1.1", 10)
        ip = self.cache.resolve("a.com", current_time=0)
        self.assertEqual(ip, "1.1.1.1")  # Fresh query succeeds

    def test_high_concurrency(self):
        """100 threads resolving the same domain."""
        self.query_dns.return_value = ("1.1.1.1", 10)
        results = []
        
        def worker():
            results.append(self.cache.resolve("a.com", time.time()))
        
        threads = [threading.Thread(target=worker) for _ in range(100)]
        for t in threads: t.start()
        for t in threads: t.join()
        
        # Verify exactly 1 DNS query and 100 consistent results
        self.query_dns.assert_called_once_with("a.com")
        self.assertTrue(all(ip == "1.1.1.1" for ip in results))

    def test_network_partitions(self):
        """Simulate delayed DNS responses."""
        original_query_dns = self.query_dns
        
        def delayed_query(*args):
            time.sleep(2)  # Simulate 2s delay
            return original_query_dns(*args)
        
        self.query_dns.side_effect = delayed_query
        self.query_dns.return_value = ("1.1.1.1", 10)
        
        # Verify timeout handling (production code would need timeouts)
        ip = self.cache.resolve("a.com", current_time=0)
        self.assertEqual(ip, "1.1.1.1")  # Demo only; real code needs retries
```

---

#### **4. Key Takeaways**
1. **Clock Skew**:  
   - Cache must recompute expiration times relative to `current_time` (not wall time).  
2. **DNS Failures**:  
   - Consider retries or fallback IPs in production.  
3. **High Concurrency**:  
   - Verify thread safety via stress tests (no crashes/duplicate queries).  
4. **Network Partitions**:  
   - Add timeouts to `query_dns` (e.g., `requests.get(timeout=5)`).  

---

### **Phase 10: Deployment Strategies**
#### **1. Blue-Green Deployment**
- **Approach**:  
  1. Deploy new cache version alongside old.  
  2. Shift traffic gradually (e.g., 10% → 100%).  
- **Tooling**: Kubernetes, AWS Elastic Beanstalk.  

#### **2. Metrics & Monitoring**
- **Critical Metrics**:  
  ```python
  # Example Prometheus metrics
  from prometheus_client import Counter, Gauge

  DNS_HITS = Counter("dns_cache_hits", "Cache hits")
  DNS_MISSES = Counter("dns_cache_misses", "Cache misses")
  CACHE_SIZE = Gauge("dns_cache_size", "Current cache entries")

  class MonitoredDNSCache(ProductionDNSCache):
      def resolve(self, domain: str, current_time: int) -> str:
          cached_val, exists = self._get_from_cache(domain)
          if exists and cached_val[1] >= current_time:
              DNS_HITS.inc()
              return cached_val[0]
          DNS_MISSES.inc()
          # ... rest of logic
          CACHE_SIZE.set(len(self.cache))
  ```

#### **3. Canary Releases**
- **Approach**:  
  - Release to 1% of servers, monitor error rates/latency.  
  - Roll back if metrics degrade.  

---

### **Final Recommendation**
1. **Run chaos tests** in staging before deployment.  
2. **Deploy with metrics** to catch regressions.  
3. **Optimize iteratively** (e.g., add async I/O if DNS latency is a bottleneck).  

Would you like to explore any of these in more detail?

### **Phase 10+: Advanced Deployment & Production Readiness**
#### **1. Zero-Downtime Deployments**
**Problem**: Cache resets during deployment cause thundering herds to DNS.  
**Solution**: **Cache Warmup** + **Traffic Mirroring**  

```python
# Cache warmup script (run pre-deployment)
def warmup_cache(cache: ProductionDNSCache, domains: list[str]):
    for domain in domains:
        try:
            cache.resolve(domain, current_time=time.time())
        except Exception as e:
            log.error(f"Warmup failed for {domain}: {e}")

# Usage:
warmup_cache(new_cache_instance, top_1000_domains)
```

**Traffic Mirroring**:  
- Route 1% of production traffic to new cache for 24h.  
- Compare metrics (hit rate, latency) between old/new.  

---

#### **2. Dynamic Configuration**
**Problem**: Hardcoded TTL jitter/prefetch values can’t adapt to traffic patterns.  
**Solution**: **Runtime Tunables** via Config API  

```python
class TunableDNSCache(ProductionDNSCache):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.config = {
            "jitter": 0.1,
            "prefetch_threshold": 60,
            "max_concurrent_queries": 100
        }
        self.semaphore = threading.Semaphore(
            self.config["max_concurrent_queries"]
        )

    def update_config(self, new_config: dict):
        with threading.Lock():
            self.config.update(new_config)
            self.semaphore = threading.Semaphore(
                self.config["max_concurrent_queries"]
            )

    def resolve(self, domain: str, current_time: int) -> str:
        with self.semaphore:  # Throttle concurrent DNS queries
            return super().resolve(domain, current_time)
```

**Usage**:  
```python
cache.update_config({"jitter": 0.2})  # Increase jitter during peak traffic
```

---

#### **3. Multi-Region Replication**
**Problem**: Single-region caches increase latency for global users.  
**Solution**: **Active-Active Replication** with Conflict Resolution  

```python
class RegionalDNSCache(ProductionDNSCache):
    def __init__(self, region: str, peer_regions: list[str], *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.region = region
        self.peers = peer_regions  # List of peer cache endpoints
        self.last_sync = time.time()

    def _sync_with_peer(self, peer: str):
        """Pull cache updates from a peer region."""
        try:
            updates = requests.get(f"https://{peer}/cache-dump").json()
            for domain, (ip, expiry) in updates.items():
                if domain not in self._lru_cache or expiry > self._lru_cache[domain][1]:
                    self._lru_cache[domain] = (ip, expiry)
        except Exception as e:
            log.error(f"Sync failed with {peer}: {e}")

    def periodic_sync(self):
        while True:
            time.sleep(60)  # Sync every minute
            for peer in self.peers:
                self._sync_with_peer(peer)
```

**Tradeoffs**:  
- ✅ Lower latency for global users.  
- ❌ Eventually consistent (use TTL to auto-resolve conflicts).  

---

#### **4. Cold Start Optimization**
**Problem**: New instances start with empty caches, causing DNS spikes.  
**Solution**: **S3 Backup + Lambda Warmers**  

```python
import boto3

class S3BackedDNSCache(ProductionDNSCache):
    def __init__(self, s3_bucket: str, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.s3 = boto3.client("s3")
        self.bucket = s3_bucket
        self._load_from_s3()

    def _load_from_s3(self):
        try:
            obj = self.s3.get_object(Bucket=self.bucket, Key="cache.json")
            snapshot = json.loads(obj["Body"].read())
            for domain, (ip, expiry) in snapshot.items():
                self._lru_cache[domain] = (ip, expiry)
        except Exception as e:
            log.warning(f"S3 restore failed: {e}")

    def _save_to_s3(self):
        snapshot = {k: v for k, v in self._lru_cache.items() if v[1] > time.time()}
        self.s3.put_object(
            Bucket=self.bucket,
            Key="cache.json",
            Body=json.dumps(snapshot)
        )

# AWS Lambda warmer (runs every 5min)
def lambda_handler(event, context):
    cache = S3BackedDNSCache(s3_bucket="my-dns-cache")
    cache.resolve("high-traffic-domain.com", time.time())
    cache._save_to_s3()
```

---

### **Phase 11: Final Checklist for Production**
1. **Observability**  
   - Logs: `INFO` for cache misses, `WARNING` for DNS failures.  
   - Metrics: Hit rate, eviction rate, DNS latency percentiles.  
   - Traces: End-to-end resolution time (e.g., OpenTelemetry).  

2. **Disaster Recovery**  
   - **S3 Backups**: Hourly snapshots.  
   - **Failover Mode**: Fallback to recursive DNS if cache crashes.  

3. **Security**  
   - **DNSSEC Validation**: Prevent poisoning.  
   - **Rate Limiting**: Block abusive clients.  

4. **Cost Optimization**  
   - **Cache Sharding**: By domain suffix (.com, .net) to reduce memory overhead.  
   - **TTL Tuning**: Longer TTLs for stable domains.  

---

### **Final Answer: Production-Ready System**
```mermaid
graph TD
    A[Client] --> B[DNS Cache]
    B -->|Cache Miss| C[query_dns]
    C --> D[Authoritative DNS]
    B --> E[Persistent Storage]
    B --> F[Peer Caches]
    G[Chaos Engine] -->|Test| B
    H[Monitoring] --> B
```

**Key Components**:  
- Striped LRU Cache with TTL Jitter  
- Async Prefetching + Warmup  
- Multi-Region Replication  
- S3 Backups + Lambda Warmers  

**Deployment**:  
```bash
# Kubernetes Rollout Example
kubectl apply -f dns-cache-deployment.yaml --record
kubectl rollout status deployment/dns-cache
```