import argparse
from typing import Tuple

def perform_operation(num1: float, num2: float, operation: str) -> float:
    """
    Perform arithmetic operations between two numbers.
    
    :param num1: First number (float)
    :param num2: Second number (float)
    :param operation: Operation to perform ('+', '-', '*', '/')
    :return: Result of the operation
    """
    if operation == '+':
        return num1 + num2
    elif operation == '-':
        return num1 - num2
    elif operation == '*':
        return num1 * num2
    elif operation == '/':
        if num2 != 0:
            return num1 / num2
        else:
            raise ValueError('Cannot divide by zero')

def main():
    parser = argparse.ArgumentParser(description='Simple Python CLI Calculator')
    parser.add_argument('num1', type=float, help='First number')
    parser.add_argument('operation', choices=['+', '-', '*', '/'], help='Operation to perform')
    parser.add_argument('num2', type=float, help='Second number')

    args = parser.parse_args()

    try:
        result = perform_operation(args.num1, args.num2, args.operation)
        print(f'Result: {result}')
    except ValueError as e:
        print(str(e))

if __name__ == '__main__':
    main()