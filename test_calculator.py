#!/usr/bin/env python
import unittest
from calculator import perform_operation as op

class TestCalculator(unittest.TestCase):
    def test_addition(self):
        self.assertEqual(op(3.0, 2.0, '+'), 5.0)

    def test_subtraction(self):
        self.assertAlmostEqual(op(10.0, 4.9, '-'), 5.1, places=6)

    def test_multiplication(self):
        self.assertEqual(op(-2.0, -3.0, '*'), 6.0)

    def test_division_success(self):
        self.assertAlmostEqual(op(8.0, 2.0, '/'), 4.0, places=6)

    def test_division_fail_zero(self):
        with self.assertRaises(ValueError) as context:
            op(5.0, 0.0, '/')
        self.assertEqual(str(context.exception), 'Cannot divide by zero')

if __name__ == '__main__':
    unittest.main()
