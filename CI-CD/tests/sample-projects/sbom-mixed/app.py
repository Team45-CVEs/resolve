"""Sample project: Python code that calls the C++ module built from src/fastmath.cpp."""
import fastmath


def main():
    print(fastmath.add(2, 3))


if __name__ == "__main__":
    main()
