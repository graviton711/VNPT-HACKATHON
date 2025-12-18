
from src.batch_solver import BatchSolver
import os

def main():
    # Define paths
    # Using raw strings or forward slashes
    input_path = r"e:\VSCODE_WORKSPACE\VNPT\public_test\test.json"
    output_path = r"e:\VSCODE_WORKSPACE\VNPT\output\submission.json"
    
    # Ensure output directory exists
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    print(f"Input: {input_path}")
    print(f"Output: {output_path}")
    
    # Initialize Solver
    solver = BatchSolver()
    
    # Run
    # Limit is None to run all
    solver.solve(input_path, output_path, limit=None)
    
    print("Done. Output saved to:", output_path)

if __name__ == "__main__":
    main()
