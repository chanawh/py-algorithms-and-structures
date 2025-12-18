import time


class TokenBucket:
    def __init__(self, capacity, refill_rate):
        # How many tokens can fit in the bucket
        self.capacity = capacity
        
        # How many tokens to add per second
        self.refill_rate = refill_rate
        
        # Current tokens (start with full bucket)
        self.tokens = capacity
        
        # Remember when we last added tokens
        self.last_time = time.time()
    
    def allow_request(self):
        """Check if request is allowed. Returns True or False."""
        
        # Step 1: Add new tokens based on time passed
        now = time.time()
        time_passed = now - self.last_time
        new_tokens = time_passed * self.refill_rate
        
        # Add tokens but don't go over capacity
        self.tokens = min(self.capacity, self.tokens + new_tokens)
        self.last_time = now
        
        # Step 2: Try to use 1 token
        if self.tokens >= 1:
            self.tokens -= 1
            return True  # Request allowed!
        else:
            return False  # Rate limited!


# ============================================

# Create bucket: holds 5 tokens, adds 1 per second
bucket = TokenBucket(capacity=5, refill_rate=1)

print("Making 8 requests quickly:\n")

for i in range(8):
    if bucket.allow_request():
        print(f"Request {i+1}: ✓ Allowed")
    else:
        print(f"Request {i+1}: ✗ Blocked (rate limited)")

print("\n--- Waiting 3 seconds ---\n")
time.sleep(3)

print("Trying 3 more requests:\n")

for i in range(3):
    if bucket.allow_request():
        print(f"Request {i+1}: ✓ Allowed")
    else:
        print(f"Request {i+1}: ✗ Blocked")