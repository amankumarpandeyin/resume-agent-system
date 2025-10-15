import time
import functools
from litellm.exceptions import RateLimitError

class RateLimitManager:
    """Manages Groq API rate limits intelligently"""
    
    def __init__(self, requests_per_minute=30, tokens_per_minute=6000):
        self.rpm_limit = requests_per_minute
        self.tpm_limit = tokens_per_minute
        self.request_times = []
        self.token_usage = []
        self.last_reset = time.time()
    
    def can_make_request(self, estimated_tokens=2000):
        """Check if we can make a request without hitting limits"""
        now = time.time()
        
        if now - self.last_reset > 60:
            self.request_times = []
            self.token_usage = []
            self.last_reset = now
        
        cutoff = now - 60
        self.request_times = [t for t in self.request_times if t > cutoff]
        self.token_usage = [(t, tokens) for t, tokens in self.token_usage if t > cutoff]
        
        # Check RPM
        if len(self.request_times) >= self.rpm_limit:
            return False, "RPM limit"
        
        # Check TPM
        total_tokens = sum(tokens for _, tokens in self.token_usage)
        if total_tokens + estimated_tokens > self.tpm_limit:
            return False, "TPM limit"
        
        return True, "OK"
    
    def record_request(self, tokens_used=2000):
        """Record a successful request"""
        now = time.time()
        self.request_times.append(now)
        self.token_usage.append((now, tokens_used))
    
    def wait_if_needed(self, estimated_tokens=2000):
        """Wait until we can make a request"""
        can_request, reason = self.can_make_request(estimated_tokens)
        
        if not can_request:
            # Calculate wait time
            if self.request_times:
                oldest_request = min(self.request_times)
                wait_time = 60 - (time.time() - oldest_request) + 1
                print(f"⏳ Rate limit protection: Waiting {wait_time:.1f}s ({reason})")
                time.sleep(max(0, wait_time))
            else:
                time.sleep(2)

# Global rate limit manager
rate_limiter = RateLimitManager()

def with_rate_limit(estimated_tokens=2000, max_retries=3):
    """Decorator to add rate limit handling to any function"""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(max_retries):
                try:
                    # Wait if needed before making request
                    rate_limiter.wait_if_needed(estimated_tokens)
                    
                    # Make the request
                    result = func(*args, **kwargs)
                    
                    # Record successful request
                    rate_limiter.record_request(estimated_tokens)
                    
                    return result
                    
                except RateLimitError as e:
                    error_msg = str(e)
                    
                    # Extract wait time from error message
                    wait_time = 10  # Default
                    if "Please try again in" in error_msg:
                        try:
                            wait_str = error_msg.split("Please try again in ")[1].split("s")[0]
                            wait_time = float(wait_str) + 1
                        except:
                            pass
                    
                    if attempt < max_retries - 1:
                        print(f"⏳ Rate limit hit. Waiting {wait_time:.1f}s (attempt {attempt + 1}/{max_retries})")
                        time.sleep(wait_time)
                    else:
                        print(f"❌ Rate limit exceeded after {max_retries} attempts")
                        raise
            
        return wrapper
    return decorator