def solve_safe_dial(input_text):
    """
    Solve the safe dial puzzle.
    Returns the number of times the dial points to 0.
    """
    rotations = input_text.strip().split('\n')
    
    position = 50  # Starting position
    count = 0      # Count how many times we hit 0
    
    print(f"Starting position: {position}")
    
    for rotation in rotations:
        direction = rotation[0]      # 'L' or 'R'
        distance = int(rotation[1:])  # Everything after first character
        
        if direction == 'L':
            position = (position - distance) % 100
        else:  # 'R'
            position = (position + distance) % 100
        
        print(f"After {rotation}: position = {position}")
        
        if position == 0:
            count += 1
            print(f"  -> Hit 0! Count is now {count}")
    
    print(f"\nFinal answer: {count}")
    return count


# Method 1: Read from file
def solve_from_file(filename):
    """Read puzzle input from a file and solve."""
    with open(filename, 'r') as f:
        input_text = f.read()
    return solve_safe_dial(input_text)


# # Method 2: Paste input directly
# example_input = """L68
# L30
# R48
# L5
# R60
# L55
# L1
# L99
# R14
# L82"""

# # Run with example
# print("=== EXAMPLE ===")
# answer = solve_safe_dial(example_input)
# print(f"\nThe password is: {answer}")

if __name__ == "__main__":
    answer = solve_from_file("./input.txt")
    print(f"\nThe password is: {answer}")