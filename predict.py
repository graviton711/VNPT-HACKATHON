
from src.batch_solver import BatchSolver
import os

def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="/code/private_test.json", help="Input path")
    parser.add_argument("--output", default="submission.json", help="Output path")
    args = parser.parse_args()

    input_path = args.input
    output_path = args.output
    
    # Local fallback for testing if file doesn't exist at default path
    if not os.path.exists(input_path) and os.path.exists("public_test/test.json"):
        print(f"Warning: Input {input_path} not found. Falling back to local 'public_test/test.json'")
        input_path = "public_test/test.json"
        output_path = "output/submission.json"

    # Ensure output directory exists
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    
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
