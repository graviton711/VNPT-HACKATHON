import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.utils import Executor
import time

def test_executor():
    print("Testing Executor Class...")
    
    # 1. Test Math
    code1 = "print(120 + 34)"
    print(f"\n[Test 1] Simple Math: {code1}")
    out1 = Executor.execute(code1)
    print(f"Output: {out1}")
    assert "154" in out1
    
    # 2. Test Timeout
    code2 = "import time; time.sleep(10); print('Done')"
    print(f"\n[Test 2] Timeout (Infinite Loop Simulation): {code2}")
    out2 = Executor.execute(code2, timeout=2) # 2s timeout
    print(f"Output: {out2}")
    assert "timed out" in out2
    
    # 3. Test Syntax Error
    code3 = "print('Hello"
    print(f"\n[Test 3] Syntax Error: {code3}")
    out3 = Executor.execute(code3)
    print(f"Output: {out3}")
    assert "Error" in out3
    
    # 4. Test Standard Library (math)
    code4 = "import math; print(math.sqrt(16))"
    print(f"\n[Test 4] Math Lib: {code4}")
    out4 = Executor.execute(code4)
    print(f"Output: {out4}")
    assert "4.0" in out4
    
    print("\nAll Tests Passed!")

if __name__ == "__main__":
    test_executor()
