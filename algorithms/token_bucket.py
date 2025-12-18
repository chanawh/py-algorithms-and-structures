import time


class TokenBucket:
    """
    A bucket that holds tokens. Requests need tokens to proceed.
    
    - Bucket refills over time
    - Each request takes 1 token
    - No tokens? Request is blocked!
    """
    
    def __init__(self, capacity, refill_rate):
        """
        capacity: Max tokens the bucket can hold (e.g., 10)
        refill_rate: Tokens added per second (e.g., 2 means 2 tokens/sec)
        """
        self.capacity = capacity
        self.refill_rate = refill_rate
        self.tokens = capacity  # Start full
        self.last_time = time.time()
    
    def _refill_tokens(self):
        """Add tokens based on time that has passed."""
        now = time.time()
        time_passed = now - self.last_time
        
        # Calculate how many tokens to add
        tokens_to_add = time_passed * self.refill_rate
        
        # Add tokens (but don't overflow the bucket)
        self.tokens = min(self.capacity, self.tokens + tokens_to_add)
        
        # Remember this time for next refill
        self.last_time = now
    
    def allow_request(self, tokens_needed=1):
        """
        Try to consume tokens for a request.
        
        Returns True if allowed, False if rate limited.
        """
        # First, refill any tokens we've earned
        self._refill_tokens()
        
        # Check if we have enough tokens
        if self.tokens >= tokens_needed:
            self.tokens -= tokens_needed
            return True
        else:
            return False
    
    def get_tokens(self):
        """Check how many tokens are currently available."""
        self._refill_tokens()
        return round(self.tokens, 2)
    
    def wait_time(self, tokens_needed=1):
        """Calculate how long to wait until tokens are available."""
        self._refill_tokens()
        
        if self.tokens >= tokens_needed:
            return 0  # No wait needed
        
        tokens_short = tokens_needed - self.tokens
        return round(tokens_short / self.refill_rate, 2)


# ============================================
# EXAMPLE 1: Basic Usage
# ============================================

print("=" * 50)
print("EXAMPLE 1: Basic Rate Limiting")
print("=" * 50)

# Create bucket: 5 tokens max, refills 1 token/second
bucket = TokenBucket(capacity=5, refill_rate=1)

print(f"\nStarting tokens: {bucket.get_tokens()}")
print("\nMaking 8 rapid requests:")

for i in range(8):
    allowed = bucket.allow_request()
    tokens_left = bucket.get_tokens()
    
    if allowed:
        print(f"  Request {i+1}: ✓ ALLOWED  (tokens left: {tokens_left})")
    else:
        wait = bucket.wait_time()
        print(f"  Request {i+1}: ✗ BLOCKED  (wait {wait}s)")

print("\n--- Waiting 3 seconds for refill ---")
time.sleep(3)

print(f"\nTokens after waiting: {bucket.get_tokens()}")
print("Making 2 more requests:")

for i in range(2):
    if bucket.allow_request():
        print(f"  Request {i+1}: ✓ ALLOWED")


# ============================================
# EXAMPLE 2: Different Request Costs
# ============================================

print("\n" + "=" * 50)
print("EXAMPLE 2: Requests with Different Costs")
print("=" * 50)

# Some requests might cost more tokens
bucket2 = TokenBucket(capacity=10, refill_rate=2)

print(f"\nStarting tokens: {bucket2.get_tokens()}")
print("\nDifferent request types:")

# Small request (1 token)
if bucket2.allow_request(tokens_needed=1):
    print(f"  Small request: ✓ (tokens: {bucket2.get_tokens()})")

# Medium request (3 tokens)
if bucket2.allow_request(tokens_needed=3):
    print(f"  Medium request: ✓ (tokens: {bucket2.get_tokens()})")

# Large request (5 tokens)
if bucket2.allow_request(tokens_needed=5):
    print(f"  Large request: ✓ (tokens: {bucket2.get_tokens()})")

# Another large request (5 tokens) - should fail
if bucket2.allow_request(tokens_needed=5):
    print(f"  Another large: ✓ (tokens: {bucket2.get_tokens()})")
else:
    wait = bucket2.wait_time(tokens_needed=5)
    print(f"  Another large: ✗ BLOCKED (need to wait {wait}s)")


# ============================================
# EXAMPLE 3: Simulating API Calls
# ============================================

print("\n" + "=" * 50)
print("EXAMPLE 3: Simulating API Rate Limits")
print("=" * 50)

# Imagine an API that allows 10 requests per second
api_limiter = TokenBucket(capacity=10, refill_rate=10)

def call_api(endpoint):
    """Simulate an API call with rate limiting."""
    if api_limiter.allow_request():
        return f"✓ Success: {endpoint}"
    else:
        return f"✗ Rate Limited (retry in {api_limiter.wait_time()}s)"

print("\nMaking API calls:")
endpoints = [
    "/users/1", "/users/2", "/users/3", 
    "/posts/1", "/posts/2", "/posts/3",
    "/comments/1", "/comments/2", "/comments/3",
    "/likes/1", "/likes/2", "/likes/3"
]

for endpoint in endpoints:
    result = call_api(endpoint)
    print(f"  {result}")
    time.sleep(0.05)  # Small delay between calls


# ============================================
# EXAMPLE 4: Multiple Buckets for Different Limits
# ============================================

print("\n" + "=" * 50)
print("EXAMPLE 4: Different Limits for Different Users")
print("=" * 50)

# Different user tiers with different limits
free_user = TokenBucket(capacity=5, refill_rate=1)    # 5 req/sec
premium_user = TokenBucket(capacity=20, refill_rate=5)  # 20 req/sec

print("\nFree user making 8 requests:")
for i in range(8):
    if free_user.allow_request():
        print(f"  Request {i+1}: ✓")
    else:
        print(f"  Request {i+1}: ✗ Upgrade for more!")

print("\nPremium user making 8 requests:")
for i in range(8):
    if premium_user.allow_request():
        print(f"  Request {i+1}: ✓")
    else:
        print(f"  Request {i+1}: ✗")


print("\n" + "=" * 50)
print("Try experimenting with different values!")
print("=" * 50)